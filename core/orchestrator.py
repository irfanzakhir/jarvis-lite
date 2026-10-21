import os
import yaml
from typing import Dict, Any, Callable, Optional, List

from core.intent_router import IntentRouter
from core.llm_agent import LLMAgent
from tools.powershell_tool import PowerShellTool
from tools.web_music_tool import WebMusicTool
from tools.app_launcher import AppLauncher
from tools.system_control import SystemControl
from tools.windows_voice_access import WindowsVoiceAccessTool
from voice.tts_edge import EdgeTTSVoice

class AssistantOrchestrator:
    """
    Central Controller for the Windows AI Assistant.
    Coordinates the Zero-AI router, LLM agent, OS automation tools, Voice I/O, and UI state.
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

        # Initialize tools
        aliases_path = "config/app_aliases.json"
        self.router = IntentRouter(aliases_path=aliases_path)
        ps_cfg = self.config.get("powershell") or {}
        self.powershell = PowerShellTool(
            safe_mode=ps_cfg.get("safe_mode", True),
            timeout=ps_cfg.get("timeout_seconds", 30)
        )
        self.web_music = WebMusicTool()
        self.app_launcher = AppLauncher(aliases_path=aliases_path)
        self.system_control = SystemControl()
        self.voice_access = WindowsVoiceAccessTool()

        # Initialize LLM Agent with Multi-Provider Failsafe Cascade
        llm_cfg = self.config.get("llm") or {}
        providers_list = llm_cfg.get("providers") or []
        if not providers_list:
            providers_list = [{
                "name": "groq",
                "api_key": llm_cfg.get("api_key") or os.getenv("GROQ_API_KEY"),
                "model": llm_cfg.get("model", "llama-3.3-70b-versatile"),
                "base_url": llm_cfg.get("base_url", "https://api.groq.com/openai/v1"),
                "enabled": True
            }]
        self.llm_agent = LLMAgent(
            providers=providers_list,
            temperature=llm_cfg.get("temperature", 0.3),
            max_tokens=llm_cfg.get("max_tokens", 1024)
        )

        # Initialize Voice TTS
        voice_cfg = self.config.get("voice") or {}
        self.tts = EdgeTTSVoice(
            voice=voice_cfg.get("tts_voice", "en-US-ChristopherNeural"),
            rate=voice_cfg.get("tts_rate", "+0%"),
            volume=voice_cfg.get("tts_volume", "+0%")
        )
        self.tts_enabled = voice_cfg.get("tts_enabled", True)

        # State callback to notify the Orb UI
        self.on_state_change: Optional[Callable[[str], None]] = None
        self.conversation_history: List[Dict[str, str]] = []

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[Orchestrator] Error reading config: {e}")
        return {}

    def set_state(self, state: str):
        """
        Updates assistant state (idle, listening, thinking, speaking, executing).
        """
        if self.on_state_change:
            try:
                self.on_state_change(state)
            except Exception as e:
                print(f"[Orchestrator] Error notifying UI state: {e}")

    def handle_query(self, user_text: str) -> Dict[str, Any]:
        """
        Main query handler. Applies Tier 1/2 Zero-AI rules first, falls back to Tier 3 LLM.
        """
        if not user_text or not user_text.strip():
            return {"status": "empty"}

        user_query = user_text.strip()
        print(f"[Orchestrator] User Query: {user_query}")
        self.set_state("thinking")

        # Step 1: Check Zero-AI Intent Router
        route_result = self.router.route(user_query)

        if route_result.get("handled"):
            tier = route_result.get("tier", 1)
            action = route_result.get("action")
            params = route_result.get("params", {})
            voice_reply = route_result.get("voice_reply", "Done.")

            print(f"[Orchestrator] Tier {tier} Deterministic Hit: {action} ({params})")
            exec_result = self._dispatch_action(action, params)

            # Speak voice response
            self._speak_reply(voice_reply)

            return {
                "handled": True,
                "tier": tier,
                "action": action,
                "params": params,
                "execution": exec_result,
                "reply": voice_reply
            }

        # Step 2: Unmatched query -> Tier 3 Agentic LLM (Groq)
        print(f"[Orchestrator] Tier 3 LLM Routing required for: {user_query}")
        self.set_state("thinking")

        llm_response = self.llm_agent.process_query(
            user_query=user_query,
            conversation_history=self.conversation_history[-6:]
        )

        if not llm_response.get("success"):
            err_msg = llm_response.get("error", "Error contacting AI service.")
            voice_reply = llm_response.get("voice_reply", "I encountered an error.")
            self._speak_reply(voice_reply)
            return {
                "handled": False,
                "tier": 3,
                "error": err_msg,
                "reply": voice_reply
            }

        # Save to conversation memory
        self.conversation_history.append({"role": "user", "content": user_query})

        tool_calls = llm_response.get("tool_calls", [])
        tool_results = []

        if tool_calls:
            self.set_state("executing")
            for tc in tool_calls:
                call_name = tc.get("name")
                call_args = tc.get("arguments", {})
                print(f"[Orchestrator] Agentic Tool Call: {call_name}({call_args})")
                res = self._dispatch_tool_call(call_name, call_args)
                tool_results.append({"name": call_name, "args": call_args, "result": res})

        voice_reply = llm_response.get("voice_reply", "Task completed.")
        self.conversation_history.append({"role": "assistant", "content": voice_reply})

        self._speak_reply(voice_reply)

        return {
            "handled": True,
            "tier": 3,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "reply": voice_reply
        }

    def _dispatch_action(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes internal action from Tier 1/2 router.
        """
        self.set_state("executing")
        try:
            if action == "open_app":
                app_name = params.get("app_name")
                return self.app_launcher.launch(app_name or "")
            elif action == "open_app_search":
                return self.app_launcher.launch(params.get("app_name") or "")
            elif action == "open_url":
                return self.web_music.open_url(params.get("url") or "")
            elif action == "play_music":
                query = params.get("query", "")
                return self.web_music.play_youtube_music(query)
            elif action == "web_search":
                return self.web_music.search_web(params.get("query", ""))
            elif action == "volume_change":
                direction = params.get("direction", "up")
                steps = params.get("steps", 5)
                return self.system_control.change_volume(direction, steps)
            elif action == "media_key":
                return self.system_control.media_key(params.get("key", "playpause"))
            elif action == "toggle_voice_access":
                return self.voice_access.toggle_voice_access()
            elif action == "take_screenshot":
                return self.system_control.take_screenshot()
            elif action == "lock_screen":
                return self.system_control.lock_screen()
            elif action == "empty_recycle_bin":
                return self.system_control.empty_recycle_bin()
            elif action == "direct_answer":
                return {"success": True, "answer": params.get("answer")}
            return {"success": False, "error": f"Unknown action {action}"}
        except Exception as e:
            print(f"[Orchestrator] Error executing action '{action}': {e}")
            return {"success": False, "error": str(e)}

    def _dispatch_tool_call(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes tool calls generated by LLM agent.
        """
        try:
            if name == "execute_powershell":
                cmd = args.get("command", "")
                return self.powershell.execute(cmd)
            elif name == "play_music":
                return self.web_music.play_youtube_music(args.get("query", ""))
            elif name == "open_app":
                return self.app_launcher.launch(args.get("app_name", ""))
            elif name == "system_control":
                action = args.get("action")
                if action == "volume_up":
                    return self.system_control.change_volume("up")
                elif action == "volume_down":
                    return self.system_control.change_volume("down")
                elif action in ["mute", "unmute"]:
                    return self.system_control.change_volume(action)
                elif action == "lock_screen":
                    return self.system_control.lock_screen()
                elif action == "screenshot":
                    return self.system_control.take_screenshot()
                elif action == "empty_recycle_bin":
                    return self.system_control.empty_recycle_bin()
                elif action in ["media_playpause", "media_next"]:
                    return self.system_control.media_key("playpause" if action == "media_playpause" else "nexttrack")
            elif name == "toggle_voice_access":
                return self.voice_access.toggle_voice_access()

            return {"success": False, "error": f"Unhandled tool {name}"}
        except Exception as e:
            print(f"[Orchestrator] Error executing tool '{name}': {e}")
            return {"success": False, "error": str(e)}

    def _speak_reply(self, text: str):
        """
        Speaks the response using Edge-TTS if voice is enabled.
        """
        if self.tts_enabled and text:
            self.set_state("speaking")
            self.tts.speak(
                text=text,
                on_start=lambda: self.set_state("speaking"),
                on_finish=lambda: self.set_state("idle"),
                block=False
            )
        else:
            self.set_state("idle")
