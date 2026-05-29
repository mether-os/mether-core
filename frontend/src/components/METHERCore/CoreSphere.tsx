import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import { MeshDistortMaterial, Sphere } from '@react-three/drei'
import * as THREE from 'three'

interface CoreSphereProps {
  state: string
}

const STATE_CONFIG: Record<string, { distort: number; speed: number; color: string; emissive: string; scale: number }> = {
  idle:       { distort: 0.35, speed: 0.8,  color: '#0e5a6e', emissive: '#0e4a5e', scale: 1.0 },
  listening:  { distort: 0.55, speed: 1.8,  color: '#1a7a8e', emissive: '#1a6a7e', scale: 1.05 },
  processing: { distort: 0.45, speed: 2.4,  color: '#4a1a7e', emissive: '#3a0a6e', scale: 1.02 },
  speaking:   { distort: 0.65, speed: 3.0,  color: '#1a8a9e', emissive: '#0e6a7e', scale: 1.08 },
  sleeping:   { distort: 0.18, speed: 0.3,  color: '#071a22', emissive: '#050e14', scale: 0.96 },
}

export default function CoreSphere({ state }: CoreSphereProps) {
  const meshRef = useRef<THREE.Mesh>(null!)
  const materialRef = useRef<THREE.Material & { color: THREE.Color; emissive: THREE.Color }>(null!)
  const timeRef = useRef(0)

  const targetColor = useMemo(() => new THREE.Color(), [])
  const targetEmissive = useMemo(() => new THREE.Color(), [])

  const cfg = STATE_CONFIG[state] ?? STATE_CONFIG.idle

  useFrame((_, delta) => {
    timeRef.current += delta
    if (!meshRef.current) return

    // Slow breathing rotation
    meshRef.current.rotation.y += delta * 0.12 * (cfg.speed / 2)
    meshRef.current.rotation.x = Math.sin(timeRef.current * 0.3) * 0.08

    // Scale breathing
    const breathe = 1 + Math.sin(timeRef.current * cfg.speed * 0.5) * 0.025
    meshRef.current.scale.setScalar(breathe * cfg.scale)

    // Smooth material color lerp
    if (materialRef.current) {
      targetColor.set(cfg.color)
      targetEmissive.set(cfg.emissive)
      materialRef.current.color.lerp(targetColor, 0.03)
      materialRef.current.emissive.lerp(targetEmissive, 0.03)
    }
  })

  return (
    <group>
      {/* Main distorted sphere */}
      <Sphere ref={meshRef} args={[1, 128, 128]}>
        <MeshDistortMaterial
          ref={materialRef}
          color={cfg.color}
          emissive={cfg.emissive}
          emissiveIntensity={2.5}
          distort={cfg.distort}
          speed={cfg.speed}
          roughness={0.15}
          metalness={0.8}
          transparent
          opacity={0.88}
          side={THREE.FrontSide}
          envMapIntensity={1.5}
        />
      </Sphere>

      {/* Inner core — brighter, smaller, same distortion */}
      <Sphere args={[0.65, 64, 64]}>
        <MeshDistortMaterial
          color={state === 'processing' ? '#7a3ab0' : '#4cd7f6'}
          emissive={state === 'processing' ? '#5a2a8e' : '#2ab8d0'}
          emissiveIntensity={state === 'speaking' ? 5 : 3}
          distort={cfg.distort * 0.6}
          speed={cfg.speed * 1.4}
          roughness={0}
          metalness={1}
          transparent
          opacity={0.6}
        />
      </Sphere>

      {/* Hot core center */}
      <Sphere args={[0.28, 32, 32]}>
        <meshBasicMaterial
          color={state === 'processing' ? '#c084fc' : state === 'speaking' ? '#ffffff' : '#7fe8f5'}
          transparent
          opacity={0.9}
        />
      </Sphere>
    </group>
  )
}
