import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

type OrbState = 'sleeping' | 'idle' | 'listening' | 'processing' | 'speaking'

interface RibbonConfig {
  tiltX: number
  tiltZ: number
  speed: number
  color1: THREE.Color // inner glow color
  color2: THREE.Color // outer edge color
  width: number
  particleCount: number
  phaseOffset: number
}

const RIBBON_CONFIGS: RibbonConfig[] = [
  {
    tiltX: 0.4, tiltZ: 0.2,
    speed: 0.8,
    color1: new THREE.Color('#c084fc'), // purple
    color2: new THREE.Color('#e879f9'), // magenta
    width: 0.12,
    particleCount: 2000,
    phaseOffset: 0,
  },
  {
    tiltX: -0.5, tiltZ: 0.6,
    speed: -0.6,
    color1: new THREE.Color('#06b6d4'), // cyan
    color2: new THREE.Color('#a78bfa'), // violet
    width: 0.1,
    particleCount: 1500,
    phaseOffset: Math.PI * 0.7,
  },
  {
    tiltX: 0.8, tiltZ: -0.3,
    speed: 0.5,
    color1: new THREE.Color('#e879f9'), // magenta
    color2: new THREE.Color('#c084fc'), // purple
    width: 0.08,
    particleCount: 1200,
    phaseOffset: Math.PI * 1.4,
  },
]

function Ribbon({ 
  config, 
  opacity,
  globalSpeed,
  state,
}: { 
  config: RibbonConfig
  opacity: number
  globalSpeed: number
  state: OrbState
}) {
  const pointsRef = useRef<THREE.Points>(null)
  const timeRef = useRef(config.phaseOffset)

  const { positions, colors } = useMemo(() => {
    const count = config.particleCount
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      // Distribute particles along the ribbon band
      const t = (i / count) * Math.PI * 2
      
      // Base orbit angle
      const bandWidth = (Math.random() - 0.5) * config.width
      const r = 1.02 + bandWidth // slightly outside sphere surface
      
      positions[i * 3] = Math.cos(t) * r
      positions[i * 3 + 1] = Math.sin(t + bandWidth * 2) * r * 0.3
      positions[i * 3 + 2] = Math.sin(t) * r

      // Color gradient along ribbon
      const edgeFactor = Math.abs(bandWidth) / (config.width * 0.5)
      const c = config.color1.clone().lerp(config.color2, edgeFactor)
      colors[i * 3] = c.r
      colors[i * 3 + 1] = c.g
      colors[i * 3 + 2] = c.b
    }

    return { positions, colors }
  }, [config])

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return geo
  }, [positions, colors])

  const material = useMemo(() => new THREE.PointsMaterial({
    size: 0.008,
    transparent: true,
    opacity: opacity,
    vertexColors: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: true,
  }), [opacity])

  useFrame((_, delta) => {
    if (!pointsRef.current) return
    timeRef.current += delta * config.speed * globalSpeed

    // Rotate the ribbon around the tilted axis
    pointsRef.current.rotation.set(
      config.tiltX,
      timeRef.current,
      config.tiltZ
    )

    // Pulse opacity based on state
    const pulse = 0.7 + 0.3 * Math.sin(timeRef.current * 2 + config.phaseOffset)
    material.opacity = opacity * pulse

    // Speaking: ribbons pulse faster and brighter
    if (state === 'speaking') {
      material.opacity = opacity * (0.8 + 0.2 * Math.sin(timeRef.current * 8))
    }
  })

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      geometry.dispose()
      material.dispose()
    }
  }, [geometry, material])

  return <points ref={pointsRef} geometry={geometry} material={material} />
}

export default function EnergyRibbons({ 
  state, 
  opacity 
}: { 
  state: OrbState
  opacity: number 
}) {
  const speedMultiplier = 
    state === 'processing' ? 2.2 :
    state === 'listening'  ? 1.6 :
    state === 'speaking'   ? 1.8 : 
    state === 'sleeping'   ? 0.4 : 1.0

  return (
    <group>
      {RIBBON_CONFIGS.map((config, i) => (
        <Ribbon
          key={i}
          config={config}
          opacity={opacity}
          globalSpeed={speedMultiplier}
          state={state}
        />
      ))}
    </group>
  )
}
