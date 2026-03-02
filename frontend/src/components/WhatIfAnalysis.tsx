interface Props {
  applicationId: string
}

export default function WhatIfAnalysis({ applicationId }: Props) {
  // TODO: Allow RM to adjust loan parameters and see simulated re-assessment results
  //       without persisting changes — for informed human review
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h2 className="text-lg font-semibold mb-2">What-If Analysis</h2>
      <p className="text-sm text-gray-500">
        Adjust parameters to simulate different scenarios.
      </p>
    </div>
  )
}
