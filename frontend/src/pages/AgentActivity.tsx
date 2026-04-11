import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bot, Mail, Activity, RefreshCw, CheckCircle2,
  AlertCircle, Clock, ChevronRight, Loader2, Radio,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Types ──────────────────────────────────────────────────────────────────

interface AgentLog {
  application_id: string
  full_name: string
  event_type: string
  actor: string
  payload: Record<string, unknown>
  at: string | null
}

interface AgentData {
  monitoring: { total_flagged: number; recent: AgentLog[] }
  outreach:   { total_sent: number;    recent: AgentLog[] }
  pipeline:   { total_node_completions: number; recent: AgentLog[] }
  assessment: { awaiting_chat: number }
}

// ── Helpers ────────────────────────────────────────────────────────────────

function relTime(iso: string | null): string {
  if (!iso) return '—'
  const diff = (Date.now() - new Date(iso).getTime()) / 1000
  if (diff < 5)    return 'just now'
  if (diff < 60)   return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return new Date(iso).toLocaleDateString()
}

const STAGE_LABEL: Record<string, string> = {
  lead_capture: 'Eligibility Check', lead_qualification: 'Doc Verification',
  identity_verification: 'KYC', credit_assessment: 'Credit Assessment',
  art_negotiation: 'ART & Offer', enach: 'e-NACH Setup', esign: 'E-Sign',
}

function stageFromEvent(eventType: string): string {
  const m = eventType.match(/^stage\.(.+)\.completed$/)
  return m ? (STAGE_LABEL[m[1]] ?? m[1]) : eventType
}

const URGENCY_COLOR: Record<string, string> = {
  high:   'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10',
  medium: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10',
  low:    'text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-white/[0.04]',
}

// ── Sub-components ─────────────────────────────────────────────────────────

