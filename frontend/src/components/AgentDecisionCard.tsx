import { useEffect, useState } from 'react'
import { Brain, Clock, User } from 'lucide-react'

interface AuditEntry {
  event: string
  actor: string
  payload: Record<string, unknown> | null
  at: string
}

interface Context {
  application: Record<string, unknown>
  audit_trail: AuditEntry[]
}

interface Props {
  applicationId: string
}

export default function AgentDecisionCard({ applicationId }: Props) {
  const [ctx, setCtx] = useState<Context | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!applicationId) return
    setLoading(true)
    fetch(`/api/v1/rm/${applicationId}/context`)
      .then(r => r.json())
      .then(setCtx)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [applicationId])

  if (!applicationId) return (
    <div className="card p-6 text-center text-slate-400 dark:text-slate-600 text-sm">
      Select an application to view context
    </div>
  )

  if (loading) return (
    <div className="card p-6 text-center text-slate-400 text-sm animate-pulse">Loading context…</div>
  )

  if (!ctx) return (
    <div className="card p-6 text-center text-slate-400 text-sm">No context available</div>
  )

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Brain size={16} className="text-brand-500" />
        <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">AI Decision Trail</h3>
      </div>

      {ctx.audit_trail.length === 0 ? (
        <p className="text-sm text-slate-400">No audit events yet.</p>
      ) : (
        <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
          {ctx.audit_trail.map((entry, i) => (
            <div key={i} className="flex gap-3 text-xs">
              <div className="mt-0.5 w-5 h-5 rounded-full bg-brand-100 dark:bg-brand-500/20 flex items-center justify-center flex-shrink-0">
                <User size={10} className="text-brand-600 dark:text-brand-400" />
              </div>
              <div>
                <p className="font-medium text-slate-700 dark:text-slate-300">{entry.event}</p>
                <p className="text-slate-400 dark:text-slate-500 flex items-center gap-1 mt-0.5">
                  <Clock size={9} />
                  {new Date(entry.at).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
