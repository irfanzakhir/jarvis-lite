import os
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI

import time
import re

def _load_env_file():
    """
    Loads environment variables from local .env file if present.
    """
    env_paths = [".env", os.path.join(os.path.dirname(__file__), "..", ".env")]
    for path in env_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'\"")
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass

class LLMAgent:
    """
    Tier 3 Agentic LLM Client with Multi-Provider Failsafe Cascade.
    Automatically fails over between Groq, Cerebras, and OpenRouter if rate limits
    (429), timeouts, or service interruptions occur.
    """

    TOOLS_SCHEMA = [
        {
            "type": "function",
            "function": {
                "name": "execute_powershell",
                "description": "Execute a PowerShell command on the Windows host to query system info, manage processes, or inspect files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The exact PowerShell command to execute (e.g. 'Get-Process | Sort-Object CPU -Descending | Select-Object -First 5')."
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "play_music",
                "description": "Search and play a song, artist, or album on YouTube Music in the default browser.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The song title or search query (e.g. 'Bohemian Rhapsody', 'Lofi hip hop')."
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "open_app",
                "description": "Launch an application, setting, or website on Windows.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Name of the app or website (e.g. 'chrome', 'spotify', 'task manager', 'calculator')."
                        }
                    },
                    "required": ["app_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "system_control",
                "description": "Control system hardware such as volume, media keys, locking the screen, or screenshots.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["volume_up", "volume_down", "mute", "unmute", "lock_screen", "screenshot", "empty_recycle_bin", "media_playpause", "media_next"],
                            "description": "The system action to perform."
                        }
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "toggle_voice_access",
                "description": "Launch or toggle Windows Voice Access for full corner-to-corner screen grid control.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "enable": {
                            "type": "boolean",
                            "description": "True to start voice access."
                        }
                    }
                }
            }
        }
    ]

    ENV_KEY_MAP = {
        "groq": "GROQ_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "openrouter": "OPENROUTER_API_KEY"
    }

    def __init__(self, providers: Optional[List[Dict[str, Any]]] = None, temperature: float = 0.3, max_tokens: int = 1024, **kwargs):
        _load_env_file()
        self.providers_config = providers or []
        self.active_clients: List[Dict[str, Any]] = []
        self.temperature = float(kwargs.get("temperature", temperature))
        self.max_tokens = int(kwargs.get("max_tokens", max_tokens))

        # Backward compatibility for legacy single-provider kwargs
        if not self.providers_config and kwargs.get("api_key"):
            self.providers_config = [{
                "name": "custom",
                "api_key": kwargs.get("api_key"),
                "model": kwargs.get("model", "llama-3.3-70b-versatile"),
                "base_url": kwargs.get("base_url", "https://api.groq.com/openai/v1"),
                "enabled": True
            }]

        self._init_providers()

    def _init_providers(self):
        """
        Initializes OpenAI clients for all enabled providers with valid API keys.
        """
        self.active_clients = []
        for p in self.providers_config:
            if not p.get("enabled", True):
                continue

            name = p.get("name", "unknown").lower()
            env_var = self.ENV_KEY_MAP.get(name, f"{name.upper()}_API_KEY")
            raw_key = (p.get("api_key") or "").strip()
            if not raw_key or raw_key.startswith("YOUR_") or raw_key.startswith("${"):
                api_key = os.getenv(env_var, "")
            else:
                api_key = raw_key

            if not api_key:
                continue

            try:
                client = OpenAI(
                    api_key=api_key,
                    base_url=p.get("base_url"),
                    timeout=15.0
                )
                self.active_clients.append({
                    "name": name,
                    "model": p.get("model"),
                    "client": client,
                    "base_url": p.get("base_url"),
                    "cooldown_until": 0.0
                })
                print(f"[LLMAgent] Configured provider: '{name}' (model: {p.get('model')})")
            except Exception as e:
                print(f"[LLMAgent] Failed to initialize provider '{name}': {e}")

    def is_configured(self) -> bool:
        return len(self.active_clients) > 0

    def process_query(self, user_query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Sends query to the first working provider. Automatically cascades to the next
        provider if a rate limit (429) or connection error occurs.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "No LLM providers are configured with an API key. Add your free Groq, Cerebras, or OpenRouter key to config/config.yaml or environment variables.",
                "voice_reply": "Please set an API key in your configuration for Groq, Cerebras, or OpenRouter.",
                "tool_calls": []
            }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are Jarvis, an ultra-fast, intelligent Windows AI desktop assistant (Jarvis Lite: The Windows Assistant), running on Windows 11. "
                    "You have direct access to tools for PowerShell execution, playing music on YouTube Music, launching apps, "
                    "controlling volume/system keys, and starting Windows Voice Access. "
                    "Keep your verbal responses concise, witty, and natural (1-2 sentences), suitable for spoken output. "
                    "Always use the provided functions whenever the user asks to perform an action on their computer."
                )
            }
        ]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": user_query})

        last_error = None
        current_time = time.time()

        # Prioritize providers not currently in cooldown
        candidate_providers = [p for p in self.active_clients if p.get("cooldown_until", 0.0) <= current_time]
        if not candidate_providers:
            candidate_providers = self.active_clients

        # Multi-Provider Failsafe Loop
        for p in candidate_providers:
            name = p["name"]
            model = p["model"]
            client = p["client"]

            try:
                print(f"[LLMAgent] Querying provider '{name}' using model '{model}'...")
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=self.TOOLS_SCHEMA,
                    tool_choice="auto",
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=15.0
                )

                if not response.choices:
                    raise ValueError(f"No choices returned by provider '{name}'")

                choice = response.choices[0]
                message = choice.message
                tool_calls = []

                if message.tool_calls:
                    for tc in message.tool_calls:
                        try:
                            args = json.loads(tc.function.arguments)
                        except Exception:
                            args = {}
                        tool_calls.append({
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": args
                        })

                # Content and reasoning handling (OpenRouter / DeepSeek / Thinking models)
                content = message.content or ""
                reasoning = getattr(message, "reasoning", None)
                if not reasoning and hasattr(message, "model_extra") and message.model_extra:
                    reasoning = message.model_extra.get("reasoning", "")
                reasoning = reasoning or ""

                if not content.strip() and reasoning.strip():
                    content = reasoning.strip()

                # Clean thinking tokens <think>...</think> from spoken output
                clean_content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
                if not clean_content and content:
                    clean_content = content.strip()

                if tool_calls:
                    voice_reply = clean_content if clean_content else "On it."
                else:
                    voice_reply = clean_content if clean_content else "I've completed your request."

                print(f"[LLMAgent] Success from provider '{name}'!")
                return {
                    "success": True,
                    "provider": name,
                    "model": model,
                    "text": content,
                    "tool_calls": tool_calls,
                    "voice_reply": voice_reply
                }

            except Exception as e:
                p["cooldown_until"] = time.time() + 60.0
                print(f"[LLMAgent] Provider '{name}' encountered error/limit: {e}. Failing over to next provider...")
                last_error = e

        return {
            "success": False,
            "error": f"All configured providers failed. Last error: {last_error}",
            "voice_reply": "All AI providers are currently unavailable or rate-limited. Please try again shortly.",
            "tool_calls": []
        }
