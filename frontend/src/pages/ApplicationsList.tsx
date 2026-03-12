import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronLeft, ChevronRight, ExternalLink, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Application {
  id: string
  full_name: string
  email: string
  pan_number: string
  loan_amount: number
  loan_purpose: string | null
  tenure_months: number | null
  status: string
  stage: string | null
  created_at: string
}

interface PaginatedResponse {
  total: number
  page: number
  page_size: number
  total_pages: number
  items: Application[]
}

const STATUS_OPTIONS = ['', 'pending', 'processing', 'approved', 'rejected', 'disbursed']

const STATUS_COLORS: Record<string, string> = {
  pending:    'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400',
  approved:   'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400',
  rejected:   'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400',
  disbursed:  'bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400',
  processing: 'bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-400',
}

const STAGE_LABELS: Record<string, string> = {
  lead_capture:          'Lead Capture',
  lead_qualification:    'Qualification',
  identity_verification: 'Identity',
  credit_assessment:     'Credit',
  fraud_detection:       'Fraud',
  compliance:            'Compliance',
  document_collection:   'Documents',
  sanction_processing:   'Sanction',
  disbursement:          'Disbursement',
}

const fmt = (n: number) =>
  n >= 10000000 ? `₹${(n / 10000000).toFixed(1)}Cr`
  : n >= 100000  ? `₹${(n / 100000).toFixed(1)}L`
  : `₹${n.toLocaleString('en-IN')}`

export default function ApplicationsList() {
  const navigate = useNavigate()

  const [data, setData]       = useState<PaginatedResponse | null>(null)
  const [search, setSearch]   = useState('')
  const [status, setStatus]   = useState('')
  const [page, setPage]       = useState(1)
  const [loading, setLoading] = useState(false)

  const PAGE_SIZE = 10

  const load = useCallback(async (p = page, s = search, st = status) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: String(p),
        page_size: String(PAGE_SIZE),
        ...(st ? { status: st } : {}),
        ...(s.trim() ? { search: s.trim() } : {}),
      })
      const res = await fetch(`/api/v1/applications/?${params}`)
      if (res.ok) setData(await res.json())
    } catch {}
    finally { setLoading(false) }
  }, [page, search, status])

  useEffect(() => { load(page, search, status) }, [page])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    load(1, search, status)
  }

  function handleStatusChange(val: string) {
    setStatus(val)
    setPage(1)
    load(1, search, val)
  }

  return (
    <div className="space-y-6 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">All Applications</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">
            {data ? `${data.total} application${data.total !== 1 ? 's' : ''} found` : 'Loading…'}
          </p>
        </div>
        <button onClick={() => load(page, search, status)} disabled={loading} className="btn-secondary flex items-center gap-2">
          <RefreshCw size={13} className={cn(loading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <form onSubmit={handleSearch} className="relative flex-1 flex gap-2">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="input pl-9"
              placeholder="Search by name, email, or PAN…"
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2">
            <Search size={14} /> Search
          </button>
        </form>

        <select
          value={status}
          onChange={e => handleStatusChange(e.target.value)}
          className="input sm:w-44"
        >
          {STATUS_OPTIONS.map(s => (
            <option key={s} value={s}>{s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All Statuses'}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
                {['Applicant', 'PAN', 'Amount', 'Purpose', 'Stage', 'Status', 'Date', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading && !data && (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-slate-400 text-sm">Loading…</td>
                </tr>
              )}
              {!loading && data?.items.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-slate-400 text-sm">No applications found</td>
                </tr>
              )}
              {data?.items.map(app => (
                <tr
                  key={app.id}
                  className="border-b border-slate-100 dark:border-slate-800 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-800 dark:text-slate-100">{app.full_name}</p>
                    <p className="text-xs text-slate-400">{app.email}</p>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600 dark:text-slate-400">{app.pan_number}</td>
                  <td className="px-4 py-3 font-semibold text-brand-600 dark:text-brand-400">{fmt(app.loan_amount)}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{app.loan_purpose ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500 dark:text-slate-400 text-xs">
                    {app.stage ? (STAGE_LABELS[app.stage] ?? app.stage) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={cn('badge', STATUS_COLORS[app.status] ?? STATUS_COLORS.processing)}>
                      {app.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
                    {new Date(app.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => navigate(`/status/${app.id}`)}
                      className="p-1.5 rounded-lg hover:bg-brand-50 dark:hover:bg-brand-500/10 text-slate-400 hover:text-brand-500 transition-colors"
                      title="Track status"
                    >
                      <ExternalLink size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.total_pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Showing {(data.page - 1) * data.page_size + 1}–{Math.min(data.page * data.page_size, data.total)} of {data.total}
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(p => p - 1)}
                disabled={data.page <= 1 || loading}
                className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={15} className="text-slate-600 dark:text-slate-400" />
              </button>
              {Array.from({ length: data.total_pages }, (_, i) => i + 1)
                .filter(n => n === 1 || n === data.total_pages || Math.abs(n - data.page) <= 1)
                .reduce<(number | '...')[]>((acc, n, idx, arr) => {
                  if (idx > 0 && (arr[idx - 1] as number) !== n - 1) acc.push('...')
                  acc.push(n)
                  return acc
                }, [])
                .map((n, i) =>
                  n === '...' ? (
                    <span key={`e${i}`} className="px-2 text-xs text-slate-400">…</span>
                  ) : (
                    <button
                      key={n}
                      onClick={() => setPage(n as number)}
                      disabled={loading}
                      className={cn(
                        'w-7 h-7 rounded-lg text-xs font-medium transition-colors',
                        data.page === n
                          ? 'bg-brand-600 text-white'
                          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'
                      )}
                    >
                      {n}
                    </button>
                  )
                )}
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={data.page >= data.total_pages || loading}
                className="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight size={15} className="text-slate-600 dark:text-slate-400" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
