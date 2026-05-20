import { Suspense, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMetherStore } from '@/stores/metherStore'
import ParticleSphere from './ParticleSphere'

export type OrbState = 'sleeping' | 'idle' | 'listening' | 'processing' | 'speaking'

export interface VoiceOrbProps {
  state?: OrbState
  onActivate?: () => void
}

const STATE_LABELS: Record<OrbState, string> = {
  sleeping: 'SLEEPING',
  idle: 'STANDBY',
  listening: 'LISTENING',
  processing: 'PROCESSING',
  speaking: 'SPEAKING',
}

const STATE_COLORS: Record<OrbState, string> = {
  sleeping: '#475569',
  idle: '#4cd7f6',
  listening: '#a78bfa',
  processing: '#c084fc',
  speaking: '#22d3ee',
}

export default function VoiceOrb({ state: propState, onActivate }: VoiceOrbProps) {
  const storeState = useMetherStore(s => s.orbState) as OrbState
  const state = propState ?? storeState

  // Detect WebGL support
  const hasWebGL = useMemo(() => {
    try {
      const canvas = document.createElement('canvas')
      return !!(
        window.WebGLRenderingContext &&
        (canvas.getContext('webgl') || canvas.getContext('experimental-webgl'))
      )
    } catch { return false }
  }, [])

  if (!hasWebGL) {
    return (
      <div className="flex items-center justify-center w-80 h-80">
        <div className="hud-label">:: WEBGL UNAVAILABLE</div>
      </div>
    )
  }

  return (
    <div className="relative flex flex-col items-center">
      <div 
        className="relative w-[360px] h-[360px] flex items-center justify-center cursor-pointer"
        onClick={onActivate}
      >
        <Suspense fallback={
          <div className="w-80 h-80 flex items-center justify-center">
            <div className="hud-label animate-pulse">:: INITIALIZING CORE...</div>
          </div>
        }>
          <ParticleSphere state={state} />
        </Suspense>
      </div>

      {/* State label below orb */}
      <div className="mt-4 flex flex-col items-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={state}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.3 }}
            className="text-[11px] font-mono tracking-[0.2em] font-bold select-none pointer-events-none"
            style={{ color: STATE_COLORS[state] }}
          >
            :: {STATE_LABELS[state]}
            {state === 'processing' && (
              <motion.span
                animate={{ opacity: [0, 1, 0] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
              >
                ...
              </motion.span>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
