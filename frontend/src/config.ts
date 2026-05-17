const config = {
  backendUrl: import.meta.env.VITE_BACKEND_URL || "http://localhost:8000",
  wsUrl: import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws",
  version: import.meta.env.VITE_APP_VERSION || "1.0.0-dev",
  isDev: import.meta.env.DEV,
}

export default config
