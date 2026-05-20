import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

type OrbState = 'sleeping' | 'idle' | 'listening' | 'processing' | 'speaking'

const PARTICLE_COUNT = 8000

export default function SphereCore({ 
  state, 
  speed 
}: { 
  state: OrbState
  speed: number 
}) {
  const pointsRef = useRef<THREE.Points>(null)
  const timeRef = useRef(0)

  // Build sphere particle positions using fibonacci sphere distribution
  // This gives perfectly even distribution unlike random placement
  const { positions, colors, sizes } = useMemo(() => {
    const positions = new Float32Array(PARTICLE_COUNT * 3)
    const colors = new Float32Array(PARTICLE_COUNT * 3)
    const sizes = new Float32Array(PARTICLE_COUNT)

    const goldenAngle = Math.PI * (3 - Math.sqrt(5))
    
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      // Fibonacci sphere — perfect even distribution
      const y = 1 - (i / (PARTICLE_COUNT - 1)) * 2
      const radius = Math.sqrt(1 - y * y)
      const theta = goldenAngle * i

      const x = Math.cos(theta) * radius
      const z = Math.sin(theta) * radius

      // Base radius with subtle noise displacement
      const r = 1.0 + (Math.random() - 0.5) * 0.08

      positions[i * 3] = x * r
      positions[i * 3 + 1] = y * r
      positions[i * 3 + 2] = z * r

      // Color: gradient from cyan (top) through blue (middle) to purple (bottom)
      // Plus some random pink/magenta accent particles
      const heightFactor = (y + 1) / 2 // 0 = bottom, 1 = top
      const isAccent = Math.random() < 0.08 // 8% are bright accent particles

      if (isAccent) {
        // Hot pink / magenta accent
        colors[i * 3] = 0.9 + Math.random() * 0.1
        colors[i * 3 + 1] = 0.1 + Math.random() * 0.2
        colors[i * 3 + 2] = 0.8 + Math.random() * 0.2
      } else {
        // Main body: interpolate cyan → blue → purple by height
        if (heightFactor > 0.6) {
          // Top: cyan
          colors[i * 3] = 0.1 + heightFactor * 0.3
          colors[i * 3 + 1] = 0.7 + heightFactor * 0.3
          colors[i * 3 + 2] = 0.9 + heightFactor * 0.1
        } else if (heightFactor > 0.3) {
          // Middle: blue
          colors[i * 3] = 0.15 + Math.random() * 0.2
          colors[i * 3 + 1] = 0.3 + Math.random() * 0.3
          colors[i * 3 + 2] = 0.85 + Math.random() * 0.15
        } else {
          // Bottom: purple
          colors[i * 3] = 0.4 + Math.random() * 0.3
          colors[i * 3 + 1] = 0.1 + Math.random() * 0.2
          colors[i * 3 + 2] = 0.7 + Math.random() * 0.3
        }
      }

      // Vary particle sizes — accent particles are bigger
      sizes[i] = isAccent 
        ? 0.012 + Math.random() * 0.008
        : 0.004 + Math.random() * 0.006
    }

    return { positions, colors, sizes }
  }, [])

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1))
    return geo
  }, [positions, colors, sizes])

  // Custom shader material for round glowing particles
  const material = useMemo(() => new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uState: { value: 0 }, // 0=idle, 1=listening, 2=processing, 3=speaking
      uBreath: { value: 1.0 },
    },
    vertexShader: `
      attribute float size;
      attribute vec3 color;
      varying vec3 vColor;
      varying float vAlpha;
      uniform float uTime;
      uniform float uBreath;
      
      void main() {
        vColor = color;
        
        // Breathing effect — sphere pulses slightly
        vec3 pos = position * uBreath;
        
        // Subtle noise displacement per particle based on time
        float noise = sin(position.x * 3.0 + uTime * 0.5) * 
                      cos(position.y * 3.0 + uTime * 0.4) * 
                      sin(position.z * 3.0 + uTime * 0.6);
        pos += normalize(position) * noise * 0.04;
        
        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
        gl_PointSize = size * (280.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
        
        // Depth-based alpha — particles at edges slightly transparent
        vAlpha = 0.6 + 0.4 * (1.0 - abs(noise));
      }
    `,
    fragmentShader: `
      varying vec3 vColor;
      varying float vAlpha;
      
      void main() {
        // Round soft particle
        vec2 center = gl_PointCoord - vec2(0.5);
        float dist = length(center);
        if (dist > 0.5) discard;
        
        // Soft glow falloff
        float strength = 1.0 - (dist * 2.0);
        strength = pow(strength, 1.5);
        
        gl_FragColor = vec4(vColor, strength * vAlpha);
      }
    `,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    vertexColors: true,
  }), [])

  useFrame((_, delta) => {
    if (!pointsRef.current) return
    timeRef.current += delta

    const t = timeRef.current
    const stateSpeed = speed

    // Slow Y rotation — main sphere rotation
    pointsRef.current.rotation.y += 0.003 * stateSpeed
    pointsRef.current.rotation.x += 0.001 * stateSpeed

    // Update shader uniforms
    material.uniforms.uTime.value = t

    // Breathing — sphere scale pulses
    const breathScale = 1.0 + Math.sin(t * 0.8) * 0.025
    material.uniforms.uBreath.value = breathScale

    // Speaking: rapid intensity flicker
    if (state === 'speaking') {
      const flicker = 1.0 + Math.sin(t * 12) * 0.04 + Math.sin(t * 7.3) * 0.02
      material.uniforms.uBreath.value = breathScale * flicker
    }
  })

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      geometry.dispose()
      material.dispose()
    }
  }, [geometry, material])

  return (
    <points ref={pointsRef} geometry={geometry} material={material} frustumCulled={false} />
  )
}
