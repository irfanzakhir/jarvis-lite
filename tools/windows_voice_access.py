import subprocess
from typing import Dict, Any

try:
    import pyautogui
except ImportError:
    pyautogui = None

class WindowsVoiceAccessTool:
    """
    Manages Windows Voice Access and corner-to-corner desktop navigation.
    Windows Voice Access allows hands-free control of every pixel, window, and grid coordinate.
    """

    @staticmethod
    def toggle_voice_access() -> Dict[str, Any]:
        """
        Toggles or starts Windows Voice Access via Win+Ctrl+S or executing voiceaccess.exe.
        """
        try:
            # 1. Try launching voiceaccess.exe
            res = subprocess.Popen("voiceaccess", shell=True)
            return {
                "success": True,
                "message": "Windows Voice Access triggered. You can now use voice numbers and grid commands across your entire screen."
            }
        except Exception:
            # 2. Fallback to Win + Ctrl + S shortcut
            if pyautogui:
                try:
                    pyautogui.hotkey("win", "ctrl", "s")
                    return {
                        "success": True,
                        "message": "Sent Win+Ctrl+S shortcut to toggle Voice Access."
                    }
                except Exception as e:
                    return {"success": False, "error": str(e)}
            return {"success": False, "error": "Could not toggle Voice Access."}

    @staticmethod
    def click_coordinate(x: int, y: int, double: bool = False) -> Dict[str, Any]:
        """
        Directly clicks any corner or coordinate of the laptop screen.
        """
        if not pyautogui:
            return {"success": False, "error": "pyautogui not installed"}

        try:
            if double:
                pyautogui.doubleClick(x, y)
            else:
                pyautogui.click(x, y)
            return {"success": True, "message": f"Clicked at coordinate ({x}, {y})."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def type_text(text: str) -> Dict[str, Any]:
        """
        Types text into the currently focused window.
        """
        if not pyautogui:
            return {"success": False, "error": "pyautogui not installed"}

        try:
            pyautogui.write(text, interval=0.02)
            return {"success": True, "message": f"Typed text into active window."}
        except Exception as e:
            return {"success": False, "error": str(e)}
