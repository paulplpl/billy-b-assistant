# billy/music_visualizer.py
import time
import threading
from dataclasses import dataclass
from typing import Callable, Optional
import subprocess

import numpy as np
try:
    from .movements import move_tail, move_head, move_mouth, stop_mouth
    from .logger import logger
    MOCK_FISH=False
except: #For standalone debugging
    import logging 
    logger = logging.getLogger(__name__)
    MOCK_FISH=True
    
@dataclass
class VisualizerConfig:
    # Matches billy.ino FFT length
    audio_samples: int = 64

    # Keep real capture rate at 48kHz
    samplerate: int = 48000
    channels: int = 2

    # Read blocks of 1024 frames for low overhead
    blocksize: int = 1024

    # billy.ino timings
    OPEN_MOUTH_TIME: int = 200
    CLOSE_MOUTH_TIME: int = 100
    MAX_MOUTH_TIME: int = 1000

    FORWARD_BODY_TIME: int = 1000
    BACKWARD_BODY_TIME: int = 200
    MAX_BODY_TIME: int = 3000

    # billy.ino thresholds (you asked: keep SR=48k and "scale cutoffs accordingly"
    # In the Arduino code thresholds were compared to magnitudes, not Hz.
    # We keep these numeric thresholds the same and provide a gain to match magnitudes.
    VOCAL_FREQ_THRESHOLD: float = 800.0
    VOCAL_FREQ_MAX_THRESHOLD: float = 3500.0
    BASS_FREQ_THRESHOLD: float = 1600.0
    BASS_FREQ_MAX_THRESHOLD: float = 2500.0

    # Magnitude scaling knob: tune once so peaks cross the thresholds
    bass_gain: float = 2500.0
    voice_gain: float = 2500.0
    # Debug prints (throttled)
    debug: bool = False
    debug_every_s: float = 0.5



class LoopbackArecordReader:
    def __init__(self, frames=1024, rate=48000, channels=2, device="loop_capture"):
        self.frames = frames
        self.rate = rate
        self.channels = channels
        self.device = device
        self.proc = None
        self.stop_evt = threading.Event()

    def start(self):
        cmd = [
            "arecord",
            "-q",               # no status spam
            "-t", "raw",        # IMPORTANT: raw PCM
            "-D", self.device,
            "-f", "S16_LE",
            "-r", str(self.rate),
            "-c", str(self.channels),
        ]
        self.proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
        # Quick sanity: if it died instantly, grab stderr
        time.sleep(0.1)
        rc = self.proc.poll()
        if rc is not None:
            err = (self.proc.stderr.read() or b"").decode(errors="replace").strip()
            raise RuntimeError(f"arecord exited immediately (rc={rc}). stderr: {err}")

    def read_block(self):
        # int16: 2 bytes
        nbytes = self.frames * self.channels * 2
        buf = self.proc.stdout.read(nbytes)
        if not buf or len(buf) < nbytes:
            return None
        x = np.frombuffer(buf, dtype=np.int16).astype(np.float32) / 32768.0
        return x.reshape(self.frames, self.channels)

    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.proc = None


