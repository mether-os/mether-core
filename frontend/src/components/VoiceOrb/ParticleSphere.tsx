import { Canvas } from '@react-three/fiber'
import { EffectComposer, Bloom, ChromaticAberration } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import { Vector2 } from 'three'
import SphereCore from './SphereCore'
import EnergyRibbons from './EnergyRibbons'
import StarField from './StarField'

type OrbState = 'sleeping' | 'idle' | 'listening' | 'processing' | 'speaking'

// State config — controls glow intensity, rotation speed, ribbon intensity
const STATE_CONFIG = {
  sleeping:   { bloom: 0.5, speed: 0.05, ribbonOpacity: 0.2, chromaticOffset: 0.0005 },
  idle:       { bloom: 1.2, speed: 0.12, ribbonOpacity: 0.6, chromaticOffset: 0.001 },
  listening:  { bloom: 1.8, speed: 0.25, ribbonOpacity: 0.9, chromaticOffset: 0.002 },
  processing: { bloom: 2.2, speed: 0.45, ribbonOpacity: 1.0, chromaticOffset: 0.003 },
  speaking:   { bloom: 2.8, speed: 0.35, ribbonOpacity: 1.0, chromaticOffset: 0.004 },
}

export default function ParticleSphere({ state }: { state: OrbState }) {
  const cfg = STATE_CONFIG[state] || STATE_CONFIG.idle

  return (
    <Canvas
      camera={{ position: [0, 0, 3.2], fov: 50 }}
      style={{ width: '360px', height: '360px', background: 'transparent' }}
      gl={{ 
        alpha: true, 
        antialias: true,
        powerPreference: 'default',
        preserveDrawingBuffer: false,
      }}
      dpr={Math.min(typeof window !== 'undefined' ? window.devicePixelRatio : 2, 2)}
      frameloop="always"
      performance={{ min: 0.5 }}
    >
      {/* Minimal lighting — particles are self-illuminated */}
      <ambientLight intensity={0.05} />
      
      {/* Star field background */}
      <StarField />
      
      {/* Main particle sphere */}
      <SphereCore state={state} speed={cfg.speed} />
      
      {/* Energy ribbons wrapping the sphere */}
      <EnergyRibbons state={state} opacity={cfg.ribbonOpacity} />
      
      {/* Post processing — this is what makes it cinematic */}
      <EffectComposer>
        <Bloom
          intensity={cfg.bloom}
          luminanceThreshold={0.08}
          luminanceSmoothing={0.95}
          mipmapBlur
          radius={0.8}
        />
        <ChromaticAberration
          blendFunction={BlendFunction.NORMAL}
          offset={new Vector2(cfg.chromaticOffset, cfg.chromaticOffset)}
        />
      </EffectComposer>
    </Canvas>
  )
}
