# ⚡ Jarvis Lite: The Windows Assistant

[![Platform: Windows 10 / 11](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Zero-AI-First Architecture](https://img.shields.io/badge/Architecture-Zero--AI--First-success)](#-zero-ai-first-hybrid-architecture)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Jarvis Lite** is a fast, agentic desktop AI assistant for Windows 10 & 11 inspired by Tony Stark's JARVIS and Apple Siri. Designed specifically to run on everyday laptops (like Intel Core i5/i7 machines with zero GPU requirements), it pairs a **Zero-AI-First deterministic engine** for sub-millisecond local commands with a high-speed **Multi-Provider Cloud Brain** (Groq & OpenRouter) for complex agentic workflows.

---

## 🔮 Key Highlights

- 🔮 **Siri-Style 3D Rotating Orb**: A floating, draggable chromatic energy orb with 5 dynamic state profiles (*Idle, Listening, Thinking, Speaking, Executing*) and an expandable frosted-glass HUD drawer.
- 👏 **Double-Clap Wake Sound**: Running in the background? Simply **clap twice** to summon Jarvis to the center of your screen with an ascending futuristic chime.
- ⌨️ **Global Summon Hotkey**: Press **`Ctrl + Shift + A`** anytime from any application to wake up Jarvis.
- ⚡ **Zero-AI-First Deterministic Engine**: Routine tasks (opening apps, playing YouTube Music, adjusting volume, taking screenshots, locking the screen) execute locally via regex and Windows APIs in **< 2ms with 0 token consumption**.
- ☁️ **Agentic Multi-Provider Brain**: When a complex question or system query is asked, Jarvis queries **Groq** (`qwen/qwen3.8-27b`) with automatic instant failover to **OpenRouter** (`openrouter/free`), requiring **0% local GPU/CPU compute**.
- 🛡️ **Hardened PowerShell Safety Guard**: Safely runs system inspection and PowerShell automation, with 1-click **Approve / Cancel** UI confirmation for destructive operations (`Remove-Item`, `Stop-Process`, etc.).
- 🎵 **Direct YouTube Music Automation**: Automatically launches your default browser with search and direct autoplay.
- 🎙️ **Windows Voice Access Grid**: Seamlessly activates Windows 11 Voice Access for corner-to-corner numbered grid control.
- 🗣️ **100% Free Neural Voice Stack**:
  - **Hearing (STT)**: Offline local speech recognition with `faster-whisper` (`tiny.en` on CPU, ~40MB RAM).
  - **Speaking (TTS)**: Microsoft Edge's natural neural voices via `edge-tts` (100% free, natural human cadence, zero robotic tone).

---

## 🧠 Zero-AI-First Hybrid Architecture

```
User Query (Voice / Text)
         │
         ▼
┌─────────────────────────────────┐
│ Tier 1: Deterministic Engine    │ ──(Instant Match <2ms)──► Direct Local Windows Action
│ • YouTube Music / Media Keys    │                           (Zero Token Cost)
│ • App Launcher & URL Opener     │
│ • Volume, Screenshot, Lock PC   │
│ • Windows Voice Access Toggle   │
└─────────────────────────────────┘
         │
         ▼ (No regex match)
┌─────────────────────────────────┐
│ Tier 2: Start Menu Indexer      │ ──(App found)───────────► Safe App Launch (ShellExecuteW)
└─────────────────────────────────┘
         │
         ▼ (Not an app)
┌─────────────────────────────────┐
│ Tier 3: Agentic Cloud LLM       │
│ • Primary: Groq Cloud           │ ──(429 / Timeout)───────► Backup: OpenRouter Free
│ • Function Calling / Tools      │
│ • PowerShell Execution Guard    │
└─────────────────────────────────┘
```

---

## 🚀 Quick Setup & Installation

### 1. Prerequisites
- **OS**: Windows 10 or Windows 11 (64-bit)
- **Python**: Python 3.10 or 3.11 installed
- **Microphone**: Any built-in or external laptop microphone

### 2. Clone & Setup Environment
```powershell
# Clone the repository
git clone https://github.com/yourusername/jarvis-lite.git
cd jarvis-lite

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Free API Keys
Copy `.env.example` to `.env`:
```powershell
copy .env.example .env
```
Open `.env` and add your free keys:
```env
# Free Groq API Key (https://console.groq.com)
GROQ_API_KEY=gsk_your_groq_key_here

# Free OpenRouter API Key (https://openrouter.ai/keys)
OPENROUTER_API_KEY=sk-or-v1_your_openrouter_key_here
```
*(Note: `.env` is ignored by Git, keeping your secrets safe).*

---

## 🎮 Running Jarvis Lite

### GUI Mode (Siri Orb + HUD)
Double-click `run.bat` or run:
```powershell
.\run.bat
```
*(Or: `.\venv\Scripts\python.exe main.py`)*

### CLI Mode (Terminal Only)
```powershell
.\venv\Scripts\python.exe main.py --cli
```

---

## 🎯 Example Voice & Text Commands

| Category | Command | Execution Tier | Action Taken |
| :--- | :--- | :--- | :--- |
| **Wake & Identity** | *"Who are you?"*<br>*"Hey Jarvis"* | Tier 1 (Deterministic) | Answers instantly: *"I am Jarvis, your Windows AI assistant."* |
| **Music Playback** | *"Play Bohemian Rhapsody on YouTube Music"*<br>*"Play lofi jazz"* | Tier 1 (Deterministic) | Launches browser with direct YouTube Music autoplay |
| **Media Controls** | *"Pause"*, *"Resume"*, *"Next track"*, *"Stop"* | Tier 1 (Deterministic) | Simulates Windows media hardware keys |
| **App Launching** | *"Open Notepad"*, *"Launch Chrome"*, *"Start Spotify"* | Tier 1 / 2 (Local) | Opens application via clean Windows ShellExecute |
| **Voice Access** | *"Turn on Voice Access"*, *"Stop Voice Access"* | Tier 1 (Deterministic) | Activates Windows 11 Voice Access numbered grid |
| **System Volume** | *"Volume up"*, *"Volume down"*, *"Mute"*, *"Unmute"* | Tier 1 (Deterministic) | Adjusts master hardware volume directly |
| **System Tools** | *"Take screenshot"*, *"Lock computer"*, *"Empty recycle bin"* | Tier 1 (Deterministic) | Executes Windows utility functions |
| **Agentic Analysis** | *"Find all files modified today in Downloads"*, *"List top 5 CPU processes"* | Tier 3 (Agentic LLM) | Analyzes intent, executes safe PowerShell, and summarizes findings |

---

## 🛡️ Security & Safe Mode

Jarvis Lite includes a strict **PowerShell Safety Guard**:
- Destructive operations (`Remove-Item`, `Stop-Process`, `diskpart`, `cipher`, etc.) are intercepted before execution.
- Bypasses (PowerShell aliases like `rm` / `ri`, backtick obfuscation `r`e`m`o`v`e, encoded commands `-enc`, and dynamic `iex` invocations) are neutralized.
- The UI presents an **Approve / Cancel** prompt requiring explicit user authorization.

---

## 🧪 Automated Testing

Run the full offline verification test suite:
```powershell
.\venv\Scripts\python.exe -m unittest discover tests
```
*Includes 20 automated unit tests covering intent routing, PowerShell safety rules, audio clipping, STT memory handling, and async bridge dispatching.*

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
