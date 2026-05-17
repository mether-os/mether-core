# METHER OS — Frontend

> Personal AI Operating System with a tactical sci-fi HUD interface.

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| **Framework** | React 19 + TypeScript |
| **Bundler** | Vite 8 |
| **Styling** | Tailwind CSS v4 (custom tactical theme) |
| **Animations** | Framer Motion |
| **State** | Zustand |
| **Icons** | Lucide React |
| **Routing** | React Router DOM v7 |
| **Real-time** | WebSocket (proxied through Vite) |

## Quick Start

```bash
# Install dependencies
npm install

# Start dev server (default: http://localhost:5173)
npm run dev

# Type-check without emitting
npm run typecheck

# Lint
npm run lint

# Production build
npm run build
```

## Project Structure

```
frontend/
├── public/                 # Static assets (favicon, icons.svg)
├── src/
│   ├── assets/             # Images, icons, sounds
│   │   ├── icons/
│   │   └── sounds/
│   ├── components/         # Reusable UI components
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Third-party wrappers & utilities
│   ├── pages/              # Route-level page components
│   ├── stores/             # Zustand state stores
│   ├── styles/             # Additional style modules (if needed)
│   ├── types/              # Shared TypeScript type definitions
│   ├── utils/              # Pure utility functions
│   ├── App.tsx             # Root application shell
│   ├── main.tsx            # React DOM entry point
│   └── index.css           # Tailwind v4 theme + HUD design system
├── index.html              # HTML shell with Google Fonts
├── vite.config.ts          # Vite config (Tailwind plugin, aliases, proxy)
├── tsconfig.json           # TypeScript project references
├── tsconfig.app.json       # App-level TS config (paths, strict)
├── tsconfig.node.json      # Node-level TS config (vite.config)
├── eslint.config.js        # ESLint flat config
└── package.json
```

## Design System

The interface follows a **Tactical Intelligence HUD** aesthetic — dark void backgrounds, cyan neon data, monospaced readouts, and angular geometry.

### Theme Colors

| Token | Hex | Role |
| --- | --- | --- |
| `void` | `#050810` | Primary background |
| `surface` | `#10131c` | Panel backgrounds |
| `surface-container` | `#1c2028` | Elevated containers |
| `primary` | `#4cd7f6` | Main interactive cyan |
| `primary-container` | `#06b6d4` | Deeper cyan accent |
| `secondary` | `#adc6ff` | Blue data accent |
| `on-surface` | `#e0e2ee` | Primary text |
| `on-surface-variant` | `#bcc9cd` | Secondary text |
| `outline` | `#869397` | Borders, metadata |
| `error` | `#ffb4ab` | Error states |
| `success` | `#10B981` | Success indicators |
| `warning` | `#F59E0B` | Warning states |

### Typography

- **Headlines:** Space Grotesk (700/600/500) — angular, uppercase command headers
- **Body & Data:** JetBrains Mono (400/700) — monospaced telemetry readouts

### HUD Utility Classes

| Class | Purpose |
| --- | --- |
| `.hud-panel` | Dark surface + 1px cyan border container |
| `.hud-label` | Uppercase, tracked, mono, cyan label |
| `.hud-metric` | Bold, large, glowing cyan metric |
| `.hud-button` | Rectangular, cyan border, fills on hover |
| `.hud-terminal` | Dark bg, mono, scrollable terminal feed |
| `.hud-chip` | Small tag (variants: `--success`, `--warning`, `--error`) |
| `.hud-corner-bracket` | L-shaped corner decorations |
| `.hud-grid` | Repeating tactical grid background |

### Animations (Tailwind `animate-*`)

| Class | Effect |
| --- | --- |
| `animate-breathe` | Slow opacity + scale pulse (orb) |
| `animate-ring-spin` | Continuous rotation (orb rings) |
| `animate-ring-spin-reverse` | Counter-rotation (outer rings) |
| `animate-flicker` | Stuttery terminal flicker |
| `animate-scan` | Vertical scan line |
| `animate-type-in` | Typewriter for log entries |
| `animate-pulse-glow` | Box-shadow pulsing glow |
| `animate-fade-in` | Opacity entrance |
| `animate-slide-up` | Slide-up entrance |

### Typography Presets

`.text-headline-xl` · `.text-headline-lg` · `.text-headline-md` · `.text-body-lg` · `.text-body-md` · `.text-label-caps` · `.text-data-mono`

### Effects

`.glow-cyan` · `.glow-cyan-intense` · `.glow-blue` · `.text-glow-cyan` · `.scan-line-overlay` · `.noise-overlay`

## Path Aliases

`@/` maps to `src/` — use `@/components/MyComponent` instead of relative paths.

## Backend Proxy

Vite proxies these routes to `http://localhost:8000`:
- `/api/*` → REST API
- `/ws/*` → WebSocket

---

*Built for the void. Designed for precision.*
