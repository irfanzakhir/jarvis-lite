"""
Google Speech Recognition STT Module (Jarvis 2.0 Technique).
Wraps JarvisEars for pluggable STT engine usage.
"""

from voice.ears import JarvisEars

GoogleSTT = JarvisEars
__all__ = ["GoogleSTT", "JarvisEars"]
