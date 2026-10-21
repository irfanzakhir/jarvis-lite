import threading
from typing import Callable, Optional

try:
    import keyboard
    _keyboard_available = True
except ImportError:
    _keyboard_available = False

class HotkeyManager:
    """
    Listens for the global summoning hotkey (default: Ctrl+Shift+A).
    """

    def __init__(self, hotkey: str = "ctrl+shift+a", on_trigger: Optional[Callable] = None):
        self.hotkey = hotkey
        self.on_trigger = on_trigger
        self.is_running = False

    def start(self):
        if not _keyboard_available:
            print("[HotkeyManager] keyboard library is not available.")
            return

        def _listener():
            self.is_running = True
            try:
                keyboard.add_hotkey(self.hotkey, self._handle_press)
                keyboard.wait()
            except Exception as e:
                print(f"[HotkeyManager] Hotkey error: {e}")

        threading.Thread(target=_listener, daemon=True).start()
        print(f"[HotkeyManager] Global hotkey registered: '{self.hotkey}'")

    def _handle_press(self):
        # Dispatch in background thread so we never block Windows WH_KEYBOARD_LL hook callback
        if self.on_trigger:
            threading.Thread(target=self._safe_trigger, daemon=True).start()

    def _safe_trigger(self):
        try:
            if self.on_trigger:
                self.on_trigger()
        except Exception as e:
            print(f"[HotkeyManager] Error in hotkey trigger: {e}")

    def stop(self):
        self.is_running = False
        if _keyboard_available:
            try:
                keyboard.remove_hotkey(self.hotkey)
            except Exception:
                pass
