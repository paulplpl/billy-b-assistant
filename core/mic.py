import sounddevice as sd

from . import audio as audio
from .logger import logger


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
