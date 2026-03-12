import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { TrendingUp, Users, CheckCircle2, XCircle, Banknote, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Overview {
  total_applications: number
  approved: number
  rejected: number
  pending: number
  approval_rate: number
  total_approved_amount: number
}

interface PipelineStage {
  stage: string
  applications_at_stage: number
}

const PIE_COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

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

function StatCard({ icon: Icon, label, value, sub, color }: {
  icon: React.ElementType; label: string; value: string; sub?: string; color: string
}) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between mb-3">
        <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center', color)}>
          <Icon size={16} className="text-white" />
        </div>
      </div>
      <p className="text-2xl font-bold text-slate-900 dark:text-white">{value}</p>
      <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-brand-500 font-medium mt-1">{sub}</p>}
    </div>
  )
}

export default function Analytics() {
  const [overview, setOverview]   = useState<Overview | null>(null)
  const [pipeline, setPipeline]   = useState<PipelineStage[]>([])
  const [loading, setLoading]     = useState(false)

  async function load() {
    setLoading(true)
    try {
      const [ov, pl] = await Promise.all([
        fetch('/api/v1/analytics/overview').then(r => r.json()),
        fetch('/api/v1/analytics/pipeline').then(r => r.json()),
      ])
      setOverview(ov)
      setPipeline(pl)
    } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const pieData = overview ? [
    { name: 'Approved', value: overview.approved },
    { name: 'Pending',  value: overview.pending },
    { name: 'Rejected', value: overview.rejected },
  ].filter(d => d.value > 0) : []

  const barData = pipeline.map(s => ({
    stage: STAGE_LABELS[s.stage] ?? s.stage,
    count: s.applications_at_stage,
  }))

  const fmt = (n: number) => n >= 10000000
    ? `₹${(n / 10000000).toFixed(1)}Cr`
    : n >= 100000
    ? `₹${(n / 100000).toFixed(1)}L`
    : `₹${n.toLocaleString('en-IN')}`

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Analytics</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Real-time pipeline metrics and disbursement stats.</p>
        </div>
        <button onClick={load} disabled={loading} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={13} className={cn(loading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Stat cards */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon={Users}       label="Total Applications" value={String(overview.total_applications)} color="bg-brand-600" />
          <StatCard icon={CheckCircle2} label="Approved"           value={String(overview.approved)} sub={`${overview.approval_rate}% rate`} color="bg-emerald-500" />
          <StatCard icon={XCircle}     label="Rejected"            value={String(overview.rejected)} color="bg-red-500" />
          <StatCard icon={Banknote}    label="Disbursed Amount"    value={fmt(overview.total_approved_amount)} color="bg-indigo-500" />
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Pipeline bar chart */}
        <div className="card p-5 md:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={14} className="text-brand-500" />
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Applications per Stage</h2>
          </div>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={barData} barSize={28}>
                <XAxis dataKey="stage" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.15)' }}
                  cursor={{ fill: 'rgba(99,102,241,0.08)' }}
                />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} name="Applications" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-slate-400 text-sm">No pipeline data yet</div>
          )}
        </div>

        {/* Pie chart */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">Status Breakdown</h2>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
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
    </div>
  )
}
