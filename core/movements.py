import atexit
import random
import threading
import time
from threading import Lock, Thread

import lgpio
import numpy as np

from .config import BILLY_PINS, MOUTH_ARTICULATION, is_classic_billy
from .logger import logger


# === Configuration ===
USE_THIRD_MOTOR = is_classic_billy()
logger.info(f"Using third motor: {USE_THIRD_MOTOR} | Pin profile: {BILLY_PINS}", "⚙️")

# === GPIO Setup ===
h = lgpio.gpiochip_open(0)
FREQ = 10000  # PWM frequency

# -------------------------------------------------------------------
# Pin mapping by profile
# -------------------------------------------------------------------
# We normalize to three "drive" pins (MOUTH, HEAD, TAIL) and up to three
# "mates" that must be held LOW for legacy wiring (GND_1..GND_3).
MOUTH = GND_1 = HEAD = TAIL = GND_2 = GND_3 = None

if BILLY_PINS == "legacy":
    # Original wiring (backwards compatible)
    # Controller 1: IN1=HEAD, IN2=TAIL (2-motor legacy) | IN3=MOUTH, IN4=GND_1
    MOUTH = 12
    HEAD = 13
    TAIL = 6
    GND_1 = 5
    if USE_THIRD_MOTOR:
        # Classic Billy (3 motors): dedicated tail bridge on second driver
        TAIL = 19  # second driver IN1 (PWM)
        GND_2 = 6  # head mate (keep LOW)
        GND_3 = 26  # tail mate (keep LOW)
else:
    # NEW quiet wiring (mates are tied to GND in hardware)
    HEAD = 22  # pin 15
    MOUTH = 17  # pin 11
    TAIL = 27  # pin 13

# Collect all pins we actually use
motor_pins = [p for p in (MOUTH, HEAD, TAIL, GND_1, GND_2, GND_3) if p is not None]

# Claim/initialize
for pin in motor_pins:
    lgpio.gpio_claim_output(h, pin)
    lgpio.gpio_write(h, pin, 0)

# === State ===
_head_tail_lock = Lock()
_motor_watchdog_running = False
_last_flap = 0
_mouth_open_until = 0
_last_rms = 0
head_out = False

# === PWM tracking (so watchdog can see PWM activity) ===
_pwm = {pin: {"duty": 0, "since": None} for pin in motor_pins}


def set_pwm(pin: int, duty: int):
    """Start/adjust PWM on pin and remember when it went active."""
    lgpio.tx_pwm(h, pin, FREQ, int(duty))
    if duty > 0:
        _pwm[pin]["duty"] = int(duty)
        _pwm[pin]["since"] = (
            time.time() if _pwm[pin]["since"] is None else _pwm[pin]["since"]
        )
    else:
        _pwm[pin]["duty"] = 0
        _pwm[pin]["since"] = None


def clear_pwm(pin: int):
    """Stop PWM on pin and clear active since timestamp."""
    lgpio.tx_pwm(h, pin, FREQ, 0)
    _pwm[pin]["duty"] = 0
    _pwm[pin]["since"] = None


# === Motor Helpers ===
def brake_motor(pin1, pin2=None):
    """Actively stop the channel: zero PWM and drive LOW."""
    clear_pwm(pin1)
    if pin2 is not None:
        clear_pwm(pin2)
        lgpio.gpio_write(h, pin2, 0)
    lgpio.gpio_write(h, pin1, 0)


def run_motor_async(pwm_pin, low_pin=None, speed_percent=100, duration=0.3, brake=True):
    if low_pin is not None:
        lgpio.gpio_write(h, low_pin, 0)
    set_pwm(pwm_pin, int(speed_percent))
    if brake:
        threading.Timer(duration, lambda: brake_motor(pwm_pin, low_pin)).start()
    else:
        # still auto-close after duration, but just clear PWM (no active brake)
        threading.Timer(duration, lambda: clear_pwm(pwm_pin)).start()


# === Movement Functions (keep signatures/behavior) ===
def move_mouth(speed_percent, duration, brake=False):
    run_motor_async(MOUTH, GND_1, speed_percent, duration, brake)


def stop_mouth():
    brake_motor(MOUTH, GND_1)


def move_head(state="on"):
    global head_out

    def _move_head_on():
        # Ensure opposite input is LOW if sharing a bridge (2-motor cases)
        # For 3-motor "new" layout, mate is hard GND so this is a no-op.
        lgpio.gpio_write(h, TAIL, 0) if TAIL is not None else None
        set_pwm(HEAD, 80)
        time.sleep(0.5)
        set_pwm(HEAD, 100)  # stay extended

    if state == "on":
        if not head_out:
            threading.Thread(target=_move_head_on, daemon=True).start()
            head_out = True
    else:
        # Brake both sides of shared bridge where relevant
        brake_motor(HEAD, TAIL)
        head_out = False


def move_tail(duration=0.2):
    """
    Tail drive matrix:
      - legacy + classic(3): TAIL has dedicated bridge => mate = GND_3
      - legacy + modern(2):  shared with HEAD => mate = HEAD
      - new    + classic(3): dedicated channel with mate tied to GND => mate = None
      - new    + modern(2):  shared bridge with HEAD => mate = HEAD
    """
    if BILLY_PINS == "legacy":
        if USE_THIRD_MOTOR and TAIL is not None and GND_3 is not None:
            run_motor_async(TAIL, GND_3, speed_percent=80, duration=duration)
        else:
            run_motor_async(TAIL, HEAD, speed_percent=80, duration=duration)
    else:
        if USE_THIRD_MOTOR:
            run_motor_async(TAIL, None, speed_percent=80, duration=duration)
        else:
            run_motor_async(TAIL, HEAD, speed_percent=80, duration=duration)


