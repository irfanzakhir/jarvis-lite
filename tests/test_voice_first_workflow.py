import os
import unittest
import numpy as np
import yaml
from unittest.mock import MagicMock, patch

from core.orchestrator import AssistantOrchestrator
from voice.wake_clap import DoubleClapDetector
from voice.audio_recorder import AudioRecorder
from ui.orb_window import OrbBridge, OrbWindow

class TestVoiceFirstWorkflow(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(self.base_dir, "config", "config.yaml")
        self.assets_dir = os.path.join(self.base_dir, "ui", "assets")

    def test_clap_threshold_config_and_defaults(self):
        """Verify config.yaml and DoubleClapDetector defaults are adjusted to 0.30 for noise resilience."""
        with open(self.config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        asst_cfg = cfg.get("assistant", {})
        self.assertEqual(asst_cfg.get("clap_threshold"), 0.30, "config.yaml clap_threshold should be 0.30")

        # Test default DoubleClapDetector threshold
        detector = DoubleClapDetector()
        self.assertEqual(detector.threshold, 0.30, "DoubleClapDetector default threshold should be 0.30")

    def test_noise_discrimination_logic(self):
        """Verify that continuous noise (low crest factor) is rejected while impulsive claps (high crest factor) pass."""
        detector = DoubleClapDetector(threshold=0.30)

        # 1. Continuous loud background noise (e.g. fan or loud talking, peak=0.35, rms=0.25)
        # 512 samples of sine wave with amplitude 0.35
        t = np.linspace(0, 1, 512)
        continuous_noise = (0.35 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        peak_noise = float(np.max(np.abs(continuous_noise)))
        rms_noise = float(np.sqrt(np.mean(continuous_noise ** 2))) + 1e-6
        crest_noise = peak_noise / rms_noise

        is_noise_spike = (peak_noise > detector.threshold) and (crest_noise >= 2.0 or rms_noise < (detector.threshold * 0.4))
        self.assertFalse(is_noise_spike, "Continuous loud noise should NOT qualify as an impulsive clap spike")

        # 2. Impulsive clap (sharp attack, 30 samples of spike, rest silence)
        clap_audio = np.zeros(512, dtype=np.float32)
        clap_audio[100:130] = 0.65 # sharp spike exceeding 0.30 threshold
        peak_clap = float(np.max(np.abs(clap_audio)))
        rms_clap = float(np.sqrt(np.mean(clap_audio ** 2))) + 1e-6
        crest_clap = peak_clap / rms_clap

        is_clap_spike = (peak_clap > detector.threshold) and (crest_clap >= 2.0 or rms_clap < (detector.threshold * 0.4))
        self.assertTrue(is_clap_spike, "Sharp impulsive clap spike should qualify as a clap spike")

    def test_restore_and_focus_triggers_auto_listening(self):
        """Voice-first requirement: waking the assistant restores window and starts listening immediately."""
        orchestrator = MagicMock()
        orchestrator.config = {"assistant": {"always_on_top": True}}
        wake_detector = MagicMock()

        orb_window = OrbWindow(orchestrator, wake_detector=wake_detector)
        mock_window = MagicMock()
        orb_window.window = mock_window

        with patch.object(orb_window.bridge, "start_listening") as mock_start_listen:
            orb_window.restore_and_focus()
            mock_window.restore.assert_called_once()
            mock_window.show.assert_called_once()
            mock_start_listen.assert_called_once()

    def test_submit_query_cancels_active_listening(self):
        """Typing fallback requirement: submitting query stops active voice listening immediately."""
        orchestrator = MagicMock()
        orchestrator.handle_query.return_value = {"reply": "Done", "handled": True}
        recorder = MagicMock()
        stt = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt)
        bridge._is_listening = True

        with patch.object(bridge, "stop_listening", wraps=bridge.stop_listening) as mock_stop:
            res = bridge.submit_query("open calculator")
            mock_stop.assert_called_once()
            self.assertFalse(bridge._is_listening)
            orchestrator.handle_query.assert_called_once_with("open calculator")
            self.assertEqual(res.get("reply"), "Done")

    def test_audio_recorder_stop(self):
        """Verify AudioRecorder has working stop() method."""
        rec = AudioRecorder()
        self.assertFalse(rec.is_recording)
        self.assertFalse(rec._stopped)
        rec.stop()
        self.assertTrue(rec._stopped)
        self.assertFalse(rec.is_recording)

    def test_ui_mute_elements_present_in_html_and_css(self):
        """Verify Mute button elements and styles are present in HTML, CSS, and JS."""
        html_path = os.path.join(self.assets_dir, "index.html")
        css_path = os.path.join(self.assets_dir, "style.css")
        js_path = os.path.join(self.assets_dir, "orb.js")

        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        self.assertIn('id="muteBtn"', html, "index.html must contain muteBtn element")
        self.assertIn('id="muteHeaderBtn"', html, "index.html must contain muteHeaderBtn element")

        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
        self.assertIn('.mute-btn', css, "style.css must define .mute-btn")
        self.assertIn('.active-listening', css, "style.css must define .active-listening")

        with open(js_path, "r", encoding="utf-8") as f:
            js = f.read()
        self.assertIn('function muteListening', js, "orb.js must define muteListening function")
        self.assertIn('commandInput.addEventListener("focus"', js, "orb.js must mute on input focus")
        self.assertIn('commandInput.addEventListener("click"', js, "orb.js must mute on input click")
        self.assertIn('e.key === "Escape"', js, "orb.js must support Escape key to mute")
        self.assertIn('if (!hudVisible)', js, "orb.js must auto-reveal HUD when listening starts")

    def test_wake_detector_pause_and_resume_during_listening(self):
        """Verify wake detector pauses when listening starts and resumes when stopped."""
        orchestrator = MagicMock()
        recorder = MagicMock()
        recorder.record_until_silence.return_value = None
        stt = MagicMock()
        wake_detector = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)
        bridge.start_listening()

        # Stop listening
        bridge.stop_listening()
        self.assertFalse(bridge._is_listening)
        wake_detector.resume.assert_called()

    def test_hide_window_stops_active_listening(self):
        """Verify hide_window terminates active voice listening session."""
        orchestrator = MagicMock()
        recorder = MagicMock()
        stt = MagicMock()
        bridge = OrbBridge(orchestrator, recorder, stt)
        bridge._window = MagicMock()
        bridge._is_listening = True

        with patch.object(bridge, "stop_listening", wraps=bridge.stop_listening) as mock_stop:
            bridge.hide_window()
            mock_stop.assert_called_once()
            bridge._window.minimize.assert_called_once()
            self.assertFalse(bridge._is_listening)

    def test_state_change_wake_detector_synchronization(self):
        """Verify wake detector is paused during busy states and resumed on idle."""
        orchestrator = MagicMock()
        recorder = MagicMock()
        stt = MagicMock()
        wake_detector = MagicMock()
        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)

        for busy_state in ["listening", "thinking", "executing", "speaking"]:
            wake_detector.reset_mock()
            bridge._on_orchestrator_state_change(busy_state)
            wake_detector.pause.assert_called_once()
            self.assertEqual(bridge._current_state, busy_state)

        wake_detector.reset_mock()
        bridge._on_orchestrator_state_change("idle")
        wake_detector.resume.assert_called_once()
        self.assertEqual(bridge._current_state, "idle")

    def test_submit_query_preserves_thinking_state_against_worker_race(self):
        """Verify submit_query sets state without worker thread race overwriting thinking with idle."""
        orchestrator = MagicMock()
        orchestrator.handle_query.return_value = {"reply": "Handled", "handled": True}
        recorder = MagicMock()
        stt = MagicMock()
        bridge = OrbBridge(orchestrator, recorder, stt)

        bridge._is_listening = True
        bridge._current_state = "listening"

        bridge.submit_query("play music")
        self.assertFalse(bridge._is_listening)
        orchestrator.handle_query.assert_called_once_with("play music")

    def test_wake_clap_empty_audio_resilience(self):
        """Verify empty audio frames do not crash DoubleClapDetector."""
        detector = DoubleClapDetector()
        empty_audio = np.array([], dtype=np.float32)
        self.assertEqual(len(empty_audio), 0)

    def test_start_listening_executes_without_name_error(self):
        """Verify start_listening worker does not crash on time.sleep with NameError."""
        orchestrator = MagicMock()
        recorder = MagicMock()
        recorder.record_until_silence.return_value = None
        stt = MagicMock()
        wake_detector = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)
        mock_window = MagicMock()
        bridge.set_window(mock_window)

        with patch("time.sleep", return_value=None):
            bridge.start_listening()
            if bridge._listen_thread:
                bridge._listen_thread.join(timeout=1.0)

        # Ensure record_until_silence was reached without NameError
        recorder.record_until_silence.assert_called_once()
        # Ensure NameError was not sent to speech bubble
        for call_args in mock_window.evaluate_js.call_args_list:
            js_call = call_args[0][0]
            self.assertNotIn("NameError", js_call)

    def test_fast_mute_during_settle_sleep_aborts_without_recording(self):
        """Verify fast mute during settle delay immediately exits and does not call record_until_silence."""
        orchestrator = MagicMock()
        recorder = MagicMock()
        stt = MagicMock()
        wake_detector = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)

        def mute_during_sleep(seconds):
            bridge.stop_listening()

        with patch("time.sleep", side_effect=mute_during_sleep):
            bridge.start_listening()
            if bridge._listen_thread:
                bridge._listen_thread.join(timeout=1.0)

        recorder.record_until_silence.assert_not_called()
        self.assertFalse(bridge._is_listening)
        self.assertEqual(bridge._current_state, "idle")
        wake_detector.resume.assert_called()

    def test_wake_detector_resumes_on_silence_timeout(self):
        """Verify wake detector properly resumes when audio capture times out (audio is None)."""
        orchestrator = MagicMock()
        recorder = MagicMock()
        recorder.record_until_silence.return_value = None
        stt = MagicMock()
        wake_detector = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)

        with patch("time.sleep", return_value=None):
            bridge.start_listening()
            if bridge._listen_thread:
                bridge._listen_thread.join(timeout=1.0)

        self.assertFalse(bridge._is_listening)
        self.assertEqual(bridge._current_state, "idle")
        wake_detector.pause.assert_called()
        wake_detector.resume.assert_called()

    def test_wake_detector_resumes_on_unrecognized_speech(self):
        """Verify wake detector properly resumes when speech cannot be transcribed (not text)."""
        orchestrator = MagicMock()
        recorder = MagicMock()
        recorder.record_until_silence.return_value = np.zeros(16000, dtype=np.float32)
        stt = MagicMock()
        stt.transcribe.return_value = ""
        wake_detector = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)

        with patch("time.sleep", return_value=None):
            bridge.start_listening()
            if bridge._listen_thread:
                bridge._listen_thread.join(timeout=1.0)

        self.assertFalse(bridge._is_listening)
        self.assertEqual(bridge._current_state, "idle")
        wake_detector.pause.assert_called()
        wake_detector.resume.assert_called()

    def test_state_recovers_to_idle_and_wake_detector_resumes_on_stt_exception(self):
        """Verify state recovers to idle and wake detector resumes if an exception occurs during transcription."""
        orchestrator = MagicMock()
        recorder = MagicMock()
        recorder.record_until_silence.return_value = np.zeros(16000, dtype=np.float32)
        stt = MagicMock()
        stt.transcribe.side_effect = RuntimeError("Whisper model crash")
        wake_detector = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)

        with patch("time.sleep", return_value=None):
            bridge.start_listening()
            if bridge._listen_thread:
                bridge._listen_thread.join(timeout=1.0)

        self.assertFalse(bridge._is_listening)
        self.assertEqual(bridge._current_state, "idle")
        wake_detector.pause.assert_called()
        wake_detector.resume.assert_called()

    def test_state_recovers_to_idle_and_wake_detector_resumes_on_handle_query_exception(self):
        """Verify state recovers to idle and wake detector resumes if an exception occurs during query handling."""
        orchestrator = MagicMock()
        orchestrator.handle_query.side_effect = Exception("Orchestrator failed")
        recorder = MagicMock()
        recorder.record_until_silence.return_value = np.zeros(16000, dtype=np.float32)
        stt = MagicMock()
        stt.transcribe.return_value = "hello"
        wake_detector = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)

        with patch("time.sleep", return_value=None):
            bridge.start_listening()
            if bridge._listen_thread:
                bridge._listen_thread.join(timeout=1.0)

        self.assertFalse(bridge._is_listening)
        self.assertEqual(bridge._current_state, "idle")
        wake_detector.pause.assert_called()
        wake_detector.resume.assert_called()

    def test_state_recovers_to_idle_and_wake_detector_resumes_on_recorder_exception(self):
        """Verify state recovers to idle and wake detector resumes if an exception occurs during recording."""
        orchestrator = MagicMock()
        recorder = MagicMock()
        recorder.record_until_silence.side_effect = IOError("Mic disconnected")
        stt = MagicMock()
        wake_detector = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)

        with patch("time.sleep", return_value=None):
            bridge.start_listening()
            if bridge._listen_thread:
                bridge._listen_thread.join(timeout=1.0)

        self.assertFalse(bridge._is_listening)
        self.assertEqual(bridge._current_state, "idle")
        wake_detector.pause.assert_called()
        wake_detector.resume.assert_called()

    def test_rapid_restart_listening_not_killed_by_prior_thread_finally_block(self):
        """Verify that when listening is stopped and restarted while the first worker thread is unwinding,
        the first thread's finally block does NOT kill the second session or set its state to idle."""
        import threading as test_threading
        import time as real_time
        orchestrator = MagicMock()
        recorder = MagicMock()

        t1_done = test_threading.Event()
        def slow_first_recording():
            real_time.sleep(0.15)
            t1_done.set()
            return None

        recorder.record_until_silence.side_effect = slow_first_recording
        stt = MagicMock()
        wake_detector = MagicMock()

        bridge = OrbBridge(orchestrator, recorder, stt, wake_detector=wake_detector)

        # Start thread 1
        with patch("time.sleep", return_value=None):
            bridge.start_listening()

        real_time.sleep(0.02)

        # Stop listening
        bridge.stop_listening()

        # Configure thread 2 recording to stay active until signalled
        t2_done = test_threading.Event()
        def session2_recording():
            t2_done.wait(0.5)
            return None

        recorder.record_until_silence.side_effect = session2_recording

        # Start thread 2 immediately
        with patch("time.sleep", return_value=None):
            bridge.start_listening()

        self.assertTrue(bridge._is_listening, "Second session should be listening")
        self.assertEqual(bridge._current_state, "listening")

        # Wait for thread 1 to finish unwinding
        t1_done.wait(1.0)
        real_time.sleep(0.05)

        # Thread 2 must still be listening and not aborted/set to idle by thread 1
        self.assertTrue(bridge._is_listening, "Second session must still be listening after thread 1 dies")
        self.assertEqual(bridge._current_state, "listening")

        # Let session 2 complete
        t2_done.set()
        if bridge._listen_thread:
            bridge._listen_thread.join(timeout=1.0)

        self.assertFalse(bridge._is_listening)
        self.assertEqual(bridge._current_state, "idle")
        wake_detector.resume.assert_called()

    def test_continuous_rattle_or_chatter_spikes_rejected_by_min_gap_debounce(self):
        """Verify that a multi-strike noise burst (spikes at 0ms, 90ms, 250ms) does NOT trigger double clap."""
        wake_called = []
        detector = DoubleClapDetector(threshold=0.30, min_gap=0.18, max_gap=0.85, on_wake=lambda: wake_called.append(True))

        # Simulate noise burst spikes with timestamps:
        # Spike 1: t=100.00 (sets first clap candidate)
        detector._last_clap_time = 100.00
        detector._waiting_for_second = True

        # Spike 2 arrives at t=100.09 (90ms later < min_gap 0.18s)
        now = 100.09
        delta = now - detector._last_clap_time
        if detector.min_gap <= delta <= detector.max_gap:
            detector.on_wake()
        elif delta > detector.max_gap:
            detector._last_clap_time = now
        elif delta < detector.min_gap:
            # Advance last_clap_time so noise doesn't trigger on subsequent spike
            detector._last_clap_time = now

        self.assertEqual(len(wake_called), 0, "Spike 2 should not trigger double clap")

        # Spike 3 arrives at t=100.25 (250ms from start, but only 160ms from Spike 2)
        now = 100.25
        delta = now - detector._last_clap_time
        if detector.min_gap <= delta <= detector.max_gap:
            detector.on_wake()
        elif delta < detector.min_gap:
            detector._last_clap_time = now

        self.assertEqual(len(wake_called), 0, "Spike 3 in continuous rattle must NOT falsely trigger double clap")

if __name__ == "__main__":
    unittest.main()