class BillyBassVisualizer:
    """
    Loopback-driven movement detector matching billy.ino logic:
      - Capture at 48kHz (from loop_capture via arecord)
      - Maintain a ring buffer of last 64 mono samples
      - 64-point FFT (Hamming)
      - bass = bin 1
      - vocal = bins 2..9
      - Same phase/timing logic as billy.ino

    Important integration note:
      Do NOT directly drive motors in the audio thread. Use callbacks that enqueue
      work to Billy's motor thread. For now, callbacks can print().
    """

    def __init__(
        self,
        capture_device=None,  # kept for compatibility; not used in arecord mode
        cfg: Optional[VisualizerConfig] = None,
        # Motion callbacks
        open_mouth: Optional[Callable[[], None]] = None,
        close_mouth: Optional[Callable[[], None]] = None,
        flap_head: Optional[Callable[[], None]] = None,
        flap_tail: Optional[Callable[[], None]] = None,
        stop_body: Optional[Callable[[], None]] = None,
        # Arecord source config
        arecord_device: str = "loop_capture",
    ):
        self.capture_device = capture_device
        self.arecord_device = arecord_device
        self.cfg = cfg or VisualizerConfig()

        # Option for dummy motion callbacks
        self.open_mouth = (lambda: move_mouth(speed_percent=100, duration=1, brake=True)) if not(MOCK_FISH) else (lambda: print("openMouth()"))
        self.close_mouth = (lambda: stop_mouth()) if not(MOCK_FISH) else  (lambda: print("closeMouth()"))
        self.flap_head = (lambda: move_head("on")) if not(MOCK_FISH) else (lambda: print("flapHead()"))
        self.flap_tail = (lambda: move_tail(duration=1)) if not(MOCK_FISH) else (lambda: print("flapTail()"))
        self.stop_body = (lambda: move_head("off")) if not(MOCK_FISH) else (lambda: print("stopBody()"))

        # State variables (mirrors billy.ino)
        self.talking_phase = 0
        self.body_phase = 0
        self._last_talking_phase = 0
        self._last_body_phase = 0

        self.talking_phase_switch_ts = 0
        self.body_phase_switch_ts = 0
        self.max_time_mouth_ts = 0
        self.max_time_body_ts = 0

        # Audio processing
        self._hamming = np.hamming(self.cfg.audio_samples).astype(np.float32)

        # Ring buffer for last 64 mono samples
        self._ring = np.zeros(self.cfg.audio_samples, dtype=np.float32)
        self._ring_pos = 0

        # Threading
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Reader (arecord)
        self._reader: Optional[LoopbackArecordReader] = None

        # Debug throttle
        self._last_debug = 0.0

    def _now_ms(self) -> int:
        return int(time.monotonic() * 1000)

    def _ring_push(self, mono: np.ndarray) -> None:
        if mono.shape[0] >= self.cfg.audio_samples:
            mono = mono[-self.cfg.audio_samples :]

        for v in mono:
            self._ring[self._ring_pos] = float(v)
            self._ring_pos = (self._ring_pos + 1) % self.cfg.audio_samples

    def _ring_snapshot_oldest_to_newest(self) -> np.ndarray:
        return np.roll(self._ring, -self._ring_pos).astype(np.float32, copy=False)

    def _fft_mag_64(self, samples64: np.ndarray) -> np.ndarray:
        w = samples64 * self._hamming
        spec = np.fft.rfft(w)
        return np.abs(spec).astype(np.float32)

    def _compute_bass_vocal(self, mag: np.ndarray) -> tuple[float, float]:
        bass = float(np.sum(mag[1:2]))      # bin 1 only
        vocal = float(np.sum(mag[2:10]))    # bins 2..9 inclusive
        return bass * self.cfg.bass_gain, vocal * self.cfg.voice_gain

    # ----- Phase machines (same behavior as billy.ino) -----

    def _talk_loop(self, t: int) -> None:
        if self.talking_phase == 0:
            self._last_talking_phase = 0
            return

        # Fire actions only when entering the phase
        if self.talking_phase != self._last_talking_phase:
            if self.talking_phase == 1:
                self.open_mouth()
            elif self.talking_phase == 2:
                self.close_mouth()
            self._last_talking_phase = self.talking_phase

        # Timed transitions
        if self.talking_phase == 1:
            if self.talking_phase_switch_ts + self.cfg.OPEN_MOUTH_TIME <= t:
                self.talking_phase = 2
                self.talking_phase_switch_ts = t
        elif self.talking_phase == 2:
            if self.talking_phase_switch_ts + self.cfg.CLOSE_MOUTH_TIME <= t:
                self.talking_phase = 0
                self.talking_phase_switch_ts = t

    def _move_loop(self, t: int) -> None:
        if self.body_phase == 0:
            self._last_body_phase = 0
            return

        if self.body_phase != self._last_body_phase:
            if self.body_phase == 1:
                self.flap_head()
            elif self.body_phase == 3:
                self.flap_tail()
            elif self.body_phase in (2, 4):
                self.stop_body()
            self._last_body_phase = self.body_phase

        if self.body_phase == 1:
            if self.body_phase_switch_ts + self.cfg.FORWARD_BODY_TIME <= t:
                self.body_phase = 2
                self.body_phase_switch_ts = t
        elif self.body_phase == 2:
            if self.body_phase_switch_ts + self.cfg.BACKWARD_BODY_TIME <= t:
                self.body_phase = 0
                self.body_phase_switch_ts = t
        elif self.body_phase == 3:
            if self.body_phase_switch_ts + self.cfg.FORWARD_BODY_TIME <= t:
                self.body_phase = 4
                self.body_phase_switch_ts = t
        elif self.body_phase == 4:
            if self.body_phase_switch_ts + self.cfg.BACKWARD_BODY_TIME <= t:
                self.body_phase = 0
                self.body_phase_switch_ts = t

    def _update_logic(self, bass: float, vocal: float) -> None:
        t = self._now_ms()

        self._talk_loop(t)
        self._move_loop(t)

        if vocal >= self.cfg.VOCAL_FREQ_THRESHOLD and self.talking_phase == 0:
            self.talking_phase = 1
            self.talking_phase_switch_ts = t
            self.max_time_mouth_ts = t + self.cfg.MAX_MOUTH_TIME

        elif vocal >= self.cfg.VOCAL_FREQ_MAX_THRESHOLD and t <= self.max_time_mouth_ts:
            self.talking_phase_switch_ts = t + self.cfg.OPEN_MOUTH_TIME - 10

        if bass >= self.cfg.BASS_FREQ_THRESHOLD and self.body_phase == 0:
            tail = (np.random.randint(1, 10) > 6)
            self.body_phase = 3 if tail else 1
            self.body_phase_switch_ts = t
            self.max_time_body_ts = t + self.cfg.MAX_BODY_TIME

        elif bass >= self.cfg.BASS_FREQ_MAX_THRESHOLD and t <= self.max_time_body_ts:
            self.body_phase_switch_ts = t + self.cfg.FORWARD_BODY_TIME - 10

        if self.cfg.debug:
            now = time.monotonic()
            if now - self._last_debug >= self.cfg.debug_every_s:
                self._last_debug = now
                logger.debug(f"[viz] bass={bass:.0f} vocal={vocal:.0f} talk={self.talking_phase} body={self.body_phase}")

    def _process_block(self, stereo_block: np.ndarray) -> None:
        """
        stereo_block: float32, shape (frames, 2), range [-1..1]
        """
        mono = 0.5 * (stereo_block[:, 0] + stereo_block[:, 1])

        with self._lock:
            self._ring_push(mono)
            samples64 = self._ring_snapshot_oldest_to_newest()
            mag = self._fft_mag_64(samples64)
            bass, vocal = self._compute_bass_vocal(mag)
            self._update_logic(bass, vocal)

    def _thread_main(self) -> None:
        assert self._reader is not None
        last_hb = 0.0
        while self._running:
            block = self._reader.read_block()
            if block is None:
                # If arecord died, surface the error once
                if self._reader.proc and (rc := self._reader.proc.poll()) is not None:
                    err = (self._reader.proc.stderr.read() or b"").decode(errors="replace").strip()
                    logger.error(f"[viz] arecord exited rc={rc}. stderr: {err}")
                    self._running = False
                    return

                time.sleep(0.01)
                continue

            now = time.monotonic()
            if now - last_hb > 2.0:
                last_hb = now
                rms = float(np.sqrt(np.mean(block * block)))
                logger.debug(f"[viz] alive. rms={rms:.5f}")

            self._process_block(block)

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        # Use arecord -> S16_LE so we avoid PortAudio S24_LE issues
        self._reader = LoopbackArecordReader(
            frames=self.cfg.blocksize,
            rate=self.cfg.samplerate,
            channels=self.cfg.channels,
            device=self.arecord_device,  # "loop_capture"
        )
        self._reader.start()

        self._thread = threading.Thread(target=self._thread_main, daemon=False)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._reader:
            self._reader.stop()
            self._reader = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None