import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { Moon, Sun, Zap } from 'lucide-react'
import ApplicationForm from '@/pages/ApplicationForm'
import StatusTracker from '@/pages/StatusTracker'
import RMDashboard from '@/pages/RMDashboard'
import Analytics from '@/pages/Analytics'
import ApplicationsList from '@/pages/ApplicationsList'

export default function App() {
  const [dark, setDark] = useState(() =>
    localStorage.getItem('theme') === 'dark' ||
    (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches)
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('theme', dark ? 'dark' : 'light')
  }, [dark])

  const navItems = [
    { to: '/', label: 'Apply' },
    { to: '/applications', label: 'Applications' },
    { to: '/status', label: 'Track Status' },
    { to: '/rm', label: 'RM Dashboard' },
    { to: '/analytics', label: 'Analytics' },
  ]

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 dot-pattern transition-colors duration-300">
        <nav className="sticky top-0 z-50 glass border-b border-slate-200 dark:border-slate-800">
          <div className="max-w-7xl mx-auto px-6 h-14 flex items-center gap-2">
            <div className="flex items-center gap-2 mr-6">
              <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-700 rounded-lg flex items-center justify-center shadow-sm">
                <Zap size={15} className="text-white" />
              </div>
              <span className="font-bold text-slate-900 dark:text-white tracking-tight">LoanFlow</span>
            </div>
            <div className="flex items-center gap-1 flex-1">
              {navItems.map(({ to, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                      isActive
                        ? 'bg-brand-600 text-white shadow-sm'
                        : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'
                    }`
                  }
                >
                  {label}
                </NavLink>
              ))}
            </div>
            <button
              onClick={() => setDark(!dark)}
              className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
            >
              {dark ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} className="text-slate-500" />}
            </button>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8 animate-fade-in">
          <Routes>
            <Route path="/" element={<ApplicationForm />} />
            <Route path="/status" element={<StatusTracker />} />
            <Route path="/status/:applicationId" element={<StatusTracker />} />
            <Route path="/rm" element={<RMDashboard />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/applications" element={<ApplicationsList />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
