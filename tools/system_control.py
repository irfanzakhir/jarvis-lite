import os
import ctypes
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import pyautogui
except ImportError:
    pyautogui = None

class SystemControl:
    """
    Controls Windows system volume, media keys, screen locking, screenshots, and system tasks.
    """

    @staticmethod
    def change_volume(direction: str, steps: int = 5) -> Dict[str, Any]:
        """
        Adjusts Windows volume up, down, mute, or unmute.
        """
        if not pyautogui:
            return {"success": False, "error": "pyautogui not installed"}

        direction = direction.lower()
        try:
            if direction in ["up", "increase"]:
                for _ in range(steps):
                    pyautogui.press("volumeup")
                return {"success": True, "message": f"Turned volume up by {steps} steps."}
            elif direction in ["down", "decrease", "lower"]:
                for _ in range(steps):
                    pyautogui.press("volumedown")
                return {"success": True, "message": f"Turned volume down by {steps} steps."}
            elif direction in ["mute", "unmute"]:
                pyautogui.press("volumemute")
                return {"success": True, "message": "Toggled volume mute."}
            else:
                return {"success": False, "error": f"Unknown volume direction '{direction}'"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def media_key(key: str) -> Dict[str, Any]:
        """
        Sends hardware media key event (playpause, nexttrack, prevtrack).
        """
        if not pyautogui:
            return {"success": False, "error": "pyautogui not installed"}

        valid_keys = {"playpause", "nexttrack", "prevtrack", "stop"}
        key_name = key.lower()
        if key_name not in valid_keys:
            key_name = "playpause"

        try:
            pyautogui.press(key_name)
            return {"success": True, "message": f"Dispatched media key: {key_name}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def lock_screen() -> Dict[str, Any]:
        """
        Locks the Windows workstation instantly.
        """
        try:
            ctypes.windll.user32.LockWorkStation()
            return {"success": True, "message": "Screen locked."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def take_screenshot(save_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Captures a desktop screenshot and saves it.
        """
        if not pyautogui:
            return {"success": False, "error": "pyautogui not installed"}

        try:
            if not save_dir:
                user_pictures = os.path.expanduser(r"~\Pictures\Screenshots")
                if os.path.exists(user_pictures):
                    save_dir = user_pictures
                else:
                    save_dir = os.path.expanduser(r"~\Pictures")
            
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(save_dir, f"Screenshot_{timestamp}.png")
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            return {
                "success": True,
                "filepath": filepath,
                "message": f"Screenshot saved to {filepath}."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def empty_recycle_bin() -> Dict[str, Any]:
        """
        Empties the Windows Recycle Bin via PowerShell.
        """
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return {"success": True, "message": "Recycle Bin emptied."}
        except Exception as e:
            return {"success": False, "error": str(e)}
