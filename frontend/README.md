# METHER OS — Frontend (Tactical Cyber HUD)

The frontend client for **METHER OS** — an enterprise-grade tactical Cyberpunk HUD interface designed for real-time human-agent collaboration, multi-modal status monitoring, and deep decision intelligence.

Built with **React 19**, **TypeScript**, **Tailwind CSS v4**, **Three.js / React Three Fiber**, **Zustand**, and **Framer Motion**.

---

## 🚀 Key Features

- **Holographic 3D Neural Orb**: Interactive Three.js/Fiber visualizer reflecting agent thinking states, audio reactivity, and idle/processing modes.
- **Decision Intelligence Console**: 12-stage research inspection suite featuring:
  - Claim Verification Layer (cross-validation, evidence snippets, source quality metrics)
  - Evidence Vault with direct cryptographic URLs and source inspectability
  - Contradiction & Consensus Matrix
  - Source Independence Network Graph (syndication detection & circular reporting protection)
  - Devil's Advocate Skeptic Engine (adverse perspectives & counter-evidence)
  - Action Plan Engine (prioritized next steps, estimated effort/impact)
  - Human-in-the-loop Evidence Review Gate
- **Autonomous Chief of Staff**: Priority queue view, scheduled automations, briefing summaries, and actionable task dispatch.
- **Cyber HUD Layout**: Modular 3-column tactical dashboard with collapsible activity logs, tool telemetry, process monitors, and voice state visualizers.
- **Real-Time WebSocket Link**: Bidirectional telemetry streaming agent events, execution logs, and research progress over FastAPI WebSocket.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | [React 19](https://react.dev/) + [Vite](https://vitejs.dev/) |
| **Language** | [TypeScript](https://www.typescriptlang.org/) (Strict Mode) |
| **Styling** | [Tailwind CSS v4](https://tailwindcss.com/) |
| **3D Rendering** | [Three.js](https://threejs.org/) + [@react-three/fiber](https://docs.pmnd.rs/react-three-fiber) + [@react-three/drei](https://github.com/pmndrs/drei) |
| **State Management** | [Zustand](https://zustand-demo.pmnd.rs/) (Slices for Agent, Audio, Research, HUD, Chief of Staff) |
| **Animations** | [Framer Motion](https://www.framer.com/motion/) |
| **Icons** | [Lucide React](https://lucide.dev/) |

---

## 📁 Project Structure

```text
frontend/
├── src/
│   ├── assets/                # Static icons, sounds, and graphics
│   ├── components/
│   │   ├── ChiefOfStaff/      # Chief of Staff dashboard & approval workflows
│   │   ├── ResearchPipeline/  # Decision Intelligence HUD & evidence viewer
│   │   ├── holographic/       # Three.js 3D Neural Orb canvas & shaders
│   │   ├── panels/            # LeftPanel, CenterPanel, RightPanel, VoiceHUD
│   │   └── ui/                # Cyberpunk HUD cards, badges, buttons, meters
│   ├── hooks/                 # WebSocket streaming, audio recorder, hotkeys
│   ├── layouts/               # HUDLayout full-screen responsive shell
│   ├── stores/                # Zustand stores (agentStore, researchStore, hudStore, etc.)
│   ├── types/                 # Shared TypeScript interfaces & protocol payloads
│   ├── App.tsx                # App root & modal mount points
│   └── main.tsx               # DOM bootstrap
├── eslint.config.js           # ESLint 9 configuration
├── package.json               # Dependencies & scripts
├── tsconfig.json              # Project references root
├── tsconfig.app.json          # Client build TypeScript configuration
├── tsconfig.node.json         # Tooling / Vite TypeScript configuration
└── vite.config.ts             # Vite bundler configuration & plugins
```

---

## ⚡ Getting Started

### Prerequisites
- **Node.js**: >= 18.0.0 (Node 20+ recommended)
- **npm** or **pnpm** / **yarn**

### 1. Installation
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

### 2. Run Development Server
```bash
npm run dev
```
The application will launch at `http://localhost:5173`. Ensure the METHER OS backend is running on `http://127.0.0.1:8000` for live telemetry.

### 3. Build for Production
```bash
npm run build
```
Generates production-optimized bundles in `frontend/dist/`.

### 4. Available Scripts

| Script | Command | Purpose |
|---|---|---|
| `dev` | `vite` | Start local development server with HMR |
| `build` | `tsc -b && vite build` | Type-check project and produce production bundle |
| `preview` | `vite preview` | Locally preview production build |
| `lint` | `eslint src` | Run ESLint across TypeScript source files |
| `type-check`| `tsc --noEmit` | Check TypeScript typing without generating emit files |

---

## 🔗 Connected Backend

The frontend communicates with METHER OS backend via:
- **WebSocket**: `ws://127.0.0.1:8000/api/v1/ws` (real-time agent thoughts, audio frequency data, research status)
- **REST API**: `http://127.0.0.1:8000/api/v1` (task dispatch, research outline approvals, deliverable downloads)

---

## 📄 License

MIT © [Mayank Sharma](https://github.com/MayankSharma-2812)
