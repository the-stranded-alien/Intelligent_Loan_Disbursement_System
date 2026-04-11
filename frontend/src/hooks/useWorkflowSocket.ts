import { useEffect, useRef, useState } from 'react'

export interface PipelineEvent {
  event: string
  application_id?: string
  stage?: string
  status?: 'pending' | 'in_progress' | 'completed' | 'failed'
  timestamp?: string
  session_id?: string
  opening?: string
  reason?: string
  data?: Record<string, unknown>
}

export function useWorkflowSocket(applicationId: string | undefined) {
  const [events, setEvents] = useState<PipelineEvent[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const attempts = useRef(0)
  const dead = useRef(false)   // set on unmount — prevents reconnect loop

  useEffect(() => {
    if (!applicationId) return

    dead.current = false
    attempts.current = 0

    function connect() {
      if (dead.current) return

      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${protocol}://${window.location.host}/ws/${applicationId}`)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        attempts.current = 0
      }

      ws.onmessage = (e) => {
        try {
          const msg: PipelineEvent = JSON.parse(e.data)
          setEvents((prev) => [msg, ...prev].slice(0, 50))
        } catch {}
      }

      ws.onclose = () => {
        setConnected(false)
        if (dead.current) return   // intentional close — do not reconnect
        const delay = Math.min(1000 * 2 ** attempts.current, 30000)
        attempts.current += 1
        reconnectTimer.current = setTimeout(connect, delay)
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      dead.current = true
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [applicationId])

  return { events, connected }
}
