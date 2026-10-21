# voice package
from voice.ears import JarvisEars
from voice.stt_google import GoogleSTT
from voice.stt_whisper import WhisperSTT
from voice.audio_recorder import AudioRecorder
from voice.tts_edge import EdgeTTSVoice
from voice.wake_clap import DoubleClapDetector

__all__ = [
    "JarvisEars",
    "GoogleSTT",
    "WhisperSTT",
    "AudioRecorder",
    "EdgeTTSVoice",
    "DoubleClapDetector",
]
