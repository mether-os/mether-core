import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface EnergyRingsProps {
  state: string
}

export default function EnergyRings({ state }: EnergyRingsProps) {
  const ring1Ref = useRef<THREE.Mesh>(null!)
  const ring2Ref = useRef<THREE.Mesh>(null!)
  const ring3Ref = useRef<THREE.Mesh>(null!)
  const dot1Ref = useRef<THREE.Mesh>(null!)
  const dot2Ref = useRef<THREE.Mesh>(null!)
  const dot3Ref = useRef<THREE.Mesh>(null!)
  const timeRef = useRef(0)

  const rings = useMemo(() => {
    return {
      r1: new THREE.TorusGeometry(1.45, 0.004, 8, 128),
      r2: new THREE.TorusGeometry(1.62, 0.004, 8, 128),
      r3: new THREE.TorusGeometry(1.78, 0.004, 8, 128),
    }
  }, [])

  const ringColor = state === 'processing' ? '#8b5cf6'
    : state === 'sleeping' ? '#0a3040'
    : '#4cd7f6'

  const ringOpacity = state === 'sleeping' ? 0.12 : 0.55

  useFrame((_, delta) => {
    timeRef.current += delta
    const t = timeRef.current
    const sp = state === 'speaking' ? 2.5 : state === 'listening' ? 1.8 : state === 'processing' ? 1.4 : 0.8

    if (ring1Ref.current) ring1Ref.current.rotation.y += delta * 0.25 * sp
    if (ring2Ref.current) {
      ring2Ref.current.rotation.x += delta * 0.18 * sp
      ring2Ref.current.rotation.y -= delta * 0.12 * sp
    }
    if (ring3Ref.current) ring3Ref.current.rotation.z += delta * 0.15 * sp

    // Data-flow dots racing along ring paths
    if (dot1Ref.current) {
      const angle = t * 2.2 * sp
      dot1Ref.current.position.set(
        Math.cos(angle) * 1.45,
        Math.sin(angle) * 1.45,
        0
      )
    }
    if (dot2Ref.current) {
      const angle = t * 1.6 * sp + 2
      dot2Ref.current.position.set(
        Math.cos(angle) * 1.62,
        0,
        Math.sin(angle) * 1.62
      )
    }
    if (dot3Ref.current) {
      const angle = -t * 1.9 * sp + 4
      dot3Ref.current.position.set(
        0,
        Math.cos(angle) * 1.78,
        Math.sin(angle) * 1.78
      )
    }
  })

  return (
    <group>
      <mesh ref={ring1Ref} geometry={rings.r1}>
        <meshBasicMaterial color={ringColor} transparent opacity={ringOpacity} depthWrite={false} />
      </mesh>
      <mesh ref={ring2Ref} geometry={rings.r2} rotation={[Math.PI / 2, 0.3, 0]}>
        <meshBasicMaterial color={ringColor} transparent opacity={ringOpacity} depthWrite={false} />
      </mesh>
      <mesh ref={ring3Ref} geometry={rings.r3} rotation={[0.5, 0, Math.PI / 3]}>
        <meshBasicMaterial color={ringColor} transparent opacity={ringOpacity} depthWrite={false} />
      </mesh>

      {/* Racing data dots */}
      <mesh ref={dot1Ref}>
        <sphereGeometry args={[0.024, 8, 8]} />
        <meshBasicMaterial color={ringColor} transparent opacity={0.9} />
      </mesh>
      <mesh ref={dot2Ref}>
        <sphereGeometry args={[0.018, 8, 8]} />
        <meshBasicMaterial color="#c084fc" transparent opacity={0.9} />
      </mesh>
      <mesh ref={dot3Ref}>
        <sphereGeometry args={[0.021, 8, 8]} />
        <meshBasicMaterial color={ringColor} transparent opacity={0.85} />
      </mesh>
    </group>
  )
}
