import os
import io
import time
import wave
import threading
from typing import Optional, Union, Any
import numpy as np

try:
    import speech_recognition as sr
    _sr_available = True
except ImportError:
    sr = None
    _sr_available = False

class JarvisEars:
    """
    Jarvis 2.0 Speech Recognition Engine.
    Ported and enhanced from Jarvis 2.0 (core/ears.py).
    
    Technique:
    - High-accuracy Google Web Speech API recognition via speech_recognition
    - Room noise calibration (adjust_for_ambient_noise)
    - Disabling continuous CPU audio polling (dynamic_energy_threshold = False)
    - Locking energy threshold above noise floor (+50 offset) to prevent false triggers
    - Automatic hardware recovery via microphone rebooting (_reboot_mic)
    - Fallback cascade to local Whisper STT on network loss / RequestError
    - Thread-safe stream management with instant stop/abort support
    - Dual compatibility: works as standalone listener (listen()) and
      pluggable audio recorder/transcriber for desktop GUI (OrbBridge)
    """

    def __init__(
        self,
        language: str = "en-US",
        calibration_duration: float = 1.5,
        energy_threshold_offset: int = 50,
        timeout: float = 5.0,
        phrase_time_limit: float = 15.0,
        fallback_stt: Any = None,
        calibrate_on_init: bool = True
    ):
        self.language = language
        self.calibration_duration = calibration_duration
        self.energy_threshold_offset = energy_threshold_offset
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.fallback_stt = fallback_stt

        self.recognizer = sr.Recognizer() if _sr_available else None
        self.microphone = None
        self.is_recording = False
        self.last_error: Optional[str] = None
        self._lock = threading.Lock()
        self._mic_lock = threading.Lock()
        self._active_source = None

        if _sr_available:
            if calibrate_on_init:
                self._init_mic()
        else:
            self.last_error = "SpeechRecognition library is not installed."
            print(f"[Ears] {self.last_error}")

    def _init_mic(self):
        """
        Initializes microphone hardware and performs ambient noise calibration.
        Technique from Jarvis 2.0:
        - Calibrates for room noise
        - Disables continuous CPU polling (dynamic_energy_threshold = False)
        - Adds energy_threshold_offset (default +50) to prevent false triggers
        """
        if not _sr_available or not self.recognizer:
            return

        with self._lock:
            try:
                self.microphone = sr.Microphone()
                with self.microphone as source:
                    print("[Ears] Calibrating for room noise...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=self.calibration_duration)
                    
                    # --- OPTIMIZATION FROM JARVIS 2.0: DISABLE CONTINUOUS CPU AUDIO POLLING ---
                    # We already calibrated above, so we don't need it wasting CPU calculating background noise continuously.
                    self.recognizer.dynamic_energy_threshold = False
                    # Lock the threshold to whatever it just calculated + offset
                    self.recognizer.energy_threshold = self.recognizer.energy_threshold + self.energy_threshold_offset
                    print(f"[Ears] Calibrated room noise. Energy threshold locked at: {self.recognizer.energy_threshold}")
            except Exception as e:
                print(f"[CRITICAL ERROR] Could not initialize microphone on startup: {e}")
                self.last_error = str(e)
                self.microphone = None

    def _reboot_mic(self):
        """
        Reboots microphone hardware stream if dropped or unavailable.
        Technique from Jarvis 2.0 with preserved offset locking.
        """
        if not _sr_available or not self.recognizer:
            return

        with self._lock:
            try:
                self.microphone = sr.Microphone()
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    self.recognizer.dynamic_energy_threshold = False
                    self.recognizer.energy_threshold = self.recognizer.energy_threshold + self.energy_threshold_offset
                time.sleep(1)
                print("[Ears] Microphone stream rebooted successfully.")
            except Exception as e:
                print(f"[ERROR] Failed to reboot microphone: {e}")
                self.last_error = str(e)
                self.microphone = None

    def preload(self, async_load: bool = True):
        """
        Warms up microphone calibration and fallback models in background.
        """
        if self.fallback_stt and hasattr(self.fallback_stt, "preload"):
            self.fallback_stt.preload(async_load=async_load)
        if not self.microphone and _sr_available:
            if async_load:
                threading.Thread(target=self._init_mic, daemon=True).start()
            else:
                self._init_mic()

    def stop(self):
        """
        Stops active recording immediately and closes the stream.
        """
        self.is_recording = False
        with self._lock:
            if self._active_source and hasattr(self._active_source, "stream") and self._active_source.stream:
                try:
                    self._active_source.stream.close()
                except Exception:
                    pass

    def listen(self, timeout: Optional[float] = None, phrase_time_limit: Optional[float] = None) -> Optional[str]:
        """
        Direct listen-and-recognize method from Jarvis 2.0.
        Listens from microphone and recognizes speech using Google Web Speech API,
        with automatic fallback to Whisper if offline.
        Returns recognized text string or None.
        """
        if not _sr_available or not self.recognizer:
            return None

        self.last_error = None

        if not self.microphone:
            print("[Ears] Microphone offline. Attempting to reconnect...")
            time.sleep(2)
            self._reboot_mic()
            if not self.microphone:
                return None

        t = timeout if timeout is not None else self.timeout
        ptl = phrase_time_limit if phrase_time_limit is not None else self.phrase_time_limit
        captured_audio = None

        with self._mic_lock:
            try:
                self.is_recording = True
                with self.microphone as source:
                    self._active_source = source
                    print("[Ears] Listening...")
                    captured_audio = self.recognizer.listen(source, timeout=t, phrase_time_limit=ptl)

            except AttributeError:
                print("[WARNING] Audio stream dropped. Rebooting microphone hardware...")
                self._reboot_mic()
                return None
            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                # If stop() was called intentionally
                if not self.is_recording:
                    return None
                print(f"[Ears] Audio capture error: {e}")
                self.last_error = str(e)
                return None
            finally:
                self._active_source = None
                self.is_recording = False

        if not captured_audio:
            return None

        try:
            print("[Ears] Recognizing...")
            text = self.recognizer.recognize_google(captured_audio, language=self.language)
            return text.strip() if text else None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[Ears] API Request failed: {e}")
            self.last_error = f"API Request failed: {e}"
            if self.fallback_stt and hasattr(self.fallback_stt, "transcribe"):
                print("[Ears] Falling back to local Whisper STT...")
                fallback_res = self.fallback_stt.transcribe(captured_audio)
                return fallback_res.strip() if fallback_res else None
            return None
        except Exception as e:
            print(f"[Ears] Unexpected recognition error: {e}")
            self.last_error = str(e)
            if self.fallback_stt and hasattr(self.fallback_stt, "transcribe"):
                print("[Ears] Falling back to local Whisper STT...")
                fallback_res = self.fallback_stt.transcribe(captured_audio)
                return fallback_res.strip() if fallback_res else None
            return None

    def record_until_silence(
        self,
        max_seconds: Optional[float] = None,
        timeout: Optional[float] = None
    ) -> Optional[Any]:
        """
        Records audio from microphone until speech phrase finishes.
        Compatible with AudioRecorder interface for OrbBridge.
        Returns sr.AudioData instance or None.
        """
        if not _sr_available or not self.recognizer:
            return None

        self.last_error = None

        if not self.microphone:
            self._reboot_mic()
            if not self.microphone:
                return None

        t = timeout if timeout is not None else self.timeout
        ptl = max_seconds if max_seconds is not None else self.phrase_time_limit

        with self._mic_lock:
            try:
                self.is_recording = True
                with self.microphone as source:
                    self._active_source = source
                    print("[Ears] Listening for speech phrase...")
                    audio = self.recognizer.listen(source, timeout=t, phrase_time_limit=ptl)
                    return audio
            except (sr.WaitTimeoutError, AttributeError):
                return None
            except Exception as e:
                # If stopped intentionally, return None cleanly
                if not self.is_recording:
                    return None
                self.last_error = str(e)
                print(f"[Ears] Recording error: {e}")
                return None
            finally:
                self._active_source = None
                self.is_recording = False

    def transcribe(self, audio: Union[Any, np.ndarray, str, bytes]) -> str:
        """
        Transcribes audio data (AudioData, numpy array, WAV bytes, or audio file path) to text
        using Google Web Speech API (with fallback to Whisper if offline/configured).
        Compatible with WhisperSTT interface.
        """
        if audio is None:
            return ""

        if isinstance(audio, (str, bytes)) and len(audio) == 0:
            return ""

        if isinstance(audio, np.ndarray) and audio.size == 0:
            return ""

        self.last_error = None

        if not _sr_available or self.recognizer is None:
            if self.fallback_stt and hasattr(self.fallback_stt, "transcribe"):
                return self.fallback_stt.transcribe(audio)
            return ""

        try:
            audio_data = None
            if isinstance(audio, sr.AudioData):
                audio_data = audio
            elif isinstance(audio, np.ndarray):
                if np.issubdtype(audio.dtype, np.floating):
                    clipped = np.clip(audio, -1.0, 1.0)
                    raw_pcm = np.int16(clipped * 32767).tobytes()
                else:
                    raw_pcm = audio.astype(np.int16).tobytes()
                audio_data = sr.AudioData(raw_pcm, 16000, 2)
            elif isinstance(audio, bytes):
                if audio.startswith(b"RIFF"):
                    with sr.AudioFile(io.BytesIO(audio)) as source:
                        audio_data = self.recognizer.record(source)
                else:
                    audio_data = sr.AudioData(audio, 16000, 2)
            elif isinstance(audio, str):
                if os.path.exists(audio):
                    with sr.AudioFile(audio) as source:
                        audio_data = self.recognizer.record(source)
                else:
                    return ""

            if audio_data is None:
                return ""

            text = self.recognizer.recognize_google(audio_data, language=self.language)
            return text.strip() if text else ""

        except sr.UnknownValueError:
            # Unintelligible speech / ambient noise
            return ""
        except sr.RequestError as e:
            print(f"[Ears] Google Speech API request error: {e}")
            self.last_error = f"API Request failed: {e}"
            if self.fallback_stt and hasattr(self.fallback_stt, "transcribe"):
                print("[Ears] Falling back to local Whisper STT...")
                return self.fallback_stt.transcribe(audio)
            return ""
        except Exception as e:
            print(f"[Ears] Transcription error: {e}")
            self.last_error = str(e)
            if self.fallback_stt and hasattr(self.fallback_stt, "transcribe"):
                return self.fallback_stt.transcribe(audio)
            return ""

    def audio_to_wav_bytes(self, audio: Union[Any, np.ndarray, bytes]) -> bytes:
        """
        Converts audio data to standard WAV bytes.
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
                wf.setframerate(16000)
                wf.writeframes(int_audio.tobytes())
            return wav_io.getvalue()
        return b""

if __name__ == "__main__":
    print("\n=======================================================")
    print("  Jarvis 2.0 Speech Recognition Module (JarvisEars)   ")
    print("=======================================================")
    ears = JarvisEars()
    print("Microphone initialized. Say a command (e.g. 'hello jarvis')...")
    result = ears.listen()
    if result:
        print(f"\n[Success] Recognized Speech: '{result}'")
    else:
        print("\n[Result] No speech recognized or timeout reached.")

