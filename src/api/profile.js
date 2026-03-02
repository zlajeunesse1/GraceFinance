/**
 * GraceFinance - Profile API
 * Matches your existing auth pattern:
 * - Token key: 'grace_token' (matches AuthContext)
 * - Base URL: VITE_API_URL env var
 * - No user_id ever sent to backend
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getAuthHeaders() {
  const token = localStorage.getItem('grace_token') // matches your AuthContext
  if (!token) throw new Error('No session found. Please log in.')
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  }
}

async function handleResponse(res) {
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export const profileApi = {
  /**
   * GET /api/profile
   * Auto-creates profile on first access — never 404 for valid users.
   */
  async get() {
    const res = await fetch(`${API_BASE}/api/profile`, {
      method: 'GET',
      headers: getAuthHeaders(),
    })
    return handleResponse(res)
  },

  /**
   * PATCH /api/profile
   * Partial update — only sends fields you pass in.
   * Never sends user_id.
   */
  async update(payload) {
    // Strip undefined so we only send what changed
    const clean = Object.fromEntries(
      Object.entries(payload).filter(([, v]) => v !== undefined)
    )
    const res = await fetch(`${API_BASE}/api/profile`, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      body: JSON.stringify(clean),
    })
    return handleResponse(res)
  },
}