import { useState } from 'react'
import {
  CheckCircle2, Circle, Loader2, XCircle, Clock,
  User, ClipboardCheck, ShieldCheck, CreditCard,
  AlertTriangle, Scale, FileText, BadgeCheck, Banknote,
  ChevronDown, ChevronUp,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Stage metadata ─────────────────────────────────────────────────────────

const STAGES = [
  { key: 'lead_capture',          label: 'Lead Capture',          icon: User },
  { key: 'lead_qualification',    label: 'Lead Qualification',    icon: ClipboardCheck },
  { key: 'identity_verification', label: 'Identity Verification', icon: ShieldCheck },
  { key: 'credit_assessment',     label: 'Credit Assessment',     icon: CreditCard },
  { key: 'fraud_detection',       label: 'Fraud Detection',       icon: AlertTriangle },
  { key: 'compliance',            label: 'Compliance',            icon: Scale },
  { key: 'document_collection',   label: 'Document Collection',   icon: FileText },
  { key: 'sanction_processing',   label: 'Sanction Processing',   icon: BadgeCheck },
  { key: 'disbursement',          label: 'Disbursement',          icon: Banknote },
]

type StageStatus = 'pending' | 'in_progress' | 'completed' | 'failed'

interface Props {
  currentStage?: string | null
  applicationStatus?: string
  stageResults?: Record<string, Record<string, unknown>>
}

// ── Helpers ────────────────────────────────────────────────────────────────

function getStatus(
  key: string,
  currentStage: string | null | undefined,
  appStatus: string | undefined,
): StageStatus {
  if (!currentStage) return 'pending'
  const ci = STAGES.findIndex(s => s.key === currentStage)
  const si = STAGES.findIndex(s => s.key === key)
  if (appStatus === 'rejected' && si === ci) return 'failed'
  if (appStatus === 'completed' || appStatus === 'disbursed' || si < ci) return 'completed'
  if (si === ci) return 'in_progress'
  return 'pending'
}

function StatusIcon({ status, size = 16 }: { status: StageStatus; size?: number }) {
  if (status === 'completed')  return <CheckCircle2 size={size} className="text-emerald-500" />
  if (status === 'in_progress') return <Loader2    size={size} className="text-brand-500 animate-spin" />
  if (status === 'failed')     return <XCircle     size={size} className="text-red-500" />
  return <Circle size={size} className="text-slate-300 dark:text-slate-600" />
}

/** Render the most useful key-value pairs from a stage result object */
function ResultSummary({ result }: { result: Record<string, unknown> }) {
  const entries = Object.entries(result).filter(
    ([, v]) => v !== null && v !== undefined && typeof v !== 'object'
  )
  if (entries.length === 0) return <p className="text-xs text-slate-400">No details available.</p>
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
      {entries.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-slate-500 dark:text-slate-400 truncate">{k.replace(/_/g, ' ')}</dt>
          <dd className="font-medium text-slate-800 dark:text-slate-200 truncate text-right">{String(v)}</dd>
        </div>
      ))}
    </dl>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function WorkflowTimeline({ currentStage, applicationStatus, stageResults }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <div className="space-y-0.5">
      {STAGES.map((stage, idx) => {
        const status    = getStatus(stage.key, currentStage, applicationStatus)
        const isLast    = idx === STAGES.length - 1
        const Icon      = stage.icon
        const result    = stageResults?.[stage.key]
        const hasResult = status === 'completed' && result && Object.keys(result).length > 0
        const isOpen    = expanded === stage.key

        return (
          <div key={stage.key}>
            <div
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all',
                status === 'in_progress' && 'bg-brand-50 dark:bg-brand-500/10 ring-1 ring-brand-200 dark:ring-brand-500/30',
                status === 'completed'   && 'opacity-80',
                status === 'failed'      && 'bg-red-50 dark:bg-red-500/10',
                hasResult && 'cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50',
              )}
              onClick={() => hasResult && setExpanded(isOpen ? null : stage.key)}
              role={hasResult ? 'button' : undefined}
            >
              {/* Stage type icon */}
              <div className={cn(
                'w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0',
                status === 'completed'   ? 'bg-emerald-50 dark:bg-emerald-500/10' :
                status === 'in_progress' ? 'bg-brand-50 dark:bg-brand-500/10' :
                status === 'failed'      ? 'bg-red-50 dark:bg-red-500/10' :
                'bg-slate-100 dark:bg-slate-800',
              )}>
                <Icon size={13} className={cn(
                  status === 'completed'   ? 'text-emerald-500' :
                  status === 'in_progress' ? 'text-brand-500' :
                  status === 'failed'      ? 'text-red-500' :
                  'text-slate-400 dark:text-slate-600',
                )} />
              </div>

              {/* Status icon + label */}
              <StatusIcon status={status} size={15} />
              <span className={cn(
                'text-sm flex-1',
                status === 'in_progress' ? 'font-semibold text-brand-600 dark:text-brand-400' :
                status === 'completed'   ? 'text-slate-500 dark:text-slate-400' :
                status === 'failed'      ? 'font-medium text-red-500' :
                'text-slate-400 dark:text-slate-600',
              )}>
                {stage.label}
              </span>

              {/* Right badge */}
              {status === 'in_progress' && (
                <span className="text-xs text-brand-500 font-medium flex items-center gap-1 flex-shrink-0">
                  <Clock size={11} /> Processing
                </span>
              )}
              {status === 'completed' && (
                <span className="text-xs text-emerald-500 flex-shrink-0">Done</span>
              )}
              {status === 'failed' && (
                <span className="text-xs text-red-400 flex-shrink-0">Rejected</span>
              )}

              {/* Expand chevron */}
              {hasResult && (
                <span className="text-slate-400 flex-shrink-0">
                  {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                </span>
              )}
            </div>

            {/* Expandable result */}
            {hasResult && isOpen && result && (
              <div className="mx-3 mb-1 px-4 py-3 bg-slate-50 dark:bg-slate-800/60 rounded-xl border border-slate-100 dark:border-slate-700/50">
                <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  AI Decision
                </p>
                <ResultSummary result={result} />
              </div>
            )}

            {/* Connector line */}
            {!isLast && (
              <div className={cn(
                'ml-[22px] w-px h-2',
                status === 'completed' ? 'bg-emerald-300 dark:bg-emerald-700' : 'bg-slate-200 dark:bg-slate-700',
              )} />
            )}
          </div>
        )
      })}
    </div>
  )
}
