'use client'
import { Suspense, useMemo, useRef, useState, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import * as THREE from 'three'
import { AnimatePresence, motion } from 'framer-motion'
import { useMetherStore } from '@/stores/metherStore'

export type OrbState = 'sleeping' | 'idle' | 'listening' | 'processing' | 'speaking'

export interface VoiceOrbProps {
  state?: OrbState
  onActivate?: () => void
}

// ---- STAR FIELD ----
function Stars() {
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry()
    const n = 1500
    const pos = new Float32Array(n * 3)
    const col = new Float32Array(n * 3)
    for (let i = 0; i < n; i++) {
      const r = 5 + Math.random() * 8
      const t = Math.random() * Math.PI * 2
      const p = Math.acos(2 * Math.random() - 1)
      pos[i*3]   = r * Math.sin(p) * Math.cos(t)
      pos[i*3+1] = r * Math.sin(p) * Math.sin(t)
      pos[i*3+2] = r * Math.cos(p)
      const isPink = Math.random() < 0.12
      col[i*3]   = isPink ? 0.95 : 0.5 + Math.random() * 0.5
      col[i*3+1] = isPink ? 0.2  : 0.6 + Math.random() * 0.4
      col[i*3+2] = isPink ? 0.8  : 0.9 + Math.random() * 0.1
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    g.setAttribute('color',    new THREE.BufferAttribute(col, 3))
    return g
  }, [])

  return (
    <points geometry={geo}>
      <pointsMaterial
        size={0.018}
        vertexColors
        transparent
        opacity={0.75}
        blending={THREE.AdditiveBlending}
        depthWrite={false}
        sizeAttenuation
      />
    </points>
  )
}

