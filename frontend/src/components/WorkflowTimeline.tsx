import { useState, useEffect } from 'react'
import {
  CheckCircle2, Circle, Loader2, XCircle, Clock,
  User, ClipboardCheck, ShieldCheck, CreditCard,
  AlertTriangle, Scale, FileText, BadgeCheck, Banknote,
  ChevronDown, ChevronUp, Brain, UserCheck, AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Types ───────────────────────────────────────────────────────────────────

export interface AuditEvent {
  event: string
  actor: string
  payload: { stage?: string; result?: Record<string, unknown>; [key: string]: unknown } | null
  at: string
}

interface Props {
  currentStage?: string | null
  applicationStatus?: string
  auditEvents?: AuditEvent[]
}

// ── Stage metadata ───────────────────────────────────────────────────────────

const STAGES = [
  { key: 'lead_capture',          label: 'Lead Capture',          icon: User },
  { key: 'lead_qualification',    label: 'Lead Qualification',    icon: ClipboardCheck },
  { key: 'identity_verification', label: 'Identity Verification', icon: ShieldCheck },
  { key: 'credit_assessment',     label: 'Credit Assessment',     icon: CreditCard },
  { key: 'fraud_detection',       label: 'Fraud Detection',       icon: AlertTriangle },
  { key: 'compliance',            label: 'Compliance',            icon: Scale },
  { key: 'document_collection',   label: 'Document Collection',   icon: FileText },
  { key: 'sanction_processing',   label: 'Sanction & Approval',   icon: BadgeCheck },
  { key: 'disbursement',          label: 'Disbursement',          icon: Banknote },
]

// Stage-specific fields to surface in the dropdown
const STAGE_FIELDS: Record<string, Array<{ key: string; label: string; type: 'text' | 'decision' | 'amount' | 'score' | 'bool' | 'percent' }>> = {
  lead_capture: [
    { key: 'full_name',    label: 'Applicant',        type: 'text' },
    { key: 'loan_amount',  label: 'Requested Amount', type: 'amount' },
    { key: 'loan_purpose', label: 'Purpose',          type: 'text' },
    { key: 'pan_number',   label: 'PAN',              type: 'text' },
  ],
  lead_qualification: [
    { key: 'qualification_result', label: 'Decision', type: 'decision' },
    { key: 'qualification_notes',  label: 'Notes',    type: 'text' },
  ],
  identity_verification: [
    { key: 'identity_verified',        label: 'Verified',       type: 'bool' },
    { key: 'kyc_status',               label: 'KYC Status',     type: 'decision' },
    { key: 'identity_provider_response', label: 'Provider',     type: 'text' },
  ],
  credit_assessment: [
    { key: 'credit_score',          label: 'Credit Score',      type: 'score' },
    { key: 'credit_decision',       label: 'Decision',          type: 'decision' },
    { key: 'suggested_loan_amount', label: 'Suggested Amount',  type: 'amount' },
  ],
  fraud_detection: [
    { key: 'fraud_risk_score', label: 'Risk Score',   type: 'score' },
    { key: 'fraud_decision',   label: 'Decision',     type: 'decision' },
    { key: 'fraud_signals',    label: 'Risk Signals', type: 'text' },
  ],
  compliance: [
    { key: 'compliance_decision', label: 'Decision', type: 'decision' },
    { key: 'compliance_notes',    label: 'Notes',    type: 'text' },
    { key: 'compliance_checks',   label: 'Checks',   type: 'text' },
  ],
  document_collection: [
    { key: 'documents_verified',  label: 'Verified',   type: 'bool' },
    { key: 'required_documents',  label: 'Required',   type: 'text' },
  ],
  sanction_processing: [
    { key: 'sanction_amount',       label: 'Sanctioned Amount', type: 'amount' },
    { key: 'interest_rate_percent', label: 'Interest Rate',     type: 'percent' },
    { key: 'monthly_emi',           label: 'Monthly EMI',       type: 'amount' },
    { key: 'total_payable',         label: 'Total Payable',     type: 'amount' },
    { key: 'processing_fee',        label: 'Processing Fee',    type: 'amount' },
  ],
  disbursement: [
    { key: 'disbursement_status',    label: 'Status',    type: 'decision' },
    { key: 'disbursement_reference', label: 'Reference', type: 'text' },
  ],
}

// ── Helpers ─────────────────────────────────────────────────────────────────

type StageStatus = 'pending' | 'in_progress' | 'completed' | 'failed'

function getStatus(key: string, currentStage: string | null | undefined, appStatus: string | undefined): StageStatus {
  if (!currentStage) return 'pending'
  const ci = STAGES.findIndex(s => s.key === currentStage)
  const si = STAGES.findIndex(s => s.key === key)
  if (appStatus === 'rejected' && si === ci) return 'failed'
  if (appStatus === 'completed' || appStatus === 'disbursed' || si < ci) return 'completed'
  if (si === ci) return 'in_progress'
  return 'pending'
}

function fmtAmount(n: unknown): string {
  const num = Number(n)
  if (isNaN(num)) return String(n)
  if (num >= 10_000_000) return `₹${(num / 10_000_000).toFixed(2)}Cr`
  if (num >= 100_000)    return `₹${(num / 100_000).toFixed(2)}L`
  return `₹${Math.round(num).toLocaleString('en-IN')}`
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}

const POSITIVE = new Set(['qualified', 'approve', 'approved', 'clear', 'pass', 'passed', 'verified', 'success', 'disbursed', 'true', 'yes'])
const NEGATIVE  = new Set(['reject', 'rejected', 'block', 'blocked', 'fail', 'failed', 'false', 'no', 'fraud'])
const WARN      = new Set(['manual_review', 'flag', 'flagged', 'pending', 'pending_review', 'request_info', 'review'])

function decisionClass(val: string): string {
  const v = val.toLowerCase()
  if (POSITIVE.has(v)) return 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400'
  if (NEGATIVE.has(v))  return 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400'
  if (WARN.has(v))      return 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400'
  return 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
}

function ScoreBar({ value }: { value: number }) {
  // credit scores ~300-900; fraud risk 0-1
  const pct = value > 1 ? Math.min(100, Math.round((value - 300) / 6)) : Math.round(value * 100)
  const color = pct > 65 ? 'bg-emerald-500' : pct > 40 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2 flex-1 justify-end">
      <div className="w-16 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-semibold text-slate-800 dark:text-slate-200 text-xs tabular-nums">{value}</span>
    </div>
  )
}

