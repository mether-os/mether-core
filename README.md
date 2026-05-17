# mether-core
AI Operating System inspired by Jarvis — modular assistant architecture with voice, automation, memory, and agent orchestration.

## HOW TO RUN
```bash
cd backend
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your proxy URL
uvicorn src.mether.main:app --reload --port 8000
```
