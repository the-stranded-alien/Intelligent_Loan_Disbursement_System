import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import ApplicationForm from '@/pages/ApplicationForm'
import StatusTracker from '@/pages/StatusTracker'
import RMDashboard from '@/pages/RMDashboard'
import Analytics from '@/pages/Analytics'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white border-b border-gray-200 px-6 py-3 flex gap-6">
          <span className="font-semibold text-gray-900 mr-4">Loan Disbursement</span>
          <NavLink to="/" className="text-sm text-gray-600 hover:text-gray-900">Apply</NavLink>
          <NavLink to="/status" className="text-sm text-gray-600 hover:text-gray-900">Status</NavLink>
          <NavLink to="/rm" className="text-sm text-gray-600 hover:text-gray-900">RM Dashboard</NavLink>
          <NavLink to="/analytics" className="text-sm text-gray-600 hover:text-gray-900">Analytics</NavLink>
        </nav>
        <main className="p-6">
          <Routes>
            <Route path="/" element={<ApplicationForm />} />
            <Route path="/status" element={<StatusTracker />} />
            <Route path="/status/:applicationId" element={<StatusTracker />} />
            <Route path="/rm" element={<RMDashboard />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
