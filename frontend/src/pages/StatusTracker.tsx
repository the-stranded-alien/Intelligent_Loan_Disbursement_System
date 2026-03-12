import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Search, RefreshCw } from 'lucide-react'
import WorkflowTimeline from '@/components/WorkflowTimeline'
import NotificationFeed from '@/components/NotificationFeed'
import { cn } from '@/lib/utils'

interface AppStatus {
  application_id: string
  status: string
  current_stage: string | null
  updated_at: string
}

const STATUS_COLORS: Record<string, string> = {
  pending:    'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400',
  approved:   'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400',
  rejected:   'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400',
  disbursed:  'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400',
  processing: 'bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-400',
}

export default function StatusTracker() {
  const { applicationId: paramId } = useParams<{ applicationId: string }>()
  const navigate = useNavigate()

  const [inputId, setInputId]     = useState(paramId ?? '')
  const [appId, setAppId]         = useState(paramId ?? '')
  const [status, setStatus]       = useState<AppStatus | null>(null)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')

  async function fetchStatus(id: string) {
    if (!id.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/v1/applications/${id}/status`)
      if (res.status === 404) throw new Error('Application not found')
      if (!res.ok) throw new Error('Failed to fetch status')
      setStatus(await res.json())
      navigate(`/status/${id}`, { replace: true })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Unknown error')
      setStatus(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (paramId) fetchStatus(paramId)
  }, [])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setAppId(inputId.trim())
    fetchStatus(inputId.trim())
  }

  const statusColor = status ? (STATUS_COLORS[status.status] ?? STATUS_COLORS.processing) : ''

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-slide-up">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Track Application</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Enter your application ID to see real-time pipeline status.</p>
      </div>

      {/* Search */}
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
        <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
          {loading ? <RefreshCw size={14} className="animate-spin" /> : <Search size={14} />}
          Track
        </button>
      </form>

      {error && (
        <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {status && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-fade-in">
          {/* Status card */}
          <div className="card p-5 md:col-span-2 space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-slate-400 dark:text-slate-500 mb-1">Application ID</p>
                <p className="font-mono text-xs text-slate-700 dark:text-slate-300 break-all">{status.application_id}</p>
              </div>
              <span className={cn('badge', statusColor)}>
                {status.status}
              </span>
            </div>

            <div>
              <p className="text-xs text-slate-400 dark:text-slate-500 mb-3">Pipeline Progress</p>
              <WorkflowTimeline currentStage={status.current_stage} applicationStatus={status.status} />
            </div>

            <p className="text-xs text-slate-400">
              Last updated: {new Date(status.updated_at).toLocaleString()}
            </p>
          </div>

          {/* Live feed */}
          <div className="space-y-4">
            <NotificationFeed applicationId={appId} />
          </div>
        </div>
      )}

      {!status && !loading && !error && (
        <div className="card p-12 text-center">
          <Search size={32} className="mx-auto text-slate-300 dark:text-slate-600 mb-3" />
          <p className="text-slate-400 text-sm">Enter an application ID above to get started</p>
        </div>
      )}
    </div>
  )
}
