import { useEffect, useState } from 'react'
import { Users, CheckCircle2, Clock, ChevronRight, RefreshCw } from 'lucide-react'
import AgentDecisionCard from '@/components/AgentDecisionCard'
import WhatIfAnalysis from '@/components/WhatIfAnalysis'
import { cn } from '@/lib/utils'

interface QueueItem {
  application_id: string
  applicant_name: string
  loan_amount: number
  waiting_since: string
}

interface ReviewForm {
  decision: 'approve' | 'reject' | 'request_info'
  notes: string
}

export default function RMDashboard() {
  const [queue, setQueue]               = useState<QueueItem[]>([])
  const [selected, setSelected]         = useState<QueueItem | null>(null)
  const [form, setForm]                 = useState<ReviewForm>({ decision: 'approve', notes: '' })
  const [submitting, setSubmitting]     = useState(false)
  const [successMsg, setSuccessMsg]     = useState('')
  const [error, setError]               = useState('')
  const [loading, setLoading]           = useState(false)

  async function loadQueue() {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/rm/queue')
      if (res.ok) setQueue(await res.json())
    } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { loadQueue() }, [])

  async function submitReview() {
    if (!selected) return
    setSubmitting(true)
    setError('')
    try {
      const res = await fetch(`/api/v1/rm/${selected.application_id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision: form.decision, notes: form.notes }),
      })
      if (!res.ok) throw new Error('Review submission failed')
      setSuccessMsg(`Decision recorded: ${form.decision}`)
      setSelected(null)
      await loadQueue()
      setTimeout(() => setSuccessMsg(''), 4000)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error')
    } finally {
      setSubmitting(false)
    }
  }

  const fmt = (n: number) => `₹${n.toLocaleString('en-IN')}`

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">RM Dashboard</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Review and process HITL loan applications.</p>
        </div>
        <button onClick={loadQueue} disabled={loading} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={13} className={cn(loading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {successMsg && (
        <div className="bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/30 rounded-xl px-4 py-3 text-sm text-emerald-700 dark:text-emerald-400 flex items-center gap-2">
          <CheckCircle2 size={14} /> {successMsg}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Queue */}
        <div className="lg:col-span-1 space-y-3">
          <div className="flex items-center gap-2">
            <Users size={14} className="text-slate-500" />
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-300">Pending Reviews</h2>
            <span className="badge bg-brand-100 dark:bg-brand-500/20 text-brand-700 dark:text-brand-400 ml-auto">{queue.length}</span>
          </div>

          {queue.length === 0 && !loading && (
            <div className="card p-8 text-center">
              <Clock size={24} className="mx-auto text-slate-300 dark:text-slate-600 mb-2" />
              <p className="text-slate-400 text-sm">No applications pending review</p>
            </div>
          )}

          {queue.map(item => (
            <button
              key={item.application_id}
              onClick={() => { setSelected(item); setError('') }}
              className={cn(
                'card p-4 w-full text-left transition-all hover:shadow-md',
                selected?.application_id === item.application_id && 'ring-2 ring-brand-500'
              )}
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-slate-800 dark:text-slate-100 text-sm">{item.applicant_name}</p>
                  <p className="text-brand-600 dark:text-brand-400 font-bold text-sm mt-0.5">{fmt(item.loan_amount)}</p>
                  <p className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                    <Clock size={10} /> {new Date(item.waiting_since).toLocaleString()}
                  </p>
                </div>
                <ChevronRight size={14} className="text-slate-400 mt-1" />
              </div>
            </button>
          ))}
        </div>

        {/* Review panel */}
        <div className="lg:col-span-2 space-y-4">
          {!selected ? (
            <div className="card p-12 text-center">
              <Users size={32} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
              <p className="text-slate-400 text-sm">Select an application from the queue to review</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4">
                <AgentDecisionCard applicationId={selected.application_id} />
                <WhatIfAnalysis applicationId={selected.application_id} />
              </div>

              {/* Review form */}
              <div className="card p-5 space-y-4">
                <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">Submit Decision</h3>

                <div className="flex gap-2">
                  {(['approve', 'reject', 'request_info'] as const).map(d => (
                    <button
                      key={d}
                      onClick={() => setForm(f => ({ ...f, decision: d }))}
                      className={cn(
                        'flex-1 py-2 rounded-lg text-xs font-medium border transition-colors',
                        form.decision === d
                          ? d === 'approve'       ? 'bg-emerald-500 border-emerald-500 text-white'
                          : d === 'reject'        ? 'bg-red-500 border-red-500 text-white'
                          :                         'bg-amber-500 border-amber-500 text-white'
                          : 'border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600'
                      )}
                    >
                      {d === 'approve' ? '✓ Approve' : d === 'reject' ? '✕ Reject' : '? Request Info'}
                    </button>
                  ))}
                </div>

                <div>
                  <label className="label">Notes (optional)</label>
                  <textarea
                    value={form.notes}
                    onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                    className="input min-h-[80px] resize-none"
                    placeholder="Add any notes for the decision…"
                  />
                </div>

                {error && <p className="text-red-500 text-xs">{error}</p>}

                <div className="flex gap-3">
                  <button onClick={() => setSelected(null)} className="btn-secondary">Cancel</button>
                  <button onClick={submitReview} disabled={submitting} className={cn(
                    'flex-1 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50',
                    form.decision === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700 text-white' :
                    form.decision === 'reject'  ? 'bg-red-600 hover:bg-red-700 text-white' :
                                                  'bg-amber-500 hover:bg-amber-600 text-white'
                  )}>
                    {submitting ? 'Submitting…' : `Submit ${form.decision}`}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