function StatCard({
  icon: Icon, label, value, color, sub,
}: {
  icon: React.ElementType; label: string; value: number | string; color: string; sub?: string
}) {
  return (
    <div className="card p-5 flex items-center gap-4">
      <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', color)}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{label}</p>
        {sub && <p className="text-[10px] text-slate-400 dark:text-slate-600 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

function SectionHeader({ icon: Icon, title, color }: { icon: React.ElementType; title: string; color: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className={cn('w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0', color)}>
        <Icon size={13} className="text-white" />
      </div>
      <h2 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">{title}</h2>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────

export default function AgentActivity() {
  const navigate = useNavigate()
  const [data, setData]       = useState<AgentData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [lastFetch, setLastFetch] = useState<Date | null>(null)

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/v1/analytics/background-agents')
      if (!res.ok) throw new Error(`Error ${res.status}`)
      setData(await res.json())
      setLastFetch(new Date())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load agent activity')
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial load + 10s polling
  useEffect(() => {
    load()
    const t = setInterval(() => load(true), 10_000)
    return () => clearInterval(t)
  }, [load])

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-slide-up">

      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Background Agents</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Live activity from monitoring, outreach, and pipeline agents.
          </p>
        </div>
        <div className="flex items-center gap-2 mt-1">
          {lastFetch && (
            <span className="text-[11px] text-slate-400 hidden sm:block">
              Updated {relTime(lastFetch.toISOString())}
            </span>
          )}
          <div className="flex items-center gap-1 text-[11px] text-emerald-500 bg-emerald-50 dark:bg-emerald-500/10 px-2 py-1 rounded-full">
            <Radio size={10} className="animate-pulse" />
            Polling 10s
          </div>
          <button
            onClick={() => load()}
            disabled={loading}
            className="p-2 rounded-xl bg-slate-100 dark:bg-white/[0.06] hover:bg-slate-200 dark:hover:bg-white/[0.1] transition-colors disabled:opacity-40"
          >
            <RefreshCw size={14} className={cn('text-slate-600 dark:text-slate-400', loading && 'animate-spin')} />
          </button>
        </div>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* ── Loading skeleton ── */}
      {loading && !data && (
        <div className="flex items-center justify-center py-16 gap-2 text-slate-400">
          <Loader2 size={18} className="animate-spin" />
          Loading agent activity…
        </div>
      )}

      {data && (
        <>
          {/* ── Stat Cards ── */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              icon={Activity}
              label="Apps flagged stale"
              value={data.monitoring.total_flagged}
              color="bg-orange-100 dark:bg-orange-500/20 text-orange-600 dark:text-orange-400"
              sub="by monitoring agent"
            />
            <StatCard
              icon={Mail}
              label="Outreach messages sent"
              value={data.outreach.total_sent}
              color="bg-emerald-100 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400"
              sub="via email + SMS"
            />
            <StatCard
              icon={CheckCircle2}
              label="Pipeline nodes completed"
              value={data.pipeline.total_node_completions}
              color="bg-brand-100 dark:bg-brand-500/20 text-brand-600 dark:text-brand-400"
              sub="across all applications"
            />
            <StatCard
              icon={Bot}
              label="Awaiting AI chat"
              value={data.assessment.awaiting_chat}
              color="bg-violet-100 dark:bg-violet-500/20 text-violet-600 dark:text-violet-400"
              sub="info_requested status"
            />
          </div>

          {/* ── Main grid: Monitoring + Outreach ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* Monitoring Agent */}
            <div className="card p-5">
              <SectionHeader icon={Activity} title="Monitoring Agent" color="bg-orange-500" />
              {data.monitoring.recent.length === 0 ? (
                <p className="text-xs text-slate-400 py-4 text-center">No stale applications flagged yet.</p>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {data.monitoring.recent.map((log, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 p-2.5 rounded-xl hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors group cursor-pointer"
                      onClick={() => navigate(`/status/${log.application_id}`)}
                    >
                      <div className="w-2 h-2 rounded-full bg-orange-400 mt-1.5 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate">
                          {log.full_name}
                        </p>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          Stale {log.payload.hours_stale}h · status: {log.payload.status as string}
                          {log.payload.outreach_attempt ? ` · attempt ${log.payload.outreach_attempt}` : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 flex-shrink-0">
                        <span className="text-[10px] text-slate-300 dark:text-slate-600">{relTime(log.at)}</span>
                        <ChevronRight size={11} className="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Outreach Agent */}
            <div className="card p-5">
              <SectionHeader icon={Mail} title="Outreach Agent" color="bg-emerald-500" />
              {data.outreach.recent.length === 0 ? (
                <p className="text-xs text-slate-400 py-4 text-center">No outreach messages sent yet.</p>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {data.outreach.recent.map((log, i) => {
                    const urgency = (log.payload.urgency as string) || 'medium'
                    return (
                      <div
                        key={i}
                        className="flex items-start gap-3 p-2.5 rounded-xl hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors group cursor-pointer"
                        onClick={() => navigate(`/status/${log.application_id}`)}
                      >
                        <div className="w-2 h-2 rounded-full bg-emerald-400 mt-1.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate">
                              {log.full_name}
                            </p>
                            <span className={cn('text-[10px] px-1.5 py-0.5 rounded-full font-medium flex-shrink-0', URGENCY_COLOR[urgency] ?? URGENCY_COLOR.medium)}>
                              {urgency}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                            {log.payload.subject as string}
                          </p>
                          <p className="text-[10px] text-slate-400 mt-0.5">
                            Attempt {log.payload.attempt as number}
                            {log.payload.sms_preview ? ` · "${log.payload.sms_preview}"` : ''}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          <span className="text-[10px] text-slate-300 dark:text-slate-600">{relTime(log.at)}</span>
                          <ChevronRight size={11} className="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* ── Pipeline node completions ── */}
          <div className="card p-5">
            <SectionHeader icon={CheckCircle2} title="Pipeline Agent — Recent Node Completions" color="bg-brand-500" />
            {data.pipeline.recent.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No pipeline activity yet.</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
                {data.pipeline.recent.map((log, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 p-2.5 rounded-xl hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors group cursor-pointer"
                    onClick={() => navigate(`/status/${log.application_id}`)}
                  >
                    <CheckCircle2 size={13} className="text-emerald-500 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-slate-700 dark:text-slate-300 truncate">
                        {stageFromEvent(log.event_type)}
                      </p>
                      <p className="text-[10px] text-slate-400 truncate">{log.full_name}</p>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <Clock size={10} className="text-slate-300" />
                      <span className="text-[10px] text-slate-300 dark:text-slate-600">{relTime(log.at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
