import os
import glob
import json
import subprocess
from typing import Dict, Any, Optional

class AppLauncher:
    """
    Windows Application & Protocol Launcher.
    Supports URI protocols, command aliases, and automatic Start Menu shortcut searching.
    """

    def __init__(self, aliases_path: Optional[str] = None):
        self.aliases: Dict[str, Dict[str, str]] = {}
        if aliases_path and os.path.exists(aliases_path):
            try:
                with open(aliases_path, "r", encoding="utf-8") as f:
                    self.aliases = json.load(f)
            except Exception as e:
                print(f"[AppLauncher] Error loading aliases: {e}")

    def launch(self, app_name: str) -> Dict[str, Any]:
        """
        Launches an application by name or keyword.
        """
        if not app_name or not isinstance(app_name, str) or not app_name.strip():
            return {
                "success": False,
                "app_name": str(app_name),
                "error": "No application name provided.",
                "message": "Please specify an application name to open."
            }

        clean_name = app_name.strip()
        lower_name = clean_name.lower()

        # Check for dangerous shell metacharacters to prevent command injection
        if any(ch in clean_name for ch in ["&", "|", ";", "<", ">", "^", "%", "\n", "\r", "`"]):
            return {
                "success": False,
                "app_name": app_name,
                "error": "Command injection detected: App name contains disallowed shell characters.",
                "message": "Security Warning: Application name contains invalid characters."
            }

        # 1. Check known aliases
        if lower_name in self.aliases:
            alias = self.aliases[lower_name]
            cmd = alias.get("cmd")
            app_type = alias.get("type", "shell")

            try:
                if app_type == "uri":
                    os.startfile(cmd)
                elif app_type == "voice_access":
                    try:
                        subprocess.Popen(["voiceaccess"])
                    except Exception:
                        subprocess.Popen("voiceaccess", shell=True)
                else:
                    subprocess.Popen(cmd, shell=True)
                return {
                    "success": True,
                    "app_name": app_name,
                    "message": f"Successfully launched {app_name}."
                }
            except Exception as e:
                return {
                    "success": False,
                    "app_name": app_name,
                    "error": str(e),
                    "message": f"Failed to launch {app_name}: {e}"
                }

        # 2. Search Windows Start Menu shortcuts
        matched_shortcut = self._find_start_menu_shortcut(lower_name)
        if matched_shortcut:
            try:
                os.startfile(matched_shortcut)
                return {
                    "success": True,
                    "app_name": app_name,
                    "path": matched_shortcut,
                    "message": f"Launched {os.path.basename(matched_shortcut).replace('.lnk', '')}."
                }
            except Exception as e:
                return {
                    "success": False,
                    "app_name": app_name,
                    "error": str(e),
                    "message": f"Error starting shortcut: {e}"
                }

        # 3. Direct execution fallback using safe os.startfile (Windows ShellExecute)
        try:
            os.startfile(clean_name)
            return {
                "success": True,
                "app_name": app_name,
                "message": f"Dispatched launch command for {app_name}."
            }
        except Exception as e:
            return {
                "success": False,
                "app_name": app_name,
                "error": str(e),
                "message": f"Could not find or launch application '{app_name}'."
            }

    def _find_start_menu_shortcut(self, query: str) -> Optional[str]:
        """
        Searches common Windows Start Menu directories for matching .lnk shortcuts.
        Prefers exact match first, then prefix match, then substring match.
        """
        search_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
        ]

        exact_matches = []
        prefix_matches = []
        sub_matches = []

        for base_dir in search_dirs:
            if not os.path.exists(base_dir):
                continue
            for root, _, files in os.walk(base_dir):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        name_without_ext = file[:-4].lower()
                        path = os.path.join(root, file)
                        if name_without_ext == query:
                            exact_matches.append(path)
                        elif name_without_ext.startswith(query):
                            prefix_matches.append(path)
                        elif len(query) >= 3 and query in name_without_ext:
                            sub_matches.append(path)

        if exact_matches:
            return exact_matches[0]
        if prefix_matches:
            return prefix_matches[0]
        if sub_matches:
            return sub_matches[0]

        return None
