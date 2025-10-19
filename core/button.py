import asyncio
import contextlib
import threading
import time
from concurrent.futures import CancelledError

from gpiozero import Button

from . import audio, config
from .movements import move_head
from .session import BillySession


# Button and session globals
is_active = False
session_thread = None
interrupt_event = threading.Event()
session_instance: BillySession | None = None
last_button_time = 0
button_debounce_delay = 0.5  # seconds debounce

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
        print("🔁 Button pressed during active session.")
        interrupt_event.set()
        audio.stop_playback()

        if session_instance:
            try:
                print("🛑 Stopping active session...")
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
                        print("✅ Session stopped.")
                    except TimeoutError:
                        print("⚠️ Session stop timeout, forcing cleanup")
                        future.cancel()
            except Exception as e:
                print(f"⚠️ Error stopping session ({type(e)}): {e}")
            finally:
                # Always ensure cleanup
                session_instance = None
        is_active = False  # ✅ Ensure this is always set after stopping
        return

    audio.ensure_playback_worker_started(config.CHUNK_MS)
    # Clear the playback done event so session waits for wake-up sound
    audio.playback_done_event.clear()
    threading.Thread(target=audio.play_random_wake_up_clip, daemon=True).start()
    is_active = True
    interrupt_event = threading.Event()  # Fresh event for each session
    print("🎤 Button pressed. Listening...")

    def run_session():
        global session_instance, is_active
        try:
            move_head("on")
            session_instance = BillySession(interrupt_event=interrupt_event)
            session_instance.last_activity[0] = time.time()
            asyncio.run(session_instance.start())
        except Exception as e:
            print(f"⚠️ Session error: {e}")
        finally:
            move_head("off")
            is_active = False
            session_instance = None  # Clear reference
            print("🕐 Waiting for button press...")

    session_thread = threading.Thread(target=run_session, daemon=True)
    session_thread.start()


def start_loop():
    audio.detect_devices(debug=config.DEBUG_MODE)
    button.when_pressed = on_button
    print("🎦 Ready. Press button to start a voice session. Press Ctrl+C to quit.")
    print("🕐 Waiting for button press...")
    while True:
        time.sleep(0.1)
