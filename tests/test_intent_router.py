import unittest
from core.intent_router import IntentRouter

class TestIntentRouter(unittest.TestCase):

    def setUp(self):
        self.router = IntentRouter("config/app_aliases.json")

    def test_voice_access(self):
        result = self.router.route("turn on voice access")
        self.assertTrue(result["handled"])
        self.assertEqual(result["action"], "toggle_voice_access")

    def test_youtube_music(self):
        result = self.router.route("play bohemian rhapsody on yt music")
        self.assertTrue(result["handled"])
        self.assertEqual(result["action"], "play_music")
        self.assertEqual(result["params"]["query"], "bohemian rhapsody")

    def test_volume_controls(self):
        res_up = self.router.route("volume up")
        self.assertTrue(res_up["handled"])
        self.assertEqual(res_up["action"], "volume_change")
        self.assertEqual(res_up["params"]["direction"], "up")

        res_mute = self.router.route("mute")
        self.assertTrue(res_mute["handled"])
        self.assertEqual(res_mute["action"], "volume_change")
        self.assertEqual(res_mute["params"]["direction"], "mute")

    def test_app_launching(self):
        result = self.router.route("open notepad")
        self.assertTrue(result["handled"])
        self.assertEqual(result["action"], "open_app")
        self.assertEqual(result["params"]["app_name"], "notepad")

    def test_system_utils(self):
        res_time = self.router.route("what is the time")
        self.assertTrue(res_time["handled"])
        self.assertEqual(res_time["action"], "direct_answer")

        res_lock = self.router.route("lock pc")
        self.assertTrue(res_lock["handled"])
        self.assertEqual(res_lock["action"], "lock_screen")

    def test_tier3_fallback(self):
        # Natural language that requires LLM reasoning
        result = self.router.route("Can you find all log files in my temporary folder and summarize errors?")
        self.assertFalse(result["handled"])
        self.assertEqual(result["tier"], 3)

if __name__ == "__main__":
    unittest.main()
