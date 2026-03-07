// ─── Auth API ─────────────────────────────────────────────────────
// All auth-related API calls to the FastAPI backend.
// ──────────────────────────────────────────────────────────────────

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/auth'

// Helper for making authenticated requests
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('grace_token')
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Something went wrong' }))
    throw new Error(error.detail || 'Request failed')
  }

  return response.json()
}

export const authApi = {
  // ─── Login ────────────────────────────────────────────────
  async login(email, password) {
    return apiFetch('/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  // ─── Signup ───────────────────────────────────────────────
  async signup(fullName, email, password) {
    // Split "Zachary Lajeunesse" into first_name + last_name
    const parts = fullName.trim().split(/\s+/)
    const firstName = parts[0] || ''
    const lastName = parts.slice(1).join(' ') || ''

    return apiFetch('/signup', {
      method: 'POST',
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
        email: email,
        password: password,
      }),
    })
  },

  // ─── Get Current User (validates token) ────────────────────
  async getMe() {
    return apiFetch('/me')
  },

  // ─── Complete Onboarding ──────────────────────────────────
  // Saves income, expenses, mission, and goal categories to the DB.
  // Grace AI reads all of this on every conversation after this point.
  // Called by AuthContext.completeOnboarding() at end of OnboardingPage.
  async completeOnboarding(payload) {
    // payload: { monthly_income, monthly_expenses, financial_goal, onboarding_goals }
    return apiFetch('/onboarding', {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  // ─── Update Income (from Settings page) ──────────────────
  // Allows users to update their income/expenses after onboarding.
  // Grace AI picks up the new numbers on the next conversation.
  async updateIncome(payload) {
    // payload: { monthly_income?, monthly_expenses? }
    return apiFetch('/income', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  // ─── Forgot Password ─────────────────────────────────────
  // Always returns 200 — backend never reveals if email exists.
  async forgotPassword(email) {
    return apiFetch('/forgot-password', {   // fixed: was '/forgot' (404)
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  },

  // ─── Reset Password ───────────────────────────────────────
  // Called from the reset-password page with token from email link.
  async resetPassword(token, newPassword) {
    return apiFetch('/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
    })
  },
}