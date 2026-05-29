import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { createNoise3D } from 'simplex-noise'

const createPRNG = (seed: number) => {
  let s = seed
  return () => {
    s = (s * 9301 + 49297) % 233280
    return s / 233280
  }
}

interface NebulaParticlesProps {
  state: string
}

export default function NebulaParticles({ state }: NebulaParticlesProps) {
  const innerRef = useRef<THREE.Points>(null!)
  const outerRef = useRef<THREE.Points>(null!)
  const timeRef = useRef(0)
  const frameCount = useRef(0)
  const noise3D = useMemo(() => createNoise3D(), [])

  // Inner shell — 2000 particles tightly around the sphere
  const inner = useMemo(() => {
    const random = createPRNG(42)
    const count = 2000
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const speeds = new Float32Array(count)

    for (let i = 0; i < count; i++) {
      const phi = Math.acos(1 - 2 * (i + 0.5) / count)
      const theta = Math.PI * (1 + Math.sqrt(5)) * i
      const r = 1.15 + random() * 0.4

      pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta)
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      pos[i * 3 + 2] = r * Math.cos(phi)

      const t = (pos[i * 3 + 1] + 1.5) / 3
      col[i * 3]     = 0.2 + t * 0.35
      col[i * 3 + 1] = 0.7 - t * 0.35
      col[i * 3 + 2] = 0.85 + t * 0.15

      speeds[i] = 0.3 + random() * 0.7
    }
    return { pos, col, speeds, count }
  }, [])

  // Outer nebula — 1200 particles in a large cloud
  const outer = useMemo(() => {
    const random = createPRNG(1337)
    const count = 1200
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      const theta = random() * Math.PI * 2
      const phi = Math.acos(2 * random() - 1)
      const r = 2.0 + random() * 2.5

      pos[i * 3]     = r * Math.sin(phi) * Math.cos(theta)
      pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta) * 0.65
      pos[i * 3 + 2] = r * Math.cos(phi)

      const isCyan = random() > 0.45
      if (isCyan) {
        col[i * 3] = 0.12 + random() * 0.15
        col[i * 3 + 1] = 0.7 + random() * 0.25
        col[i * 3 + 2] = 0.88 + random() * 0.12
      } else {
        col[i * 3] = 0.4 + random() * 0.3
        col[i * 3 + 1] = 0.1 + random() * 0.2
        col[i * 3 + 2] = 0.7 + random() * 0.28
      }
    }
    return { pos, col, count }
  }, [])

  // Buffer geometries
  const innerGeo = useMemo(() => {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(inner.pos.slice(), 3))
    g.setAttribute('color', new THREE.BufferAttribute(inner.col.slice(), 3))
    return g
  }, [inner])

  const outerGeo = useMemo(() => {
    const g = new THREE.BufferGeometry()
    g.setAttribute('position', new THREE.BufferAttribute(outer.pos.slice(), 3))
    g.setAttribute('color', new THREE.BufferAttribute(outer.col.slice(), 3))
    return g
  }, [outer])

  useFrame((_, delta) => {
    frameCount.current++
    // Only update particle positions every OTHER frame for performance
    if (frameCount.current % 2 !== 0) {
      // Still rotate even on skipped frames
      if (innerRef.current) {
        const sp = state === 'speaking' ? 2.2 : state === 'listening' ? 1.6 : state === 'processing' ? 1.3 : 0.7
        innerRef.current.rotation.y += delta * 0.08 * sp
        innerRef.current.rotation.x += delta * 0.03 * sp
      }
      if (outerRef.current) {
        outerRef.current.rotation.y += delta * 0.02
        outerRef.current.rotation.z += delta * 0.008
      }
      timeRef.current += delta
      return
    }

    timeRef.current += delta
    const t = timeRef.current
    const sp = state === 'speaking' ? 2.2 : state === 'listening' ? 1.6 : state === 'processing' ? 1.3 : 0.7

    // Inner particles — rotate + noise displacement
    if (innerRef.current) {
      innerRef.current.rotation.y += delta * 0.08 * sp
      innerRef.current.rotation.x += delta * 0.03 * sp

      const arr = innerRef.current.geometry.attributes.position.array as Float32Array
      const base = inner.pos

      for (let i = 0; i < inner.count; i++) {
        const bx = base[i * 3], by = base[i * 3 + 1], bz = base[i * 3 + 2]
        const n = noise3D(bx * 0.5 + t * 0.2, by * 0.5, bz * 0.5) * 0.12

        const pullFactor = state === 'listening' ? 0.88
          : state === 'speaking' ? 1.12
          : 1.0

        arr[i * 3]     = bx * pullFactor + n
        arr[i * 3 + 1] = by * pullFactor + n
        arr[i * 3 + 2] = bz * pullFactor + n
      }
      innerRef.current.geometry.attributes.position.needsUpdate = true
    }

    // Outer nebula — slow drift
    if (outerRef.current) {
      outerRef.current.rotation.y += delta * 0.02
      outerRef.current.rotation.z += delta * 0.008

      const arr = outerRef.current.geometry.attributes.position.array as Float32Array
      const base = outer.pos
      for (let i = 0; i < outer.count; i++) {
        const bx = base[i * 3], by = base[i * 3 + 1], bz = base[i * 3 + 2]
        const n = noise3D(bx * 0.3 + t * 0.05, by * 0.3, bz * 0.3) * 0.06
        arr[i * 3]     = bx + n
        arr[i * 3 + 1] = by + n
        arr[i * 3 + 2] = bz + n
      }
      outerRef.current.geometry.attributes.position.needsUpdate = true
    }
  })

  const innerOpacity = state === 'sleeping' ? 0.3 : state === 'speaking' ? 0.95 : 0.72
  const outerOpacity = state === 'sleeping' ? 0.08 : state === 'speaking' ? 0.55 : 0.28

  return (
    <>
      {/* Inner particle shell */}
      <points ref={innerRef} geometry={innerGeo}>
        <pointsMaterial
          vertexColors
          size={0.022}
          sizeAttenuation
          transparent
          opacity={innerOpacity}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* Outer nebula field */}
      <points ref={outerRef} geometry={outerGeo}>
        <pointsMaterial
          vertexColors
          size={0.014}
          sizeAttenuation
          transparent
          opacity={outerOpacity}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>
    </>
  )
}
