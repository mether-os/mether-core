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
      className="relative w-full h-full flex items-center justify-center"
      onClick={onActivate}
      style={{ cursor: onActivate ? 'pointer' : undefined }}
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
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                className="w-[2px] bg-primary rounded-none"
                style={{
                  height: `${30 + Math.random() * 70}%`,
                  animation: `waveform ${0.25 + Math.random() * 0.5}s ease-in-out infinite alternate`,
                  animationDelay: `${i * 0.04}s`,
                  opacity: 0.6 + Math.random() * 0.4,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
