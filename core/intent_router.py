import re
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class IntentRouter:
    """
    Tier 1 & Tier 2 Zero-AI Intent Router.
    Executes common desktop commands instantly (<2ms) without consuming LLM tokens or API calls.
    """

    def __init__(self, aliases_path: Optional[str] = None):
        self.aliases: Dict[str, Dict[str, str]] = {}
        if aliases_path and os.path.exists(aliases_path):
            try:
                with open(aliases_path, "r", encoding="utf-8") as f:
                    self.aliases = json.load(f)
            except Exception as e:
                print(f"[IntentRouter] Warning loading aliases: {e}")

    def route(self, text: str) -> Dict[str, Any]:
        """
        Routes user query through Tier 1 (Regex/Direct Rules) and Tier 2 (App Resolver).
        Returns a dictionary with 'handled' (bool), 'action', 'params', and 'voice_reply'.
        If 'handled' is False, the query should be passed to Tier 3 (Agentic LLM).
        """
        clean_text = text.strip()
        lower_text = clean_text.lower()

        # -------------------------------------------------------------
        # 1. Voice Access Controls
        # -------------------------------------------------------------
        if re.search(r"\b(open|start|launch|turn on|enable)\s+(voice access|windows voice access)\b", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "toggle_voice_access",
                "params": {"enable": True},
                "voice_reply": "Starting Windows Voice Access."
            }
        if re.search(r"\b(close|stop|turn off|disable|exit)\s+(voice access|windows voice access)\b", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "toggle_voice_access",
                "params": {"enable": False},
                "voice_reply": "Stopping Windows Voice Access."
            }
        if re.match(r"^\s*(voice access|windows voice access)\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "toggle_voice_access",
                "params": {"enable": True},
                "voice_reply": "Starting Windows Voice Access."
            }

        # -------------------------------------------------------------
        # 2. YouTube Music & Music Playback
        # -------------------------------------------------------------
        music_match = re.search(r"^\s*play\s+(.*?)\s+(?:on|in)\s+(?:yt music|youtube music)\s*$", lower_text)
        if not music_match:
            music_match = re.search(r"^\s*play\s+(.*?)\s+(?:on|in)\s+youtube\s*$", lower_text)
        if not music_match:
            # e.g., "play shape of you" or "play some jazz music"
            music_match = re.search(r"^\s*play\s+(?:music\s+)?(.*?)(?:\s+music)?\s*$", lower_text)
            
        if music_match:
            song_query = music_match.group(1).strip()
            # If user said simply "play music" or "play", resume playback
            if song_query in ["", "music", "some music", "a song"]:
                return {
                    "handled": True,
                    "tier": 1,
                    "action": "media_key",
                    "params": {"key": "playpause"},
                    "voice_reply": "Resuming playback."
                }
            elif song_query and song_query not in ["song", "audio"]:
                return {
                    "handled": True,
                    "tier": 1,
                    "action": "play_music",
                    "params": {"query": song_query, "platform": "youtube_music"},
                    "voice_reply": f"Playing {song_query} on YouTube Music."
                }

        # -------------------------------------------------------------
        # 3. Media Controls (Play, Pause, Next, Prev, Stop)
        # -------------------------------------------------------------
        if re.match(r"^\s*(pause|pause music|stop music|stop)\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "media_key",
                "params": {"key": "playpause"},
                "voice_reply": "Pausing playback."
            }
        if re.match(r"^\s*(resume|resume music|play)\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "media_key",
                "params": {"key": "playpause"},
                "voice_reply": "Resuming playback."
            }
        if re.match(r"^\s*(next|next track|next song|skip)\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "media_key",
                "params": {"key": "nexttrack"},
                "voice_reply": "Skipping to next track."
            }
        if re.match(r"^\s*(previous|previous track|previous song|prev track)\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "media_key",
                "params": {"key": "prevtrack"},
                "voice_reply": "Going back to previous track."
            }

        # -------------------------------------------------------------
        # 4. Volume and System Audio Controls
        # -------------------------------------------------------------
        if re.search(r"\b(volume up|increase volume|turn up( the)? volume)\b", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "volume_change",
                "params": {"direction": "up", "steps": 5},
                "voice_reply": "Turning the volume up."
            }
        if re.search(r"\b(volume down|decrease volume|lower volume|turn down( the)? volume)\b", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "volume_change",
                "params": {"direction": "down", "steps": 5},
                "voice_reply": "Turning the volume down."
            }
        if re.search(r"^\s*(mute|mute audio|mute volume|mute the (volume|sound|audio))\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "volume_change",
                "params": {"direction": "mute"},
                "voice_reply": "Audio muted."
            }
        if re.search(r"^\s*(unmute|unmute audio|unmute volume|unmute the (volume|sound|audio))\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "volume_change",
                "params": {"direction": "unmute"},
                "voice_reply": "Audio unmuted."
            }

        # -------------------------------------------------------------
        # 5. Application Launching (Tier 1 & Tier 2)
        # -------------------------------------------------------------
        app_match = re.search(r"^\s*(?:open|launch|start)\s+(.+?)\s*$", lower_text)
        if app_match:
            target_app = app_match.group(1).strip()
            # Ignore compound requests with conjunctions that belong in Tier 3 LLM
            if not any(conj in target_app for conj in [" and ", " then ", " with ", " for ", " about "]):
                # Check against pre-configured aliases
                if target_app in self.aliases:
                    alias_info = self.aliases[target_app]
                    return {
                        "handled": True,
                        "tier": 1,
                        "action": "open_app",
                        "params": {"app_name": target_app, "cmd": alias_info.get("cmd"), "type": alias_info.get("type", "shell")},
                        "voice_reply": f"Opening {target_app}."
                    }
                
                # Direct website launching if target is a domain or URL
                if re.match(r"^(https?://|[a-zA-Z0-9-]+\.(com|org|net|io|edu|gov|co|app))", target_app):
                    return {
                        "handled": True,
                        "tier": 1,
                        "action": "open_url",
                        "params": {"url": target_app if target_app.startswith("http") else f"https://{target_app}"},
                        "voice_reply": f"Opening {target_app}."
                    }

                # Tier 2 Fallback: Pass to general application launcher
                return {
                    "handled": True,
                    "tier": 2,
                    "action": "open_app_search",
                    "params": {"app_name": target_app},
                    "voice_reply": f"Launching {target_app}."
                }

        # -------------------------------------------------------------
        # 6. Web Search
        # -------------------------------------------------------------
        search_match = re.search(r"^\s*(?:search|google|search for)\s+(.+?)\s*$", lower_text)
        if search_match:
            search_query = search_match.group(1).strip()
            return {
                "handled": True,
                "tier": 1,
                "action": "web_search",
                "params": {"query": search_query},
                "voice_reply": f"Searching for {search_query}."
            }

        # -------------------------------------------------------------
        # 7. System Utilities (Screenshot, Lock, Recycle Bin, Time)
        # -------------------------------------------------------------
        if re.search(r"^\s*(take (a )?screenshot|screenshot|capture screen)\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "take_screenshot",
                "params": {},
                "voice_reply": "Taking a screenshot."
            }
        if re.search(r"^\s*(lock (pc|computer|screen|workstation)|lock)\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "lock_screen",
                "params": {},
                "voice_reply": "Locking your PC."
            }
        if re.search(r"^\s*(empty recycle bin|clear recycle bin|empty the recycle bin)\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "empty_recycle_bin",
                "params": {},
                "voice_reply": "Emptying the Recycle Bin."
            }
        if re.search(r"\b(what('?s| is) the time|current time|time now)\b", lower_text):
            now_str = datetime.now().strftime("%I:%M %p")
            return {
                "handled": True,
                "tier": 1,
                "action": "direct_answer",
                "params": {"answer": f"The time is {now_str}."},
                "voice_reply": f"It's {now_str}."
            }
        if re.search(r"\b(what('?s| is) today'?s date|current date|what day is it)\b", lower_text):
            date_str = datetime.now().strftime("%A, %B %d, %Y")
            return {
                "handled": True,
                "tier": 1,
                "action": "direct_answer",
                "params": {"answer": f"Today is {date_str}."},
                "voice_reply": f"Today is {date_str}."
            }

        # Jarvis Identity & Greetings
        if re.search(r"\b(who are you|what('?s| is) your name|introduce yourself)\b", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "direct_answer",
                "params": {"answer": "I am Jarvis, your ultra-fast Windows AI assistant."},
                "voice_reply": "I am Jarvis, your Windows AI assistant. How may I assist you?"
            }
        if re.search(r"^\s*(hey jarvis|hello jarvis|hi jarvis|jarvis)\s*$", lower_text):
            return {
                "handled": True,
                "tier": 1,
                "action": "direct_answer",
                "params": {"answer": "Online and ready."},
                "voice_reply": "Online and ready, sir. How can I help?"
            }

        # -------------------------------------------------------------
        # Tier 3: Unhandled -> Route to Agentic LLM (Groq)
        # -------------------------------------------------------------
        return {
            "handled": False,
            "tier": 3,
            "query": clean_text
        }
