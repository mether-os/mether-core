<div align="center">

# ⚡ METHER OS

### **The Open-Source Holographic AI Operating System**
*Autonomous workflows, real-time multimodal intelligence, voice sidecars, decision engine & persistent neural memory.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

<br />

<p align="center">
  <a href="#-the-problem">The Problem</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-core-capabilities">Core Capabilities</a> •
  <a href="#-decision-intelligence-engine">Decision Engine</a> •
  <a href="#-visual-proof--interface">Visual Proof</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-project-structure">Structure</a>
</p>

---

![METHER OS Tactical HUD](docs/assets/mether-demo.png)

</div>

---

## 🎯 The Problem

Commercial AI assistants (ChatGPT, Claude, Gemini) are **stateless and passive text boxes**. Every conversation starts from a blank slate. They cannot:
- **Act Autonomously**: They cannot proactively dispatch tasks, respond across communication channels (WhatsApp, Email), or monitor critical events while you sleep.
- **Provide Verifiable Evidence**: Standard generative LLMs hallucinate facts, invent sources, and mask ambiguity with confident prose.
- **Maintain Local Control**: Cloud assistants upload your private files, conversations, and workflows to external corporate servers.
- **Integrate Native System Workflows**: They lack deep, low-latency control over your native desktop environment, terminal sessions, and local hardware.

**METHER OS transforms passive LLMs into an autonomous personal operating system.** It runs locally on your machine, retains structured context across sessions, executes real-world tools, and delivers transparent, evidence-backed decision intelligence.

---

## 📸 Visual Proof & Interface

METHER OS features a **tactical Cyberpunk HUD** designed for rapid human-agent telemetry and deep cognitive inspection:

| Interface Component | Role & Functionality | Visual Preview |
|---|---|:---:|
| **3D Holographic Neural Orb** | Interactive Three.js/Fiber visualizer with frequency-reactive audio pulsation and agent cognitive state shaders. | `Orb Canvas` |
| **Tactical 3-Column HUD** | Left: Active agents, schedule, Chief of Staff. Center: Conversation & tool execution stream. Right: Telemetry, process monitor & hardware status. | [View HUD](docs/assets/mether-demo.png) |
| **Decision Intelligence Studio** | 12-stage research pipeline modal with Claim Verifier, Evidence Vault, Contradiction Matrix, and Devil's Advocate skeptic panel. | [Inspect Demo](docs/assets/mether-demo.png) |

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│               HUMAN CONTROL & TELEMETRY INTERFACES                     │
│  [Voice: Whisper + Piper]   [Web: React 19 HUD]   [WhatsApp / Bridge]  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     LAYER 2: ASYNC EVENT BRAIN                         │
│   FastAPI Gateway  ◄──►  WebSocket Telemetry  ◄──►  Async EventBus     │
│   Persistent Memory (~/.mether/CLAUDE.md + SQLite State + Embeddings)  │
│   Chief of Staff Engine (Priority Queue, Heartbeat Automations)        │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│               LAYER 3: DECISION INTELLIGENCE ENGINE                    │
│   Budget Controller ──► Multi-Source Harvester ──► Source Network      │
│            │                                              │            │
│            ▼                                              ▼            │
│   Claim Verification ──► Contradiction Engine  ──► Devil's Advocate   │
│            │                                              │            │
│            ▼                                              ▼            │
│   Human Review Gate  ──► Decision Formatter   ──► Action Plan Engine   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   LAYER 4: TOOL EXECUTION RUNTIME                      │
│  [System: Terminal, FS, Apps]    [Comms: WhatsApp, Gmail, Calendar]    │
│  [Web: Scrapers, DuckDuckGo]     [Memory: SQLite, Vector Index]        │
└────────────────────────────────────────────────────────────────────────┘
```

Detailed architectural breakdown available in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## ⚡ Core Capabilities

### 1. 🎙️ Real-Time Voice Sidecar (Whisper + Piper)
- Local wake-word detection (`"Hey Mether"`) using `openWakeWord`.
- Low-latency local Speech-to-Text via `faster-whisper` with Hinglish and English multi-language recognition.
- Natural offline Text-to-Speech synthesis via `piper-tts` streaming audio packets to frontend and audio output devices.

### 2. 📱 WhatsApp Autonomous Bridge
- Built on `whatsapp-web.js` running in an isolated sidecar process.
- Autonomous conversation triage: reads incoming messages, categorizes urgency, drafts context-aware replies using your voice and style guidelines, and executes user-approved outbound messages.

### 3. 🛡️ Decision Intelligence Engine (No Hallucinations)
Unlike standard research summarizers that synthesize hallucinations, METHER OS implements an enterprise-grade **12-stage evidence verification pipeline**:
- **Claim Verification**: Every factual statement is decomposed into an atomic Claim object tagged with verified evidence snippets, source quality metrics, and verification states (`Verified`, `Partially Verified`, `Contradicted`, `Hypothesis`, `Unverified`).
- **Zero Hallucination Guarantee**: Strict prohibition on fallback fact generation. If evidence is missing, the system outputs `Unknown`.
- **Source Independence Analysis**: Detects syndication loops, syndicated AP/Reuters wire copies, and circular citations to calculate a true *Source Independence Score*.
- **Contradiction & Consensus Matrix**: Scans numerical values, dates, and causal assertions across divergent sources to expose conflicting data points.
- **Devil's Advocate Skeptic**: Adversarial LLM agent deliberately challenges hypotheses, identifies confirmation bias, and formulates counter-theses.
- **Action Plan Engine**: Synthesizes verified insights into ranked, executable action plans with impact/effort estimations.
- **Human-in-the-Loop Review Gate**: Optional manual review for high-stakes investor, medical, or legal decisions.

### 4. 👔 Autonomous Chief of Staff
- Proactive background monitor scheduling recurring briefings, email triage, and calendar conflicts.
- Priority ranking framework scoring tasks by urgency, impact, and dependencies.

### 5. 💻 Deep Desktop Control
- Execute shell commands with live streaming stdout/stderr back to the HUD.
- Read, search, edit, and index files across your local filesystem.
- Launch applications and capture contextual screenshots for visual QA.

---

## 🛠️ Tech Stack

| Domain | Technologies & Libraries |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS v4, Three.js, React Three Fiber, Framer Motion, Zustand |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, asyncio, Pydantic v2, SQLite, DuckDuckGo API |
| **Voice Sidecar** | Faster-Whisper, Piper TTS, openWakeWord, SoundDevice |
| **Integrations** | WhatsApp Web.js, Google Workspace (Gmail, Calendar, Drive OAuth2) |
| **Architecture** | EventBus pub/sub, WebSocket streaming, modular microservices |

---

## 🚀 Quick Start

### Prerequisites
- **Node.js**: >= 18.0.0
- **Python**: >= 3.11
- **Git**
- *Free API Keys*: NVIDIA NIM, OpenRouter, or Groq (optional, for LLM routing)

### 1. Clone Repository
```bash
git clone https://github.com/MayankSharma-2812/METHER-OS.git
cd METHER-OS
```

### 2. Environment Configuration
```bash
# Copy example environment configuration
cp backend/.env.example backend/.env

