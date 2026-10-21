import os
import asyncio
import tempfile
import threading
from typing import Optional, Callable
import edge_tts

try:
    import pygame
    _pygame_available = True
except ImportError:
    _pygame_available = False

class EdgeTTSVoice:
    """
    100% Free, natural neural text-to-speech powered by Microsoft Edge's cloud engine.
    Zero robotic artifacts, zero API key required, supports multiple realistic voices.
    """

    DEFAULT_VOICE = "en-US-ChristopherNeural"

    def __init__(self, voice: str = DEFAULT_VOICE, rate: str = "+0%", volume: str = "+0%"):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self._is_speaking = False
        self._mixer_initialized = False
        self._playback_lock = threading.Lock()

    def _ensure_mixer(self):
        if _pygame_available and not self._mixer_initialized:
            try:
                pygame.mixer.init()
                self._mixer_initialized = True
            except Exception as e:
                print(f"[EdgeTTS] Pygame mixer init warning: {e}")

    def _run_async(self, coro):
        """
        Safely runs an async coroutine across threads without event loop collisions.
        """
        import sys
        if getattr(sys, "is_finalizing", lambda: False)():
            return None
        try:
            new_loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(new_loop)
                return new_loop.run_until_complete(coro)
            finally:
                try:
                    new_loop.close()
                except Exception:
                    pass
        except RuntimeError:
            if getattr(sys, "is_finalizing", lambda: False)():
                return None
            raise

    async def _generate_audio(self, text: str, output_path: str):
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume
        )
        await communicate.save(output_path)

    def speak(self, text: str, on_start: Optional[Callable] = None, on_finish: Optional[Callable] = None, block: bool = True):
        """
        Synthesizes text and plays audio with callbacks for UI synchronization.
        """
        if not text or not text.strip():
            return

        def _play_worker():
            with self._playback_lock:
                self._is_speaking = True
                if on_start:
                    try:
                        on_start()
                    except Exception:
                        pass

                temp_path = None
                try:
                    self._ensure_mixer()
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                        temp_path = tf.name

                    # Generate speech in isolated event loop
                    self._run_async(self._generate_audio(text, temp_path))

                    # Play speech
                    if _pygame_available and self._mixer_initialized:
                        pygame.mixer.music.load(temp_path)
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.wait(30)
                        pygame.mixer.music.unload()

                except (RuntimeError, Exception) as e:
                    import sys
                    if not getattr(sys, "is_finalizing", lambda: False)():
                        print(f"[EdgeTTS] Speech playback error: {e}")
                finally:
                    self._is_speaking = False
                    if on_finish:
                        try:
                            on_finish()
                        except Exception:
                            pass
                    if temp_path and os.path.exists(temp_path):
                        for _ in range(3):
                            try:
                                os.remove(temp_path)
                                break
                            except Exception:
                                import time
                                time.sleep(0.1)

        if block:
            _play_worker()
        else:
            threading.Thread(target=_play_worker, daemon=True).start()

    def is_speaking(self) -> bool:
        return self._is_speaking

    def stop(self):
        if _pygame_available and self._mixer_initialized:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self._is_speaking = False