function FieldValue({ type, value }: { type: string; value: unknown }) {
  if (value === null || value === undefined) return null
  const str = Array.isArray(value) ? value.join(', ') : String(value)

  if (type === 'amount') return (
    <span className="font-semibold text-brand-600 dark:text-brand-400">{fmtAmount(value)}</span>
  )
  if (type === 'percent') return (
    <span className="font-semibold text-slate-800 dark:text-slate-200">{str}%</span>
  )
  if (type === 'bool') {
    const yes = str === 'true' || str === 'yes'
    return (
      <span className={cn('badge text-[10px]', yes
        ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400'
        : 'bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400')}>
        {yes ? 'Yes' : 'No'}
      </span>
    )
  }
  if (type === 'decision') return (
    <span className={cn('badge text-[10px]', decisionClass(str))}>
      {str.replace(/_/g, ' ')}
    </span>
  )
  if (type === 'score') return <ScoreBar value={Number(value)} />
  return <span className="text-slate-700 dark:text-slate-300 text-right">{str}</span>
}

// ── Sub-components ──────────────────────────────────────────────────────────

function StatusIcon({ status, size = 16 }: { status: StageStatus; size?: number }) {
  if (status === 'completed')  return <CheckCircle2 size={size} className="text-emerald-500" />
  if (status === 'in_progress') return <Loader2    size={size} className="text-brand-500 animate-spin" />
  if (status === 'failed')     return <XCircle     size={size} className="text-red-500" />
  return <Circle size={size} className="text-slate-300 dark:text-slate-600" />
}

function ActorBadge({ actor }: { actor: string }) {
  const isRM = actor === 'rm' || actor.startsWith('rm_') || actor.startsWith('user_')
  return isRM ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400">
      <UserCheck size={9} /> RM Reviewed
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-400">
      <Brain size={9} /> AI Agent
    </span>
  )
}

interface StageDetailProps {
  stageKey: string
  auditEvent: AuditEvent | undefined
  rmEvent: AuditEvent | undefined
}

function StageDetail({ stageKey, auditEvent, rmEvent }: StageDetailProps) {
  const result = auditEvent?.payload?.result ?? {}
  const fields = STAGE_FIELDS[stageKey] ?? []

  // Collect fields that have values
  const visibleFields = fields.filter(f => {
    const v = result[f.key]
    return v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && v.length === 0)
  })

  // Also collect any extra fields not in the config (generic fallback)
  const configuredKeys = new Set(fields.map(f => f.key))
  const extraEntries = Object.entries(result).filter(
    ([k, v]) => !configuredKeys.has(k) && typeof v !== 'object' && v !== null && v !== undefined && v !== ''
  )

  return (
    <div className="space-y-3">
      {/* RM Review section (for sanction_processing with HITL) */}
      {rmEvent && (
        <div className="rounded-xl border border-violet-200 dark:border-violet-500/20 bg-violet-50 dark:bg-violet-500/10 p-3 space-y-2">
          <div className="flex items-center gap-2">
            <UserCheck size={11} className="text-violet-600 dark:text-violet-400" />
            <span className="text-[10px] font-bold text-violet-600 dark:text-violet-400 uppercase tracking-wider">
              Human Review Decision
            </span>
            <span className="ml-auto text-[10px] text-slate-400">{fmtTime(rmEvent.at)}</span>
          </div>
          <div className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1.5 text-xs">
            {rmEvent.payload?.decision !== undefined && (
              <>
                <span className="text-slate-500 dark:text-slate-400">Decision</span>
                <FieldValue type="decision" value={rmEvent.payload.decision as string} />
              </>
            )}
            {rmEvent.payload?.notes && (
              <>
                <span className="text-slate-500 dark:text-slate-400 self-start">Notes</span>
                <span className="text-slate-700 dark:text-slate-300 text-right text-wrap max-w-[160px]">
                  {rmEvent.payload.notes as string}
                </span>
              </>
            )}
          </div>
        </div>
      )}

      {/* AI decisions */}
      {auditEvent && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <ActorBadge actor={auditEvent.actor} />
            </div>
            <span className="text-[10px] text-slate-400">{fmtTime(auditEvent.at)}</span>
          </div>

          {visibleFields.length > 0 ? (
            <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1.5 text-xs">
              {visibleFields.map(f => (
                <div key={f.key} className="contents">
                  <dt className="text-slate-500 dark:text-slate-400 self-center">{f.label}</dt>
                  <dd className="flex items-center justify-end">
                    <FieldValue type={f.type} value={result[f.key]} />
                  </dd>
                </div>
              ))}
              {extraEntries.map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-slate-500 dark:text-slate-400">{k.replace(/_/g, ' ')}</dt>
                  <dd className="text-slate-700 dark:text-slate-300 text-right">{String(v)}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-xs text-slate-400 italic">
              Agent completed this stage — no detailed output recorded.
            </p>
          )}
        </div>
      )}

      {/* Nothing at all — in_progress placeholder */}
      {!auditEvent && !rmEvent && (
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <AlertCircle size={12} className="text-brand-400" />
          Processing in progress — results will appear here once complete.
        </div>
      )}
    </div>
  )
}

