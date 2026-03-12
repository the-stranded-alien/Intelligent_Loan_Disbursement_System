import { useState } from 'react'
import { Calculator, TrendingUp } from 'lucide-react'

interface Props {
  applicationId: string
}

export default function WhatIfAnalysis({ applicationId: _ }: Props) {
  const [amount, setAmount]   = useState(500000)
  const [tenure, setTenure]   = useState(36)
  const [rate]                = useState(12)

  const emi = amount * (rate / 1200) * Math.pow(1 + rate / 1200, tenure) /
    (Math.pow(1 + rate / 1200, tenure) - 1)
  const totalPayable = emi * tenure
  const totalInterest = totalPayable - amount

  const fmt = (n: number) => `₹${Math.round(n).toLocaleString('en-IN')}`

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Calculator size={15} className="text-brand-500" />
        <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">What-If Simulator</h3>
      </div>

      <div className="space-y-3">
        <div>
          <div className="flex justify-between mb-1">
            <label className="label">Loan Amount</label>
            <span className="text-xs font-medium text-brand-600 dark:text-brand-400">{fmt(amount)}</span>
          </div>
          <input type="range" min={50000} max={5000000} step={50000} value={amount}
            onChange={e => setAmount(+e.target.value)}
            className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer accent-brand-600" />
        </div>

        <div>
          <div className="flex justify-between mb-1">
            <label className="label">Tenure</label>
            <span className="text-xs font-medium text-brand-600 dark:text-brand-400">{tenure} months</span>
          </div>
          <input type="range" min={6} max={84} step={6} value={tenure}
            onChange={e => setTenure(+e.target.value)}
            className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer accent-brand-600" />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-1">
        {[
          { label: 'Monthly EMI', value: fmt(emi), icon: '📅' },
          { label: 'Total Interest', value: fmt(totalInterest), icon: '📈' },
          { label: 'Total Payable', value: fmt(totalPayable), icon: '💰' },
        ].map(({ label, value, icon }) => (
          <div key={label} className="bg-slate-50 dark:bg-slate-800 rounded-xl p-3 text-center">
            <p className="text-base mb-1">{icon}</p>
            <p className="text-xs font-bold text-slate-800 dark:text-slate-100">{value}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        <TrendingUp size={11} />
        <span>Indicative at {rate}% p.a. — actual rate may vary</span>
      </div>
    </div>
  )
}
