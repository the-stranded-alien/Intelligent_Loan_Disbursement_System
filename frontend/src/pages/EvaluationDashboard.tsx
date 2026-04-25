import { useEffect, useState } from 'react'
import {
  BarChart2, Brain, Search, ChevronDown, ChevronUp,
  Zap, Clock, Hash, MessageSquare, RefreshCw, AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Types ──────────────────────────────────────────────────────────────────

interface NodeMetric {
  node_name: string
  agent_role: string
  call_count: number
  avg_latency_ms: number
  avg_input_tokens: number
  avg_output_tokens: number
  total_input_tokens: number
  total_output_tokens: number
}

interface PipelineMetric {
  total_applications: number
  hitl_rate_pct: number
  completion_rate_pct: number
  rejection_rate_pct: number
}

interface Trace {
  id: string
  agent_role: string
  node_name: string
  prompt_rendered: string
  raw_llm_response: string
  parsed_output: Record<string, unknown>
  duration_ms: number
  model: string
  input_tokens: number
  output_tokens: number
  created_at: string
}

// ── Constants ──────────────────────────────────────────────────────────────

const ROLE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  planner:     { label: 'Planner',     color: 'text-violet-700 dark:text-violet-300', bg: 'bg-violet-100 dark:bg-violet-500/20' },
  analyst:     { label: 'Analyst',     color: 'text-blue-700 dark:text-blue-300',     bg: 'bg-blue-100 dark:bg-blue-500/20' },
  critic:      { label: 'Critic',      color: 'text-amber-700 dark:text-amber-300',   bg: 'bg-amber-100 dark:bg-amber-500/20' },
  coordinator: { label: 'Coordinator', color: 'text-slate-600 dark:text-slate-400',   bg: 'bg-slate-100 dark:bg-slate-700' },
}

const AGENT_INVENTORY = [
  { role: 'critic',      node: 'lead_capture',          desc: 'Screens raw form data for eligibility — age, PAN, income, loan limits' },
  { role: 'analyst',     node: 'lead_qualification',    desc: 'Verifies documents, validates income vs salary slips and ITR' },
  { role: 'critic',      node: 'identity_verification', desc: 'KYC — PAN image match, name match, face confidence' },
  { role: 'analyst',     node: 'credit_assessment',     desc: 'Tool-use CIBIL lookup → deterministic credit score + underwriting decision' },
  { role: 'planner',     node: 'art_negotiation',       desc: 'Synthesises all upstream data → 3 offer options (amount, rate, tenure)' },
  { role: 'coordinator', node: 'enach',                 desc: 'Simulates e-NACH mandate registration for EMI auto-debit' },
  { role: 'coordinator', node: 'esign',                 desc: 'Simulates Aadhaar OTP e-sign of loan agreement' },
]

const NODE_ORDER = AGENT_INVENTORY.map(a => a.node)

// ── Helpers ────────────────────────────────────────────────────────────────

function RoleBadge({ role }: { role: string }) {
  const cfg = ROLE_CONFIG[role] ?? ROLE_CONFIG.coordinator
  return (
    <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-full', cfg.bg, cfg.color)}>
      {cfg.label}
    </span>
  )
}

