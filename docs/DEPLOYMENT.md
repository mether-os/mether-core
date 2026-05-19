# Deployment Guide for METHER OS

METHER OS can be deployed locally for personal use or on a cloud provider like Render.

## Local Deployment

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (optional, for sidecars)

### Step 1: Clone and Install
```bash
git clone https://github.com/yourusername/mether-core.git
cd mether-core
./infra/install.bat  # On Windows
# or
./infra/install.sh   # On Linux/macOS
```

### Step 2: Configure
Copy `.env.example` to `.env` in `backend/`, `frontend/`, `voice/`, and `whatsapp/` folders.
Fill in the required API keys and configuration.

### Step 3: Start
```bash
./infra/start.bat
```

## Cloud Deployment (Render)

METHER OS is designed to be easily deployable on Render.

1. Create a new Web Service on Render.
2. Connect your GitHub repository.
3. Use the `render.yaml` provided in the root.
4. Set the Environment Variables as listed in `docs/CONFIGURATION.md`.

## Docker Deployment

You can use `docker-compose.yml` to start the entire stack:
```bash
docker-compose up -d
```

## Production Considerations

- **Security:** Ensure `LLM_PROXY_URL` is protected if exposed.
- **Persistence:** Use persistent disks for `CLAUDE.md` and Google OAuth tokens.
- **Monitoring:** The `/health` endpoint can be used for uptime monitoring.
