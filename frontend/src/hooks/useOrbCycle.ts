import { useEffect } from 'react'
import { useMetherStore } from '@/stores/metherStore'

export function useOrbCycle() {
  const voiceStatus = useMetherStore(s => s.voiceStatus)
  const isDemo = useMetherStore(s => s.isDemo)
  const setOrbState = useMetherStore(s => s.setOrbState)
  const orbState = useMetherStore(s => s.orbState)

  useEffect(() => {
    if (voiceStatus === 'online') return
    if (!isDemo) return

    const states = ['idle', 'listening', 'processing', 'speaking'] as const
    let i = 0
    const id = setInterval(() => {
      i = (i + 1) % states.length
      setOrbState(states[i])
    }, 4000)

    return () => clearInterval(id)
  }, [voiceStatus, isDemo, setOrbState])

  return orbState
}
