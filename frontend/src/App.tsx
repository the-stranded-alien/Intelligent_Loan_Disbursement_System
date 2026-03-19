import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'
import {
  Moon, Sun, Zap, Menu, X,
  FileText, LayoutList, Activity, Users, BarChart2,
} from 'lucide-react'
import ApplicationForm from '@/pages/ApplicationForm'
import StatusTracker from '@/pages/StatusTracker'
import RMDashboard from '@/pages/RMDashboard'
import Analytics from '@/pages/Analytics'
import ApplicationsList from '@/pages/ApplicationsList'

const navItems = [
  { to: '/',            label: 'Apply',        icon: FileText },
  { to: '/applications', label: 'Applications', icon: LayoutList },
  { to: '/status',      label: 'Track Status', icon: Activity },
  { to: '/rm',          label: 'RM Dashboard', icon: Users },
  { to: '/analytics',   label: 'Analytics',    icon: BarChart2 },
]

export default function App() {
  const [dark, setDark] = useState(() =>
    localStorage.getItem('theme') === 'dark' ||
    (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)
  )
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  function closeMenu() { setMenuOpen(false) }

  return (
    <BrowserRouter>
      <div className="min-h-screen mesh-bg transition-colors duration-300">

        {/* ── Nav bar ── */}
        <nav className="sticky top-0 z-50 glass border-b border-slate-200/60 dark:border-white/[0.06]">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-2">

            {/* Logo */}
            <div className="flex items-center gap-2.5 mr-5 flex-shrink-0">
              <div className="relative w-8 h-8 flex-shrink-0">
                <div className="absolute inset-0 bg-gradient-to-br from-brand-500 to-violet-600 rounded-xl shadow-glow opacity-80 blur-[6px]" />
                <div className="relative w-8 h-8 bg-gradient-to-br from-brand-500 to-violet-600 rounded-xl flex items-center justify-center shadow-inner-glow">
                  <Zap size={15} className="text-white drop-shadow-sm" fill="currentColor" />
                </div>
              </div>
              <div className="flex flex-col leading-none">
                <span className="font-bold text-slate-900 dark:text-white tracking-tight text-[15px]">LoanFlow</span>
                <span className="text-[9px] font-medium text-brand-500 dark:text-brand-400 tracking-widest uppercase">AI Powered</span>
              </div>
            </div>

            {/* Desktop nav links */}
            <div className="hidden md:flex items-center gap-0.5 flex-1">
              {navItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                      isActive
                        ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-sm shadow-brand-500/30'
                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-white/[0.06] hover:text-slate-900 dark:hover:text-white'
                    }`
                  }
                >
                  <Icon size={13} />
                  {label}
                </NavLink>
              ))}
            </div>

            {/* Spacer on mobile */}
            <div className="flex-1 md:hidden" />

            <div className="flex items-center gap-2">
              {/* Dark mode toggle */}
              <button
                onClick={() => setDark(!dark)}
                className="p-2 rounded-xl bg-slate-100/80 dark:bg-white/[0.06] hover:bg-slate-200/80 dark:hover:bg-white/[0.1] transition-all duration-150 border border-slate-200/60 dark:border-white/[0.06]"
                aria-label="Toggle dark mode"
              >
                {dark
                  ? <Sun size={15} className="text-amber-400" />
                  : <Moon size={15} className="text-slate-500" />}
              </button>

              {/* Mobile hamburger */}
              <button
                onClick={() => setMenuOpen(v => !v)}
                className="md:hidden p-2 rounded-xl bg-slate-100/80 dark:bg-white/[0.06] hover:bg-slate-200/80 dark:hover:bg-white/[0.1] transition-all duration-150 border border-slate-200/60 dark:border-white/[0.06]"
                aria-label="Toggle menu"
              >
                {menuOpen
                  ? <X size={17} className="text-slate-700 dark:text-slate-300" />
                  : <Menu size={17} className="text-slate-700 dark:text-slate-300" />}
              </button>
            </div>
          </div>
        </nav>

        {/* ── Mobile dropdown menu ── */}
        {menuOpen && (
          <>
            <div
              className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm md:hidden"
              onClick={closeMenu}
            />
            <div className="fixed top-14 left-0 right-0 z-50 md:hidden bg-white/95 dark:bg-slate-900/95 backdrop-blur-xl border-b border-slate-200/60 dark:border-white/[0.06] p-2 space-y-1 shadow-xl">
              {navItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  onClick={closeMenu}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-gradient-to-r from-brand-600 to-brand-500 text-white shadow-sm shadow-brand-500/20'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-white/[0.06]'
                    }`
                  }
                >
                  <Icon size={16} />
                  {label}
                </NavLink>
              ))}
            </div>
          </>
        )}

        {/* ── Page content ── */}
        <main className="max-w-7xl mx-auto px-4 py-6 md:py-8 animate-fade-in">
          <Routes>
            <Route path="/"                      element={<ApplicationForm />} />
            <Route path="/status"                element={<StatusTracker />} />
            <Route path="/status/:applicationId" element={<StatusTracker />} />
            <Route path="/rm"                    element={<RMDashboard />} />
            <Route path="/analytics"             element={<Analytics />} />
            <Route path="/applications"          element={<ApplicationsList />} />
          </Routes>
        </main>

        {/* ── Footer ── */}
        <footer className="max-w-7xl mx-auto px-4 py-6 mt-4">
          <div className="border-t border-slate-200/60 dark:border-white/[0.06] pt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-600">
              <div className="w-4 h-4 bg-gradient-to-br from-brand-500 to-violet-600 rounded flex items-center justify-center">
                <Zap size={9} className="text-white" fill="currentColor" />
              </div>
              <span>LoanFlow — Intelligent Loan Disbursement</span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-400 dark:text-slate-600">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                AI Pipeline Active
              </span>
              <span>·</span>
              <span>Powered by Claude</span>
              <span>·</span>
              <span>LangGraph</span>
            </div>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  )
}
