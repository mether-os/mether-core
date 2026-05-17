# METHER OS

> Personal AI Operating System — Jarvis-style voice + WhatsApp + system control.

[![Backend CI](https://github.com/mether-os/mether-core/actions/workflows/test-backend.yml/badge.svg)](https://github.com/mether-os/mether-core/actions/workflows/test-backend.yml)
[![Frontend CI](https://github.com/mether-os/mether-core/actions/workflows/test-frontend.yml/badge.svg)](https://github.com/mether-os/mether-core/actions/workflows/test-frontend.yml)

---

## Quick Start

### First Time Setup
```bash
git clone https://github.com/mether-os/mether-core.git
cd mether-core
infra\install.bat
```

### Daily Use
```bash
infra\start.bat
```

### PowerShell (Advanced)
```powershell
# Start with health checks + monitoring
powershell -ExecutionPolicy Bypass -File infra\mether.ps1

# Check status
powershell -ExecutionPolicy Bypass -File infra\mether.ps1 -Status

# Stop all
powershell -ExecutionPolicy Bypass -File infra\mether.ps1 -Stop
```

### Auto-Start on Windows Boot
```bash
infra\autostart\register_autostart.bat
```

### Stop Everything
```bash
infra\stop.bat
```

---

## Services

| Service | Port | Technology | Purpose |
|---------|------|------------|---------|
| LLM Proxy | 8082 | Python / uvicorn | Routes to NVIDIA NIM / OpenRouter |
| Backend | 8000 | FastAPI + WebSocket | Agent core, tools, memory |
| WhatsApp | 3001 | Node.js / whatsapp-web.js | WhatsApp bridge + auto-reply |
| Voice | — | Python / Whisper + Piper | Wake word, STT, TTS |
| Frontend | 5173 | React 19 + Vite | Tactical HUD dashboard |

---

## Architecture

```
mether-core/
├── backend/          Python FastAPI — agent, tools, memory, API
│   └── src/mether/
│       ├── agent/        LLM client + agent loop
│       ├── api/          REST + WebSocket endpoints
│       ├── events/       EventBus pub/sub
│       ├── memory/       Context memory (CLAUDE.md)
│       ├── tools/        System, Google, clipboard tools
│       │   └── google/   Gmail, Calendar, Drive integration
│       └── main.py       App entrypoint
├── frontend/         React 19 TypeScript — Tactical HUD
│   └── src/
│       ├── components/   VoiceOrb, panels, dialogs
│       ├── hooks/        useWebSocket, useUptime, useOrbState
│       ├── layouts/      HUDLayout shell
│       └── stores/       Zustand global state
├── voice/            Python voice sidecar
│   └── src/              Wake word + Whisper STT + Piper TTS
├── whatsapp/         Node.js WhatsApp bridge
│   └── src/              whatsapp-web.js + auto-reply engine
├── infra/            Startup scripts + installer
│   ├── start.bat         Launch all services (Windows)
│   ├── stop.bat          Stop all services (Windows)
│   ├── start.sh          Launch all services (Linux/Mac)
│   ├── install.bat       First-time setup
│   ├── mether.ps1        PowerShell advanced launcher
│   └── autostart/        Windows Task Scheduler registration
├── docs/             Architecture + design system docs
└── .github/          CI/CD workflows + templates
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design.

---

## Features

- **Voice Control** — Wake word detection → Whisper STT → LLM → Piper TTS
- **System Tools** — CPU/RAM monitoring, process kill, code execution, clipboard, screenshots
- **Google Integration** — Gmail search/send, Calendar CRUD, Drive file management
- **WhatsApp Bridge** — Auto-reply, conversation summaries, ping notifications
- **Dangerous Action Confirmation** — Visual confirm dialog before destructive operations
- **Live Terminal** — Streamed command output in the dashboard
- **Tactical HUD** — Sci-fi dashboard with radar, voice orb, real-time logs
- **Cloud-Free Core** — Completely local orchestrator and reasoning loop

---

## Environment Variables

Copy `.env.example` to `.env` in the backend directory:

```env
LLM_PROXY_URL=http://localhost:8082
LLM_MODEL=nvidia/llama-3.3-70b-instruct
ANTHROPIC_AUTH_TOKEN=your_token
METHER_PORT=8000

# Google (optional)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_TOKEN_PATH=~/.mether/google_token.json
GOOGLE_CREDENTIALS_PATH=~/.mether/google_credentials.json
```

---

## Development

```bash
# Backend (hot reload)
cd backend && uvicorn src.mether.main:app --reload --port 8000

# Frontend (hot reload)
cd frontend && npm run dev

# Run tests
cd backend && pytest tests/ -v
cd frontend && npm run lint && npm run type-check
```

---

## License

Private — All rights reserved.
