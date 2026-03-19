import { useEffect, useRef, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend, AreaChart, Area, CartesianGrid,
} from 'recharts'
import {
  TrendingUp, Users, CheckCircle2, XCircle, Banknote,
  RefreshCw, Clock, AlertTriangle, BarChart2, Activity,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Types ──────────────────────────────────────────────────────────────────

interface Overview {
  total_applications: number
  approved: number
  rejected: number
  pending: number
  approval_rate: number
  total_approved_amount: number
}

interface PipelineStage { stage: string; applications_at_stage: number }

interface AgentStage {
  stage: string
  total_at_stage: number
  rejected_at_stage: number
  rejection_rate: number
}

interface AgentMetrics {
  stages: AgentStage[]
  pending_hitl_review: number
  avg_loan_amount: number
}

interface Disbursements {
  total_disbursed: number
  total_amount: number
  avg_loan_amount: number
}

// ── Constants ──────────────────────────────────────────────────────────────

const PIE_COLORS = ['#10b981', '#f59e0b', '#ef4444', '#6366f1']

const STAGE_LABELS: Record<string, string> = {
  lead_capture:           'Lead Capture',
  lead_qualification:     'Qualification',
  identity_verification:  'Identity',
  credit_assessment:      'Credit',
  fraud_detection:        'Fraud',
  compliance:             'Compliance',
  document_collection:    'Documents',
  sanction_processing:    'Sanction',
  disbursement:           'Disbursement',
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmt(n: number) {
  if (n >= 10_000_000) return `₹${(n / 10_000_000).toFixed(1)}Cr`
  if (n >= 100_000)    return `₹${(n / 100_000).toFixed(1)}L`
  return `₹${Math.round(n).toLocaleString('en-IN')}`
}

// ── Sub-components ─────────────────────────────────────────────────────────

function StatCard({
  icon: Icon, label, value, sub, color, loading,
}: {
  icon: React.ElementType; label: string; value: string
  sub?: string; color: string; loading?: boolean
}) {
  return (
    <div className="card p-5 flex flex-col gap-2">
      <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0', color)}>
        <Icon size={16} className="text-white" />
      </div>
      {loading ? (
        <div className="h-7 w-16 bg-slate-100 dark:bg-slate-800 rounded animate-pulse" />
      ) : (
        <p className="text-2xl font-bold text-slate-900 dark:text-white leading-none">{value}</p>
      )}
      <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
      {sub && <p className="text-xs text-brand-500 font-medium">{sub}</p>}
    </div>
  )
}

function SectionTitle({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <Icon size={14} className="text-brand-500" />
      <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">{title}</h2>
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function Analytics() {
  const [overview, setOverview]         = useState<Overview | null>(null)
  const [pipeline, setPipeline]         = useState<PipelineStage[]>([])
  const [agents, setAgents]             = useState<AgentMetrics | null>(null)
  const [disburse, setDisburse]         = useState<Disbursements | null>(null)
  const [loading, setLoading]           = useState(false)
  const [autoRefresh, setAutoRefresh]   = useState(false)
  const intervalRef                     = useRef<ReturnType<typeof setInterval> | null>(null)

  async function load() {
    setLoading(true)
    try {
      const [ov, pl, ag, di] = await Promise.all([
        fetch('/api/v1/analytics/overview').then(r => r.json()),
        fetch('/api/v1/analytics/pipeline').then(r => r.json()),
        fetch('/api/v1/analytics/agents').then(r => r.json()),
        fetch('/api/v1/analytics/disbursements').then(r => r.json()),
      ])
      setOverview(ov)
      setPipeline(pl)
      setAgents(ag)
      setDisburse(di)
    } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(load, 30_000)
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [autoRefresh])

  const pieData = overview ? [
    { name: 'Approved', value: overview.approved },
    { name: 'Pending',  value: overview.pending },
    { name: 'Rejected', value: overview.rejected },
  ].filter(d => d.value > 0) : []

  const barData = pipeline.map(s => ({
    stage: STAGE_LABELS[s.stage] ?? s.stage,
    count: s.applications_at_stage,
  }))

  // Synthetic conversion funnel — cumulative drop-off across stages
  const funnelData = pipeline.map((s, i) => ({
    stage: STAGE_LABELS[s.stage] ?? s.stage,
    applications: pipeline.slice(i).reduce((acc, x) => acc + x.applications_at_stage, 0),
  }))

  return (
    <div className="space-y-6 animate-slide-up">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Analytics</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            Real-time pipeline metrics and disbursement stats.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh(v => !v)}
            className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all',
              autoRefresh
                ? 'bg-brand-600 border-brand-600 text-white'
                : 'border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-brand-400'
            )}
          >
            <span className={cn('w-1.5 h-1.5 rounded-full', autoRefresh ? 'bg-white animate-pulse' : 'bg-slate-400')} />
            {autoRefresh ? 'Live' : 'Auto-refresh'}
          </button>
          <button onClick={load} disabled={loading} className="btn-secondary flex items-center gap-2">
            <RefreshCw size={13} className={cn(loading && 'animate-spin')} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>
      </div>

      {/* ── 6 Stat cards ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard icon={Users}        label="Total"            value={String(overview?.total_applications ?? '—')}  color="bg-brand-600"   loading={loading} />
        <StatCard icon={TrendingUp}   label="Approval Rate"   value={overview ? `${overview.approval_rate}%` : '—'} color="bg-emerald-500" loading={loading} />
        <StatCard icon={CheckCircle2} label="Approved"         value={String(overview?.approved ?? '—')}             color="bg-teal-500"   loading={loading} />
        <StatCard icon={XCircle}      label="Rejected"         value={String(overview?.rejected ?? '—')}             color="bg-red-500"    loading={loading} />
        <StatCard icon={Clock}        label="HITL Pending"     value={String(agents?.pending_hitl_review ?? '—')}    color="bg-amber-500"  loading={loading} />
        <StatCard icon={Banknote}     label="Disbursed"        value={disburse ? fmt(disburse.total_amount) : '—'}   color="bg-indigo-500" loading={loading} />
      </div>

      {/* ── Conversion Funnel + Status Pie ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card p-5 lg:col-span-2">
          <SectionTitle icon={Activity} title="Conversion Funnel" />
          {funnelData.some(d => d.applications > 0) ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={funnelData}>
                <defs>
                  <linearGradient id="funnelGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.2)" />
                <XAxis dataKey="stage" tick={{ fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }} />
                <Area type="monotone" dataKey="applications" stroke="#6366f1" strokeWidth={2} fill="url(#funnelGrad)" name="Active" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-52 flex items-center justify-center text-slate-400 text-sm">No funnel data yet</div>
          )}
        </div>

        <div className="card p-5">
          <SectionTitle icon={BarChart2} title="Status Breakdown" />
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="45%" innerRadius={48} outerRadius={72} paddingAngle={3} dataKey="value">
                  {pieData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: 'none' }} />
                <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-400 text-sm">No data yet</div>
          )}
        </div>
      </div>

      {/* ── Pipeline Distribution Bar ── */}
      <div className="card p-5">
        <SectionTitle icon={TrendingUp} title="Applications per Stage" />
        {barData.length > 0 ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData} barSize={28}>
              <XAxis dataKey="stage" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }}
                cursor={{ fill: 'rgba(99,102,241,0.08)' }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} name="Applications">
                {barData.map((_, i) => (
                  <Cell key={i} fill={`hsl(${240 + i * 12},70%,${55 + i * 2}%)`} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-52 flex items-center justify-center text-slate-400 text-sm">No pipeline data yet</div>
        )}
      </div>

      {/* ── Per-node Agents Table + Disbursements ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Agents table */}
        <div className="card p-5 lg:col-span-2">
          <SectionTitle icon={AlertTriangle} title="Per-Node Rejection Rates" />
          <div className="overflow-x-auto -mx-1">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-800">
                  <th className="text-left py-2 px-2 font-medium text-slate-500 dark:text-slate-400">Stage</th>
                  <th className="text-right py-2 px-2 font-medium text-slate-500 dark:text-slate-400">At Stage</th>
                  <th className="text-right py-2 px-2 font-medium text-slate-500 dark:text-slate-400">Rejected</th>
                  <th className="text-right py-2 px-2 font-medium text-slate-500 dark:text-slate-400">Rejection %</th>
                  <th className="py-2 px-2 w-28"></th>
                </tr>
              </thead>
              <tbody>
                {(agents?.stages ?? []).map(s => (
                  <tr key={s.stage} className="border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <td className="py-2.5 px-2 font-medium text-slate-700 dark:text-slate-300">
                      {STAGE_LABELS[s.stage] ?? s.stage}
                    </td>
                    <td className="py-2.5 px-2 text-right text-slate-500">{s.total_at_stage}</td>
                    <td className="py-2.5 px-2 text-right text-red-500">{s.rejected_at_stage}</td>
                    <td className="py-2.5 px-2 text-right">
                      <span className={cn(
                        'font-semibold',
                        s.rejection_rate === 0   ? 'text-emerald-500' :
                        s.rejection_rate < 20    ? 'text-amber-500' : 'text-red-500'
                      )}>
                        {s.rejection_rate}%
                      </span>
                    </td>
                    <td className="py-2.5 px-2">
                      <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5">
                        <div
                          className={cn(
                            'h-1.5 rounded-full transition-all',
                            s.rejection_rate === 0   ? 'bg-emerald-500' :
                            s.rejection_rate < 20    ? 'bg-amber-500' : 'bg-red-500'
                          )}
                          style={{ width: `${Math.min(s.rejection_rate, 100)}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
                {!agents && (
                  <tr><td colSpan={5} className="py-8 text-center text-slate-400">Loading…</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Disbursements card */}
        <div className="card p-5 space-y-5">
          <SectionTitle icon={Banknote} title="Disbursements" />
          {disburse ? (
            <div className="space-y-4">
              {[
                { label: 'Total Disbursed',  value: String(disburse.total_disbursed), sub: 'loans paid out' },
                { label: 'Total Amount',     value: fmt(disburse.total_amount), sub: 'across all loans' },
                { label: 'Avg Loan Size',    value: fmt(disburse.avg_loan_amount), sub: 'per disbursement' },
                { label: 'Avg Loan (All)',   value: agents ? fmt(agents.avg_loan_amount) : '—', sub: 'all applications' },
              ].map(({ label, value, sub }) => (
                <div key={label} className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-slate-500 dark:text-slate-400">{label}</p>
                    <p className="text-xs text-slate-400">{sub}</p>
                  </div>
                  <p className="text-sm font-bold text-slate-800 dark:text-slate-100">{value}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {[1,2,3,4].map(i => (
                <div key={i} className="h-8 bg-slate-100 dark:bg-slate-800 rounded animate-pulse" />
              ))}
            </div>
          )}

          {/* HITL badge */}
          {agents && agents.pending_hitl_review > 0 && (
            <div className="bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 rounded-xl p-3 flex items-center gap-2">
              <Clock size={14} className="text-amber-500 flex-shrink-0" />
              <p className="text-xs text-amber-700 dark:text-amber-400">
                <span className="font-semibold">{agents.pending_hitl_review}</span> application{agents.pending_hitl_review > 1 ? 's' : ''} awaiting RM review
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
