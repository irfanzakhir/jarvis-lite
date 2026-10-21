import time
import threading
from typing import Callable, Optional
import numpy as np

try:
    import sounddevice as sd
    _sd_available = True
except ImportError:
    _sd_available = False

try:
    import winsound
    _winsound_available = True
except ImportError:
    _winsound_available = False

class DoubleClapDetector:
    """
    Lightweight background audio listener that detects double-claps to summon the assistant.
    When a double clap is detected, it plays a pleasant wake chime and brings the assistant to the top.
    """

    def __init__(
        self,
        on_wake: Optional[Callable] = None,
        threshold: float = 0.30,
        min_gap: float = 0.18,
        max_gap: float = 0.85,
        sample_rate: int = 16000
    ):
        self.on_wake = on_wake
        self.threshold = threshold
        self.min_gap = min_gap
        self.max_gap = max_gap
        self.sample_rate = sample_rate

        self.is_running = False
        self.is_paused = False
        self._thread: Optional[threading.Thread] = None

        # Clap state tracking
        self._last_clap_time = 0.0
        self._waiting_for_second = False

    def play_wake_sound(self):
        """
        Plays a crisp, high-tech two-tone wake chime.
        """
        def _chime():
            try:
                if _winsound_available:
                    # Ascending two-tone futuristic chime (880Hz -> 1320Hz)
                    winsound.Beep(880, 80)
                    winsound.Beep(1320, 120)
                else:
                    print("\a", end="", flush=True)
            except Exception:
                try:
                    if _winsound_available:
                        winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

        threading.Thread(target=_chime, daemon=True).start()

    def start(self):
        """
        Starts the background double-clap detection listener.
        """
        if not _sd_available:
            print("[WakeClap] sounddevice is not available. Wake sound detection disabled.")
            return

        if self.is_running:
            return

        self.is_running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("[WakeClap] Double-clap wake detector activated. Clap twice to summon Jarvis.")

    def pause(self):
        """Pauses detection while voice recording is active."""
        self.is_paused = True

    def resume(self):
        """Resumes detection after voice recording completes."""
        self._last_clap_time = 0.0
        self._waiting_for_second = False
        self.is_paused = False

    def stop(self):
        """Stops the background listener."""
        self.is_running = False

    def _listen_loop(self):
        chunk_size = 512  # ~32ms chunks at 16kHz
        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32", blocksize=chunk_size) as stream:
                while self.is_running:
                    if self.is_paused:
                        if hasattr(stream, "active") and stream.active:
                            try:
                                stream.stop()
                            except Exception:
                                pass
                        time.sleep(0.05)
                        continue
                    elif hasattr(stream, "active") and not stream.active:
                        try:
                            stream.start()
                            try:
                                stream.read(chunk_size)
                            except Exception:
                                pass
                        except Exception:
                            pass

                    data, _ = stream.read(chunk_size)
                    audio = data.flatten()
                    if len(audio) == 0:
                        continue

                    # Peak amplitude and RMS energy for noise discrimination
                    peak = float(np.max(np.abs(audio)))
                    rms = float(np.sqrt(np.mean(audio ** 2))) + 1e-6
                    crest_factor = peak / rms
                    now = time.time()

                    # Check timeout if waiting for second clap
                    if self._waiting_for_second and (now - self._last_clap_time) > self.max_gap:
                        self._waiting_for_second = False

                    # Check if audio spike exceeds clap threshold with impulsive transient characteristic
                    # Claps have high peak-to-RMS crest factor (>= 2.0) or low background floor
                    is_clap_spike = (peak > self.threshold) and (crest_factor >= 2.0 or rms < (self.threshold * 0.4))

                    if is_clap_spike:
                        if not self._waiting_for_second:
                            # First clap detected
                            self._last_clap_time = now
                            self._waiting_for_second = True
                            # Brief debounce so the decay of the first clap doesn't trigger as clap 2
                            time.sleep(0.08)
                        else:
                            # Second clap candidate
                            delta = now - self._last_clap_time
                            if self.min_gap <= delta <= self.max_gap:
                                print(f"[WakeClap] Double-clap detected! (interval: {delta:.2f}s). Summoning Jarvis...")
                                self._waiting_for_second = False
                                self._last_clap_time = 0.0

                                # Play wake chime
                                self.play_wake_sound()

                                # Trigger UI wake
                                if self.on_wake:
                                    try:
                                        self.on_wake()
                                    except Exception as e:
                                        print(f"[WakeClap] Error in on_wake callback: {e}")

                                # Post-wake debounce
                                time.sleep(1.0)
                            elif delta > self.max_gap:
                                # Reset and treat this as first clap
                                self._last_clap_time = now
                                self._waiting_for_second = True
                                time.sleep(0.08)
                            elif delta < self.min_gap:
                                # Too fast: continuous noise burst or rattle.
                                # Advance last_clap_time to current spike and debounce so noise train doesn't trigger
                                self._last_clap_time = now
                                time.sleep(0.08)

        except Exception as e:
            if self.is_running:
                print(f"[WakeClap] Listener warning: {e}")
            self.is_running = False
