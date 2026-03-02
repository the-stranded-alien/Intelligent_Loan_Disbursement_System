import { useParams } from 'react-router-dom'
import WorkflowTimeline from '@/components/WorkflowTimeline'

export default function StatusTracker() {
  const { applicationId } = useParams<{ applicationId: string }>()

  // TODO: Fetch application status via REST + subscribe to WebSocket for live updates
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Application Status</h1>
      {applicationId ? (
        <WorkflowTimeline applicationId={applicationId} />
      ) : (
        <p className="text-gray-500">Enter an Application ID to track status.</p>
      )}
    </div>
  )
}