// ── Main component ──────────────────────────────────────────────────────────

export default function WorkflowTimeline({ currentStage, applicationStatus, auditEvents = [] }: Props) {
  // Auto-expand the active stage
  const [expanded, setExpanded] = useState<string | null>(currentStage ?? null)

  useEffect(() => {
    if (currentStage) setExpanded(currentStage)
  }, [currentStage])

  // Index audit events by stage key for O(1) lookup
  const stageAuditMap: Record<string, AuditEvent> = {}
  let rmReviewEvent: AuditEvent | undefined
  for (const ev of auditEvents) {
    if (ev.event.startsWith('stage.') && ev.event.endsWith('.completed')) {
      const key = ev.event.slice('stage.'.length, -'.completed'.length)
      stageAuditMap[key] = ev
    }
    if (ev.event === 'rm_review_submitted') {
      rmReviewEvent = ev
    }
  }

  return (
    <div className="space-y-0.5">
      {STAGES.map((stage, idx) => {
        const status    = getStatus(stage.key, currentStage, applicationStatus)
        const isLast    = idx === STAGES.length - 1
        const Icon      = stage.icon
        const isOpen    = expanded === stage.key
        const isClickable = status !== 'pending'
        const auditEvent = stageAuditMap[stage.key]
        const isHITL = stage.key === 'sanction_processing' && !!rmReviewEvent

        return (
          <div key={stage.key}>
            {/* ── Stage row ── */}
            <div
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-150',
                status === 'in_progress' && 'bg-brand-50 dark:bg-brand-500/10 ring-1 ring-brand-200 dark:ring-brand-500/30',
                status === 'failed'      && 'bg-red-50 dark:bg-red-500/10',
                isClickable && 'cursor-pointer hover:bg-slate-50 dark:hover:bg-white/[0.03]',
              )}
              onClick={() => isClickable && setExpanded(isOpen ? null : stage.key)}
              role={isClickable ? 'button' : undefined}
              aria-expanded={isOpen}
            >
              {/* Stage icon */}
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

              <StatusIcon status={status} size={15} />

              <span className={cn(
                'text-sm flex-1',
                status === 'in_progress' ? 'font-semibold text-brand-600 dark:text-brand-400' :
                status === 'completed'   ? 'text-slate-600 dark:text-slate-400' :
                status === 'failed'      ? 'font-medium text-red-500' :
                'text-slate-400 dark:text-slate-600',
              )}>
                {stage.label}
              </span>

              {/* Right-side indicators */}
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {isHITL && status === 'completed' && (
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400">
                    <UserCheck size={9} /> Human
                  </span>
                )}
                {status === 'in_progress' && (
                  <span className="text-xs text-brand-500 font-medium flex items-center gap-1">
                    <Clock size={11} /> Processing
                  </span>
                )}
                {status === 'completed' && !isHITL && (
                  <span className="text-[10px] text-emerald-500">Done</span>
                )}
                {status === 'failed' && (
                  <span className="text-[10px] text-red-400">Rejected</span>
                )}
                {isClickable && (
                  <span className="text-slate-300 dark:text-slate-600">
                    {isOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                  </span>
                )}
              </div>
            </div>

            {/* ── Expandable detail panel ── */}
            {isClickable && isOpen && (
              <div className="mx-3 mb-1 px-4 py-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-700/40 animate-fade-in">
                <StageDetail
                  stageKey={stage.key}
                  auditEvent={auditEvent}
                  rmEvent={stage.key === 'sanction_processing' ? rmReviewEvent : undefined}
                />
              </div>
            )}

            {/* ── Connector line ── */}
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
