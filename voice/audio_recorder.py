import numpy as np
import time
import io
import wave
from typing import Optional, Tuple, Union, Any

try:
    import speech_recognition as sr
    _sr_available = True
except ImportError:
    sr = None
    _sr_available = False

try:
    import sounddevice as sd
    _sd_available = True
except ImportError:
    _sd_available = False

class AudioRecorder:
    """
    Microphone audio capture utility with simple silence detection (VAD).
    Optimized for fast local voice input on laptop hardware.
    """

    def __init__(self, sample_rate: int = 16000, silence_threshold: float = 0.008, silence_duration: float = 1.2):
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.is_recording = False
        self.last_error: Optional[str] = None

    def record_until_silence(self, max_seconds: float = 10.0, timeout: float = 4.0) -> Optional[np.ndarray]:
        """
        Records from microphone until silence is detected after user speaks.
        Returns float32 audio numpy array normalized to [-1.0, 1.0].
        """
        self.last_error = None
        if not _sd_available:
            self.last_error = "sounddevice library is not available"
            print(f"[AudioRecorder] {self.last_error}")
            return None

        chunk_size = int(self.sample_rate * 0.1) # 100ms chunks
        chunks = []
        has_spoken = False
        silence_start = None
        start_time = time.time()

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
                self.is_recording = True
                while self.is_recording:
                    chunk, _ = stream.read(chunk_size)
                    audio_data = chunk.flatten()
                    chunks.append(audio_data)

                    # Compute RMS volume
                    rms = np.sqrt(np.mean(audio_data ** 2))

                    current_time = time.time()
                    elapsed = current_time - start_time

                    if rms > self.silence_threshold:
                        has_spoken = True
                        silence_start = None
                    elif has_spoken:
                        if silence_start is None:
                            silence_start = current_time
                        elif current_time - silence_start >= self.silence_duration:
                            # Silence reached after speech
                            break

                    # Timeout if user hasn't started speaking
                    if not has_spoken and elapsed > timeout:
                        break

                    # Maximum safety duration
                    if elapsed > max_seconds:
                        break

        except Exception as e:
            self.last_error = str(e)
            print(f"[AudioRecorder] Error during recording: {e}")
            return None
        finally:
            self.is_recording = False

        if not chunks or not has_spoken:
            return None

        full_audio = np.concatenate(chunks)
        return full_audio

    def audio_to_wav_bytes(self, audio: Union[np.ndarray, bytes, Any]) -> bytes:
        """
        Converts float32 audio numpy array or sr.AudioData to WAV bytes with safe clipping.
        """
        if hasattr(audio, "get_wav_data"):
            return audio.get_wav_data()
        if isinstance(audio, bytes):
            return audio
        if isinstance(audio, np.ndarray):
            clipped = np.clip(audio, -1.0, 1.0)
            int_audio = np.int16(clipped * 32767)
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(int_audio.tobytes())
            return wav_io.getvalue()
        return b""
