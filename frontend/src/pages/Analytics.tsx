import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function Analytics() {
  // TODO: Fetch metrics from GET /api/v1/analytics/overview and /pipeline
  const placeholder = [
    { stage: 'Lead Capture', pass: 95, fail: 5 },
    { stage: 'Qualification', pass: 72, fail: 28 },
    { stage: 'Identity', pass: 88, fail: 12 },
    { stage: 'Credit', pass: 65, fail: 35 },
    { stage: 'Fraud', pass: 92, fail: 8 },
    { stage: 'Compliance', pass: 98, fail: 2 },
    { stage: 'Documents', pass: 80, fail: 20 },
    { stage: 'Sanction', pass: 90, fail: 10 },
    { stage: 'Disbursement', pass: 96, fail: 4 },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h1>
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold mb-4">Pipeline Pass/Fail Rates (%)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={placeholder}>
            <XAxis dataKey="stage" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Bar dataKey="pass" fill="#22c55e" name="Pass %" />
            <Bar dataKey="fail" fill="#ef4444" name="Fail %" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
