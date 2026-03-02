interface Props {
  applicationId: string
}

export default function AgentDecisionCard({ applicationId }: Props) {
  // TODO: Display the AI agent's decision rationale for each pipeline node
  //       Data source: GET /api/v1/rm/{application_id}/context
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-2">AI Decision Summary</h2>
      <p className="text-sm text-gray-500">
        {applicationId ? `Showing context for ${applicationId}` : 'No application selected.'}
      </p>
    </div>
  )
}
