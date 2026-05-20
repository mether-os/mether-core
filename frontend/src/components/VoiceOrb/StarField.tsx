import { useMemo, useEffect } from 'react'
import * as THREE from 'three'

export default function StarField() {
  const { positions, colors } = useMemo(() => {
    const count = 1200
    const positions = new Float32Array(count * 3)
    const colors = new Float32Array(count * 3)

    for (let i = 0; i < count; i++) {
      // Random positions in a large sphere around the scene
      const r = 4 + Math.random() * 6
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)

      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = r * Math.cos(phi)

      // Stars are mostly white/blue with occasional pink
      const isCool = Math.random() > 0.15
      if (isCool) {
        const brightness = 0.6 + Math.random() * 0.4
        colors[i * 3] = brightness * 0.7
        colors[i * 3 + 1] = brightness * 0.8
        colors[i * 3 + 2] = brightness
      } else {
        // Warm pink star
        colors[i * 3] = 0.8 + Math.random() * 0.2
        colors[i * 3 + 1] = 0.3 + Math.random() * 0.2
        colors[i * 3 + 2] = 0.7 + Math.random() * 0.3
      }
    }

    return { positions, colors }
  }, [])

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    return geo
  }, [positions, colors])

  const material = useMemo(() => new THREE.PointsMaterial({
    size: 0.015,
    transparent: true,
    opacity: 0.7,
    vertexColors: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: true,
  }), [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      geometry.dispose()
      material.dispose()
    }
  }, [geometry, material])

  return <points geometry={geometry} material={material} />
}