function fmtMs(ms: number) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`
}

function StatPill({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string | number }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
      <Icon size={11} />
      <span>{label}:</span>
      <span className="font-semibold text-slate-700 dark:text-slate-200">{value}</span>
    </div>
  )
}

// ── Trace Card ─────────────────────────────────────────────────────────────

function TraceCard({ trace }: { trace: Trace }) {
  const [open, setOpen] = useState(false)
  const [tab, setTab] = useState<'prompt' | 'response' | 'output'>('output')
  const cfg = ROLE_CONFIG[trace.agent_role] ?? ROLE_CONFIG.coordinator
  const label = AGENT_INVENTORY.find(a => a.node === trace.node_name)?.desc ?? trace.node_name

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors text-left"
      >
        <RoleBadge role={trace.agent_role} />
        <span className="font-semibold text-sm text-slate-800 dark:text-slate-100 flex-1">
          {trace.node_name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
        </span>
        <div className="hidden sm:flex items-center gap-3">
          <StatPill icon={Clock}    label="latency"   value={fmtMs(trace.duration_ms)} />
          <StatPill icon={Hash}     label="in"        value={trace.input_tokens} />
          <StatPill icon={Hash}     label="out"       value={trace.output_tokens} />
        </div>
        <span className="text-slate-300 dark:text-slate-600 ml-2">
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="border-t border-slate-100 dark:border-slate-700/50 bg-slate-50 dark:bg-slate-800/40 p-4 space-y-3">
          <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>

          {/* Tab bar */}
          <div className="flex gap-1">
            {(['output', 'prompt', 'response'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  'text-xs px-3 py-1.5 rounded-lg font-medium transition-colors',
                  tab === t
                    ? `${cfg.bg} ${cfg.color}`
                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300',
                )}
              >
                {t === 'output' ? 'Parsed Output' : t === 'prompt' ? 'Prompt' : 'Raw Response'}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="rounded-xl bg-slate-900 dark:bg-black/40 p-3 max-h-80 overflow-y-auto">
            <pre className="text-xs text-slate-200 whitespace-pre-wrap break-words font-mono leading-relaxed">
              {tab === 'output'
                ? JSON.stringify(trace.parsed_output, null, 2)
                : tab === 'prompt'
                ? trace.prompt_rendered
                : trace.raw_llm_response}
            </pre>
          </div>

          {/* Footer stats */}
          <div className="flex flex-wrap gap-3">
            <StatPill icon={Clock}       label="Latency"     value={fmtMs(trace.duration_ms)} />
            <StatPill icon={Hash}        label="Input tokens"  value={trace.input_tokens} />
            <StatPill icon={Hash}        label="Output tokens" value={trace.output_tokens} />
            <StatPill icon={Brain}       label="Model"       value={trace.model} />
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function EvaluationDashboard() {
  const [metrics, setMetrics]   = useState<{ per_node: NodeMetric[]; pipeline: PipelineMetric } | null>(null)
  const [traces, setTraces]     = useState<Trace[]>([])
  const [appId, setAppId]       = useState('')
  const [searching, setSearching] = useState(false)
  const [traceError, setTraceError] = useState('')
  const [loadingMetrics, setLoadingMetrics] = useState(true)

  async function loadMetrics() {
    setLoadingMetrics(true)
    try {
      const res = await fetch('/api/v1/analytics/evaluation')
      if (res.ok) setMetrics(await res.json())
    } catch {}
    finally { setLoadingMetrics(false) }
  }

  async function searchTraces(e: React.FormEvent) {
    e.preventDefault()
    if (!appId.trim()) return
    setSearching(true)
    setTraceError('')
    setTraces([])
    try {
      const res = await fetch(`/api/v1/applications/${appId.trim()}/traces`)
      if (res.status === 404) { setTraceError('Application not found'); return }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        setTraceError(body.detail || `Error ${res.status} — check that the backend is running`)
        return
      }
      const data: Trace[] = await res.json()
      if (data.length === 0) {
        setTraceError('No traces yet for this application. Traces are recorded on pipelines run after the latest deploy — submit a new application to generate them.')
        return
      }
      // Sort by pipeline order
      data.sort((a, b) => NODE_ORDER.indexOf(a.node_name) - NODE_ORDER.indexOf(b.node_name))
      setTraces(data)
    } catch {
      setTraceError('Network error')
    } finally {
      setSearching(false)
    }
  }

  useEffect(() => { loadMetrics() }, [])

  // Summary stats for the node metric cards
  const totalCalls   = metrics?.per_node.reduce((s, r) => s + r.call_count, 0) ?? 0
  const totalTokensIn  = metrics?.per_node.reduce((s, r) => s + r.total_input_tokens, 0) ?? 0
  const totalTokensOut = metrics?.per_node.reduce((s, r) => s + r.total_output_tokens, 0) ?? 0
  const avgLatency   = metrics?.per_node.length
    ? Math.round(metrics.per_node.reduce((s, r) => s + r.avg_latency_ms, 0) / metrics.per_node.length)
    : 0

  return (
    <div className="max-w-5xl mx-auto space-y-8 animate-slide-up">

      {/* ── Title ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Evaluation Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Agent reasoning traces, token usage, and pipeline metrics.
          </p>
        </div>
        <button onClick={loadMetrics} disabled={loadingMetrics} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={13} className={cn(loadingMetrics && 'animate-spin')} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* ── Summary pills ── */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Total LLM Calls',   value: totalCalls,           icon: Brain },
            { label: 'Avg Node Latency',  value: fmtMs(avgLatency),    icon: Clock },
            { label: 'Total Input Tokens', value: totalTokensIn.toLocaleString(),  icon: Hash },
            { label: 'Total Output Tokens', value: totalTokensOut.toLocaleString(), icon: MessageSquare },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="card p-4 space-y-1">
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Icon size={11} /> {label}
              </div>
              <p className="text-xl font-bold text-slate-900 dark:text-white">{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Pipeline health ── */}
      {metrics && (
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Completion Rate', value: `${metrics.pipeline.completion_rate_pct}%`, color: 'text-emerald-600' },
            { label: 'Rejection Rate',  value: `${metrics.pipeline.rejection_rate_pct}%`,  color: 'text-red-500' },
            { label: 'HITL Rate',       value: `${metrics.pipeline.hitl_rate_pct}%`,       color: 'text-amber-600' },
          ].map(({ label, value, color }) => (
            <div key={label} className="card p-4 text-center">
              <p className={cn('text-2xl font-bold', color)}>{value}</p>
              <p className="text-xs text-slate-400 mt-1">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* ── Agent Inventory ── */}
      <div className="card p-5 space-y-3">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <BarChart2 size={14} className="text-brand-500" /> Agent Inventory
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-slate-400 border-b border-slate-100 dark:border-slate-700">
                <th className="pb-2 pr-4 font-medium">Node</th>
                <th className="pb-2 pr-4 font-medium">Role</th>
                <th className="pb-2 pr-4 font-medium hidden sm:table-cell">Description</th>
                <th className="pb-2 pr-4 font-medium text-right">Calls</th>
                <th className="pb-2 font-medium text-right">Avg Latency</th>
              </tr>
            </thead>
            <tbody>
              {AGENT_INVENTORY.map(({ role, node, desc }) => {
                const m = metrics?.per_node.find(r => r.node_name === node)
                return (
                  <tr key={node} className="border-b border-slate-50 dark:border-slate-800">
                    <td className="py-2 pr-4 font-mono text-slate-700 dark:text-slate-300">
                      {node.replace(/_/g, '_')}
                    </td>
                    <td className="py-2 pr-4"><RoleBadge role={role} /></td>
                    <td className="py-2 pr-4 text-slate-400 hidden sm:table-cell max-w-xs truncate">{desc}</td>
                    <td className="py-2 pr-4 text-right text-slate-600 dark:text-slate-400">
                      {m ? m.call_count : '—'}
                    </td>
                    <td className="py-2 text-right text-slate-600 dark:text-slate-400">
                      {m ? fmtMs(m.avg_latency_ms) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Reasoning Trace Explorer ── */}
      <div className="card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2">
          <Brain size={14} className="text-violet-500" /> Reasoning Trace Explorer
        </h2>
        <p className="text-xs text-slate-400">
          Paste an application ID to inspect every agent's prompt, raw LLM response, and parsed output.
        </p>

        <form onSubmit={searchTraces} className="flex gap-2">
          <div className="relative flex-1">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={appId}
              onChange={e => setAppId(e.target.value)}
              placeholder="Paste application ID…"
              className="input pl-9 text-sm"
            />
          </div>
          <button type="submit" disabled={searching || !appId.trim()} className="btn-primary flex items-center gap-2 flex-shrink-0">
            {searching ? <RefreshCw size={13} className="animate-spin" /> : <Search size={13} />}
            <span className="hidden sm:inline">Load Traces</span>
          </button>
        </form>

        {traceError && (
          <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 rounded-xl px-4 py-3">
            <AlertCircle size={14} /> {traceError}
          </div>
        )}

        {traces.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
              <span>{traces.length} nodes traced</span>
              <span>
                {traces.reduce((s, t) => s + t.input_tokens + t.output_tokens, 0).toLocaleString()} total tokens ·{' '}
                {fmtMs(traces.reduce((s, t) => s + t.duration_ms, 0))} total latency
              </span>
            </div>
            {traces.map(t => <TraceCard key={t.id} trace={t} />)}
          </div>
        )}
      </div>

      {/* ── Per-node token usage ── */}
      {metrics && metrics.per_node.length > 0 && (
        <div className="card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2">
            <Zap size={14} className="text-amber-500" /> Per-Node Token Usage
          </h2>
          <div className="space-y-2">
            {metrics.per_node
              .sort((a, b) => NODE_ORDER.indexOf(a.node_name) - NODE_ORDER.indexOf(b.node_name))
              .map(r => {
                const maxTokens = Math.max(...metrics.per_node.map(x => x.avg_input_tokens + x.avg_output_tokens))
                const total = r.avg_input_tokens + r.avg_output_tokens
                const pct = maxTokens > 0 ? (total / maxTokens) * 100 : 0
                return (
                  <div key={r.node_name} className="grid grid-cols-[180px_1fr_80px] items-center gap-3 text-xs">
                    <div className="flex items-center gap-2">
                      <RoleBadge role={r.agent_role} />
                      <span className="text-slate-600 dark:text-slate-400 truncate font-mono">
                        {r.node_name}
                      </span>
                    </div>
                    <div className="flex gap-1 h-4">
                      <div
                        className="bg-blue-400 dark:bg-blue-500 rounded-l-full"
                        style={{ width: `${(r.avg_input_tokens / total) * pct}%` }}
                        title={`Avg input: ${Math.round(r.avg_input_tokens)}`}
                      />
                      <div
                        className="bg-violet-400 dark:bg-violet-500 rounded-r-full"
                        style={{ width: `${(r.avg_output_tokens / total) * pct}%` }}
                        title={`Avg output: ${Math.round(r.avg_output_tokens)}`}
                      />
                    </div>
                    <span className="text-right text-slate-500">
                      {Math.round(total)} tok · {fmtMs(r.avg_latency_ms)}
                    </span>
                  </div>
                )
              })}
          </div>
          <div className="flex gap-4 text-[10px] text-slate-400">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-blue-400 dark:bg-blue-500" /> Input tokens</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-violet-400 dark:bg-violet-500" /> Output tokens</span>
          </div>
        </div>
      )}

    </div>
  )
}
