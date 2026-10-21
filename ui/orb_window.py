import os
import json
import threading
from typing import Optional, Any
import webview

from core.orchestrator import AssistantOrchestrator
from voice.audio_recorder import AudioRecorder
from voice.stt_whisper import WhisperSTT
from voice.ears import JarvisEars

class OrbBridge:
    """
    Python-to-JavaScript API Bridge for pywebview.
    Handles events from the HTML/JS frontend.
    """

    def __init__(self, orchestrator: AssistantOrchestrator, recorder: Any = None, stt: Any = None, wake_detector=None):
        self._orchestrator = orchestrator
        self._recorder = recorder
        self._stt = stt
        self._wake_detector = wake_detector
        self._window = None
        self._pending_command = None
        self._is_listening = False
        self._listen_thread = None

        # Bind orchestrator state change to JS frontend
        self._orchestrator.on_state_change = self._on_orchestrator_state_change

    def set_wake_detector(self, wake_detector):
        self._wake_detector = wake_detector

    def set_window(self, window):
        self._window = window

    def _eval_js(self, script: str):
        if self._window:
            try:
                self._window.evaluate_js(script)
            except Exception:
                pass

    def _on_orchestrator_state_change(self, state: str):
        safe_state = json.dumps(state)
        self._eval_js(f"window.setAssistantState({safe_state});")

    def submit_query(self, query: str):
        """
        Receives text query from the HUD input box.
        """
        result = self._orchestrator.handle_query(query)
        if result.get("needs_confirmation"):
            self._pending_command = result.get("command")
        return result

    def start_listening(self):
        """
        Records voice from microphone, transcribes with Whisper, and routes query.
        Runs asynchronously in a background thread so pywebview JS bridge remains responsive.
        """
        if self._is_listening:
            return {"status": "already_listening"}

        self._is_listening = True

        def _listen_worker():
            if self._wake_detector:
                try:
                    self._wake_detector.pause()
                except Exception:
                    pass
            try:
                self._on_orchestrator_state_change("listening")
                audio = self._recorder.record_until_silence()
                if not self._is_listening:
                    self._on_orchestrator_state_change("idle")
                    return

                if audio is None:
                    self._on_orchestrator_state_change("idle")
                    err = getattr(self._recorder, "last_error", None)
                    msg = f"Audio device notice: {err}" if err else "I couldn't hear anything. Please try again."
                    self._eval_js(f"window.setSpeechBubble({json.dumps(msg)});")
                    return

                self._on_orchestrator_state_change("thinking")
                text = self._stt.transcribe(audio)
                if not text:
                    self._on_orchestrator_state_change("idle")
                    msg = json.dumps("I didn't catch that. Could you repeat?")
                    self._eval_js(f"window.setSpeechBubble({msg});")
                    return

                js_arg = json.dumps(f'You: "{text}"')
                self._eval_js(f"window.setSpeechBubble({js_arg});")

                result = self._orchestrator.handle_query(text)
                if result.get("needs_confirmation"):
                    self._pending_command = result.get("command")
                self._eval_js(f"window.onAssistantResponse({json.dumps(result)});")
            except Exception as e:
                err_msg = json.dumps(f"Error: {e}")
                self._eval_js(f"window.setSpeechBubble({err_msg});")
            finally:
                self._is_listening = False
                self._on_orchestrator_state_change("idle")
                if self._wake_detector:
                    try:
                        self._wake_detector.resume()
                    except Exception:
                        pass

        self._listen_thread = threading.Thread(target=_listen_worker, daemon=True)
        self._listen_thread.start()
        return {"status": "listening_started"}

    def stop_listening(self):
        self._is_listening = False
        if hasattr(self._recorder, "stop"):
            try:
                self._recorder.stop()
            except Exception:
                pass
        if hasattr(self._recorder, "is_recording"):
            self._recorder.is_recording = False
        self._on_orchestrator_state_change("idle")
        return {"status": "stopped"}

    def confirm_action(self, approved: bool):
        """
        Handles user approval for potentially destructive PowerShell commands.
        """
        if approved and self._pending_command:
            cmd = self._pending_command
            self._pending_command = None
            exec_res = self._orchestrator.powershell.execute(cmd, force=True)
            reply = f"Executed: {cmd}" if exec_res.get("success") else f"Failed: {exec_res.get('error')}"
            self._orchestrator._speak_reply(reply)
            return {"success": True, "reply": reply}
        else:
            self._pending_command = None
            self._orchestrator._speak_reply("Action cancelled.")
            return {"success": False, "reply": "Action cancelled."}

    def move_window(self, delta_x: int, delta_y: int):
        """
        Smoothly repositions the window via mouse drag delta.
        """
        if self._window:
            try:
                self._window.move(self._window.x + delta_x, self._window.y + delta_y)
            except Exception:
                pass

    def hide_window(self):
        if self._window:
            self._window.minimize()

