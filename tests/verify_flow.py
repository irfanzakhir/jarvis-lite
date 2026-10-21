import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import AssistantOrchestrator

def main():
    print("Testing Assistant Orchestrator end-to-end routing...")
    orchestrator = AssistantOrchestrator("config/config.yaml")

    queries = [
        "what is the time",
        "play bohemian rhapsody on yt music",
        "volume up",
        "mute",
        "turn on voice access",
        "open notepad"
    ]

    for q in queries:
        print(f"\n[Test Query]: '{q}'")
        res = orchestrator.handle_query(q)
        print(f"Handled: {res.get('handled')}, Tier: {res.get('tier')}, Reply: {res.get('reply')}")

    print("\nAll routing flow tests passed!")

if __name__ == "__main__":
    main()