// ---- MAIN SPHERE BODY (fibonacci distribution, 10000 particles) ----
function Spherebody({ state }: { state: string }) {
  const ref = useRef<THREE.Points>(null!)
  const matRef = useRef<THREE.ShaderMaterial>(null!)
  const clock = useRef(0)

  const currentEnergy = useRef(0.4)
  const currentSpeed  = useRef(0.12)
  const currentBreath = useRef(1.0)

  const { geo } = useMemo(() => {
    const N = 10000
    const pos   = new Float32Array(N * 3)
    const col   = new Float32Array(N * 3)
    const sizes = new Float32Array(N)
    const phi   = Math.PI * (3 - Math.sqrt(5)) // golden angle

    for (let i = 0; i < N; i++) {
      const y     = 1 - (i / (N - 1)) * 2
      const rad   = Math.sqrt(Math.max(0, 1 - y * y))
      const theta = phi * i
      const jitter = 0.06 * (Math.random() - 0.5)
      const r = 1.0 + jitter

      pos[i*3]   = Math.cos(theta) * rad * r
      pos[i*3+1] = y * r
      pos[i*3+2] = Math.sin(theta) * rad * r

      // Color: cyan top, blue mid, purple bottom + pink accents
      const h = (y + 1) / 2 // 0-1
      const isAccent = Math.random() < 0.07

      if (isAccent) {
        col[i*3] = 0.88; col[i*3+1] = 0.15; col[i*3+2] = 0.85 // pink
        sizes[i] = 0.014 + Math.random() * 0.008
      } else if (h > 0.65) {
        col[i*3] = 0.1;  col[i*3+1] = 0.82; col[i*3+2] = 0.95 // cyan
        sizes[i] = 0.005 + Math.random() * 0.005
      } else if (h > 0.35) {
        col[i*3] = 0.18; col[i*3+1] = 0.35; col[i*3+2] = 0.92 // blue
        sizes[i] = 0.004 + Math.random() * 0.006
      } else {
        col[i*3] = 0.55; col[i*3+1] = 0.12; col[i*3+2] = 0.82 // purple
        sizes[i] = 0.005 + Math.random() * 0.007
      }
    }

    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    geo.setAttribute('color',    new THREE.BufferAttribute(col, 3))
    geo.setAttribute('aSize',    new THREE.BufferAttribute(sizes, 1))
    return { geo }
  }, [])

  const mat = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      uTime:     { value: 0 },
      uBreath:   { value: 1 },
      uEnergy:   { value: 0.4 },
      uColorMix: { value: 0.0 },
    },
    vertexShader: /* glsl */`
      attribute float aSize;
      attribute vec3 color;
      varying   vec3 vCol;
      uniform  float uTime;
      uniform  float uBreath;
      uniform  float uEnergy;
      uniform  float uColorMix;

      void main() {
        // Shift colors toward purple/warm when uColorMix > 0
        vCol = mix(color, vec3(color.r + 0.3, color.g * 0.3, color.b * 0.8), uColorMix * 0.4);
        vec3 p = position * uBreath;

        // Per-particle noise displacement
        float noise =
          sin(position.x * 4.0 + uTime * 0.6) *
          cos(position.y * 4.0 + uTime * 0.5) *
          sin(position.z * 3.5 + uTime * 0.7);
        p += normalize(position) * noise * 0.035 * uEnergy;

        vec4 mv = modelViewMatrix * vec4(p, 1.0);
        gl_PointSize = aSize * (300.0 / -mv.z);
        gl_Position  = projectionMatrix * mv;
      }
    `,
    fragmentShader: /* glsl */`
      varying vec3 vCol;
      void main() {
        vec2  c    = gl_PointCoord - 0.5;
        float d    = length(c);
        if (d > 0.5) discard;
        float str  = pow(1.0 - d * 2.0, 1.8);
        gl_FragColor = vec4(vCol, str * 0.92);
      }
    `,
    transparent:  true,
    depthWrite:   false,
    blending:     THREE.AdditiveBlending,
    vertexColors: true,
  }), [])

  matRef.current = mat

  const speedMap: Record<string, number> = {
    sleeping: 0.04, idle: 0.12, listening: 0.28, processing: 0.5, speaking: 0.38
  }
  const energyMap: Record<string, number> = {
    sleeping: 0.15, idle: 0.4, listening: 0.75, processing: 0.95, speaking: 1.0
  }

  useFrame((_, dt) => {
    clock.current += dt
    const t = clock.current
    const targetEnergy = energyMap[state] ?? 0.4
    const targetSpeed  = speedMap[state]  ?? 0.12
    const targetMix = state === 'processing' ? 1.0
      : state === 'listening' ? 0.7
      : state === 'speaking'  ? 0.3
      : 0.0

    // Lerp speed & energy: 0.025 = smooth ~1.5s transition
    currentEnergy.current += (targetEnergy - currentEnergy.current) * 0.025
    currentSpeed.current  += (targetSpeed  - currentSpeed.current)  * 0.025
    mat.uniforms.uColorMix.value += (targetMix - mat.uniforms.uColorMix.value) * 0.02

    // Lerp breath scale dynamically
    let targetBreath = 1.0 + Math.sin(t * 0.9) * 0.022
    if (state === 'speaking') {
      targetBreath *= 1.0 + Math.sin(t * 11) * 0.035 + Math.sin(t * 7) * 0.018
    }
    currentBreath.current += (targetBreath - currentBreath.current) * 0.025

    ref.current.rotation.y += 0.004 * currentSpeed.current * 8
    ref.current.rotation.x += 0.0015 * currentSpeed.current * 8

    mat.uniforms.uTime.value   = t
    mat.uniforms.uEnergy.value = currentEnergy.current
    mat.uniforms.uBreath.value = currentBreath.current
  })

  // Cleanup geometries & shaders
  useMemo(() => {
    return () => {
      geo.dispose()
      mat.dispose()
    }
  }, [geo, mat])

  return <points ref={ref} geometry={geo} material={mat} frustumCulled={false} />
}

