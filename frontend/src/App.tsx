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

  // Close mobile menu on route change
  function closeMenu() { setMenuOpen(false) }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 dot-pattern transition-colors duration-300">

        {/* ── Nav bar ── */}
        <nav className="sticky top-0 z-50 glass border-b border-slate-200 dark:border-slate-800">
          <div className="max-w-7xl mx-auto px-4 h-14 flex items-center gap-2">

            {/* Logo */}
            <div className="flex items-center gap-2 mr-4 flex-shrink-0">
              <div className="w-8 h-8 bg-gradient-to-br from-brand-500 to-brand-700 rounded-lg flex items-center justify-center shadow-sm">
                <Zap size={15} className="text-white" />
              </div>
              <span className="font-bold text-slate-900 dark:text-white tracking-tight">LoanFlow</span>
            </div>

            {/* Desktop nav links */}
            <div className="hidden md:flex items-center gap-1 flex-1">
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

            {/* Spacer on mobile */}
            <div className="flex-1 md:hidden" />

            <div className="flex items-center gap-2">
              {/* Dark mode toggle */}
              <button
                onClick={() => setDark(!dark)}
                className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                aria-label="Toggle dark mode"
              >
                {dark
                  ? <Sun size={15} className="text-amber-400" />
                  : <Moon size={15} className="text-slate-500" />}
              </button>

              {/* Mobile hamburger */}
              <button
                onClick={() => setMenuOpen(v => !v)}
                className="md:hidden p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors"
                aria-label="Toggle menu"
              >
                {menuOpen ? <X size={17} className="text-slate-700 dark:text-slate-300" /> : <Menu size={17} className="text-slate-700 dark:text-slate-300" />}
              </button>
            </div>
          </div>
        </nav>

        {/* ── Mobile dropdown menu ── */}
        {menuOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm md:hidden"
              onClick={closeMenu}
            />
            {/* Menu panel */}
            <div className="fixed top-14 left-0 right-0 z-50 md:hidden glass border-b border-slate-200 dark:border-slate-800 p-2 space-y-1 shadow-lg">
              {navItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  onClick={closeMenu}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-brand-600 text-white'
                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
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
      </div>
    </BrowserRouter>
  )
}
