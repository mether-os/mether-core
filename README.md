<div align="center">
  <h1>METHER OS</h1>
  <p><strong>Personal AI Operating System — Your own Jarvis</strong></p>
  
  <img src="docs/assets/mether-demo.png" alt="METHER OS Dashboard" width="800"/>
  
  <p>
    <a href="https://github.com/mether-os/mether-core/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-yellow.svg" />
    </a>
    <a href="https://github.com/mether-os/mether-core/actions">
      <img src="https://github.com/mether-os/mether-core/workflows/Backend%20CI/badge.svg" />
    </a>
    <a href="https://github.com/mether-os/mether-core/stargazers">
      <img src="https://img.shields.io/github/stars/mether-os/mether-core" />
    </a>
  </p>
</div>

## What is METHER OS?

METHER OS is a self-hosted personal AI operating system with:

- 🎙️ **Voice control** — "Hey Jarvis" wake word, Whisper STT, Piper TTS
- 💬 **WhatsApp automation** — read, send, auto-reply on your behalf
- 🖥️ **System control** — open apps, run code, manage files via voice/text
- 📧 **Google integration** — Gmail, Calendar, Drive
- 🧠 **Persistent memory** — knows your projects, priorities, contacts
- ⚡ **Tactical HUD dashboard** — React + Framer Motion sci-fi interface
- 🔒 **100% self-hosted** — your data never leaves your machine
- 💸 **Free** — runs on free LLM APIs (NVIDIA NIM, OpenRouter)

## Architecture

Voice → [Whisper STT] → Backend Agent → [LLM via free proxy] → Tools
Web UI → [WebSocket] → Backend Agent → [Gmail/Calendar/Drive/System/WhatsApp]
WhatsApp → [Node.js bridge] → Backend Agent → [Auto-reply]

5 layers: Input → Brain → Tools → Output → Infra

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for full breakdown.

## Quick Start

### Prerequisites
- Windows 10/11 or Linux
- Python 3.11+
- Node.js 18+
- Git

### Install

```bash
git clone https://github.com/mether-os/mether-core.git
cd mether-core
infra\install.bat        # Windows
# or: bash infra/start.sh  # Linux
```

### Configure

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — add your NVIDIA NIM or OpenRouter key
```

Get a free API key:
- NVIDIA NIM: https://build.nvidia.com/settings/api-keys
- OpenRouter: https://openrouter.ai/keys (has free models)

### Run

```bash
infra\start.bat    # Windows
# Opens dashboard at http://localhost:5173
```

### Say "Hey Jarvis"

The voice pipeline starts automatically. Say the wake word and talk.

## Configuration

| File | Purpose |
|------|---------|
| `backend/.env` | API keys, ports, model selection |
| `~/.mether/CLAUDE.md` | Your personal context (who you are, priorities, style) |
| `whatsapp/.env` | WhatsApp bridge config |
| `voice/.env` | Voice pipeline config |

## Services & Ports

| Service | Port | Purpose |
|---------|------|---------|
| Frontend | 5173 | React HUD dashboard |
| Backend | 8000 | FastAPI agent + WebSocket |
| LLM Proxy | 8082 | Routes to free LLM APIs |
| WhatsApp | 3001 | whatsapp-web.js bridge |

## Tools Available

| Tool | What it does |
|------|-------------|
| `gmail` | Search, read, send, reply to emails |
| `calendar` | View and create Google Calendar events |
| `drive` | Search and read Google Drive files |
| `whatsapp` | Send messages, manage chats, auto-reply |
| `app_launch` | Open any application |
| `code_run` | Execute shell commands and scripts |
| `filesystem` | Read files, list dirs, search |
| `process` | List processes, kill apps, system info |
| `clipboard` | Read/write clipboard |
| `screenshot` | Take screenshots |
| `system_info` | CPU, RAM, uptime |

## Adding New Tools

```python
from mether.tools.base import BaseTool, ToolResult, SecurityLevel

class MyTool(BaseTool):
    name = "my_tool"
    description = "What this tool does"
    security_level = SecurityLevel.READ
    
    async def execute(self, **kwargs) -> ToolResult:
        # Your logic here
        return ToolResult(success=True, data={"result": "..."})
```

Register in `backend/src/mether/main.py`:
```python
registry.register(MyTool())
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md)

## Security

See [SECURITY.md](SECURITY.md)

## License

MIT — see [LICENSE](LICENSE)

---

Built by [Mayank Sharma](https://github.com/Mayank_2812) and contributors.
