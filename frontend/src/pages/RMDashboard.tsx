import AgentDecisionCard from '@/components/AgentDecisionCard'
import WhatIfAnalysis from '@/components/WhatIfAnalysis'

export default function RMDashboard() {
  // TODO: Fetch HITL queue from GET /api/v1/rm/queue
  //       Display pending reviews with AI analysis context
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-4">RM Dashboard</h1>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AgentDecisionCard applicationId="" />
        <WhatIfAnalysis applicationId="" />
      </div>
    </div>
  )
}
