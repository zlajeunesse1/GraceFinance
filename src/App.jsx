/**
 * App.jsx — Root router with onboarding guard.
 *
 * CHANGES:
 *   - Added /onboarding route (OnboardingPage)
 *   - Added OnboardingGuard: redirects new users to onboarding before dashboard
 *   - Added RequireAuth: redirects unauthenticated users to login
 *   - OnboardingPage now wired to completeOnboarding from AuthContext
 */

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


/**
 * RequireAuth — blocks unauthenticated access to protected routes.
 * Redirects to /login if no user session exists.
 */
function RequireAuth({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: '#000',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#fff',
        fontSize: 14,
        fontFamily: "'Geist', sans-serif",
        letterSpacing: '-0.01em',
      }}>
        Loading...
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children
}


/**
 * OnboardingGuard — after auth, sends new users to onboarding.
 * Once onboarding_completed is true on the user object, passes through.
 *
 * Used on /dashboard (and other protected pages) so new users can't
 * skip the onboarding flow by navigating directly.
 */
function OnboardingGuard({ children }) {
  const { user } = useAuth()

  if (user && !user.onboarding_completed) {
    return <Navigate to="/onboarding" replace />
  }

  return children
}


/**
 * OnboardingWrapper — connects OnboardingPage to AuthContext.
 * Handles the API call and redirects to /dashboard on completion.
 */
function OnboardingWrapper() {
  const { user, completeOnboarding } = useAuth()
  const navigate = useNavigate()

  // If already onboarded, skip to dashboard
  if (user?.onboarding_completed) {
    return <Navigate to="/dashboard" replace />
  }

  async function handleComplete(data) {
    if (data) {
      try {
        await completeOnboarding(data)
      } catch (err) {
        console.error('Onboarding save failed:', err)
        // Don't block navigation — user can still use the app
        // The data will re-sync next time they update from Settings
      }
    }
    navigate('/dashboard', { replace: true })
  }

  return <OnboardingPage onComplete={handleComplete} />
}


export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        {/* Public routes */}
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />

        {/* Onboarding — requires auth, skips if already completed */}
        <Route
          path="/onboarding"
          element={
            <RequireAuth>
              <OnboardingWrapper />
            </RequireAuth>
          }
        />

        {/* Protected routes — require auth + completed onboarding */}
        <Route
          path="/dashboard"
          element={
            <RequireAuth>
              <OnboardingGuard>
                <DashboardPage />
              </OnboardingGuard>
            </RequireAuth>
          }
        />
        <Route
          path="/grace"
          element={
            <RequireAuth>
              <OnboardingGuard>
                <GraceChatPage />
              </OnboardingGuard>
            </RequireAuth>
          }
        />
        <Route
          path="/index"
          element={
            <RequireAuth>
              <OnboardingGuard>
                <IndexPage />
              </OnboardingGuard>
            </RequireAuth>
          }
        />
        <Route
          path="/profile"
          element={
            <RequireAuth>
              <OnboardingGuard>
                <ProfilePage />
              </OnboardingGuard>
            </RequireAuth>
          }
        />
        <Route
          path="/settings"
          element={
            <RequireAuth>
              <OnboardingGuard>
                <SettingsPage />
              </OnboardingGuard>
            </RequireAuth>
          }
        />
      </Routes>
    </ErrorBoundary>
  )
}