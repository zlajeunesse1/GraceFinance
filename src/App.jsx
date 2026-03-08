import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import ErrorBoundary from './components/ErrorBoundary'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import DashboardPage from './pages/DashboardPage'
import GraceChatPage from './pages/GraceChatPage'
import IndexPage from './pages/IndexPage'
import ProfilePage from './pages/ProfilePage'
import SettingsPage from './pages/SettingsPage'
import OnboardingPage from './pages/OnboardingPage'
import UpgradePage from './pages/UpgradePage'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', background: '#000', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        color: '#fff', fontSize: 14, fontFamily: "'Geist', sans-serif", letterSpacing: '-0.01em',
      }}>
        Loading...
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return children
}

function OnboardingGuard({ children }) {
  const { user } = useAuth()
  if (user && !user.onboarding_completed) return <Navigate to="/onboarding" replace />
  return children
}

function OnboardingWrapper() {
  const { user, completeOnboarding } = useAuth()
  const navigate = useNavigate()
  if (user?.onboarding_completed) return <Navigate to="/dashboard" replace />
  async function handleComplete(data) {
    if (data) {
      try { await completeOnboarding(data) }
      catch (err) { console.error('Onboarding save failed:', err) }
    }
    navigate('/dashboard', { replace: true })
  }
  return <OnboardingPage onComplete={handleComplete} />
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />

        <Route path="/onboarding" element={<RequireAuth><OnboardingWrapper /></RequireAuth>} />

        <Route path="/dashboard" element={<RequireAuth><OnboardingGuard><DashboardPage /></OnboardingGuard></RequireAuth>} />
        <Route path="/grace" element={<RequireAuth><OnboardingGuard><GraceChatPage /></OnboardingGuard></RequireAuth>} />
        <Route path="/index" element={<RequireAuth><OnboardingGuard><IndexPage /></OnboardingGuard></RequireAuth>} />
        <Route path="/profile" element={<RequireAuth><OnboardingGuard><ProfilePage /></OnboardingGuard></RequireAuth>} />
        <Route path="/settings" element={<RequireAuth><OnboardingGuard><SettingsPage /></OnboardingGuard></RequireAuth>} />
        <Route path="/upgrade" element={<RequireAuth><OnboardingGuard><UpgradePage /></OnboardingGuard></RequireAuth>} />
      </Routes>
    </ErrorBoundary>
  )
}