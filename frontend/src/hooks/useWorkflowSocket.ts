import { useEffect, useRef, useState } from 'react'

interface PipelineEvent {
  stage: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  timestamp: string
  data?: Record<string, unknown>
}

export function useWorkflowSocket(applicationId: string | undefined) {
  const [events, setEvents] = useState<PipelineEvent[]>([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!applicationId) return

    // TODO: Connect to ws://backend-api/ws/{applicationId}
    //       Parse incoming messages as PipelineEvent, append to events list
    //       Reconnect on close with exponential back-off

    return () => {
      wsRef.current?.close()
    }
  }, [applicationId])

  return { events, connected }
}
