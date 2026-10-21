import urllib.parse
import webbrowser
import os
from typing import Dict, Any

class WebMusicTool:
    """
    Automates web navigation and YouTube Music playback using Windows default browser.
    """

    @staticmethod
    def play_youtube_music(query: str) -> Dict[str, Any]:
        """
        Launches YouTube Music in the default browser with the query.
        """
        encoded = urllib.parse.quote_plus(query)
        url = f"https://music.youtube.com/search?q={encoded}"
        try:
            webbrowser.open(url)
            return {
                "success": True,
                "url": url,
                "query": query,
                "message": f"Opened YouTube Music for '{query}' in your default browser."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to open YouTube Music: {e}"
            }

    @staticmethod
    def play_youtube(query: str) -> Dict[str, Any]:
        """
        Launches standard YouTube search in the default browser.
        """
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        try:
            webbrowser.open(url)
            return {
                "success": True,
                "url": url,
                "query": query,
                "message": f"Opened YouTube for '{query}' in your default browser."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to open YouTube: {e}"
            }

    @staticmethod
    def search_web(query: str) -> Dict[str, Any]:
        """
        Performs Google web search in default browser.
        """
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"
        try:
            webbrowser.open(url)
            return {
                "success": True,
                "url": url,
                "query": query,
                "message": f"Searching web for '{query}'."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to search web: {e}"
            }

    @staticmethod
    def open_url(url: str) -> Dict[str, Any]:
        """
        Opens arbitrary URL in default browser.
        """
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        try:
            webbrowser.open(url)
            return {
                "success": True,
                "url": url,
                "message": f"Opened {url} in your default browser."
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to open URL: {e}"
            }
