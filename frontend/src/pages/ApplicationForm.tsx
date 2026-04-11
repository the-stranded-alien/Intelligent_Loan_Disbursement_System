import { useState, useEffect, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { useApplicationStore } from '@/store/applicationStore'
import {
  CheckCircle2, ArrowRight, ArrowLeft,
  User, Banknote, ClipboardCheck, Building2,
  Zap, Shield, Clock, Copy, Check, XCircle, Loader2,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Schemas ────────────────────────────────────────────────────────────────

const personalSchema = z.object({
  full_name:                z.string().min(2, 'Name must be at least 2 characters'),
  email:                    z.string().email('Invalid email address'),
  phone:                    z.string().regex(/^[6-9]\d{9}$/, 'Enter a valid 10-digit Indian mobile number'),
  pan_number:               z.string().regex(/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/, 'Enter a valid PAN (e.g. ABCDE1234F)'),
  date_of_birth:            z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Enter date as YYYY-MM-DD'),
  city:                     z.string().min(2, 'Enter your city'),
  state:                    z.string().min(2, 'Select your state'),
  residential_status:       z.enum(['owned', 'rented', 'family'], { errorMap: () => ({ message: 'Select residential status' }) }),
  years_at_current_address: z.number({ invalid_type_error: 'Enter years at address' }).min(0).max(99),
})

const financialSchema = z.object({
  employment_type:     z.enum(['salaried', 'self_employed', 'business'], { errorMap: () => ({ message: 'Select employment type' }) }),
  employer_name:       z.string().optional(),
  years_in_current_job: z.number({ invalid_type_error: 'Enter years in job' }).min(0).max(50).optional(),
  monthly_income:      z.number({ invalid_type_error: 'Enter your monthly income' }).min(15000, 'Minimum income ₹15,000'),
  existing_emi_amount: z.number({ invalid_type_error: 'Enter 0 if none' }).min(0),
  bank_account_number: z.string().regex(/^\d{9,18}$/, 'Enter valid account number (9–18 digits)'),
  ifsc_code:           z.string().regex(/^[A-Z]{4}0[A-Z0-9]{6}$/, 'Enter valid IFSC (e.g. HDFC0001234)'),
})

const loanSchema = z.object({
  loan_amount:   z.number({ invalid_type_error: 'Enter a valid amount' }).min(1000, 'Minimum ₹1,000').max(5000000, 'Maximum ₹50L'),
  loan_purpose:  z.string().min(3, 'Please select a purpose'),
  tenure_months: z.number({ invalid_type_error: 'Select tenure' }).min(6).max(84),
})

type PersonalData   = z.infer<typeof personalSchema>
type FinancialData  = z.infer<typeof financialSchema>
type LoanData       = z.infer<typeof loanSchema>

// ── Constants ──────────────────────────────────────────────────────────────

const PURPOSES = ['Home Renovation', 'Education', 'Medical', 'Business', 'Vehicle', 'Wedding', 'Travel', 'Other']
const TENURES  = [6, 12, 18, 24, 36, 48, 60, 84]
const EMPLOYMENT_TYPES = [
  { value: 'salaried',      label: 'Salaried' },
  { value: 'self_employed', label: 'Self-Employed' },
  { value: 'business',      label: 'Business Owner' },
]
const RESIDENTIAL_TYPES = [
  { value: 'owned',  label: 'Owned' },
  { value: 'rented', label: 'Rented' },
  { value: 'family', label: 'Family' },
]
const INDIAN_STATES = [
  'Andhra Pradesh','Arunachal Pradesh','Assam','Bihar','Chhattisgarh','Goa','Gujarat',
  'Haryana','Himachal Pradesh','Jharkhand','Karnataka','Kerala','Madhya Pradesh',
  'Maharashtra','Manipur','Meghalaya','Mizoram','Nagaland','Odisha','Punjab','Rajasthan',
  'Sikkim','Tamil Nadu','Telangana','Tripura','Uttar Pradesh','Uttarakhand','West Bengal',
  'Delhi','Jammu & Kashmir','Ladakh','Chandigarh','Puducherry',
]

const STEPS = [
  { label: 'Personal',   icon: User },
  { label: 'Financial',  icon: Building2 },
  { label: 'Loan',       icon: Banknote },
  { label: 'Review',     icon: ClipboardCheck },
]

const TRUST_BADGES = [
  { icon: Shield,  label: 'Bank-grade Security' },
  { icon: Zap,     label: 'AI-Powered Decisions' },
  { icon: Clock,   label: 'Approval in Minutes' },
]

// ── Step indicator ─────────────────────────────────────────────────────────

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-1 mb-8">
      {STEPS.map((step, i) => {
        const Icon = step.icon
        const done   = i < current
        const active = i === current
        return (
          <div key={i} className="flex items-center gap-1 flex-1 last:flex-none">
            <div className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all duration-300 flex-shrink-0',
              done   ? 'bg-gradient-to-br from-emerald-400 to-emerald-600 text-white shadow-sm' :
              active ? 'bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-sm shadow-brand-500/30' :
                       'bg-slate-100 dark:bg-slate-800 text-slate-400',
            )}>
              {done ? <CheckCircle2 size={14} /> : <Icon size={14} />}
            </div>
            <span className={cn(
              'text-[11px] font-medium hidden sm:block transition-colors duration-200 whitespace-nowrap',
              active ? 'text-brand-600 dark:text-brand-400' :
              done   ? 'text-emerald-600 dark:text-emerald-400' :
                       'text-slate-400',
            )}>
              {step.label}
            </span>
            {i < STEPS.length - 1 && (
              <div className={cn(
                'flex-1 h-px mx-1 transition-all duration-300',
                done ? 'bg-gradient-to-r from-emerald-300 to-brand-200 dark:from-emerald-700 dark:to-brand-800' : 'bg-slate-200 dark:bg-slate-700',
              )} />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Field error helper ─────────────────────────────────────────────────────

function Err({ msg }: { msg?: string }) {
  if (!msg) return null
  return <p className="text-red-500 dark:text-red-400 text-xs mt-1">{msg}</p>
}

// ── Review row ─────────────────────────────────────────────────────────────

function ReviewRow({ label, value, last = false }: { label: string; value: string; last?: boolean }) {
  return (
    <div className={cn('flex justify-between items-center px-4 py-2.5', !last && 'border-b border-slate-200/60 dark:border-slate-700/30')}>
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">{value}</span>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

// ── Eligibility result screen ──────────────────────────────────────────────

interface EligibilityState {
  applicationId: string
  result: 'checking' | 'eligible' | 'ineligible'
  reason?: string
}

export default function ApplicationForm() {
  const [step, setStep]             = useState(0)
  const [personal, setPersonal]     = useState<PersonalData | null>(null)
  const [financial, setFinancial]   = useState<FinancialData | null>(null)
  const [loan, setLoan]             = useState<LoanData | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [eligibility, setEligibility] = useState<EligibilityState | null>(null)
  const [error, setError]           = useState('')
  const [copied, setCopied]         = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const navigate = useNavigate()
  const addApplication = useApplicationStore(s => s.addApplication)

  // Poll /events after submit to detect lead_capture completion
  useEffect(() => {
    if (!eligibility || eligibility.result !== 'checking') return

    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/applications/${eligibility.applicationId}/events`)
        if (!res.ok) return
        const events: Array<{ event: string; payload: Record<string, unknown> | null }> = await res.json()
        const leadEvent = events.find(e => e.event === 'stage.lead_capture.completed')
        if (!leadEvent?.payload) return

        const result = leadEvent.payload.result as Record<string, unknown> | undefined
        const eligResult = result?.eligibility_result as string | undefined
        if (!eligResult) return

        clearInterval(pollRef.current!)
        setEligibility(prev => prev ? {
          ...prev,
          result: eligResult === 'eligible' ? 'eligible' : 'ineligible',
          reason: result?.eligibility_reason as string | undefined,
        } : prev)
      } catch { /* ignore */ }
    }, 2000)

    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [eligibility?.applicationId, eligibility?.result])

  const personalForm  = useForm<PersonalData>({ resolver: zodResolver(personalSchema) })
  const financialForm = useForm<FinancialData>({
    resolver: zodResolver(financialSchema),
    defaultValues: { employment_type: 'salaried', existing_emi_amount: 0 },
  })
  const loanForm = useForm<LoanData>({
    resolver: zodResolver(loanSchema),
    defaultValues: { tenure_months: 36 },
  })

  async function submit() {
    if (!personal || !financial || !loan) return
    setSubmitting(true)
    setError('')
    try {
      const body = { ...personal, ...financial, ...loan }
      const res = await fetch('/api/v1/applications/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      addApplication({
        applicationId: data.application_id,
        status: data.status,
        currentStage: data.stage,
        applicantName: personal.full_name,
        loanAmount: loan.loan_amount,
      })
      // Show eligibility checking screen instead of going straight to status
      setEligibility({ applicationId: data.application_id, result: 'checking' })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  function copyId() {
    if (!eligibility) return
    navigator.clipboard.writeText(eligibility.applicationId).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  // ── Eligibility screen (checking → eligible | ineligible) ───────────────

  if (eligibility) {
    const checking   = eligibility.result === 'checking'
    const eligible   = eligibility.result === 'eligible'
    const ineligible = eligibility.result === 'ineligible'

    return (
      <div className="max-w-lg mx-auto animate-slide-up">
        <div className="card p-8 text-center space-y-5 relative overflow-hidden">
          <div className={cn(
            'absolute top-0 left-0 right-0 h-1 bg-gradient-to-r',
            checking   ? 'from-brand-500 via-violet-500 to-brand-500 animate-pulse' :
            eligible   ? 'from-brand-500 via-violet-500 to-emerald-400' :
                         'from-red-500 to-red-400',
          )} />

          <div className="relative">
            <div className="w-20 h-20 mx-auto relative">
              {checking && (
                <>
                  <div className="absolute inset-0 bg-brand-400/20 rounded-full blur-xl animate-glow-pulse" />
                  <div className="relative w-20 h-20 bg-gradient-to-br from-brand-400 to-brand-600 rounded-full flex items-center justify-center shadow-lg">
                    <Loader2 size={36} className="text-white animate-spin" />
                  </div>
                </>
              )}
              {eligible && (
                <>
                  <div className="absolute inset-0 bg-emerald-400/20 rounded-full blur-xl animate-glow-pulse" />
                  <div className="relative w-20 h-20 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-full flex items-center justify-center shadow-lg">
                    <CheckCircle2 size={36} className="text-white" />
                  </div>
                </>
              )}
              {ineligible && (
                <div className="relative w-20 h-20 bg-gradient-to-br from-red-400 to-red-600 rounded-full flex items-center justify-center shadow-lg mx-auto">
                  <XCircle size={36} className="text-white" />
                </div>
              )}
            </div>
          </div>

          <div>
            {checking && (
              <>
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">Checking Eligibility…</h2>
                <p className="text-slate-500 dark:text-slate-400 text-sm">
                  Our AI is reviewing your application. This takes just a few seconds.
                </p>
              </>
            )}
            {eligible && (
              <>
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">You're Eligible!</h2>
                <p className="text-slate-500 dark:text-slate-400 text-sm">
                  Your application passed initial screening. KYC verification is next — no action needed from you.
                </p>
              </>
            )}
            {ineligible && (
              <>
                <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">Not Eligible at This Time</h2>
                {eligibility.reason && (
                  <p className="text-slate-500 dark:text-slate-400 text-sm">{eligibility.reason}</p>
                )}
              </>
            )}
          </div>

          <div className="bg-slate-50 dark:bg-slate-800/60 rounded-xl p-4 border border-slate-200/60 dark:border-slate-700/50">
            <p className="text-xs text-slate-400 mb-1.5 font-medium">Application ID</p>
            <p className="font-mono text-sm font-bold text-slate-800 dark:text-slate-100 break-all mb-2">{eligibility.applicationId}</p>
            <button onClick={copyId} className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-brand-500 transition-colors mx-auto">
              {copied ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
              {copied ? 'Copied!' : 'Copy ID'}
            </button>
          </div>

          {!checking && (
            <button
              onClick={() => navigate(`/status/${eligibility.applicationId}`)}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {eligible ? 'Track Your Application' : 'View Details'} <ArrowRight size={14} />
            </button>
          )}
        </div>
      </div>
    )
  }

  // ── Form ────────────────────────────────────────────────────────────────

  return (
    <div className="max-w-xl mx-auto animate-slide-up space-y-5">

      {/* Hero */}
      <div className="text-center space-y-2 pt-2">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
          Apply for a <span className="gradient-text">Loan</span>
        </h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm">Complete the form — it takes under 3 minutes.</p>
        <div className="flex items-center justify-center gap-4 pt-2">
          {TRUST_BADGES.map(({ icon: Icon, label }) => (
            <div key={label} className="flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500">
              <Icon size={12} className="text-brand-500" />
              <span className="hidden sm:block">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Card */}
      <div className="card p-6 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-brand-500/50 via-violet-500/50 to-brand-500/50" />

        <StepIndicator current={step} />

        {/* ── Step 1: Personal Info ── */}
        {step === 0 && (
          <form onSubmit={personalForm.handleSubmit(d => { setPersonal(d); setStep(1) })} className="space-y-4 animate-fade-in">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="label">Full Name</label>
                <input {...personalForm.register('full_name')} className="input" placeholder="Ravi Kumar" />
                <Err msg={personalForm.formState.errors.full_name?.message} />
              </div>
              <div>
                <label className="label">Email</label>
                <input {...personalForm.register('email')} className="input" placeholder="ravi@example.com" />
                <Err msg={personalForm.formState.errors.email?.message} />
              </div>
              <div>
                <label className="label">Mobile Number</label>
                <input {...personalForm.register('phone')} className="input" placeholder="9876543210" />
                <Err msg={personalForm.formState.errors.phone?.message} />
              </div>
              <div>
                <label className="label">PAN Number</label>
                <input
                  {...personalForm.register('pan_number')}
                  className="input uppercase"
                  placeholder="ABCDE1234F"
                  onChange={e => personalForm.setValue('pan_number', e.target.value.toUpperCase())}
                />
                <Err msg={personalForm.formState.errors.pan_number?.message} />
              </div>
              <div>
                <label className="label">Date of Birth</label>
                <input {...personalForm.register('date_of_birth')} type="date" className="input" />
                <Err msg={personalForm.formState.errors.date_of_birth?.message} />
              </div>
              <div>
                <label className="label">City</label>
                <input {...personalForm.register('city')} className="input" placeholder="Mumbai" />
                <Err msg={personalForm.formState.errors.city?.message} />
              </div>
              <div>
                <label className="label">State</label>
                <select {...personalForm.register('state')} className="input">
                  <option value="">Select state…</option>
                  {INDIAN_STATES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <Err msg={personalForm.formState.errors.state?.message} />
              </div>
              <div className="col-span-2">
                <label className="label">Residential Status</label>
                <div className="grid grid-cols-3 gap-2">
                  {RESIDENTIAL_TYPES.map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => personalForm.setValue('residential_status', value as PersonalData['residential_status'])}
                      className={cn(
                        'px-3 py-2 rounded-xl text-xs font-semibold border transition-all duration-150',
                        personalForm.watch('residential_status') === value
                          ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white border-transparent shadow-sm'
                          : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-brand-400',
                      )}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <Err msg={personalForm.formState.errors.residential_status?.message} />
              </div>
              <div className="col-span-2">
                <label className="label">Years at Current Address</label>
                <input
                  type="number"
                  {...personalForm.register('years_at_current_address', { valueAsNumber: true })}
                  className="input"
                  placeholder="3"
                  min={0}
                />
                <Err msg={personalForm.formState.errors.years_at_current_address?.message} />
              </div>
            </div>
            <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2">
              Continue <ArrowRight size={14} />
            </button>
          </form>
        )}

        {/* ── Step 2: Financial Profile ── */}
        {step === 1 && (
          <form onSubmit={financialForm.handleSubmit(d => { setFinancial(d); setStep(2) })} className="space-y-4 animate-fade-in">
            <div>
              <label className="label">Employment Type</label>
              <div className="grid grid-cols-3 gap-2">
                {EMPLOYMENT_TYPES.map(({ value, label }) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => financialForm.setValue('employment_type', value as FinancialData['employment_type'])}
                    className={cn(
                      'px-3 py-2 rounded-xl text-xs font-semibold border transition-all duration-150',
                      financialForm.watch('employment_type') === value
                        ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white border-transparent shadow-sm'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-brand-400',
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <Err msg={financialForm.formState.errors.employment_type?.message} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              {/* Conditional employer fields for salaried/business */}
              {financialForm.watch('employment_type') !== 'self_employed' && (
                <>
                  <div className="col-span-2">
                    <label className="label">Employer / Company Name</label>
                    <input {...financialForm.register('employer_name')} className="input" placeholder="Acme Corp" />
                    <Err msg={financialForm.formState.errors.employer_name?.message} />
                  </div>
                  <div className="col-span-2">
                    <label className="label">Years in Current Job</label>
                    <input
                      type="number"
                      {...financialForm.register('years_in_current_job', { valueAsNumber: true })}
                      className="input"
                      placeholder="2"
                      min={0}
                    />
                    <Err msg={financialForm.formState.errors.years_in_current_job?.message} />
                  </div>
                </>
              )}
              <div>
                <label className="label">Monthly Income (₹)</label>
                <input
                  type="number"
                  {...financialForm.register('monthly_income', { valueAsNumber: true })}
                  className="input"
                  placeholder="50000"
                />
                <Err msg={financialForm.formState.errors.monthly_income?.message} />
              </div>
              <div>
                <label className="label">Existing EMI / Month (₹)</label>
                <input
                  type="number"
                  {...financialForm.register('existing_emi_amount', { valueAsNumber: true })}
                  className="input"
                  placeholder="0"
                />
                <Err msg={financialForm.formState.errors.existing_emi_amount?.message} />
              </div>
              <div>
                <label className="label">Bank Account Number</label>
                <input {...financialForm.register('bank_account_number')} className="input" placeholder="1234567890" />
                <Err msg={financialForm.formState.errors.bank_account_number?.message} />
              </div>
              <div>
                <label className="label">IFSC Code</label>
                <input
                  {...financialForm.register('ifsc_code')}
                  className="input uppercase"
                  placeholder="HDFC0001234"
                  onChange={e => financialForm.setValue('ifsc_code', e.target.value.toUpperCase())}
                />
                <Err msg={financialForm.formState.errors.ifsc_code?.message} />
              </div>
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={() => setStep(0)} className="btn-secondary flex items-center gap-1">
                <ArrowLeft size={14} /> Back
              </button>
              <button type="submit" className="btn-primary flex-1 flex items-center justify-center gap-2">
                Continue <ArrowRight size={14} />
              </button>
            </div>
          </form>
        )}

        {/* ── Step 3: Loan Details ── */}
        {step === 2 && (
          <form onSubmit={loanForm.handleSubmit(d => { setLoan(d); setStep(3) })} className="space-y-4 animate-fade-in">
            <div>
              <label className="label">Loan Amount (₹)</label>
              <input
                type="number"
                {...loanForm.register('loan_amount', { valueAsNumber: true })}
                className="input"
                placeholder="500000"
              />
              <Err msg={loanForm.formState.errors.loan_amount?.message} />
            </div>
            <div>
              <label className="label">Loan Purpose</label>
              <select {...loanForm.register('loan_purpose')} className="input">
                <option value="">Select purpose…</option>
                {PURPOSES.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              <Err msg={loanForm.formState.errors.loan_purpose?.message} />
            </div>
            <div>
              <label className="label">Tenure</label>
              <div className="flex gap-2 flex-wrap">
                {TENURES.map(t => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => loanForm.setValue('tenure_months', t)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all duration-150',
                      loanForm.watch('tenure_months') === t
                        ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white border-transparent shadow-sm shadow-brand-500/20'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-brand-400 hover:text-brand-600 dark:hover:text-brand-400',
                    )}
                  >
                    {t}m
                  </button>
                ))}
              </div>
              <Err msg={loanForm.formState.errors.tenure_months ? 'Please select a tenure' : undefined} />
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={() => setStep(1)} className="btn-secondary flex items-center gap-1">
                <ArrowLeft size={14} /> Back
              </button>
              <button type="submit" className="btn-primary flex-1 flex items-center justify-center gap-2">
                Review <ArrowRight size={14} />
              </button>
            </div>
          </form>
        )}

        {/* ── Step 4: Review ── */}
        {step === 3 && personal && financial && loan && (
          <div className="space-y-4 animate-fade-in">
            {/* Personal */}
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Personal</p>
              <div className="bg-slate-50 dark:bg-slate-800/60 rounded-xl overflow-hidden border border-slate-200/60 dark:border-slate-700/50">
                <ReviewRow label="Full Name"        value={personal.full_name} />
                <ReviewRow label="Email"            value={personal.email} />
                <ReviewRow label="Mobile"           value={personal.phone} />
                <ReviewRow label="PAN"              value={personal.pan_number} />
                <ReviewRow label="Date of Birth"    value={personal.date_of_birth} />
                <ReviewRow label="City / State"     value={`${personal.city}, ${personal.state}`} />
                <ReviewRow label="Residence"        value={personal.residential_status} />
                <ReviewRow label="Years at Address" value={`${personal.years_at_current_address} yr${personal.years_at_current_address !== 1 ? 's' : ''}`} last />
              </div>
            </div>
            {/* Financial */}
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Financial</p>
              <div className="bg-slate-50 dark:bg-slate-800/60 rounded-xl overflow-hidden border border-slate-200/60 dark:border-slate-700/50">
                <ReviewRow label="Employment"     value={EMPLOYMENT_TYPES.find(e => e.value === financial.employment_type)?.label ?? financial.employment_type} />
                {financial.employer_name && <ReviewRow label="Employer"        value={financial.employer_name} />}
                {financial.years_in_current_job != null && <ReviewRow label="Years in Job"   value={`${financial.years_in_current_job} yr${financial.years_in_current_job !== 1 ? 's' : ''}`} />}
                <ReviewRow label="Monthly Income" value={`₹${financial.monthly_income.toLocaleString('en-IN')}`} />
                <ReviewRow label="Existing EMI"   value={`₹${financial.existing_emi_amount.toLocaleString('en-IN')}`} />
                <ReviewRow label="Bank Account"   value={financial.bank_account_number} />
                <ReviewRow label="IFSC"           value={financial.ifsc_code} last />
              </div>
            </div>
            {/* Loan */}
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Loan Request</p>
              <div className="bg-slate-50 dark:bg-slate-800/60 rounded-xl overflow-hidden border border-slate-200/60 dark:border-slate-700/50">
                <ReviewRow label="Loan Amount" value={`₹${loan.loan_amount.toLocaleString('en-IN')}`} />
                <ReviewRow label="Purpose"     value={loan.loan_purpose} />
                <ReviewRow label="Tenure"      value={`${loan.tenure_months} months`} last />
              </div>
            </div>

            {error && (
              <div className="bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/30 rounded-xl px-4 py-3">
                <p className="text-red-600 dark:text-red-400 text-xs">{error}</p>
              </div>
            )}
            <div className="flex gap-3">
              <button onClick={() => setStep(2)} className="btn-secondary flex items-center gap-1">
                <ArrowLeft size={14} /> Edit
              </button>
              <button onClick={submit} disabled={submitting} className="btn-primary flex-1 flex items-center justify-center gap-2">
                {submitting ? (
                  <>
                    <span className="w-3.5 h-3.5 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                    Submitting…
                  </>
                ) : (
                  <>Submit Application <Zap size={13} fill="currentColor" /></>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
