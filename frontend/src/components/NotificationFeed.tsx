import { useWorkflowSocket } from '@/hooks/useWorkflowSocket'
import { Wifi, WifiOff, Bell } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  applicationId?: string
}

export default function NotificationFeed({ applicationId }: Props) {
  const { events, connected } = useWorkflowSocket(applicationId)

  return (
    <div className="card p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell size={15} className="text-brand-500" />
          <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">Live Updates</h3>
        </div>
        <span className={cn('flex items-center gap-1 text-xs font-medium', connected ? 'text-emerald-500' : 'text-slate-400')}>
          {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
          {connected ? 'Connected' : applicationId ? 'Disconnected' : 'No app selected'}
        </span>
      </div>

      {events.length === 0 ? (
        <p className="text-xs text-slate-400 dark:text-slate-500 text-center py-4">
          {applicationId ? 'Waiting for pipeline events…' : 'Select an application to stream events'}
        </p>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
          {events.map((e, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-500 mt-1.5 flex-shrink-0" />
              <div>
                <span className="font-medium text-slate-700 dark:text-slate-300">{e.event}</span>
                {e.stage && <span className="ml-1 text-slate-400">— {e.stage}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
