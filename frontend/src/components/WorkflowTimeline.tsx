interface Props {
  applicationId: string
}

const PIPELINE_STAGES = [
  'Lead Capture',
  'Lead Qualification',
  'Identity Verification',
  'Credit Assessment',
  'Fraud Detection',
  'Compliance',
  'Document Collection',
  'Sanction Processing',
  'Disbursement',
]

export default function WorkflowTimeline({ applicationId }: Props) {
  // TODO: Accept live stage data from useWorkflowSocket hook
  //       Render each stage with status icon (pending / in_progress / complete / failed)
  return (
    <div className="space-y-3">
      {PIPELINE_STAGES.map((stage, idx) => (
        <div key={idx} className="flex items-center gap-3">
          <div className="w-6 h-6 rounded-full bg-gray-200 flex-shrink-0" />
          <span className="text-sm text-gray-700">{stage}</span>
        </div>
      ))}
    </div>
  )
}
