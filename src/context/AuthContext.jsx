import { createContext, useContext, useState, useEffect } from 'react'
import { authApi } from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Check for existing session on mount
  useEffect(() => {
    const token = localStorage.getItem('grace_token')
    if (token) {
      authApi.getMe()
        .then((userData) => {
          setUser(userData)
          setLoading(false)
        })
        .catch(() => {
          localStorage.removeItem('grace_token')
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, [])

  async function login(email, password) {
    const response = await authApi.login(email, password)
    if (response.access_token) {
      localStorage.setItem('grace_token', response.access_token)
      setUser(response.user)
    }
    return response
  }

  async function signup(name, email, password, dob) {
    const response = await authApi.signup(name, email, password, dob)
    // NOTE: after signup user is unverified — do NOT store token or set user.
    // SignupPage handles the "check your inbox" state directly.
    return response
  }

  /**
   * completeOnboarding — called at the end of OnboardingPage.
   * Sends financial profile to /auth/onboarding, updates user state,
   * and cleans up localStorage draft data.
   *
   * @param {Object} data - { goals, income, expenses, debt, mission }
   * @returns {Object} updated user object from server
   */
  async function completeOnboarding(data) {
    const payload = {
      monthly_income: data.income ? Number(data.income) : 0,
      monthly_expenses: data.expenses ? Number(data.expenses) : 0,
      financial_goal: data.mission || '',
      onboarding_goals: data.goals || [],
    }

    const updatedUser = await authApi.completeOnboarding(payload)

    // Update user state so onboarding_completed = true flows to guards
    setUser(updatedUser)

    // Clean up localStorage draft
    localStorage.removeItem('grace-onboarding-complete')
    localStorage.removeItem('grace-onboarding-data')

    return updatedUser
  }

  /**
   * updateIncome — lets users update income/expenses from Settings.
   * Calls PATCH /auth/income and syncs user state.
   */
  async function updateIncome(monthly_income, monthly_expenses) {
    const updatedUser = await authApi.updateIncome({ monthly_income, monthly_expenses })
    setUser(updatedUser)
    return updatedUser
  }

  function logout() {
    localStorage.removeItem('grace_token')
    localStorage.removeItem('grace-onboarding-complete')
    localStorage.removeItem('grace-onboarding-data')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{
      user,
      loading,
      login,
      signup,
      logout,
      completeOnboarding,
      updateIncome,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}