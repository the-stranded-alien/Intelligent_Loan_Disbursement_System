import { useEffect, useState } from 'react'
import { Brain, Clock, CheckCircle2, AlertCircle, User, Banknote } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AuditEntry {
  event: string
  actor: string
  payload: Record<string, unknown> | null
  at: string
}

interface AppDetail {
  id: string
  full_name: string
  email: string
  phone: string
  pan_number: string
  loan_amount: number
  loan_purpose: string | null
  tenure_months: number | null
  status: string
  current_stage: string | null
}

interface Context {
  application: AppDetail
  audit_trail: AuditEntry[]
}

interface Props { applicationId: string }

// ── Helpers ────────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  approved:       'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400',
  rejected:       'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400',
  pending_review: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400',
  pending:        'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400',
  completed:      'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400',
}

function fmtAmt(n: number) {
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(1)}Cr`
  if (n >= 100_000)    return `₹${(n / 100_000).toFixed(1)}L`
  return `₹${Math.round(n).toLocaleString('en-IN')}`
}

function EventIcon({ event }: { event: string }) {
  if (event.endsWith('.completed') || event === 'rm_review_submitted')
    return <CheckCircle2 size={12} className="text-emerald-500" />
  return <AlertCircle size={12} className="text-amber-500" />
}

// ── Component ──────────────────────────────────────────────────────────────

export default function AgentDecisionCard({ applicationId }: Props) {
  const [ctx, setCtx]       = useState<Context | null>(null)
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
    <div className="card p-6 text-center text-slate-400 text-sm">
      Select an application to view context
    </div>
  )

  if (loading) return (
    <div className="card p-5 space-y-3 animate-pulse">
      <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded w-1/2" />
      <div className="h-16 bg-slate-100 dark:bg-slate-800 rounded" />
      <div className="h-32 bg-slate-100 dark:bg-slate-800 rounded" />
    </div>
  )

  if (!ctx) return (
    <div className="card p-6 text-center text-slate-400 text-sm">No context available</div>
  )

  const app = ctx.application

  return (
    <div className="card p-5 space-y-4 flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Brain size={15} className="text-brand-500" />
        <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-sm flex-1">AI Decision Trail</h3>
        <span className={cn('badge', STATUS_COLORS[app.status] ?? STATUS_COLORS.pending)}>
          {app.status.replace('_', ' ')}
        </span>
      </div>

      {/* Application summary */}
      <div className="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-3 space-y-2">
        <div className="flex items-center gap-2">
          <User size={13} className="text-slate-400 flex-shrink-0" />
          <span className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{app.full_name}</span>
        </div>
        <div className="flex items-center gap-2">
          <Banknote size={13} className="text-brand-500 flex-shrink-0" />
          <span className="text-sm font-bold text-brand-600 dark:text-brand-400">{fmtAmt(app.loan_amount)}</span>
          {app.loan_purpose && (
            <span className="text-xs text-slate-400 truncate">— {app.loan_purpose}</span>
          )}
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-slate-400">
          <span>PAN: <span className="font-mono text-slate-600 dark:text-slate-300">{app.pan_number}</span></span>
          {app.tenure_months && <span>{app.tenure_months} months</span>}
          {app.current_stage && (
            <span className="text-brand-500">
              @ {app.current_stage.replace(/_/g, ' ')}
            </span>
          )}
        </div>
      </div>

      {/* Audit trail */}
      <div className="flex-1">
        <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
          Pipeline Events
        </p>
        {ctx.audit_trail.length === 0 ? (
          <p className="text-xs text-slate-400 text-center py-4">No events recorded yet</p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
            {ctx.audit_trail.map((entry, i) => (
              <div key={i} className="flex gap-2.5 text-xs">
                <div className="flex-shrink-0 mt-0.5">
                  <EventIcon event={entry.event} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-700 dark:text-slate-300 truncate">
                    {entry.event.replace(/[._]/g, ' ')}
                  </p>
                  <p className="text-slate-400 flex items-center gap-1 mt-0.5">
                    <Clock size={9} />
                    {new Date(entry.at).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
