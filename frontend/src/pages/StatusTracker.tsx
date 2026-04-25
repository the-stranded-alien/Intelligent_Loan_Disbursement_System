import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Search, RefreshCw, Banknote, Calendar, User, Copy, Check, CheckCircle2, XCircle, Percent, MessageSquare, Upload, FileText, AlertCircle } from 'lucide-react'
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
  payload: { stage?: string; result?: Record<string, unknown>; [key: string]: unknown } | null
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
  info_requested: 'bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400',
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
  const [activeStage, setActiveStage] = useState<string | null>(null)

  // Auto-started assessment session (from assessment_ready WS event)
  const [autoSessionId, setAutoSessionId] = useState<string | null>(null)
  const [assessmentDone, setAssessmentDone] = useState<{ recommendation: string; repayment_confidence: string; notes: string } | null>(null)

  // Document upload state
  const [uploadFile, setUploadFile]     = useState<File | null>(null)
  const [uploadType, setUploadType]     = useState('salary_slip')
  const [uploading, setUploading]       = useState(false)
  const [uploadMsg, setUploadMsg]       = useState('')
  const [uploadError, setUploadError]   = useState('')

  // ── Live WebSocket — owned here and passed to children ──────────────────
  const { events: wsEvents, connected: wsConnected } = useWorkflowSocket(appId || undefined)
  const lastWsEvent = useRef<typeof wsEvents[0] | null>(null)

  useEffect(() => {
    const latest = wsEvents[0]
    if (!latest || latest === lastWsEvent.current) return
    lastWsEvent.current = latest

    if (latest.event === 'node.started' && latest.stage) {
      setActiveStage(latest.stage)
    } else if (latest.event === 'node.completed' && latest.stage) {
      setActiveStage(null)  // node done — clear active indicator
      setStatus(s => s ? { ...s, current_stage: latest.stage! } : s)
      // Background-fetch updated audit events to populate stage result dropdowns
      if (appId) {
        fetch(`/api/v1/applications/${appId}/events`)
          .then(r => r.ok ? r.json() : [])
          .then(setEvents)
          .catch(() => {})
      }
    } else if (latest.event === 'info_requested') {
      setStatus(s => s ? { ...s, status: 'info_requested' } : s)
    } else if (latest.event === 'assessment_ready' && latest.session_id) {
      setAutoSessionId(latest.session_id as string)
    } else if (latest.event === 'assessment.completed') {
      setAutoSessionId(null)
      setAssessmentDone({
        recommendation: (latest as any).recommendation ?? '',
        repayment_confidence: (latest as any).repayment_confidence ?? '',
        notes: (latest as any).assessment_notes ?? '',
      })
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

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!uploadFile || !appId) return
    setUploading(true)
    setUploadMsg('')
    setUploadError('')
    try {
      const form = new FormData()
      form.append('file', uploadFile)
      form.append('document_type', uploadType)
      const res = await fetch(`/api/v1/documents/${appId}/upload`, { method: 'POST', body: form })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Upload failed (${res.status})`)
      }
      setUploadMsg('Document uploaded successfully.')
      setUploadFile(null)
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
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

            {status.status === 'pending_review' && (
              <button
                onClick={() => navigate(`/assessment/${status.application_id}`)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium transition-colors flex-shrink-0"
              >
                <MessageSquare size={12} />
                Start Assessment
              </button>
            )}
          </div>

          {/* ── Eligibility banner ── */}
          {(() => {
            const leadEvent = events.find(e => e.event === 'stage.lead_capture.completed')
            if (!leadEvent?.payload?.result) return null
            const r = leadEvent.payload.result as Record<string, unknown>
            const eligible = r.eligibility_result === 'eligible'
            const ineligible = r.eligibility_result === 'ineligible'
            if (!eligible && !ineligible) return null
            return eligible ? (
              <div className="flex items-start gap-3 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 rounded-xl px-4 py-3">
                <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">Eligible — KYC Step Next</p>
                  <p className="text-xs text-emerald-600 dark:text-emerald-300 mt-0.5">
                    Your application passed initial eligibility. Your identity will be verified next.
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-3 bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl px-4 py-3">
                <XCircle size={16} className="text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-semibold text-red-700 dark:text-red-400">Application Not Eligible</p>
                  {r.eligibility_reason && (
                    <p className="text-xs text-red-600 dark:text-red-300 mt-0.5">{String(r.eligibility_reason)}</p>
                  )}
                </div>
              </div>
            )
          })()}

          {/* ── Assessment Ready Banner (auto-triggered from Node 2 request_info) ── */}
          {autoSessionId && (
            <div className="flex items-center gap-3 bg-violet-50 dark:bg-violet-500/10 border border-violet-200 dark:border-violet-500/30 rounded-xl px-4 py-3">
              <MessageSquare size={16} className="text-violet-600 dark:text-violet-400 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-semibold text-violet-700 dark:text-violet-400">
                  Quick chat required
                </p>
                <p className="text-xs text-violet-600 dark:text-violet-300 mt-0.5">
                  Priya, our AI advisor, is ready to clarify a few details about your application.
                </p>
              </div>
              <button
                onClick={() => navigate(`/assessment/${status.application_id}?session=${autoSessionId}`)}
                className="flex-shrink-0 px-3 py-1.5 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-medium transition-colors"
              >
                Start Chat
              </button>
            </div>
          )}

          {/* ── Assessment Done Banner ── */}
          {assessmentDone && (
            <div className="flex items-start gap-3 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 rounded-xl px-4 py-3">
              <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">
                  Repayment Assessment Complete
                  {assessmentDone.recommendation && (
                    <span className={cn(
                      'ml-2 text-xs font-medium px-2 py-0.5 rounded-full',
                      assessmentDone.recommendation === 'approve'
                        ? 'bg-emerald-100 dark:bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                        : assessmentDone.recommendation === 'reject'
                        ? 'bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-300'
                        : 'bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-300',
                    )}>
                      {assessmentDone.recommendation}
                    </span>
                  )}
                </p>
                {assessmentDone.notes && (
                  <p className="text-xs text-emerald-600 dark:text-emerald-300 mt-0.5">{assessmentDone.notes}</p>
                )}
              </div>
            </div>
          )}

          {/* ── ART Offers Card ── */}
          {(() => {
            const artEvent = events.find(e => e.event === 'stage.art_negotiation.completed')
            if (!artEvent?.payload?.result) return null
            const r = artEvent.payload.result as Record<string, unknown>
            const offers = r.offers as Array<Record<string, unknown>> | undefined
            if (!offers?.length) return null
            return (
              <div className="card p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <Percent size={14} className="text-brand-500" />
                  <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Loan Offers</h3>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {offers.map((offer) => {
                    const opt = String(offer.option ?? '')
                    const recommended = r.recommended_option === opt
                    return (
                      <div
                        key={opt}
                        className={cn(
                          'rounded-xl border p-4 space-y-2 transition-all',
                          recommended
                            ? 'border-brand-400 bg-brand-50 dark:bg-brand-500/10 ring-1 ring-brand-400'
                            : 'border-slate-200 dark:border-slate-700',
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Option {opt}</span>
                          {recommended && (
                            <span className="badge bg-brand-100 dark:bg-brand-500/20 text-brand-700 dark:text-brand-400 text-[10px]">
                              Recommended
                            </span>
                          )}
                        </div>
                        <div className="space-y-1">
                          <p className="text-lg font-bold text-brand-600 dark:text-brand-400">
                            {Number((offer.interest_rate_percent ?? offer.interest_rate) ?? 0).toFixed(1)}%
                            <span className="text-xs font-normal text-slate-400 ml-1">p.a.</span>
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            {offer.tenure_months} months · ₹{Math.round(Number((offer.monthly_emi ?? offer.emi_amount) ?? 0)).toLocaleString('en-IN')}/mo
                          </p>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })()}

          {/* ── Document Upload (shown when info is requested or app is processing) ── */}
          {(status.status === 'info_requested' || status.status === 'processing') && (
            <div className="card p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Upload size={14} className="text-violet-500" />
                <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-100">Upload Document</h3>
              </div>

              {status.status === 'info_requested' && (
                <div className="flex items-start gap-2 bg-violet-50 dark:bg-violet-500/10 rounded-xl px-3 py-2">
                  <AlertCircle size={13} className="text-violet-500 mt-0.5 flex-shrink-0" />
                  <p className="text-xs text-violet-600 dark:text-violet-300">
                    Additional documents are required to continue processing your application.
                  </p>
                </div>
              )}

              <form onSubmit={handleUpload} className="space-y-3">
                <div className="flex gap-2">
                  <select
                    value={uploadType}
                    onChange={e => setUploadType(e.target.value)}
                    className="input text-xs py-1.5 flex-1"
                  >
                    <option value="salary_slip">Salary Slip</option>
                    <option value="itr">ITR</option>
                    <option value="bank_statement">Bank Statement</option>
                    <option value="pan_card">PAN Card</option>
                    <option value="aadhaar">Aadhaar</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-xl p-4 cursor-pointer hover:border-brand-400 transition-colors">
                  <FileText size={20} className="text-slate-300 dark:text-slate-600" />
                  <span className="text-xs text-slate-400">
                    {uploadFile ? uploadFile.name : 'Click to select file (PDF, JPG, PNG)'}
                  </span>
                  <input
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png"
                    className="hidden"
                    onChange={e => setUploadFile(e.target.files?.[0] ?? null)}
                  />
                </label>

                {uploadMsg && (
                  <div className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 size={13} />
                    {uploadMsg}
                  </div>
                )}
                {uploadError && (
                  <div className="flex items-center gap-2 text-xs text-red-500">
                    <XCircle size={13} />
                    {uploadError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={!uploadFile || uploading}
                  className="btn-primary w-full flex items-center justify-center gap-2 text-sm disabled:opacity-50"
                >
                  {uploading
                    ? <><RefreshCw size={13} className="animate-spin" /> Uploading…</>
                    : <><Upload size={13} /> Upload Document</>}
                </button>
              </form>
            </div>
          )}

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
                activeStage={activeStage}
                applicationStatus={status.status}
                auditEvents={events}
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
