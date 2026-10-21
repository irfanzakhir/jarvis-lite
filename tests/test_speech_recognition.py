import os
import unittest
from unittest.mock import MagicMock, patch
import numpy as np

import speech_recognition as sr
from voice.ears import JarvisEars
from voice.stt_google import GoogleSTT
from voice.stt_whisper import WhisperSTT
from voice.audio_recorder import AudioRecorder

class TestSpeechRecognitionJarvis2(unittest.TestCase):
    """
    Test suite for speech recognition using Jarvis 2.0 technique:
    - Ambient noise calibration and CPU dynamic energy threshold disable
    - Energy threshold offset locking
    - Google Web Speech API recognition
    - Audio format handling (sr.AudioData, numpy array, bytes, WAV)
    - Error handling (UnknownValueError, WaitTimeoutError, RequestError)
    - Fallback cascade to Whisper when offline
    - Microphone rebooting
    """

    def test_jarvis_ears_initialization(self):
        """Verify JarvisEars initializes with configuration and default properties."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars(
                language="en-US",
                calibration_duration=1.5,
                energy_threshold_offset=50,
                timeout=5.0,
                phrase_time_limit=15.0
            )
            self.assertEqual(ears.language, "en-US")
            self.assertEqual(ears.calibration_duration, 1.5)
            self.assertEqual(ears.energy_threshold_offset, 50)
            self.assertEqual(ears.timeout, 5.0)
            self.assertEqual(ears.phrase_time_limit, 15.0)
            self.assertIsNotNone(ears.recognizer)
            self.assertTrue(hasattr(ears, "_lock"))
            self.assertFalse(ears.is_recording)

    def test_google_stt_alias(self):
        """Verify GoogleSTT is an alias for JarvisEars."""
        self.assertIs(GoogleSTT, JarvisEars)

    def test_jarvis_ears_ambient_noise_optimization(self):
        """
        Verify the Jarvis 2.0 optimization:
        - Calibrates for ambient noise
        - Sets dynamic_energy_threshold = False (disables continuous CPU polling)
        - Adds energy_threshold_offset to energy_threshold
        """
        mock_mic = MagicMock()
        mock_rec = MagicMock()
        mock_rec.energy_threshold = 300

        with patch("speech_recognition.Recognizer", return_value=mock_rec), \
             patch("speech_recognition.Microphone", return_value=mock_mic):
            ears = JarvisEars(calibration_duration=1.5, energy_threshold_offset=50)
            
            mock_rec.adjust_for_ambient_noise.assert_called_once_with(mock_mic.__enter__.return_value, duration=1.5)
            self.assertFalse(mock_rec.dynamic_energy_threshold)
            self.assertEqual(mock_rec.energy_threshold, 350)

    def test_transcribe_empty_and_none(self):
        """Verify empty audio or None returns empty string cleanly."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            self.assertEqual(ears.transcribe(None), "")
            self.assertEqual(ears.transcribe(""), "")
            self.assertEqual(ears.transcribe(b""), "")
            self.assertEqual(ears.transcribe(np.array([], dtype=np.float32)), "")

    def test_transcribe_sr_audio_data(self):
        """Verify transcribe handles sr.AudioData using recognize_google."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            ears.recognizer = MagicMock()
            ears.recognizer.recognize_google.return_value = "hello jarvis"

            audio = sr.AudioData(b"\x00" * 3200, 16000, 2)
            result = ears.transcribe(audio)

            self.assertEqual(result, "hello jarvis")
            ears.recognizer.recognize_google.assert_called_once_with(audio, language="en-US")

    def test_transcribe_numpy_array(self):
        """Verify transcribe converts numpy float32 audio to AudioData and transcribes."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            ears.recognizer = MagicMock()
            ears.recognizer.recognize_google.return_value = "open notepad"

            audio_np = np.zeros(16000, dtype=np.float32)
            result = ears.transcribe(audio_np)

            self.assertEqual(result, "open notepad")
            self.assertEqual(ears.recognizer.recognize_google.call_count, 1)

    def test_transcribe_unknown_value_error(self):
        """Verify sr.UnknownValueError (silence/unintelligible) returns empty string without error."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            ears.recognizer = MagicMock()
            ears.recognizer.recognize_google.side_effect = sr.UnknownValueError()

            audio = sr.AudioData(b"\x00" * 1600, 16000, 2)
            result = ears.transcribe(audio)
            self.assertEqual(result, "")

    def test_transcribe_fallback_to_whisper_on_request_error(self):
        """Verify fallback to WhisperSTT when Google API raises RequestError (offline)."""
        mock_fallback = MagicMock()
        mock_fallback.transcribe.return_value = "fallback transcription from whisper"

        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars(fallback_stt=mock_fallback)
            ears.recognizer = MagicMock()
            ears.recognizer.recognize_google.side_effect = sr.RequestError("recognition service unreachable")

            audio = sr.AudioData(b"\x00" * 1600, 16000, 2)
            result = ears.transcribe(audio)

            self.assertEqual(result, "fallback transcription from whisper")
            mock_fallback.transcribe.assert_called_once_with(audio)

    def test_audio_to_wav_bytes(self):
        """Verify audio_to_wav_bytes handles AudioData, bytes, and numpy arrays."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            audio = sr.AudioData(b"\x00" * 1600, 16000, 2)
            wav_bytes = ears.audio_to_wav_bytes(audio)
            self.assertTrue(len(wav_bytes) > 44)
            self.assertTrue(wav_bytes.startswith(b"RIFF"))

            np_audio = np.zeros(1600, dtype=np.float32)
            wav_np = ears.audio_to_wav_bytes(np_audio)
            self.assertTrue(len(wav_np) > 44)
            self.assertTrue(wav_np.startswith(b"RIFF"))

    def test_reboot_mic(self):
        """Verify _reboot_mic recalibrates, preserves energy threshold offset, and resets microphone."""
        mock_mic = MagicMock()
        mock_rec = MagicMock()
        mock_rec.energy_threshold = 200
        with patch("speech_recognition.Recognizer", return_value=mock_rec), \
             patch("speech_recognition.Microphone", return_value=mock_mic), \
             patch("time.sleep"):
            ears = JarvisEars(energy_threshold_offset=50)
            mock_rec.energy_threshold = 200
            ears._reboot_mic()
            self.assertIsNotNone(ears.microphone)
            mock_rec.adjust_for_ambient_noise.assert_called()
            self.assertEqual(mock_rec.energy_threshold, 250)

    def test_ears_listen_success(self):
        """Verify listen() records audio and returns recognized text."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            ears.microphone = MagicMock()
            ears.recognizer = MagicMock()
            mock_audio = MagicMock()
            ears.recognizer.listen.return_value = mock_audio
            ears.recognizer.recognize_google.return_value = "jarvis check system"

            result = ears.listen(timeout=3.0, phrase_time_limit=10.0)

            self.assertEqual(result, "jarvis check system")
            ears.recognizer.listen.assert_called_once_with(
                ears.microphone.__enter__.return_value, timeout=3.0, phrase_time_limit=10.0
            )
            ears.recognizer.recognize_google.assert_called_once_with(mock_audio, language="en-US")
            self.assertFalse(ears.is_recording)

    def test_ears_listen_timeout(self):
        """Verify listen() returns None cleanly on sr.WaitTimeoutError."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            ears.microphone = MagicMock()
            ears.recognizer = MagicMock()
            ears.recognizer.listen.side_effect = sr.WaitTimeoutError("timed out")

            result = ears.listen()
            self.assertIsNone(result)
            self.assertFalse(ears.is_recording)

    def test_ears_listen_unknown_value(self):
        """Verify listen() returns None on sr.UnknownValueError (unintelligible)."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            ears.microphone = MagicMock()
            ears.recognizer = MagicMock()
            ears.recognizer.recognize_google.side_effect = sr.UnknownValueError()

            result = ears.listen()
            self.assertIsNone(result)
            self.assertFalse(ears.is_recording)

    def test_ears_listen_attribute_error_reboots(self):
        """Verify listen() triggers _reboot_mic() when audio stream drops (AttributeError)."""
        with patch.object(JarvisEars, "_init_mic"), \
             patch.object(JarvisEars, "_reboot_mic") as mock_reboot:
            ears = JarvisEars()
            ears.microphone = MagicMock()
            ears.recognizer = MagicMock()
            ears.recognizer.listen.side_effect = AttributeError("stream dropped")

            result = ears.listen()
            self.assertIsNone(result)
            mock_reboot.assert_called_once()
            self.assertFalse(ears.is_recording)

    def test_ears_listen_request_error_with_fallback(self):
        """Verify listen() cascades to fallback_stt when Google API fails (RequestError)."""
        mock_fallback = MagicMock()
        mock_fallback.transcribe.return_value = "offline command text"

        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars(fallback_stt=mock_fallback)
            ears.microphone = MagicMock()
            ears.recognizer = MagicMock()
            mock_audio = MagicMock()
            ears.recognizer.listen.return_value = mock_audio
            ears.recognizer.recognize_google.side_effect = sr.RequestError("No internet connection")

            result = ears.listen()
            self.assertEqual(result, "offline command text")
            mock_fallback.transcribe.assert_called_once_with(mock_audio)

    def test_ears_listen_request_error_without_fallback(self):
        """Verify listen() returns None and records last_error when Google API fails without fallback."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars(fallback_stt=None)
            ears.microphone = MagicMock()
            ears.recognizer = MagicMock()
            mock_audio = MagicMock()
            ears.recognizer.listen.return_value = mock_audio
            ears.recognizer.recognize_google.side_effect = sr.RequestError("No internet")

            result = ears.listen()
            self.assertIsNone(result)
            self.assertIn("API Request failed", ears.last_error)

    def test_ears_stop_cancels_recording(self):
        """Verify stop() closes active microphone stream and sets is_recording to False."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            mock_source = MagicMock()
            mock_stream = MagicMock()
            mock_source.stream = mock_stream
            ears._active_source = mock_source
            ears.is_recording = True

            ears.stop()

            self.assertFalse(ears.is_recording)
            mock_stream.close.assert_called_once()

    def test_record_until_silence_returns_audio_data(self):
        """Verify record_until_silence returns AudioData captured by recognizer.listen."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            ears.microphone = MagicMock()
            ears.recognizer = MagicMock()
            mock_audio = MagicMock()
            ears.recognizer.listen.return_value = mock_audio

            audio = ears.record_until_silence()
            self.assertIs(audio, mock_audio)
            self.assertFalse(ears.is_recording)

    def test_preload_sync_and_async(self):
        """Verify preload triggers _init_mic and fallback_stt preload."""
        mock_fallback = MagicMock()
        with patch.object(JarvisEars, "_init_mic") as mock_init:
            ears = JarvisEars(fallback_stt=mock_fallback, calibrate_on_init=False)
            ears.preload(async_load=False)
            mock_init.assert_called_once()
            mock_fallback.preload.assert_called_once_with(async_load=False)

    def test_transcribe_riff_wav_bytes(self):
        """Verify transcribe parses RIFF WAV bytes with sr.AudioFile."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            ears.recognizer = MagicMock()
            ears.recognizer.recognize_google.return_value = "wav transcription"

            # Create minimal valid RIFF WAV bytes in memory
            import io, wave
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00" * 3200)
            wav_bytes = buf.getvalue()

            res = ears.transcribe(wav_bytes)
            self.assertEqual(res, "wav transcription")
            self.assertEqual(ears.recognizer.recognize_google.call_count, 1)

    def test_transcribe_file_path(self):
        """Verify transcribe handles file paths and returns empty string for nonexistent files."""
        with patch.object(JarvisEars, "_init_mic"):
            ears = JarvisEars()
            self.assertEqual(ears.transcribe("non_existent_audio_file.wav"), "")

    def test_whisper_stt_audio_data_fast_path(self):
        """Verify WhisperSTT extracts float32 numpy array directly from 16kHz AudioData."""
        stt = WhisperSTT(model_size="tiny.en")
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = " fast path whisper "
        mock_model.transcribe.return_value = ([mock_segment], None)
        stt.model = mock_model

        # 16kHz, 16-bit (2 bytes per sample) AudioData
        raw_pcm = np.zeros(1600, dtype=np.int16).tobytes()
        audio = sr.AudioData(raw_pcm, 16000, 2)

        result = stt.transcribe(audio)
        self.assertEqual(result, "fast path whisper")
        # Ensure model.transcribe was called with a numpy array (fast path)
        call_args = mock_model.transcribe.call_args[0]
        self.assertIsInstance(call_args[0], np.ndarray)
        self.assertEqual(call_args[0].dtype, np.float32)

    def test_orb_bridge_stop_listening_calls_recorder_stop(self):
        """Verify OrbBridge.stop_listening calls stop() on the recorder if present."""
        from ui.orb_window import OrbBridge
        mock_orch = MagicMock()
        mock_recorder = MagicMock()
        mock_stt = MagicMock()
        bridge = OrbBridge(mock_orch, mock_recorder, mock_stt)

        res = bridge.stop_listening()
        self.assertEqual(res.get("status"), "stopped")
        mock_recorder.stop.assert_called_once()

    def test_orb_window_stt_engine_selection(self):
        """Verify OrbWindow correctly wires JarvisEars when stt_engine is google."""
        from ui.orb_window import OrbWindow
        mock_orchestrator = MagicMock()
        mock_orchestrator.config = {
            "voice": {
                "stt_engine": "google",
                "calibration_duration": 0.1,
                "fallback_to_whisper": False
            }
        }
        with patch.object(JarvisEars, "_init_mic"):
            win = OrbWindow(mock_orchestrator)
            self.assertIsInstance(win.stt, JarvisEars)
            self.assertIsInstance(win.recorder, JarvisEars)

    def test_orb_window_whisper_engine_selection(self):
        """Verify OrbWindow correctly wires WhisperSTT and AudioRecorder when stt_engine is whisper."""
        from ui.orb_window import OrbWindow
        mock_orchestrator = MagicMock()
        mock_orchestrator.config = {
            "voice": {
                "stt_engine": "whisper",
                "stt_model": "tiny.en"
            }
        }
        with patch.object(WhisperSTT, "preload"):
            win = OrbWindow(mock_orchestrator)
            self.assertIsInstance(win.stt, WhisperSTT)
            self.assertIsInstance(win.recorder, AudioRecorder)

if __name__ == "__main__":
    unittest.main()
