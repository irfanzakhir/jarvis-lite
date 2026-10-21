import os
import io
import threading
from typing import Optional, Union
import numpy as np

class WhisperSTT:
    """
    Local Speech-to-Text using Faster-Whisper.
    Zero cloud API cost, 100% private, low memory footprint (~40MB RAM on 'tiny.en').
    """

    def __init__(self, model_size: str = "tiny.en", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._lock = threading.Lock()

    def _load_model(self):
        with self._lock:
            if self.model is None:
                try:
                    from faster_whisper import WhisperModel
                    self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
                except Exception as e:
                    print(f"[WhisperSTT] Error loading Faster-Whisper model: {e}")

    def preload(self, async_load: bool = True):
        """
        Warms up and loads the model into memory.
        """
        if async_load:
            threading.Thread(target=self._load_model, daemon=True).start()
        else:
            self._load_model()

    def transcribe(self, audio: Union[np.ndarray, str, bytes]) -> str:
        """
        Transcribes audio data (numpy float32 array, WAV bytes, or audio file path) to text.
        Processes in-memory without temporary disk files.
        """
        if audio is None or (isinstance(audio, (str, bytes)) and len(audio) == 0):
            return ""

        if self.model is None:
            self._load_model()
        if self.model is None:
            return ""

        try:
            if isinstance(audio, np.ndarray):
                segments, info = self.model.transcribe(audio, beam_size=1)
                text = " ".join([seg.text for seg in segments]).strip()
                return text
            elif isinstance(audio, bytes):
                # Faster-whisper supports in-memory binary streams directly
                audio_stream = io.BytesIO(audio)
                segments, info = self.model.transcribe(audio_stream, beam_size=1)
                text = " ".join([seg.text for seg in segments]).strip()
                return text
            else:
                segments, info = self.model.transcribe(audio, beam_size=1)
                text = " ".join([seg.text for seg in segments]).strip()
                return text
        except Exception as e:
            print(f"[WhisperSTT] Transcription error: {e}")
            return ""
