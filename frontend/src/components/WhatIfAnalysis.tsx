import { useState } from 'react'
import { Calculator, TrendingUp, Percent } from 'lucide-react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

interface Props { applicationId: string }

export default function WhatIfAnalysis({ applicationId: _ }: Props) {
  const [amount, setAmount] = useState(500_000)
  const [tenure, setTenure] = useState(36)
  const [rate,   setRate]   = useState(12)

  const r   = rate / 1200
  const emi = amount * r * Math.pow(1 + r, tenure) / (Math.pow(1 + r, tenure) - 1)
  const totalPayable  = emi * tenure
  const totalInterest = totalPayable - amount

  const fmt = (n: number) =>
    n >= 100_000
      ? `₹${(n / 100_000).toFixed(1)}L`
      : `₹${Math.round(n).toLocaleString('en-IN')}`

  const pieData = [
    { name: 'Principal', value: Math.round(amount) },
    { name: 'Interest',  value: Math.round(totalInterest) },
  ]

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Calculator size={14} className="text-brand-500" />
        <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">What-If Simulator</h3>
      </div>

      {/* Sliders */}
      <div className="space-y-3.5">
        {/* Amount */}
        <div>
          <div className="flex justify-between mb-1">
            <label className="label">Loan Amount</label>
            <span className="text-xs font-semibold text-brand-600 dark:text-brand-400">{fmt(amount)}</span>
          </div>
          <input type="range" min={50_000} max={5_000_000} step={50_000} value={amount}
            onChange={e => setAmount(+e.target.value)}
            className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer accent-brand-600" />
        </div>

        {/* Tenure */}
        <div>
          <div className="flex justify-between mb-1">
            <label className="label">Tenure</label>
            <span className="text-xs font-semibold text-brand-600 dark:text-brand-400">{tenure} months</span>
          </div>
          <input type="range" min={6} max={84} step={6} value={tenure}
            onChange={e => setTenure(+e.target.value)}
            className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer accent-brand-600" />
        </div>

        {/* Interest rate */}
        <div>
          <div className="flex justify-between mb-1">
            <label className="label flex items-center gap-1"><Percent size={10} />Interest Rate p.a.</label>
            <span className={`text-xs font-semibold ${rate <= 10 ? 'text-emerald-500' : rate <= 15 ? 'text-amber-500' : 'text-red-500'}`}>
              {rate}%
            </span>
          </div>
          <input type="range" min={8} max={24} step={0.5} value={rate}
            onChange={e => setRate(+e.target.value)}
            className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full appearance-none cursor-pointer accent-brand-600" />
        </div>
      </div>

      {/* Donut + stats */}
      <div className="flex items-center gap-4">
        <div className="w-28 h-28 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={28} outerRadius={46} dataKey="value" paddingAngle={2}>
                <Cell fill="#6366f1" />
                <Cell fill="#f59e0b" />
              </Pie>
              <Tooltip
                formatter={(v: number) => fmt(v)}
                contentStyle={{ fontSize: 11, borderRadius: 6, border: 'none', boxShadow: '0 2px 10px rgba(0,0,0,0.15)' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-slate-500">
              <span className="w-2 h-2 rounded-full bg-brand-500 flex-shrink-0" />
              Principal
            </span>
            <span className="font-semibold text-slate-700 dark:text-slate-300">{fmt(amount)}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-slate-500">
              <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
              Interest
            </span>
            <span className="font-semibold text-amber-600 dark:text-amber-400">{fmt(totalInterest)}</span>
          </div>
          <div className="pt-1 border-t border-slate-100 dark:border-slate-700 flex items-center justify-between text-xs">
            <span className="font-medium text-slate-600 dark:text-slate-400">Monthly EMI</span>
            <span className="font-bold text-slate-900 dark:text-white text-sm">{fmt(emi)}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500">Total Payable</span>
            <span className="font-semibold text-slate-700 dark:text-slate-300">{fmt(totalPayable)}</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-xs text-slate-400">
        <TrendingUp size={11} />
        <span>Indicative only — actual rate set by RM</span>
      </div>
    </div>
  )
}
