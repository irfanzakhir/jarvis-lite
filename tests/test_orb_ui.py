import os
import unittest
from unittest.mock import MagicMock

class TestOrbAssets(unittest.TestCase):
    def setUp(self):
        self.assets_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "assets"
        )

    def test_ui_assets_exist(self):
        index_html = os.path.join(self.assets_dir, "index.html")
        style_css = os.path.join(self.assets_dir, "style.css")
        orb_js = os.path.join(self.assets_dir, "orb.js")
        self.assertTrue(os.path.exists(index_html), "index.html is missing")
        self.assertTrue(os.path.exists(style_css), "style.css is missing")
        self.assertTrue(os.path.exists(orb_js), "orb.js is missing")

    def test_orb_bridge_methods(self):
        from ui.orb_window import OrbBridge
        orchestrator = MagicMock()
        recorder = MagicMock()
        stt = MagicMock()
        bridge = OrbBridge(orchestrator, recorder, stt)
        self.assertTrue(hasattr(bridge, "submit_query"))
        self.assertTrue(hasattr(bridge, "start_listening"))
        self.assertTrue(hasattr(bridge, "stop_listening"))
        self.assertTrue(hasattr(bridge, "confirm_action"))
        self.assertTrue(hasattr(bridge, "move_window"))

    def test_mute_button_in_ui(self):
        index_html = os.path.join(self.assets_dir, "index.html")
        with open(index_html, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("muteBtn", content)
        self.assertIn("muteHeaderBtn", content)

if __name__ == "__main__":
    unittest.main()
