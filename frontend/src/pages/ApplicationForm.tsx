import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate } from 'react-router-dom'
import { useApplicationStore } from '@/store/applicationStore'
import { CheckCircle2, ArrowRight, ArrowLeft, User, Banknote, ClipboardCheck } from 'lucide-react'
import { cn } from '@/lib/utils'

const personalSchema = z.object({
  full_name:  z.string().min(2, 'Name must be at least 2 characters'),
  email:      z.string().email('Invalid email address'),
  phone:      z.string().regex(/^[6-9]\d{9}$/, 'Enter a valid 10-digit Indian mobile number'),
  pan_number: z.string().regex(/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/, 'Enter a valid PAN (e.g. ABCDE1234F)'),
})

const loanSchema = z.object({
  loan_amount:    z.number({ invalid_type_error: 'Enter a valid amount' }).min(10000, 'Minimum ₹10,000').max(10000000, 'Maximum ₹1 Cr'),
  loan_purpose:   z.string().min(3, 'Please describe the loan purpose'),
  tenure_months:  z.number({ invalid_type_error: 'Select tenure' }).min(6).max(84),
})

type PersonalData = z.infer<typeof personalSchema>
type LoanData     = z.infer<typeof loanSchema>

const PURPOSES = ['Home Renovation', 'Education', 'Medical', 'Business', 'Vehicle', 'Wedding', 'Travel', 'Other']
const TENURES  = [6, 12, 18, 24, 36, 48, 60, 84]

