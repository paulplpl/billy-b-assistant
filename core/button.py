import asyncio
import contextlib
import threading
import time
from concurrent.futures import CancelledError

from gpiozero import Button

from . import audio, config
from .logger import logger
from .movements import move_head
from .session import BillySession


# Button and session globals
is_active = False
session_thread = None
interrupt_event = threading.Event()
session_instance: BillySession | None = None
last_button_time = 0
button_debounce_delay = 0.5  # seconds debounce
_session_start_lock = threading.Lock()  # Lock to prevent concurrent session starts

# Setup hardware button
button = Button(config.BUTTON_PIN, pull_up=True)


def is_billy_speaking():
    """Return True if Billy is playing audio (wake-up or response)."""
    if not audio.playback_done_event.is_set():
        return True
    return bool(not audio.playback_queue.empty())


def on_button():
    global \
        is_active, \
        session_thread, \
        interrupt_event, \
        session_instance, \
        last_button_time

    now = time.time()
    if now - last_button_time < button_debounce_delay:
        return  # Ignore very quick repeat presses (debounce)
    last_button_time = now

    if not button.is_pressed:
        return

    if is_active:
        logger.info("Button pressed during active session.", "🔁")
        interrupt_event.set()
        audio.stop_playback()

        if session_instance:
            try:
                logger.info("Stopping active session...", "🛑")
                # A concurrent.futures.CancelledError is expected here, because the last
                # thing that BillySession.stop_session does is `await asyncio.sleep`,
                # and that will raise CancelledError because it's a logical place to
                # stop.
                with contextlib.suppress(CancelledError):
                    future = asyncio.run_coroutine_threadsafe(
                        session_instance.stop_session(), session_instance.loop
                    )
                    # Add timeout to prevent hanging
                    try:
                        future.result(timeout=5.0)  # Wait up to 5 seconds
                        logger.success("Session stopped.")
                    except TimeoutError:
                        logger.warning("Session stop timeout, forcing cleanup")
                        future.cancel()
            except Exception as e:
                logger.warning(f"Error stopping session ({type(e)}): {e}")
            finally:
                # Always ensure cleanup
                session_instance = None
                # Wait for session thread to finish to ensure mic is fully closed
                if session_thread and session_thread.is_alive():
                    logger.info("Waiting for session thread to finish...", "⏳")
                    session_thread.join(timeout=2.0)
                    if session_thread.is_alive():
                        logger.warning("Session thread did not finish in time", "⚠️")
        is_active = False  # ✅ Ensure this is always set after stopping
        return

    # Use lock to prevent concurrent session starts (but allow interruption above)
    if not _session_start_lock.acquire(blocking=False):
        logger.warning("Session start already in progress, ignoring button press", "⚠️")
        return

    try:
        # Ensure previous session thread is fully finished before starting new one
        if session_thread and session_thread.is_alive():
            logger.warning("Previous session thread still running, waiting...", "⏳")
            session_thread.join(timeout=2.0)
            if session_thread.is_alive():
                logger.error(
                    "Previous session thread did not finish, aborting new session", "❌"
                )
                _session_start_lock.release()
                return

        audio.ensure_playback_worker_started(config.CHUNK_MS)
        # Clear the playback done event so session waits for wake-up sound
        audio.playback_done_event.clear()
        logger.info("🔧 playback_done_event cleared (waiting for wake-up sound)", "🔧")
        threading.Thread(target=audio.play_random_wake_up_clip, daemon=True).start()
        is_active = True
        interrupt_event = threading.Event()  # Fresh event for each session
        logger.info("Button pressed. Listening...", "🎤")

        def run_session():
            global session_instance, is_active
            try:
                move_head("on")
                session_instance = BillySession(interrupt_event=interrupt_event)
                session_instance.last_activity[0] = time.time()
                asyncio.run(session_instance.start())
            except Exception as e:
                logger.error(f"Session error: {e}")
            finally:
                move_head("off")
                is_active = False
                session_instance = None  # Clear reference
                logger.info("Waiting for button press...", "🕐")
                # Release lock when session finishes
                with contextlib.suppress(Exception):
                    _session_start_lock.release()  # Lock might already be released

        session_thread = threading.Thread(target=run_session, daemon=True)
        session_thread.start()
        # Lock will be released by the session thread when it finishes
    except Exception as e:
        # If anything goes wrong, release the lock
        logger.error(f"Error starting session: {e}")
        with contextlib.suppress(Exception):
            _session_start_lock.release()


def start_loop():
    audio.detect_devices(debug=config.DEBUG_MODE)
    button.when_pressed = on_button
    logger.info(
        "Ready. Press button to start a voice session. Press Ctrl+C to quit.", "🎦"
    )
    logger.info("Waiting for button press...", "🕐")
    while True:
        time.sleep(0.1)
