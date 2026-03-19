import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Search, RefreshCw, Banknote, Calendar, User, Copy, Check } from 'lucide-react'
import WorkflowTimeline from '@/components/WorkflowTimeline'
import NotificationFeed from '@/components/NotificationFeed'
import { useWorkflowSocket } from '@/hooks/useWorkflowSocket'
import { cn } from '@/lib/utils'

// ── Types ──────────────────────────────────────────────────────────────────

interface AppStatus {
  application_id: string
  full_name: string
  loan_amount: number
  loan_purpose: string | null
  tenure_months: number | null
  status: string
  current_stage: string | null
  updated_at: string
  created_at: string
}

interface EventEntry {
  event: string
  actor: string
  payload: { stage?: string; result?: Record<string, unknown> } | null
  at: string
}

// ── Constants ──────────────────────────────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
  pending:        'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400',
  approved:       'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400',
  rejected:       'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400',
  disbursed:      'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400',
  completed:      'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400',
  processing:     'bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-400',
  pending_review: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400',
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmt(n: number) {
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(1)}Cr`
  if (n >= 100_000)    return `₹${(n / 100_000).toFixed(1)}L`
  return `₹${Math.round(n).toLocaleString('en-IN')}`
}

// ── Component ──────────────────────────────────────────────────────────────

export default function StatusTracker() {
  const { applicationId: paramId } = useParams<{ applicationId: string }>()
  const navigate = useNavigate()

  const [inputId, setInputId] = useState(paramId ?? '')
  const [appId, setAppId]     = useState(paramId ?? '')
  const [status, setStatus]   = useState<AppStatus | null>(null)
  const [events, setEvents]   = useState<EventEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [copied, setCopied]   = useState(false)

  // Build stageResults from audit events
  const stageResults: Record<string, Record<string, unknown>> = {}
  for (const ev of events) {
    if (ev.event.startsWith('stage.') && ev.event.endsWith('.completed') && ev.payload?.result) {
      const stage = ev.payload.stage
      if (stage) stageResults[stage] = ev.payload.result as Record<string, unknown>
    }
  }

  // ── Live WebSocket — owned here and passed to children ──────────────────
  const { events: wsEvents, connected: wsConnected } = useWorkflowSocket(appId || undefined)
  const lastWsEvent = useRef<typeof wsEvents[0] | null>(null)

  useEffect(() => {
    const latest = wsEvents[0]
    if (!latest || latest === lastWsEvent.current) return
    lastWsEvent.current = latest

    if (latest.event === 'node.completed' && latest.stage) {
      // Immediately advance the current stage shown in the timeline
      setStatus(s => s ? { ...s, current_stage: latest.stage! } : s)
      // Background-fetch updated audit events to populate stage results
      if (appId) {
        fetch(`/api/v1/applications/${appId}/events`)
          .then(r => r.ok ? r.json() : [])
          .then(setEvents)
          .catch(() => {})
      }
    } else if (latest.event === 'pipeline.completed' || latest.event === 'hitl.requested') {
      // Full refetch to get accurate final status
      if (appId) fetchStatus(appId)
    }
  }, [wsEvents])

  async function fetchStatus(id: string) {
    if (!id.trim()) return
    setLoading(true)
    setError('')
    try {
      const [statusRes, eventsRes] = await Promise.all([
        fetch(`/api/v1/applications/${id}/status`),
        fetch(`/api/v1/applications/${id}/events`),
      ])
      if (statusRes.status === 404) throw new Error('Application not found')
      if (!statusRes.ok) throw new Error('Failed to fetch status')
      const [statusData, eventsData] = await Promise.all([
        statusRes.json(),
        eventsRes.ok ? eventsRes.json() : Promise.resolve([]),
      ])
      setStatus(statusData)
      setEvents(eventsData)
      navigate(`/status/${id}`, { replace: true })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setStatus(null)
      setEvents([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { if (paramId) fetchStatus(paramId) }, [])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const id = inputId.trim()
    setAppId(id)
    fetchStatus(id)
  }

  function copyId() {
    if (!status) return
    navigator.clipboard.writeText(status.application_id).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const statusColor = status ? (STATUS_COLORS[status.status] ?? STATUS_COLORS.processing) : ''

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-slide-up">
      {/* ── Title ── */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Track Application</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
          Enter your application ID to see real-time pipeline status.
        </p>
      </div>

      {/* ── Search ── */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={inputId}
            onChange={e => setInputId(e.target.value)}
            className="input pl-9"
            placeholder="Paste application ID…"
          />
        </div>
        <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2 flex-shrink-0">
          {loading
            ? <RefreshCw size={14} className="animate-spin" />
            : <Search size={14} />}
          <span className="hidden sm:inline">Track</span>
        </button>
      </form>

      {/* ── Error ── */}
      {error && (
        <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* ── Results ── */}
      {status && (
        <div className="space-y-4 animate-fade-in">

          {/* Applicant summary bar */}
          <div className="card px-5 py-4 flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-500/20 flex items-center justify-center flex-shrink-0">
                <User size={14} className="text-brand-600 dark:text-brand-400" />
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-slate-800 dark:text-slate-100 text-sm truncate">
                  {status.full_name || 'Unknown Applicant'}
                </p>
                <p className="text-xs text-slate-400">
                  Applied {new Date(status.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>

            {status.loan_amount > 0 && (
              <div className="flex items-center gap-1.5">
                <Banknote size={13} className="text-brand-500" />
                <span className="font-bold text-brand-600 dark:text-brand-400 text-sm">
                  {fmt(status.loan_amount)}
                </span>
                {status.loan_purpose && (
                  <span className="text-xs text-slate-400 hidden sm:inline">
                    — {status.loan_purpose}
                  </span>
                )}
              </div>
            )}

            {status.tenure_months && (
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <Calendar size={12} />
                {status.tenure_months} months
              </div>
            )}

            <span className={cn('badge ml-auto flex-shrink-0', statusColor)}>
              {status.status.replace('_', ' ')}
            </span>
          </div>

          {/* Main grid: timeline + live feed */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

            {/* Timeline */}
            <div className="card p-5 md:col-span-2 space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Pipeline Progress
                </p>
                <button
                  onClick={() => fetchStatus(appId)}
                  className="text-xs text-brand-500 hover:text-brand-600 flex items-center gap-1"
                  disabled={loading}
                >
                  <RefreshCw size={11} className={cn(loading && 'animate-spin')} />
                  Refresh
                </button>
              </div>
              <WorkflowTimeline
                currentStage={status.current_stage}
                applicationStatus={status.status}
                stageResults={Object.keys(stageResults).length > 0 ? stageResults : undefined}
              />

              {/* App ID with copy */}
              <div className="flex items-center gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                <p className="font-mono text-xs text-slate-400 truncate flex-1">{status.application_id}</p>
                <button
                  onClick={copyId}
                  className="text-xs text-slate-400 hover:text-brand-500 flex items-center gap-1 transition-colors flex-shrink-0"
                >
                  {copied ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                  {copied ? 'Copied' : 'Copy ID'}
                </button>
              </div>
            </div>

            {/* Live feed — reuses the same WS connection owned by this page */}
            <div className="min-h-[200px]">
              <NotificationFeed
                applicationId={appId}
                events={wsEvents}
                connected={wsConnected}
              />
            </div>
          </div>

          {/* Stage results section — shown when audit data has AI decisions */}
          {Object.keys(stageResults).length > 0 && (
            <div className="card p-5 space-y-3">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                AI Decisions per Stage
              </p>
              <p className="text-xs text-slate-400">
                Click any completed stage in the timeline above to expand its AI reasoning.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Empty state ── */}
      {!status && !loading && !error && (
        <div className="card p-16 text-center">
          <Search size={36} className="mx-auto text-slate-200 dark:text-slate-700 mb-3" />
          <p className="text-slate-400 text-sm">Enter an application ID above to get started</p>
        </div>
      )}
    </div>
  )
}