const STEPS = [
  { label: 'Personal Info', icon: User },
  { label: 'Loan Details', icon: Banknote },
  { label: 'Review', icon: ClipboardCheck },
]

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {STEPS.map((step, i) => {
        const Icon = step.icon
        const done = i < current
        const active = i === current
        return (
          <div key={i} className="flex items-center gap-2 flex-1 last:flex-none">
            <div className={cn(
              'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors',
              done   ? 'bg-emerald-500 text-white' :
              active ? 'bg-brand-600 text-white' :
                       'bg-slate-100 dark:bg-slate-800 text-slate-400'
            )}>
              {done ? <CheckCircle2 size={14} /> : <Icon size={14} />}
            </div>
            <span className={cn(
              'text-xs font-medium hidden sm:block',
              active ? 'text-brand-600 dark:text-brand-400' :
              done   ? 'text-emerald-600 dark:text-emerald-400' :
                       'text-slate-400'
            )}>
              {step.label}
            </span>
            {i < STEPS.length - 1 && (
              <div className={cn('flex-1 h-px mx-1', done ? 'bg-emerald-300 dark:bg-emerald-700' : 'bg-slate-200 dark:bg-slate-700')} />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function ApplicationForm() {
  const [step, setStep]           = useState(0)
  const [personal, setPersonal]   = useState<PersonalData | null>(null)
  const [loan, setLoan]           = useState<LoanData | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess]     = useState<{ id: string } | null>(null)
  const [error, setError]         = useState('')
  const navigate = useNavigate()
  const addApplication = useApplicationStore(s => s.addApplication)

  const personalForm = useForm<PersonalData>({ resolver: zodResolver(personalSchema) })
  const loanForm     = useForm<LoanData>({
    resolver: zodResolver(loanSchema),
    defaultValues: { tenure_months: 36 },
  })

  async function submit() {
    if (!personal || !loan) return
    setSubmitting(true)
    setError('')
    try {
      const res = await fetch('/api/v1/applications/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...personal, ...loan }),
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
      setSuccess({ id: data.application_id })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Submission failed')
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return (
      <div className="max-w-lg mx-auto animate-slide-up">
        <div className="card p-8 text-center space-y-4">
          <div className="w-16 h-16 bg-emerald-100 dark:bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle2 size={32} className="text-emerald-500" />
          </div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-white">Application Submitted!</h2>
          <p className="text-slate-500 dark:text-slate-400 text-sm">Your application has been received and is being processed.</p>
          <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-4">
            <p className="text-xs text-slate-400 mb-1">Application ID</p>
            <p className="font-mono text-sm font-bold text-slate-800 dark:text-slate-100 break-all">{success.id}</p>
          </div>
          <button onClick={() => navigate(`/status/${success.id}`)} className="btn-primary w-full">
            Track Status <ArrowRight size={14} className="inline ml-1" />
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-xl mx-auto animate-slide-up">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Apply for a Loan</h1>
        <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Complete the form below — it takes under 2 minutes.</p>
      </div>

      <div className="card p-6">
        <StepIndicator current={step} />

        {/* Step 1 — Personal Info */}
        {step === 0 && (
          <form onSubmit={personalForm.handleSubmit(d => { setPersonal(d); setStep(1) })} className="space-y-4 animate-fade-in">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="label">Full Name</label>
                <input {...personalForm.register('full_name')} className="input" placeholder="Ravi Kumar" />
                {personalForm.formState.errors.full_name && <p className="text-red-500 text-xs mt-1">{personalForm.formState.errors.full_name.message}</p>}
              </div>
              <div>
                <label className="label">Email</label>
                <input {...personalForm.register('email')} className="input" placeholder="ravi@example.com" />
                {personalForm.formState.errors.email && <p className="text-red-500 text-xs mt-1">{personalForm.formState.errors.email.message}</p>}
              </div>
              <div>
                <label className="label">Mobile Number</label>
                <input {...personalForm.register('phone')} className="input" placeholder="9876543210" />
                {personalForm.formState.errors.phone && <p className="text-red-500 text-xs mt-1">{personalForm.formState.errors.phone.message}</p>}
              </div>
              <div className="col-span-2">
                <label className="label">PAN Number</label>
                <input {...personalForm.register('pan_number')} className="input uppercase" placeholder="ABCDE1234F" />
                {personalForm.formState.errors.pan_number && <p className="text-red-500 text-xs mt-1">{personalForm.formState.errors.pan_number.message}</p>}
              </div>
            </div>
            <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2">
              Continue <ArrowRight size={14} />
            </button>
          </form>
        )}

        {/* Step 2 — Loan Details */}
        {step === 1 && (
          <form onSubmit={loanForm.handleSubmit(d => { setLoan(d); setStep(2) })} className="space-y-4 animate-fade-in">
            <div>
              <label className="label">Loan Amount (₹)</label>
              <input
                type="number"
                {...loanForm.register('loan_amount', { valueAsNumber: true })}
                className="input"
                placeholder="500000"
              />
              {loanForm.formState.errors.loan_amount && <p className="text-red-500 text-xs mt-1">{loanForm.formState.errors.loan_amount.message}</p>}
            </div>
            <div>
              <label className="label">Loan Purpose</label>
              <select {...loanForm.register('loan_purpose')} className="input">
                <option value="">Select purpose…</option>
                {PURPOSES.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              {loanForm.formState.errors.loan_purpose && <p className="text-red-500 text-xs mt-1">{loanForm.formState.errors.loan_purpose.message}</p>}
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
                      'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
                      loanForm.watch('tenure_months') === t
                        ? 'bg-brand-600 text-white border-brand-600'
                        : 'border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-brand-400'
                    )}
                  >
                    {t}m
                  </button>
                ))}
              </div>
              {loanForm.formState.errors.tenure_months && <p className="text-red-500 text-xs mt-1">Please select a tenure</p>}
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={() => setStep(0)} className="btn-secondary flex items-center gap-1">
                <ArrowLeft size={14} /> Back
              </button>
              <button type="submit" className="btn-primary flex-1 flex items-center justify-center gap-2">
                Review <ArrowRight size={14} />
              </button>
            </div>
          </form>
        )}

        {/* Step 3 — Review */}
        {step === 2 && personal && loan && (
          <div className="space-y-4 animate-fade-in">
            <div className="space-y-3">
              {[
                { label: 'Full Name',     value: personal.full_name },
                { label: 'Email',         value: personal.email },
                { label: 'Mobile',        value: personal.phone },
                { label: 'PAN',           value: personal.pan_number },
                { label: 'Loan Amount',   value: `₹${loan.loan_amount.toLocaleString('en-IN')}` },
                { label: 'Purpose',       value: loan.loan_purpose },
                { label: 'Tenure',        value: `${loan.tenure_months} months` },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center py-2 border-b border-slate-100 dark:border-slate-800 last:border-0">
                  <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
                  <span className="text-sm font-medium text-slate-800 dark:text-slate-100">{value}</span>
                </div>
              ))}
            </div>
            {error && <p className="text-red-500 text-xs bg-red-50 dark:bg-red-500/10 px-3 py-2 rounded-lg">{error}</p>}
            <div className="flex gap-3">
              <button onClick={() => setStep(1)} className="btn-secondary flex items-center gap-1">
                <ArrowLeft size={14} /> Edit
              </button>
              <button onClick={submit} disabled={submitting} className="btn-primary flex-1">
                {submitting ? 'Submitting…' : 'Submit Application'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
