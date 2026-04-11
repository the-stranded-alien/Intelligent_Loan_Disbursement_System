import { useEffect, useState } from 'react'
import { Sparkles, Loader2, AlertCircle, TrendingUp, ShieldAlert, CheckCircle2, Calculator } from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Types ──────────────────────────────────────────────────────────────────

interface CounterOfferResult {
  principal: number
  rate: number
  tenure_months: number
  monthly_emi: number
  total_payable: number
  total_interest: number
  processing_fee: number
}

interface NegotiationAdvice {
  recommended_option: 'A' | 'B' | 'C'
  recommendation_reason: string
  risk_analysis: { A: string; B: string; C: string }
  dti_after_loan: { A: number; B: number; C: number }
  affordability_verdict: 'comfortable' | 'stretched' | 'risky'
  counter_offer_note: string
}

// ── Helpers ────────────────────────────────────────────────────────────────

const AFFORDABILITY_CONFIG = {
  comfortable: { label: 'Comfortable', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-500/10' },
  stretched:   { label: 'Stretched',   color: 'text-amber-600 dark:text-amber-400',    bg: 'bg-amber-50 dark:bg-amber-500/10' },
  risky:       { label: 'Risky',       color: 'text-red-600 dark:text-red-400',        bg: 'bg-red-50 dark:bg-red-500/10' },
}

const OPTION_COLORS: Record<string, string> = {
  A: 'border-l-emerald-400',
  B: 'border-l-brand-400',
  C: 'border-l-amber-400',
}

// ── Component ──────────────────────────────────────────────────────────────

export default function NegotiationPanel({ applicationId }: { applicationId: string }) {
  const [advice, setAdvice]   = useState<NegotiationAdvice | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const [fetched, setFetched] = useState(false)

  // Counter-offer simulator state
  const [coRate, setCoRate]         = useState('12.5')
  const [coTenure, setCoTenure]     = useState('24')
  const [coResult, setCoResult]     = useState<CounterOfferResult | null>(null)
  const [coLoading, setCoLoading]   = useState(false)
  const [coError, setCoError]       = useState('')

  async function loadAdvice() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`/api/v1/rm/${applicationId}/negotiation-advice`)
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Error ${res.status}`)
      }
      setAdvice(await res.json())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load advice')
    } finally {
      setLoading(false)
      setFetched(true)
    }
  }

  async function simulateCounterOffer(e: React.FormEvent) {
    e.preventDefault()
    setCoLoading(true)
    setCoError('')
    setCoResult(null)
    try {
      const res = await fetch(`/api/v1/rm/${applicationId}/counter-offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rate: parseFloat(coRate), tenure_months: parseInt(coTenure) }),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Error ${res.status}`)
      }
      setCoResult(await res.json())
    } catch (e: unknown) {
      setCoError(e instanceof Error ? e.message : 'Calculation failed')
    } finally {
      setCoLoading(false)
    }
  }

  // Auto-load on mount
  useEffect(() => { loadAdvice() }, [applicationId])

  const aff = advice ? (AFFORDABILITY_CONFIG[advice.affordability_verdict] ?? AFFORDABILITY_CONFIG.stretched) : null

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-violet-500" />
          <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">AI Negotiation Advisor</h3>
        </div>
        {fetched && (
          <button
            onClick={loadAdvice}
            disabled={loading}
            className="text-xs text-brand-600 dark:text-brand-400 hover:underline disabled:opacity-40"
          >
            Refresh
          </button>
        )}
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-2 text-slate-400 text-sm py-4 justify-center">
          <Loader2 size={14} className="animate-spin" />
          Analysing offers…
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="flex items-start gap-2 text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 rounded-xl p-3">
          <AlertCircle size={13} className="mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Advice */}
      {!loading && advice && (
        <>
          {/* Recommended option banner */}
          <div className="flex items-center gap-3 bg-brand-50 dark:bg-brand-500/10 rounded-xl p-3">
            <CheckCircle2 size={18} className="text-brand-600 dark:text-brand-400 flex-shrink-0" />
            <div>
              <p className="text-xs font-bold text-brand-700 dark:text-brand-400">
                Recommend Option {advice.recommended_option}
              </p>
              <p className="text-xs text-brand-600 dark:text-brand-300 mt-0.5 leading-relaxed">
                {advice.recommendation_reason}
              </p>
            </div>
          </div>

          {/* Affordability verdict */}
          <div className={cn('flex items-center gap-2 rounded-xl px-3 py-2', aff?.bg)}>
            <TrendingUp size={13} className={aff?.color} />
            <span className={cn('text-xs font-semibold', aff?.color)}>
              Affordability: {aff?.label}
            </span>
          </div>

          {/* Per-option risk + DTI */}
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Risk by Option</p>
            {(['A', 'B', 'C'] as const).map(opt => (
              <div
                key={opt}
                className={cn(
                  'border-l-2 pl-3 py-1',
                  OPTION_COLORS[opt],
                  advice.recommended_option === opt
                    ? 'opacity-100'
                    : 'opacity-60',
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Option {opt}</span>
                  <span className="text-[10px] text-slate-400">DTI {advice.dti_after_loan[opt].toFixed(1)}%</span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 leading-relaxed">
                  {advice.risk_analysis[opt]}
                </p>
              </div>
            ))}
          </div>

          {/* Counter-offer note */}
          <div className="flex items-start gap-2 bg-slate-50 dark:bg-white/[0.03] rounded-xl p-3">
            <ShieldAlert size={13} className="text-slate-400 mt-0.5 flex-shrink-0" />
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
              <span className="font-semibold text-slate-600 dark:text-slate-300">Counter-offer: </span>
              {advice.counter_offer_note}
            </p>
          </div>
        </>
      )}

      {/* ── Counter-offer simulator (always visible once fetched) ── */}
      {fetched && (
        <div className="border-t border-slate-100 dark:border-slate-800 pt-4 space-y-3">
          <div className="flex items-center gap-2">
            <Calculator size={13} className="text-slate-400" />
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Counter-offer Simulator</p>
          </div>
          <form onSubmit={simulateCounterOffer} className="flex gap-2">
            <div className="flex-1">
              <label className="text-[10px] text-slate-400 mb-1 block">Rate (% p.a.)</label>
              <input
                type="number"
                step="0.1"
                min="1"
                max="36"
                value={coRate}
                onChange={e => setCoRate(e.target.value)}
                className="input py-1.5 text-xs"
                placeholder="12.5"
              />
            </div>
            <div className="flex-1">
              <label className="text-[10px] text-slate-400 mb-1 block">Tenure (months)</label>
              <input
                type="number"
                step="1"
                min="3"
                max="84"
                value={coTenure}
                onChange={e => setCoTenure(e.target.value)}
                className="input py-1.5 text-xs"
                placeholder="24"
              />
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={coLoading}
                className="btn-primary py-1.5 px-3 text-xs flex items-center gap-1"
              >
                {coLoading ? <Loader2 size={11} className="animate-spin" /> : <Calculator size={11} />}
                Calc
              </button>
            </div>
          </form>

          {coError && (
            <p className="text-[11px] text-red-500">{coError}</p>
          )}

          {coResult && (
            <div className="grid grid-cols-3 gap-2 bg-slate-50 dark:bg-white/[0.03] rounded-xl p-3">
              <div>
                <p className="text-[10px] text-slate-400">Monthly EMI</p>
                <p className="text-xs font-bold text-brand-600 dark:text-brand-400">
                  ₹{Math.round(coResult.monthly_emi).toLocaleString('en-IN')}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400">Total Payable</p>
                <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  ₹{Math.round(coResult.total_payable).toLocaleString('en-IN')}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-slate-400">Interest Cost</p>
                <p className="text-xs font-semibold text-slate-500">
                  ₹{Math.round(coResult.total_interest).toLocaleString('en-IN')}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
