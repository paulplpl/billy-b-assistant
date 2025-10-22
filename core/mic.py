import subprocess

import sounddevice as sd

from . import audio as audio
from .logger import logger


def diagnose_audio_issues():
    """Diagnose common audio issues that might cause mic failures."""
    logger.info("Running audio diagnostics...", "🔍")

    try:
        # Check for processes using audio devices
        result = subprocess.run(
            ["lsof", "/dev/snd/*"], capture_output=True, text=True, timeout=5
        )
        if result.stdout:
            logger.warning("Processes using audio devices:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    logger.warning(f"  {line}")
        else:
            logger.info("No processes found using audio devices", "✅")
    except Exception as e:
        logger.warning(f"Could not check audio device usage: {e}")

    try:
        # Check ALSA status
        result = subprocess.run(
            ["cat", "/proc/asound/cards"], capture_output=True, text=True, timeout=3
        )
        if result.stdout:
            logger.info("ALSA sound cards:")
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    logger.info(f"  {line}")
    except Exception as e:
        logger.warning(f"Could not check ALSA cards: {e}")


class MicManager:
    def __init__(self):
        self.stream = None

    def start(self, callback):
        self.stop()
        try:
            self.stream = sd.InputStream(
                samplerate=audio.MIC_RATE,
                device=audio.MIC_DEVICE_INDEX,
                channels=audio.MIC_CHANNELS,
                dtype='int16',
                blocksize=audio.CHUNK_SIZE,
                callback=callback,
            )
            self.stream.start()
        except Exception as e:
            # If device-specific opening fails, try with default device
            if audio.MIC_DEVICE_INDEX is not None:
                logger.warning(
                    f"Failed to open mic with device {audio.MIC_DEVICE_INDEX}, trying default device..."
                )
                try:
                    self.stream = sd.InputStream(
                        samplerate=audio.MIC_RATE,
                        device=None,  # Use default device
                        channels=audio.MIC_CHANNELS,
                        dtype='int16',
                        blocksize=audio.CHUNK_SIZE,
                        callback=callback,
                    )
                    self.stream.start()
                    logger.success("Mic opened with default device")
                except Exception as fallback_error:
                    logger.error(f"Fallback mic open also failed: {fallback_error}")
                    # For ALSA device unavailable errors, provide more helpful error message
                    if "Device unavailable" in str(e):
                        logger.error("ALSA device unavailable. This usually means:")
                        logger.error("1. Another process is using the audio device")
                        logger.error("2. Audio driver needs to be reset")
                        logger.error("3. Hardware connection issue")
                        diagnose_audio_issues()
                    raise e  # Re-raise original error
            else:
                raise e

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                print(f"⚠️ Error closing mic stream: {e}")
            self.stream = None
