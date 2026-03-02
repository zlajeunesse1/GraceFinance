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

  // ─── Forgot Password ─────────────────────────────────────
  async forgotPassword(email) {
    return apiFetch('/forgot', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  },

  // ─── Get Current User (validates token) ────────────────────
  async getMe() {
    return apiFetch('/me')
  },
}