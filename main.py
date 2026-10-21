import sys
import os
import argparse

# Ensure current directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.orchestrator import AssistantOrchestrator

def run_cli_mode(orchestrator: AssistantOrchestrator):
    """
    Terminal CLI Mode for testing and running without GUI.
    """
    print("\n=========================================================")
    print("      Jarvis Lite: The Windows Assistant (CLI Mode)      ")
    print("=========================================================")
    print("Type your command (e.g. 'open notepad', 'play lofi on yt music',")
    print("'volume up', 'take screenshot', 'turn on voice access', or ask anything).")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            prompt = input("You > ").strip()
            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit"]:
                print("Exiting Jarvis. Goodbye!")
                break

            result = orchestrator.handle_query(prompt)
            print(f"\nJarvis > {result.get('reply', 'Done.')}")
            if result.get("execution"):
                print(f"Details: {result.get('execution')}")
            print("-" * 55 + "\n")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Jarvis.")
            break

def run_gui_mode(orchestrator: AssistantOrchestrator, start_minimized: bool = False):
    """
    Full Desktop Siri-like Orb GUI Mode.
    """
    from ui.orb_window import OrbWindow
    from ui.hotkey import HotkeyManager
    from ui.tray import AssistantTray
    from voice.wake_clap import DoubleClapDetector

    print("\n[Jarvis Lite] Launching Siri-like Rotating Orb UI...")

    wake_detector = None
    asst_cfg = orchestrator.config.get("assistant") or {}
    if asst_cfg.get("wake_clap", True):
        clap_thresh = float(asst_cfg.get("clap_threshold", 0.30))
        wake_detector = DoubleClapDetector(threshold=clap_thresh)

    orb_window = OrbWindow(orchestrator, wake_detector=wake_detector)

    if wake_detector:
        wake_detector.on_wake = orb_window.restore_and_focus
        wake_detector.start()

    # Setup global hotkey (default: Ctrl+Shift+A)
    wake_hotkey = asst_cfg.get("wake_hotkey", "ctrl+shift+a")
    hotkey = HotkeyManager(hotkey=wake_hotkey, on_trigger=orb_window.restore_and_focus)
    hotkey.start()

    def _clean_exit():
        if wake_detector:
            try:
                wake_detector.stop()
            except Exception:
                pass
        try:
            hotkey.stop()
        except Exception:
            pass
        try:
            tray.stop()
        except Exception:
            pass
        if orb_window.window:
            try:
                orb_window.window.destroy()
            except Exception:
                pass

    # Setup System Tray
    tray = AssistantTray(
        on_show=orb_window.restore_and_focus,
        on_exit=_clean_exit
    )
    tray.start()

    # Launch Orb Desktop Window (Blocks on main thread for UI event loop)
    try:
        orb_window.start(minimized=start_minimized)
    finally:
        _clean_exit()

def main():
    parser = argparse.ArgumentParser(description="Windows AI Assistant (Agentic Desktop AI)")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode without GUI")
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    parser.add_argument("--minimized", action="store_true", help="Start minimized in background / tray")
    args = parser.parse_args()

    orchestrator = AssistantOrchestrator(config_path=args.config)

    if args.cli:
        run_cli_mode(orchestrator)
    else:
        try:
            run_gui_mode(orchestrator, start_minimized=args.minimized)
        except Exception as e:
            import traceback
            print(f"[Main] GUI failed to start ({e}). Full stack trace:")
            traceback.print_exc()
            run_cli_mode(orchestrator)

if __name__ == "__main__":
    main()