class OrbWindow:
    """
    Manages the transparent, draggable, always-on-top desktop assistant window.
    """

    def __init__(self, orchestrator: AssistantOrchestrator, wake_detector=None):
        self.orchestrator = orchestrator
        self.wake_detector = wake_detector
        voice_cfg = self.orchestrator.config.get("voice") or {}
        stt_engine = str(voice_cfg.get("stt_engine", "google")).strip().lower()

        if stt_engine == "whisper":
            self.recorder = AudioRecorder()
            self.stt = WhisperSTT(
                model_size=voice_cfg.get("stt_model", "tiny.en"),
                device=voice_cfg.get("stt_device", "cpu"),
                compute_type=voice_cfg.get("stt_compute_type", "int8")
            )
            self.stt.preload(async_load=True)
        else:
            # Jarvis 2.0 technique: Google Speech Recognition with room noise calibration
            fallback_whisper = None
            if voice_cfg.get("fallback_to_whisper", True):
                fallback_whisper = WhisperSTT(
                    model_size=voice_cfg.get("stt_model", "tiny.en"),
                    device=voice_cfg.get("stt_device", "cpu"),
                    compute_type=voice_cfg.get("stt_compute_type", "int8")
                )
            self.ears = JarvisEars(
                language=voice_cfg.get("stt_language", "en-US"),
                calibration_duration=float(voice_cfg.get("calibration_duration", 1.5)),
                energy_threshold_offset=int(voice_cfg.get("energy_threshold_offset", 50)),
                timeout=float(voice_cfg.get("listen_timeout", 5.0)),
                phrase_time_limit=float(voice_cfg.get("phrase_time_limit", 15.0)),
                fallback_stt=fallback_whisper,
                calibrate_on_init=False
            )
            self.ears.preload(async_load=True)
            self.recorder = self.ears
            self.stt = self.ears

        self.bridge = OrbBridge(self.orchestrator, self.recorder, self.stt, wake_detector=self.wake_detector)
        self.window = None

    def start(self):
        """
        Creates and starts the pywebview desktop overlay window.
        """
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        index_html = os.path.join(assets_dir, "index.html")

        # Center window on screen using Windows work area (accounting for DPI scaling & taskbar)
        start_x, start_y = None, None
        try:
            import ctypes
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long)
                ]
            rect = RECT()
            # SPI_GETWORKAREA = 0x0030
            if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                work_width = rect.right - rect.left
                work_height = rect.bottom - rect.top
                start_x = rect.left + max(20, (work_width - 360) // 2)
                start_y = rect.top + max(20, (work_height - 520) // 2)
        except Exception:
            pass

        if start_x is None or start_y is None:
            try:
                import pyautogui
                sw, sh = pyautogui.size()
                start_x = max(20, (sw - 360) // 2)
                start_y = max(20, (sh - 520) // 2)
            except Exception:
                start_x, start_y = None, None

        self.window = webview.create_window(
            title="Jarvis Lite - The Windows Assistant",
            url=index_html,
            js_api=self.bridge,
            width=360,
            height=520,
            x=start_x,
            y=start_y,
            resizable=False,
            frameless=True,
            easy_drag=False,
            on_top=(self.orchestrator.config.get("assistant") or {}).get("always_on_top", True),
            background_color="#0f111c"
        )
        self.bridge.set_window(self.window)
        webview.start(debug=False)

    def restore_and_focus(self):
        if self.window:
            try:
                self.window.restore()
                self.window.show()
            except Exception:
                pass