// ---- ENERGY RIBBONS ----
function Ribbon({
  tiltX, tiltZ, speed, phaseOffset, color1, color2, particleCount, state
}: {
  tiltX: number; tiltZ: number; speed: number; phaseOffset: number
  color1: string; color2: string; particleCount: number; state: string
}) {
  const ref   = useRef<THREE.Points>(null!)
  const matRef = useRef<THREE.PointsMaterial>(null!)
  const t = useRef(phaseOffset)
  const currentSpeed = useRef(0.9)
  const currentOpacity = useRef(0.85)

  const geo = useMemo(() => {
    const N   = particleCount
    const pos = new Float32Array(N * 3)
    const col = new Float32Array(N * 3)
    const c1  = new THREE.Color(color1)
    const c2  = new THREE.Color(color2)

    for (let i = 0; i < N; i++) {
      const angle    = (i / N) * Math.PI * 2
      const bandW    = (Math.random() - 0.5) * 0.14
      const r        = 1.03 + Math.abs(bandW) * 0.5
      pos[i*3]   = Math.cos(angle) * r
      pos[i*3+1] = bandW * 2.5 + Math.sin(angle * 2) * 0.06
      pos[i*3+2] = Math.sin(angle) * r

      const edge = Math.abs(bandW) / 0.07
      const c    = c1.clone().lerp(c2, Math.min(1, edge))
      col[i*3] = c.r; col[i*3+1] = c.g; col[i*3+2] = c.b
    }

    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3))
    g.setAttribute('color',    new THREE.BufferAttribute(col, 3))
    return g
  }, [particleCount, color1, color2])

  const mat = useMemo(() => new THREE.PointsMaterial({
    size: 0.009,
    vertexColors: true,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: true,
  }), [])

  matRef.current = mat

  const spdMap: Record<string,number> = {
    sleeping:0.3, idle:0.9, listening:1.6, processing:2.4, speaking:2.0
  }

  useFrame((_, dt) => {
    const targetSpeed = spdMap[state] ?? 1.0
    currentSpeed.current += (targetSpeed - currentSpeed.current) * 0.02
    t.current += dt * speed * currentSpeed.current

    ref.current.rotation.set(tiltX, t.current, tiltZ)

    const targetOpacity = state === 'speaking' ? 1.0
      : state === 'listening' ? 0.95
      : state === 'processing' ? 0.98
      : 0.75

    currentOpacity.current += (targetOpacity - currentOpacity.current) * 0.03
    const pulse = 0.8 + 0.2 * Math.sin(t.current * 2.5)
    mat.opacity = currentOpacity.current * pulse
  })

  // Cleanup
  useMemo(() => {
    return () => {
      geo.dispose()
      mat.dispose()
    }
  }, [geo, mat])

  return <points ref={ref} geometry={geo} material={mat} frustumCulled={false} />
}

function EnergyRibbons({ state }: { state: string }) {
  const ribbons = [
    { tiltX:  0.45, tiltZ:  0.20, speed:  0.80, phaseOffset: 0,            color1: '#c084fc', color2: '#f0abfc', particleCount: 2500 },
    { tiltX: -0.55, tiltZ:  0.65, speed: -0.62, phaseOffset: Math.PI*0.7,  color1: '#06b6d4', color2: '#a78bfa', particleCount: 2000 },
    { tiltX:  0.80, tiltZ: -0.30, speed:  0.50, phaseOffset: Math.PI*1.4,  color1: '#e879f9', color2: '#c084fc', particleCount: 1600 },
  ]
  return (
    <group>
      {ribbons.map((r, i) => (
        <Ribbon key={i} {...r} state={state} />
      ))}
    </group>
  )
}

// ---- SCENE ----
function BloomController({ 
  state, 
  bloomRef 
}: { 
  state: string
  bloomRef: React.MutableRefObject<number>
}) {
  const targetMap: Record<string, number> = {
    sleeping: 0.6, idle: 1.4, listening: 2.0, processing: 2.6, speaking: 3.2
  }

  useFrame(() => {
    const target = targetMap[state] ?? 1.4
    bloomRef.current += (target - bloomRef.current) * 0.018
  })

  return null
}

function Scene({ state }: { state: string }) {
  const [bloomVal, setBloomVal] = useState(1.4)
  const bloomRef = useRef(1.4)

  useEffect(() => {
    const id = setInterval(() => {
      setBloomVal(prev => {
        const diff = bloomRef.current - prev
        if (Math.abs(diff) < 0.01) return bloomRef.current
        return prev + diff * 0.15
      })
    }, 16) // ~60fps
    return () => clearInterval(id)
  }, [])

  return (
    <>
      <ambientLight intensity={0.04} />
      <Stars />
      <Spherebody state={state} />
      <EnergyRibbons state={state} />
      <BloomController state={state} bloomRef={bloomRef} />
      <EffectComposer>
        <Bloom
          intensity={bloomVal}
          luminanceThreshold={0.05}
          luminanceSmoothing={0.92}
          mipmapBlur
          radius={0.85}
        />
      </EffectComposer>
    </>
  )
}

// ---- STATE LABEL ----
const STATE_META: Record<string, { label: string; color: string }> = {
  sleeping:   { label: ':: SLEEPING',   color: '#475569' },
  idle:       { label: ':: STANDBY',    color: '#4cd7f6' },
  listening:  { label: ':: LISTENING',  color: '#a78bfa' },
  processing: { label: ':: PROCESSING', color: '#c084fc' },
  speaking:   { label: ':: SPEAKING',   color: '#22d3ee' },
}

