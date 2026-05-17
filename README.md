# METHER OS

METHER OS is a personalized, agentic AI operating system featuring a highly stylized, cinematic "HUD" interface. It is designed to be a modular assistant architecture supporting real-time streaming, automation, tool execution, and dynamic agent orchestration.

## 🚀 Current Features

- **Cinematic HUD Interface:** A React-based tactical dashboard featuring dynamic system vitals, a central VoiceOrb, and a unified real-time agent log.
- **Bi-Directional WebSocket Flow:** Fully decoupled, asynchronous communication between the frontend and backend, delivering zero-blocking, real-time UI updates.
- **Agent Orchestration:** Powered by an async Python backend utilizing `FastAPI` and `httpx`.
- **Advanced Streaming Parser:** Automatically detects and parses Server-Sent Events (SSE) from Anthropic-compatible endpoints, rendering responses with a typewriter effect directly above the command interface.
- **Tool Registry Framework:** Currently implements a `SystemTool` for reading live hardware metrics (CPU, RAM, Uptime), ready to be expanded.
- **Optimized for NVIDIA Nemotron:** Currently configured to route requests to the lightning-fast **NVIDIA Nemotron 3 Super** (120b) model via NVIDIA NIM APIs.

## 🛠 Tech Stack

**Frontend:**
- React 19 + TypeScript + Vite
- TailwindCSS (Custom HUD theming)
- Zustand (Global State Management)

**Backend:**
- Python 3.11+
- FastAPI + Uvicorn
- Asyncio + Structlog
- Pydantic v2

---

## ⚙️ How to Run Locally

You will need three terminal windows to run the complete METHER OS stack.

### 1. The LLM Proxy
METHER OS delegates reasoning to an external proxy (e.g., `free-claude-code`).
Make sure the proxy is running on **port 8082** with the NVIDIA NIM configuration (`ENABLE_MODEL_THINKING=false` for max speed).
```bash
cd ../free-claude-code
uv run python server.py
```

### 2. The Backend
Start the asynchronous Python server.
```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env

# Start the server (runs on port 8000)
uvicorn src.mether.main:app --reload --port 8000
```

### 3. The Frontend
Start the React interface.
```bash
cd frontend
npm install
npm run dev
```
Navigate to `http://localhost:5173` to access the METHER OS interface.

---

## 📋 Environment Configuration (`backend/.env`)

Make sure your backend `.env` file maps correctly to your proxy:

```env
LLM_PROXY_URL=http://localhost:8082
LLM_MODEL=nvidia_nim/nvidia/nemotron-3-super-120b-a12b
ANTHROPIC_AUTH_TOKEN=freecc
```

## 🏗 Roadmap / Missing Features (Developer Preview)
- **Voice Pipeline:** Implement actual Speech-to-Text (STT) and Text-to-Speech (TTS) binary streaming.
- **Persistent Memory:** Migrate from static `CLAUDE.md` to dynamic ChromaDB + SQLite vector recall.
- **Expanded Toolset:** Browser automation, file system access, and native app control.
