import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { Send, Bot, User, CheckCircle2, AlertCircle, ArrowLeft, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Types ──────────────────────────────────────────────────────────────────

interface Message {
  role: 'assistant' | 'user'
  text: string
}

interface AssessmentResult {
  repayment_confidence: 'high' | 'medium' | 'low'
  recommendation: 'approve' | 'review' | 'reject'
  risk_flags: string[]
  assessment_notes: string
  conversation_summary: string
}

// ── Helpers ────────────────────────────────────────────────────────────────

const CONFIDENCE_CONFIG = {
  high:   { label: 'High Confidence',   color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/30' },
  medium: { label: 'Medium Confidence', color: 'text-amber-600 dark:text-amber-400',    bg: 'bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/30' },
  low:    { label: 'Low Confidence',    color: 'text-red-600 dark:text-red-400',        bg: 'bg-red-50 dark:bg-red-500/10 border-red-200 dark:border-red-500/30' },
}

const RECOMMENDATION_CONFIG = {
  approve: { label: 'Recommend: Approve', color: 'text-emerald-700 dark:text-emerald-400' },
  review:  { label: 'Recommend: Further Review', color: 'text-amber-700 dark:text-amber-400' },
  reject:  { label: 'Recommend: Reject', color: 'text-red-700 dark:text-red-400' },
}

// ── Message Bubble ─────────────────────────────────────────────────────────

function ChatBubble({ msg }: { msg: Message }) {
  const isAssistant = msg.role === 'assistant'
  return (
    <div className={cn('flex gap-3', isAssistant ? 'justify-start' : 'justify-end')}>
      {isAssistant && (
        <div className="w-8 h-8 rounded-xl bg-brand-100 dark:bg-brand-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Bot size={14} className="text-brand-600 dark:text-brand-400" />
        </div>
      )}
      <div
        className={cn(
          'max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
          isAssistant
            ? 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200/60 dark:border-white/[0.06] rounded-tl-sm'
            : 'bg-brand-600 text-white rounded-tr-sm',
        )}
      >
        {msg.text}
      </div>
      {!isAssistant && (
        <div className="w-8 h-8 rounded-xl bg-slate-200 dark:bg-slate-700 flex items-center justify-center flex-shrink-0 mt-0.5">
          <User size={14} className="text-slate-600 dark:text-slate-400" />
        </div>
      )}
    </div>
  )
}

// ── Result Card ────────────────────────────────────────────────────────────

function ResultCard({ result }: { result: AssessmentResult }) {
  const conf = CONFIDENCE_CONFIG[result.repayment_confidence] ?? CONFIDENCE_CONFIG.medium
  const rec = RECOMMENDATION_CONFIG[result.recommendation] ?? RECOMMENDATION_CONFIG.review
  return (
    <div className={cn('card p-5 border space-y-4', conf.bg)}>
      <div className="flex items-center gap-2">
        <CheckCircle2 size={18} className={conf.color} />
        <h3 className={cn('font-bold text-sm', conf.color)}>Assessment Complete — {conf.label}</h3>
      </div>
      <p className={cn('font-semibold text-sm', rec.color)}>{rec.label}</p>
      <p className="text-slate-600 dark:text-slate-400 text-sm">{result.assessment_notes}</p>
      {result.risk_flags.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">Risk Flags</p>
          <ul className="space-y-1">
            {result.risk_flags.map((flag, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                <AlertCircle size={11} className="text-amber-500 mt-0.5 flex-shrink-0" />
                {flag}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// ── Main Component ─────────────────────────────────────────────────────────

export default function AssessmentChat() {
  const { applicationId } = useParams<{ applicationId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const preCreatedSessionId = searchParams.get('session')

  const [messages, setMessages]     = useState<Message[]>([])
  const [input, setInput]           = useState('')
  const [sessionId, setSessionId]   = useState<string | null>(null)
  const [loading, setLoading]       = useState(false)
  const [starting, setStarting]     = useState(true)
  const [result, setResult]         = useState<AssessmentResult | null>(null)
  const [error, setError]           = useState('')

  const wsRef      = useRef<WebSocket | null>(null)
  const bottomRef  = useRef<HTMLDivElement | null>(null)
  const inputRef   = useRef<HTMLInputElement | null>(null)

  // Scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Start session on mount
  useEffect(() => {
    if (!applicationId) return

    async function startSession() {
      setStarting(true)
      try {
        let sid: string
        let opening: string

        if (preCreatedSessionId) {
          // Session was auto-created by event_consumer — just fetch its metadata
          const res = await fetch(`/api/v1/assessment/session/${preCreatedSessionId}`)
          if (!res.ok) throw new Error('Pre-created session not found — it may have expired')
          const data = await res.json()
          sid = data.session_id
          opening = data.opening
        } else {
          // Manual start: create session now
          const appRes = await fetch(`/api/v1/applications/${applicationId}`)
          if (!appRes.ok) throw new Error('Application not found')
          const appData = await appRes.json()

          const res = await fetch(`/api/v1/assessment/${applicationId}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ applicant_data: appData }),
          })
          if (!res.ok) {
            const body = await res.json().catch(() => ({}))
            throw new Error(body.detail || `Assessment service error (HTTP ${res.status})`)
          }
          const data = await res.json()
          sid = data.session_id
          opening = data.opening
        }

        setSessionId(sid)
        setMessages([{ role: 'assistant', text: opening }])

        // Connect WebSocket
        const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const wsUrl = `${wsProto}//${window.location.host}/api/v1/assessment/ws/${sid}`
        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onmessage = (evt) => {
          const msg = JSON.parse(evt.data)
          if (msg.error) {
            setError(msg.error)
            return
          }
          setMessages(prev => [...prev, { role: 'assistant', text: msg.message }])
          setLoading(false)
          if (msg.is_complete) {
            // Fetch finalized result
            fetch(`/api/v1/assessment/${sid}/finalize`, { method: 'POST' })
              .then(r => r.json())
              .then(setResult)
              .catch(() => {})
          }
        }

        ws.onerror = () => setError('WebSocket error — please refresh')

      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to start assessment')
      } finally {
        setStarting(false)
        inputRef.current?.focus()
      }
    }

    startSession()

    return () => {
      wsRef.current?.close()
    }
  }, [applicationId])

  function sendMessage() {
    if (!input.trim() || loading || !wsRef.current || result) return
    const text = input.trim()
    setInput('')
    setLoading(true)
    setMessages(prev => [...prev, { role: 'user', text }])
    wsRef.current.send(JSON.stringify({ message: text }))
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4 animate-slide-up">

      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
        >
          <ArrowLeft size={16} className="text-slate-600 dark:text-slate-400" />
        </button>
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-white">Repayment Assessment</h1>
          <p className="text-slate-500 dark:text-slate-400 text-xs mt-0.5">
            {applicationId ? `Application ${applicationId.slice(0, 8)}…` : ''}
          </p>
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs text-slate-400">Priya · AI Advisor</span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* Chat window */}
      <div className="card p-4 h-[480px] flex flex-col">
        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          {starting && (
            <div className="flex items-center gap-2 text-slate-400 text-sm">
              <Loader2 size={14} className="animate-spin" /> Starting assessment…
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatBubble key={i} msg={msg} />
          ))}
          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-xl bg-brand-100 dark:bg-brand-500/20 flex items-center justify-center flex-shrink-0">
                <Bot size={14} className="text-brand-600 dark:text-brand-400" />
              </div>
              <div className="bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-white/[0.06] rounded-2xl rounded-tl-sm px-4 py-3">
                <div className="flex gap-1">
                  {[0, 1, 2].map(i => (
                    <span key={i} className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="mt-4 flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            disabled={loading || !!result || starting}
            placeholder={result ? 'Assessment complete' : 'Type your reply…'}
            className="input flex-1"
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading || !!result || starting}
            className="p-3 rounded-xl bg-brand-600 hover:bg-brand-700 disabled:opacity-40 disabled:cursor-not-allowed text-white transition-colors"
          >
            <Send size={15} />
          </button>
        </div>
      </div>

      {/* Result card */}
      {result && <ResultCard result={result} />}
    </div>
  )
}
