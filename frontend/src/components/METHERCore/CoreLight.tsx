import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface CoreLightProps {
  state: string
}

const INTENSITIES: Record<string, { key: number; fill: number; point: number }> = {
  idle:       { key: 3, fill: 1.5, point: 4 },
  listening:  { key: 6, fill: 2.5, point: 8 },
  processing: { key: 4, fill: 2,   point: 6 },
  speaking:   { key: 9, fill: 4,   point: 12 },
  sleeping:   { key: 1, fill: 0.5, point: 1.5 },
}

export default function CoreLight({ state }: CoreLightProps) {
  const light1Ref = useRef<THREE.PointLight>(null!)
  const light2Ref = useRef<THREE.PointLight>(null!)
  const timeRef = useRef(0)

  const cfg = INTENSITIES[state] ?? INTENSITIES.idle
  const color = state === 'processing' ? '#8b5cf6' : '#4cd7f6'
  const fillColor = state === 'processing' ? '#c084fc' : '#a8edfc'

  useFrame((_, delta) => {
    timeRef.current += delta
    const t = timeRef.current

    if (light1Ref.current) {
      light1Ref.current.position.x = Math.cos(t * 0.5) * 3
      light1Ref.current.position.z = Math.sin(t * 0.5) * 3
      light1Ref.current.intensity += (cfg.key - light1Ref.current.intensity) * 0.02
    }
    if (light2Ref.current) {
      light2Ref.current.position.x = Math.cos(t * 0.3 + Math.PI) * 2
      light2Ref.current.position.y = Math.sin(t * 0.4) * 2
      light2Ref.current.intensity += (cfg.fill - light2Ref.current.intensity) * 0.02
    }
  })

  return (
    <>
      <ambientLight intensity={0.3} color="#0a1a2a" />
      <pointLight
        ref={light1Ref}
        color={color}
        intensity={cfg.key}
        distance={8}
        decay={2}
      />
      <pointLight
        ref={light2Ref}
        color={fillColor}
        intensity={cfg.fill}
        distance={6}
        decay={2}
      />
      {/* Static back rim light */}
      <pointLight
        position={[0, 2, -3]}
        color={state === 'processing' ? '#6d28d9' : '#0ea5e9'}
        intensity={cfg.point}
        distance={10}
        decay={2}
      />
    </>
  )
}
