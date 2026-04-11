import { useWorkflowSocket, PipelineEvent } from '@/hooks/useWorkflowSocket'
import { Wifi, WifiOff, Bell, CheckCircle2, Zap, AlertCircle, Info, Loader2, Mail, FileQuestion, Bot } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  applicationId?: string
  // Optional: pass events/connected from a parent that already owns the socket
  events?: PipelineEvent[]
  connected?: boolean
}

// ── Event type config ──────────────────────────────────────────────────────

const EVENT_CONFIG: Record<string, { icon: React.ElementType; color: string; dot: string }> = {
  'node.started':       { icon: Loader2,       color: 'text-brand-500',   dot: 'bg-brand-500'   },
  'node.completed':     { icon: CheckCircle2,  color: 'text-emerald-500', dot: 'bg-emerald-500' },
  'pipeline.completed': { icon: Zap,           color: 'text-indigo-500',  dot: 'bg-indigo-500'  },
  'hitl.requested':     { icon: AlertCircle,   color: 'text-amber-500',   dot: 'bg-amber-500'   },
  'outreach.required':  { icon: Mail,          color: 'text-orange-500',  dot: 'bg-orange-500'  },
  'outreach.sent':      { icon: Mail,          color: 'text-emerald-500', dot: 'bg-emerald-500' },
  'info_requested':     { icon: FileQuestion,  color: 'text-violet-500',  dot: 'bg-violet-500'  },
  'assessment_ready':   { icon: Bot,           color: 'text-violet-500',  dot: 'bg-violet-500'  },
  'connected':          { icon: Wifi,          color: 'text-brand-500',   dot: 'bg-brand-500'   },
}

const DEFAULT_CONFIG = { icon: Info, color: 'text-slate-400', dot: 'bg-slate-400' }

// ── Helpers ────────────────────────────────────────────────────────────────

function relativeTime(ts?: string): string {
  if (!ts) return ''
  const diff = (Date.now() - new Date(ts).getTime()) / 1000
  if (diff < 5)  return 'just now'
  if (diff < 60) return `${Math.floor(diff)}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function stageLabel(stage?: string): string {
  const MAP: Record<string, string> = {
    lead_capture: 'Eligibility Check', lead_qualification: 'Doc Verification',
    identity_verification: 'KYC', credit_assessment: 'Credit',
    art_negotiation: 'ART & Offer', enach: 'e-NACH Setup',
    esign: 'E-Sign',
  }
  return stage ? (MAP[stage] ?? stage) : ''
}

function eventLabel(e: PipelineEvent): string {
  switch (e.event) {
    case 'node.started':      return `${stageLabel(e.stage)} started`
    case 'node.completed':    return `${stageLabel(e.stage)} completed`
    case 'pipeline.completed':return 'Pipeline finished'
    case 'hitl.requested':    return 'RM review required'
    case 'outreach.required': return 'Follow-up triggered'
    case 'outreach.sent':     return 'Follow-up sent'
    case 'info_requested':    return 'More info needed'
    case 'assessment_ready':  return 'AI advisor ready to chat'
    default:                  return e.event
  }
}

function eventSub(e: PipelineEvent): string {
  switch (e.event) {
    case 'node.started':
    case 'node.completed':
      return e.stage && e.event !== 'node.completed' ? stageLabel(e.stage) : ''
    case 'outreach.required':
      return (e.data as Record<string, unknown> | undefined)?.hours_stale
        ? `Application stale ${(e.data as Record<string, unknown>).hours_stale}h`
        : ''
    case 'outreach.sent':
      return (e as unknown as Record<string, unknown>).subject as string ?? ''
    case 'info_requested':
      return (e as unknown as Record<string, unknown>).reason as string ?? 'Qualification needs clarification'
    case 'assessment_ready':
      return 'Priya · AI Advisor is waiting'
    default:
      return e.stage ? stageLabel(e.stage) : ''
  }
}

// ── Component ──────────────────────────────────────────────────────────────

export default function NotificationFeed({ applicationId, events: propEvents, connected: propConnected }: Props) {
  // Use the parent-provided socket data if available, otherwise open our own
  const own = useWorkflowSocket(propEvents !== undefined ? undefined : applicationId)
  const events    = propEvents    ?? own.events
  const connected = propConnected ?? own.connected

  return (
    <div className="card p-5 space-y-3 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <Bell size={14} className="text-brand-500" />
          <h3 className="font-semibold text-slate-800 dark:text-slate-100 text-sm">Live Updates</h3>
          {events.length > 0 && (
            <span className="badge bg-brand-100 dark:bg-brand-500/20 text-brand-700 dark:text-brand-400">
              {events.length}
            </span>
          )}
        </div>
        <span className={cn(
          'flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full',
          connected
            ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
            : 'bg-slate-100 dark:bg-slate-800 text-slate-400',
        )}>
          {connected ? <Wifi size={11} /> : <WifiOff size={11} />}
          {connected ? 'Live' : applicationId ? 'Offline' : '—'}
        </span>
      </div>

      {/* Event list */}
      <div className="flex-1 min-h-0">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full py-6 text-center">
            <Bell size={24} className="text-slate-200 dark:text-slate-700 mb-2" />
            <p className="text-xs text-slate-400 dark:text-slate-500">
              {applicationId ? 'Waiting for pipeline events…' : 'Select an application'}
            </p>
          </div>
        ) : (
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {events.map((e, i) => {
              const cfg  = EVENT_CONFIG[e.event] ?? DEFAULT_CONFIG
              const Icon = cfg.icon
              return (
                <div key={i} className="flex items-start gap-2.5 text-xs group">
                  <div className={cn('mt-0.5 flex-shrink-0', cfg.color)}>
                    <Icon size={13} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-700 dark:text-slate-300 truncate">
                      {eventLabel(e)}
                    </p>
                    {eventSub(e) && (
                      <p className="text-slate-400 truncate text-[11px]">{eventSub(e)}</p>
                    )}
                  </div>
                  {e.timestamp && (
                    <span className="text-slate-300 dark:text-slate-600 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      {relativeTime(e.timestamp)}
                    </span>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
