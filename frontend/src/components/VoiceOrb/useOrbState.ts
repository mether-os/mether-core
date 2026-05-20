import { useEffect } from 'react'
import { useMetherStore } from '@/stores/metherStore'

export function useOrbState() {
  const orbState = useMetherStore(s => s.orbState)
  const voiceStatus = useMetherStore(s => s.voiceStatus)
  const setOrbState = useMetherStore(s => s.setOrbState)
  const voiceSidecarOnline = voiceStatus === 'online'

  // Demo cycle when voice is offline
  useEffect(() => {
    if (voiceSidecarOnline) return

    const states = ['idle', 'listening', 'processing', 'speaking'] as const
    let i = 0
    const interval = setInterval(() => {
      i = (i + 1) % states.length
      setOrbState(states[i])
    }, 4000)

    return () => clearInterval(interval)
  }, [voiceSidecarOnline, setOrbState])

  return orbState
}
