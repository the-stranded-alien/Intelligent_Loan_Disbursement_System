import { CheckCircle2, Circle, Loader2, XCircle, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'

interface StageStatus {
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'current'
}

interface Props {
  currentStage?: string | null
  applicationStatus?: string
}

const STAGES = [
  { key: 'lead_capture',          label: 'Lead Capture' },
  { key: 'lead_qualification',    label: 'Lead Qualification' },
  { key: 'identity_verification', label: 'Identity Verification' },
  { key: 'credit_assessment',     label: 'Credit Assessment' },
  { key: 'fraud_detection',       label: 'Fraud Detection' },
  { key: 'compliance',            label: 'Compliance' },
  { key: 'document_collection',   label: 'Document Collection' },
  { key: 'sanction_processing',   label: 'Sanction Processing' },
  { key: 'disbursement',          label: 'Disbursement' },
]

function getStageStatus(stageKey: string, currentStage: string | null | undefined, appStatus: string | undefined): StageStatus['status'] {
  if (!currentStage) return 'pending'
  const currentIdx = STAGES.findIndex(s => s.key === currentStage)
  const stageIdx   = STAGES.findIndex(s => s.key === stageKey)
  if (appStatus === 'rejected' && stageIdx === currentIdx) return 'failed'
  if (appStatus === 'disbursed' || (stageIdx < currentIdx)) return 'completed'
  if (stageIdx === currentIdx) return 'in_progress'
  return 'pending'
}

function StageIcon({ status }: StageStatus) {
  if (status === 'completed')  return <CheckCircle2 size={18} className="text-emerald-500" />
  if (status === 'in_progress') return <Loader2 size={18} className="text-brand-500 animate-spin" />
  if (status === 'failed')     return <XCircle size={18} className="text-red-500" />
  return <Circle size={18} className="text-slate-300 dark:text-slate-600" />
}

export default function WorkflowTimeline({ currentStage, applicationStatus }: Props) {
  return (
    <div className="space-y-1">
      {STAGES.map((stage, idx) => {
        const status = getStageStatus(stage.key, currentStage, applicationStatus)
        const isLast = idx === STAGES.length - 1
        return (
          <div key={stage.key}>
            <div className={cn(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
              status === 'in_progress' && 'bg-brand-50 dark:bg-brand-500/10',
              status === 'completed'   && 'opacity-70',
            )}>
              <StageIcon status={status} />
              <span className={cn(
                'text-sm',
                status === 'in_progress' ? 'font-semibold text-brand-600 dark:text-brand-400' :
                status === 'completed'   ? 'text-slate-500 dark:text-slate-400' :
                status === 'failed'      ? 'text-red-500' :
                'text-slate-400 dark:text-slate-600'
              )}>
                {stage.label}
              </span>
              {status === 'in_progress' && (
                <span className="ml-auto text-xs text-brand-500 font-medium flex items-center gap-1">
                  <Clock size={11} /> Processing
                </span>
              )}
              {status === 'completed' && (
                <span className="ml-auto text-xs text-emerald-500">Done</span>
              )}
            </div>
            {!isLast && (
              <div className={cn(
                'ml-[22px] w-px h-3',
                status === 'completed' ? 'bg-emerald-300 dark:bg-emerald-700' : 'bg-slate-200 dark:bg-slate-700'
              )} />
            )}
          </div>
        )
      })}
    </div>
  )
}
