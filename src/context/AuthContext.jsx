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
      // Validate the token by calling /auth/me
      authApi.getMe()
        .then((userData) => {
          setUser(userData)
          setLoading(false)
        })
        .catch(() => {
          // Token is invalid or expired — clear it
          localStorage.removeItem('grace_token')
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, [])

  async function login(email, password) {
    const response = await authApi.login(email, password)
    // FastAPI returns { access_token: "...", user: { id, email, first_name, ... } }
    if (response.access_token) {
      localStorage.setItem('grace_token', response.access_token)
      setUser(response.user)
    }
    return response
  }

  async function signup(name, email, password) {
    const response = await authApi.signup(name, email, password)
    // FastAPI returns { access_token: "...", user: { id, email, first_name, ... } }
    if (response.access_token) {
      localStorage.setItem('grace_token', response.access_token)
      setUser(response.user)
    }
    return response
  }

  function logout() {
    localStorage.removeItem('grace_token')
    localStorage.removeItem('grace-onboarding-complete')
    localStorage.removeItem('grace-onboarding-data')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
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