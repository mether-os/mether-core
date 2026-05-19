# METHER OS Configuration Reference

## Backend (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| LLM_PROXY_URL | http://localhost:8082 | URL of the free-claude-code proxy |
| LLM_MODEL | nvidia_nim/z-ai/glm4.7 | Model to use for reasoning |
| ANTHROPIC_AUTH_TOKEN | freecc | Auth token for proxy |
| METHER_HOST | 0.0.0.0 | Host to bind backend |
| METHER_PORT | 8000 | Port for backend API |
| CLAUDE_MD_PATH | ~/.mether/CLAUDE.md | Path to personal context file |
| LOG_LEVEL | INFO | Logging level |
| GOOGLE_CREDENTIALS_PATH | ~/.mether/google_credentials.json | OAuth credentials |
| GOOGLE_TOKEN_PATH | ~/.mether/google_token.json | OAuth token (auto-generated) |

## Voice (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| WHISPER_MODEL | base | STT model size (tiny/base/small) |
| WHISPER_LANGUAGE | hi | Language hint (hi=Hindi+English) |
| WAKE_WORD | hey_mether | Wake word to listen for |
| PIPER_EXE | ./bin/piper.exe | Path to Piper TTS binary |
| PIPER_MODEL | ./models/... | Path to voice model |

## Personal Context (CLAUDE.md)

The most important configuration file.
Located at ~/.mether/CLAUDE.md

Sections to fill:
- Identity: your name, location, role
- Current Focus: top 3 priorities
- People: key contacts
- Tools: apps you use daily
- Style: how METHER should communicate
- Hard Rules: things METHER must never do

The richer this file, the more personalized METHER becomes.