def move_tail_async(duration=0.3):
    threading.Thread(target=move_tail, args=(duration,), daemon=True).start()


def _articulation_multiplier():
    """Return direct articulation multiplier (1 = normal, higher = slower)."""
    return max(0, min(10, float(MOUTH_ARTICULATION)))


# === Mouth Sync ===
def flap_from_pcm_chunk(
    audio, threshold=1500, min_flap_gap=0.15, chunk_ms=40, sample_rate=24000
):
    global _last_flap, _mouth_open_until, _last_rms
    now = time.time()

    if audio.size == 0:
        return

    rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
    peak = np.max(np.abs(audio))

    # Smooth out sudden fluctuations
    if '_last_rms' not in globals():
        _last_rms = rms
    alpha = 1  # smoothing factor
    rms = alpha * rms + (1 - alpha) * _last_rms
    _last_rms = rms

    # If too quiet and mouth might be open, stop motor
    if rms < threshold / 2 and now >= _mouth_open_until:
        stop_mouth()
        return

    if rms <= threshold or (now - _last_flap) < min_flap_gap:
        return

    normalized = np.clip(rms / 32768.0, 0.0, 1.0)
    dyn_range = peak / (rms + 1e-5)

    # Flap speed and duration scaling
    speed = int(np.clip(np.interp(normalized, [0.005, 0.15], [25, 100]), 25, 100))
    duration_ms = np.interp(normalized, [0.005, 0.15], [15, 70])

    duration_ms = np.clip(duration_ms, 15, chunk_ms)
    duration = duration_ms / 1000.0

    duration *= _articulation_multiplier()

    _last_flap = now
    _mouth_open_until = now + duration

    move_mouth(speed, duration, brake=False)


# === Interlude Behavior ===
def _interlude_routine():
    try:
        move_head("off")
        time.sleep(random.uniform(0.2, 2))
        flap_count = random.randint(1, 3)
        for _ in range(flap_count):
            move_tail()
            time.sleep(random.uniform(0.25, 0.9))
        if random.random() < 0.9:
            move_head("on")
            # Head movement during interlude (no logging needed)
            # Auto-turn off head after max 3 seconds to prevent getting stuck
            threading.Timer(5.0, lambda: move_head("off")).start()
    except Exception as e:
        print(f"⚠️ Interlude error: {e}")


def interlude():
    """Run head/tail interlude in a background thread if not already running."""
    if _head_tail_lock.locked():
        return
    Thread(target=lambda: _interlude_routine(), daemon=True).start()


# === Motor Watchdog (per-pin continuous activity) ===
WATCHDOG_TIMEOUT_SEC = 30  # max continuous ON time per pin
WATCHDOG_POLL_SEC = 1.0  # poll cadence


def _mate_for(pin: int):
    """
    Return the logical 'mate' input that should be LOW when 'pin' drives.
    This lets the watchdog brake a channel safely.
    """
    if pin == MOUTH:
        return GND_1
    if pin == HEAD:
        if BILLY_PINS == "legacy":
            # legacy modern shares bridge with tail
            return TAIL
        # new layout: 3-motor => mate hard GND (None); 2-motor => mate is TAIL
        return None if USE_THIRD_MOTOR else TAIL
    if pin == TAIL:
        if BILLY_PINS == "legacy":
            return GND_3 if USE_THIRD_MOTOR else HEAD
        return None if USE_THIRD_MOTOR else HEAD
    return None


def _stop_channel(pin: int):
    """Brake one channel safely (pin + its mate)."""
    mate = _mate_for(pin)
    clear_pwm(pin)
    lgpio.gpio_write(h, pin, 0)
    if mate is not None:
        clear_pwm(mate)
        lgpio.gpio_write(h, mate, 0)


def _pin_is_active(pin: int) -> bool:
    """Active if line is HIGH or PWM duty > 0."""
    try:
        if lgpio.gpio_read(h, pin) == 1:
            return True
    except Exception:
        pass
    return _pwm.get(pin, {}).get("duty", 0) > 0


def stop_all_motors():
    logger.info("Stopping all motors", "🛑")
    for pin in motor_pins:
        clear_pwm(pin)
        lgpio.gpio_write(h, pin, 0)


def is_motor_active():
    return any(_pin_is_active(pin) for pin in motor_pins)


def motor_watchdog():
    """Stop any single pin that stays active longer than WATCHDOG_TIMEOUT_SEC."""
    global _motor_watchdog_running
    _motor_watchdog_running = True

    # Track continuous-on start time per pin
    since_on = {pin: None for pin in motor_pins}

    while _motor_watchdog_running:
        now = time.time()
        for pin in motor_pins:
            active = _pin_is_active(pin)
            if active:
                if since_on[pin] is None:
                    since_on[pin] = now
                else:
                    if (now - since_on[pin]) >= WATCHDOG_TIMEOUT_SEC:
                        logger.warning(
                            f"Watchdog: pin {pin} active > {WATCHDOG_TIMEOUT_SEC}s → braking channel",
                            "⏱️",
                        )
                        _stop_channel(pin)
                        since_on[pin] = None
            else:
                since_on[pin] = None
        time.sleep(WATCHDOG_POLL_SEC)


def start_motor_watchdog():
    Thread(target=motor_watchdog, daemon=True).start()


def stop_motor_watchdog():
    global _motor_watchdog_running
    _motor_watchdog_running = False


# Ensure safe shutdown
atexit.register(stop_all_motors)
atexit.register(stop_motor_watchdog)