# Open backend/.env and populate your preferred LLM endpoint/keys
```

### 3. One-Click Setup (Windows & Linux)

**On Windows:**
```cmd
infra\install.bat
infra\start.bat
```

**On Linux / macOS:**
```bash
bash infra/install.sh
bash infra/start.sh
```

---

## 💻 Manual Setup

If you prefer installing services individually:

### Backend Setup (FastAPI)
```bash
cd backend
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -e .

# Launch FastAPI backend
uvicorn mether.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Setup (Vite + React 19)
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** in your browser to access the METHER Tactical HUD.

### Testing & Verification
```bash
# Verify backend syntax
python -m py_compile backend/src/mether/main.py

# Verify frontend types and production build
cd frontend
npm run type-check
npm run build
```

---

## 📁 Repository Structure

```text
METHER-OS/
├── backend/                  # Python FastAPI core backend
│   ├── src/mether/
│   │   ├── agent/            # Core reasoning agent loop & tool orchestrator
│   │   ├── api/              # REST v1 endpoints & WebSocket handlers
│   │   ├── memory/           # Persistent context, SQLite state, vector store
│   │   ├── services/
│   │   │   ├── chief_of_staff/ # Proactive task queue & automated briefings
│   │   │   └── research/     # 12-stage Decision Intelligence Engine
│   │   └── tools/            # Native tool execution (system, web, google, etc.)
│   └── pyproject.toml        # Backend Python dependencies
├── frontend/                 # Tactical Cyber HUD (React 19, TS, Three.js)
│   ├── src/
│   │   ├── components/       # HUD panels, 3D Neural Orb, Decision Intelligence UI
│   │   ├── hooks/            # WebSocket telemetry & audio handlers
│   │   ├── layouts/          # Full-screen responsive HUD shell
│   │   └── stores/           # Zustand state slices
│   ├── README.md             # Frontend specific documentation
│   └── package.json          # Frontend dependencies & build scripts
├── voice/                    # Offline voice sidecar (Whisper STT + Piper TTS)
├── whatsapp/                 # WhatsApp Web.js communication bridge
├── docs/                     # Architectural specifications & guides
│   ├── ARCHITECTURE.md       # Deep architectural overview
│   ├── CONFIGURATION.md      # Configuration & environment variables
│   ├── DESIGN_SYSTEM.md      # Cyberpunk HUD styling standards
│   └── TOOL_DEVELOPMENT.md   # How to build custom tools in 20 lines
├── infra/                    # One-click startup and installer scripts
└── README.md                 # Master project documentation
```

---

## 🧰 Available Tools & Extensibility

| Tool Identifier | Capability & Functionality |
|---|---|
| `filesystem` | Sandboxed reading, writing, and fuzzy-searching across workspace directories |
| `code_run` | Real-time command execution in PowerShell / Bash with streamed output |
| `app_launch` | Launch native system desktop applications and utilities |
| `screenshot` | Capture display frames for multi-modal analysis and vision debugging |
| `whatsapp` | Inbound/outbound WhatsApp messaging, message triage, and automated replies |
| `gmail` | Query mailboxes, read threads, compose emails, and manage priority labels |
| `calendar` | Query calendar availability, resolve scheduling conflicts, and book events |
| `drive` | Index, search, and download documents from Google Drive |
| `clipboard` | Read and write system clipboard data |

Adding a custom tool takes fewer than 20 lines of Python. See [`docs/TOOL_DEVELOPMENT.md`](docs/TOOL_DEVELOPMENT.md).

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a dedicated feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'feat: add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

Please review [`CONTRIBUTING.md`](CONTRIBUTING.md) for style conventions and test guidelines.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.

---

<div align="center">

**Built with passion by [Mayank Sharma](https://github.com/MayankSharma-2812)**  
*B.Tech Computer Science — Kalvium × JECRC University*

[⭐ Star on GitHub](https://github.com/MayankSharma-2812/METHER-OS) • [Report Bug](https://github.com/MayankSharma-2812/METHER-OS/issues) • [Request Feature](https://github.com/MayankSharma-2812/METHER-OS/issues)

</div>
