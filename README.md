# METHER OS

**A self-hosted personal AI system that connects to your tools and acts on your behalf.**

METHER OS is an open-source project that gives you a locally-running AI 
assistant with persistent memory, voice control, and integrations 
with your daily tools — email, calendar, WhatsApp, and system control.

No subscriptions. No cloud dependency. Runs on your machine.

---

## The Problem

Current AI assistants (ChatGPT, Claude, Gemini) are powerful but stateless.
Every session starts from scratch. They can answer questions but cannot:

- Remember your ongoing projects and priorities
- Send a WhatsApp message or reply to an email
- Open an application or run a terminal command
- Know your communication style or who your contacts are

METHER OS is built to solve this.

---

## What It Does

**Voice Interface**
Say the wake word, speak your request, hear the response.
Supports Hindi and English (Hinglish).
Built on Whisper STT and Piper TTS — both run locally.

**WhatsApp Integration**
Read incoming messages, send replies, manage group chats.
Auto-handle mode lets the AI respond on your behalf
with your communication style while you're unavailable.

**Google Suite**
Search and send Gmail. View and create Calendar events.
Search and read Google Drive files.

**System Control**
Open applications, run terminal commands with live output,
read and search files, manage running processes.

**Persistent Memory**
A personal context file (CLAUDE.md) tells the system who you are,
what you're working on, and how you prefer to communicate.
This context is loaded at every session — the AI always knows you.

**Local LLM Routing**
Routes requests through free LLM APIs (NVIDIA NIM, OpenRouter).
No OpenAI subscription required.

---

## Architecture
User Input (Voice / Web / WhatsApp)
↓
FastAPI Backend
asyncio + EventBus
↓
Agent Loop (LLM + Tool Calling)
↓
Tool Execution (Gmail / Calendar / WhatsApp / System)
↓
Output (Voice / Dashboard / WhatsApp Reply)
Full breakdown: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Getting Started

**Requirements**
- Python 3.11+
- Node.js 18+
- Git
- A free NVIDIA NIM or OpenRouter API key

**Install**
```bash
git clone https://github.com/mether-os/mether-core.git
cd mether-core
infra\install.bat       # Windows
bash infra/install.sh   # Linux
```

**Configure**
```bash
cp backend/.env.example backend/.env
# Add your API key to backend/.env
```

**Run**
```bash
infra\start.bat         # Windows
bash infra/start.sh     # Linux
```

Dashboard opens at http://localhost:5173

**Personal Context**
Create `~/.mether/CLAUDE.md` with your information.
The more complete this file, the more personalized the system becomes.
See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for a template.

---

## Project Structure

```text
mether-core/
├── 📂 backend/       # Python (FastAPI, asyncio, tool system)
│   ├── 🛠️ agent/     # Core reasoning & tool-calling loop
│   ├── 🌐 api/       # REST v1 routes & WebSocket handlers
│   └── ⚙️ tools/     # Tool implementations (Gmail, WhatsApp, etc.)
├── 📂 frontend/      # React 19, TypeScript, real-time HUD dashboard
├── 📂 voice/         # STT + TTS + wake word sidecar (Python)
├── 📂 whatsapp/      # WhatsApp-web.js bridge sidecar (Node.js)
├── 📂 infra/         # Startup scripts, installer, Docker config
└── 📂 docs/          # Architecture, Configuration, Tool Dev guides
```

## Available Tools

| Tool | What It Does |
|------|-------------|
| `gmail` | Search, read, send, reply to emails |
| `calendar` | View schedule, create events, find free slots |
| `drive` | Search and read Google Drive files |
| `whatsapp` | Send messages, read chats, auto-reply |
| `app_launch` | Open any installed application |
| `code_run` | Execute shell commands, stream output |
| `filesystem` | Read, search, and write files |
| `process` | List processes, get system info |
| `clipboard` | Read and write clipboard |
| `screenshot` | Capture the screen |

Adding new tools takes about 20 lines of Python.
See [docs/TOOL_DEVELOPMENT.md](docs/TOOL_DEVELOPMENT.md).

---

## Current Status

This project is in active development. Core functionality works.
Voice pipeline and WhatsApp integration are stable on Windows.

What works:
- Voice wake word, STT, TTS
- WhatsApp send/receive/auto-handle
- Gmail, Calendar, Drive
- System control (Windows)
- Real-time dashboard

What is being worked on:
- Linux compatibility improvements
- Mobile interface (Telegram bridge)
- Additional tool integrations

---

## How to Contribute

Issues and pull requests are welcome.

Areas where help would be valuable:
- New tool integrations (Notion, Spotify, Slack, Home Assistant)
- Linux packaging and compatibility
- Voice model improvements for Indian languages
- Windows installer (.exe)
- Documentation improvements

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## What I Am Looking For

If you find this project useful or interesting, a few things would help:

1. **Feedback** — open an issue or discussion with what works, 
   what doesn't, and what you'd want added
2. **Testing** — try running it and report any setup issues
3. **Tool contributions** — if you build a new integration, 
   a PR would be welcome
4. **Suggestions** — if you have ideas for making this more useful
   as a daily tool, share them in Discussions

This is a student project built over one month.
The goal is to make it genuinely useful, not just technically impressive.

---

## License

MIT — free to use, modify, and distribute.

---

Built by Mayank Sharma — B.Tech Computer Science, Kalvium × JECRC University
