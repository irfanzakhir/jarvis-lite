import threading
from typing import Callable, Optional
from PIL import Image, ImageDraw

try:
    import pystray
    _pystray_available = True
except ImportError:
    _pystray_available = False

class AssistantTray:
    """
    Windows System Tray icon manager with quick action menu.
    """

    def __init__(self, on_show: Optional[Callable] = None, on_exit: Optional[Callable] = None):
        self.on_show = on_show
        self.on_exit = on_exit
        self.icon = None

    def _create_icon_image(self) -> Image.Image:
        """
        Generates a glowing Siri-style circular icon.
        """
        width = 64
        height = 64
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Outer purple glow
        draw.ellipse([4, 4, 60, 60], fill=(99, 102, 241, 160))
        # Inner cyan core
        draw.ellipse([14, 14, 50, 50], fill=(56, 189, 248, 230))
        # White center sparkle
        draw.ellipse([26, 26, 38, 38], fill=(255, 255, 255, 255))

        return image

    def start(self):
        if not _pystray_available:
            print("[AssistantTray] pystray is not available.")
            return

        image = self._create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Show Jarvis (Ctrl+Shift+A)", lambda icon, item: self._handle_show()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit Jarvis", lambda icon, item: self._handle_exit())
        )

        self.icon = pystray.Icon("JarvisLite", image, "Jarvis Lite: The Windows Assistant", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _handle_show(self):
        if self.on_show:
            self.on_show()

    def _handle_exit(self):
        self.stop()
        if self.on_exit:
            self.on_exit()

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
