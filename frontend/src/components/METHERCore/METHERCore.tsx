'use client'
import { Canvas } from '@react-three/fiber'
import { Bloom, EffectComposer, ChromaticAberration, Vignette } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import { Suspense, useMemo } from 'react'
import { Vector2 } from 'three'
import CoreSphere from './CoreSphere'
import NebulaParticles from './NebulaParticles'
import EnergyRings from './EnergyRings'
import CoreLight from './CoreLight'

interface METHERCoreProps {
  state: 'idle' | 'listening' | 'processing' | 'speaking' | 'sleeping'
  onActivate?: () => void
}

const STATE_GLOW: Record<string, { bg: number; bloom: number }> = {
  idle:       { bg: 0.07, bloom: 1.2 },
  listening:  { bg: 0.14, bloom: 2.0 },
  processing: { bg: 0.11, bloom: 1.6 },
  speaking:   { bg: 0.18, bloom: 2.8 },
  sleeping:   { bg: 0.03, bloom: 0.6 },
}

const chromaticOffset = new Vector2(0.0008, 0.0008)

const WAVEFORM_BARS = [
  { height: 45, duration: 0.45, opacity: 0.8 },
  { height: 85, duration: 0.62, opacity: 0.9 },
  { height: 55, duration: 0.38, opacity: 0.7 },
  { height: 95, duration: 0.71, opacity: 0.95 },
  { height: 65, duration: 0.50, opacity: 0.85 },
  { height: 35, duration: 0.31, opacity: 0.65 },
  { height: 75, duration: 0.58, opacity: 0.88 },
  { height: 50, duration: 0.42, opacity: 0.75 },
  { height: 90, duration: 0.68, opacity: 0.92 },
  { height: 40, duration: 0.35, opacity: 0.7 },
  { height: 80, duration: 0.55, opacity: 0.85 },
  { height: 60, duration: 0.48, opacity: 0.78 },
]

export default function METHERCore({ state, onActivate }: METHERCoreProps) {
  const { bg, bloom } = STATE_GLOW[state] ?? STATE_GLOW.idle

  const hasWebGL = useMemo(() => {
    try {
      const c = document.createElement('canvas')
      return !!(window.WebGLRenderingContext &&
        (c.getContext('webgl') || c.getContext('experimental-webgl')))
    } catch { return false }
  }, [])

  if (!hasWebGL) {
    return (
      <div className="flex items-center justify-center w-full h-full">
        <p className="hud-label">:: WEBGL UNAVAILABLE</p>
      </div>
    )
  }

  return (
    <div
      className="absolute inset-0 flex items-center justify-center"
      onClick={onActivate}
      style={{ cursor: onActivate ? 'pointer' : undefined, minHeight: 300 }}
    >
      {/* Layered ambient glow — 3 radial gradients stacked */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: `
          radial-gradient(ellipse 55% 50% at 50% 50%,
            rgba(76,215,246,${bg * 1.2}) 0%,
            rgba(139,92,246,${bg * 0.8}) 35%,
            transparent 65%),
          radial-gradient(ellipse 80% 75% at 50% 50%,
            rgba(20,40,180,${bg * 0.4}) 0%,
            transparent 70%)
        `,
        transition: 'all 1s ease',
      }} />

      {/* Three.js canvas */}
      <Canvas
        camera={{ position: [0, 0, 3.8], fov: 50 }}
        style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0, background: 'transparent' }}
        gl={{ alpha: true, antialias: true, powerPreference: 'high-performance' }}
        dpr={[1, 1.5]}
        performance={{ min: 0.5 }}
        frameloop="always"
      >
        <Suspense fallback={null}>
          <CoreLight state={state} />
          <EnergyRings state={state} />
          <CoreSphere state={state} />
          <NebulaParticles state={state} />

          <EffectComposer>
            <Bloom
              intensity={bloom}
              luminanceThreshold={0.05}
              luminanceSmoothing={0.85}
              mipmapBlur
              radius={0.75}
            />
            <ChromaticAberration
              blendFunction={BlendFunction.NORMAL}
              offset={chromaticOffset}
            />
            <Vignette
              eskil={false}
              offset={0.15}
              darkness={0.6}
            />
          </EffectComposer>
        </Suspense>
      </Canvas>

      {/* State label */}
      <div className="absolute bottom-8 left-0 right-0 flex flex-col items-center gap-1 pointer-events-none" style={{ zIndex: 2 }}>
        <div className="hud-label text-xs tracking-[0.3em]">
          :: {state.toUpperCase()}
        </div>
        {state === 'listening' && (
          <div className="flex gap-[3px] items-end h-5 mt-1">
            {WAVEFORM_BARS.map((bar, i) => (
              <div
                key={i}
                className="w-[2px] bg-primary rounded-none"
                style={{
                  height: `${bar.height}%`,
                  animation: `waveform ${bar.duration}s ease-in-out infinite alternate`,
                  animationDelay: `${i * 0.04}s`,
                  opacity: bar.opacity,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