// ---- MAIN EXPORT ----
export default function VoiceOrb({
  state: propState,
  onActivate
}: VoiceOrbProps) {
  const storeState = useMetherStore(s => s.orbState)
  const state = propState ?? storeState ?? 'idle'
  const meta  = STATE_META[state] ?? STATE_META.idle

  const hasWebGL = useMemo(() => {
    try {
      const c = document.createElement('canvas')
      return !!(window.WebGLRenderingContext &&
        (c.getContext('webgl') || c.getContext('experimental-webgl')))
    } catch { return false }
  }, [])

  if (!hasWebGL) {
    return (
      <div className="flex items-center justify-center w-80 h-80">
        <p className="hud-label">:: WEBGL UNAVAILABLE</p>
      </div>
    )
  }

  return (
    <div onClick={onActivate} className="relative flex flex-col items-center select-none cursor-pointer">
      {/* Ambient glow behind canvas */}
      <motion.div
        className="absolute pointer-events-none"
        animate={{
          background: state === 'speaking'
            ? 'radial-gradient(ellipse 65% 65% at 50% 50%, rgba(167,139,250,0.13) 0%, rgba(76,215,246,0.08) 45%, transparent 75%)'
            : state === 'listening'
            ? 'radial-gradient(ellipse 65% 65% at 50% 50%, rgba(167,139,250,0.10) 0%, rgba(76,215,246,0.06) 45%, transparent 75%)'
            : state === 'processing'
            ? 'radial-gradient(ellipse 65% 65% at 50% 50%, rgba(192,132,252,0.12) 0%, rgba(167,139,250,0.05) 45%, transparent 75%)'
            : state === 'sleeping'
            ? 'radial-gradient(ellipse 65% 65% at 50% 50%, rgba(167,139,250,0.03) 0%, rgba(76,215,246,0.02) 45%, transparent 75%)'
            : 'radial-gradient(ellipse 65% 65% at 50% 50%, rgba(167,139,250,0.06) 0%, rgba(76,215,246,0.04) 45%, transparent 75%)',
        }}
        transition={{ duration: 1.8, ease: 'easeInOut' }}
        style={{ inset: 0, zIndex: 0 }}
      />

      <Suspense fallback={
        <div className="w-[380px] h-[380px] flex items-center justify-center">
          <p className="hud-label animate-pulse">:: INITIALIZING CORE...</p>
        </div>
      }>
        <Canvas
          camera={{ position: [0, 0, 3.4], fov: 48 }}
          style={{ width: 380, height: 380, background: 'transparent', zIndex: 1 }}
          gl={{ alpha: true, antialias: true, powerPreference: 'default' }}
          dpr={[1, 2]}
          frameloop="always"
          performance={{ min: 0.5 }}
        >
          <Scene state={state} />
        </Canvas>
      </Suspense>

      {/* State label */}
      <AnimatePresence mode="wait">
        <motion.p
          key={state}
          initial={{ opacity: 0, y: 6, filter: 'blur(4px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          exit={{   opacity: 0, y: -6, filter: 'blur(4px)' }}
          transition={{ duration: 0.4, ease: 'easeInOut' }}
          className="font-mono text-[11px] tracking-[0.22em] uppercase mt-1"
          style={{ color: meta.color, zIndex: 2, position: 'relative' }}
        >
          {meta.label}
        </motion.p>
      </AnimatePresence>

      {/* Waveform bars for listening/speaking */}
      <AnimatePresence>
        {(state === 'listening' || state === 'speaking') && (
          <motion.div
            key="waveform"
            initial={{ opacity: 0, scaleY: 0.3, y: 4 }}
            animate={{ opacity: 1, scaleY: 1,   y: 0 }}
            exit={{   opacity: 0, scaleY: 0.3,  y: 4 }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
            className="flex gap-[3px] mt-2 items-end h-6"
            style={{ zIndex: 2 }}
          >
            {Array.from({ length: 14 }).map((_, i) => (
              <div
                key={i}
                className="w-[3px] rounded-none"
                style={{
                  background: i % 2 === 0 ? '#4cd7f6' : '#a78bfa',
                  height: '60%',
                  animation: `waveform ${0.28 + (i * 0.03)}s ease-in-out infinite alternate`,
                  animationDelay: `${i * 0.04}s`,
                }}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
