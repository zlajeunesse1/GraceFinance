import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../api/auth'
import AuthLayout from '../components/AuthLayout'
import Input from '../components/Input'
import Button from '../components/Button'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)

  function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const errs = {}
    if (!email.trim()) errs.email = 'Email is required'
    else if (!validateEmail(email)) errs.email = 'Enter a valid email'
    setErrors(errs)
    if (Object.keys(errs).length > 0) return

    setLoading(true)
    try {
      await authApi.forgotPassword(email)
      setSent(true)
    } catch (err) {
      // Still show success to prevent email enumeration
      setSent(true)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <div className="w-full rounded-[20px] p-9 backdrop-blur-xl"
        style={{
          background: 'linear-gradient(165deg, #111827 0%, rgba(17,24,39,0.95) 100%)',
          border: '1px solid #334155',
          boxShadow: '0 24px 48px rgba(0,0,0,0.4), 0 0 80px rgba(34,211,167,0.15)',
        }}
      >
        <h2 className="text-2xl font-bold text-grace-text mb-1">Reset password</h2>
        <p className="text-sm text-grace-muted mb-7">
          {sent ? 'Check your inbox for a reset link' : "Enter your email and we'll send a reset link"}
        </p>

        {!sent ? (
          <form onSubmit={handleSubmit}>
            <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} error={errors.email} placeholder="you@example.com" icon="✉" />
            <Button loading={loading}>Send Reset Link</Button>
          </form>
        ) : (
          <div className="text-center py-5">
            <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl"
              style={{ background: 'rgba(34, 211, 167, 0.15)' }}
            >
              ✓
            </div>
            <p className="text-grace-muted text-sm">
              We sent a reset link to <strong className="text-grace-text">{email}</strong>
            </p>
          </div>
        )}

        <p className="text-center mt-6 text-sm">
          <Link to="/login" className="text-grace-accent font-semibold no-underline hover:underline">
            ← Back to sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
