import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import AuthLayout from '../components/AuthLayout'
import Input from '../components/Input'
import Button from '../components/Button'
import { SocialButton, GoogleIcon, AppleIcon, Divider } from '../components/SocialAuth'

export default function LoginPage() {
  var navigate = useNavigate()
  var auth = useAuth()
  var login = auth.login
  var ctx = useTheme()
  var theme = ctx.theme

  var emailState = useState('')
  var email = emailState[0]
  var setEmail = emailState[1]

  var passwordState = useState('')
  var password = passwordState[0]
  var setPassword = passwordState[1]

  var errorsState = useState({})
  var errors = errorsState[0]
  var setErrors = errorsState[1]

  var loadingState = useState(false)
  var loading = loadingState[0]
  var setLoading = loadingState[1]

  var apiErrorState = useState('')
  var apiError = apiErrorState[0]
  var setApiError = apiErrorState[1]

  function validateEmail(em) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setApiError('')
    var errs = {}
    if (!email.trim()) errs.email = 'Email is required'
    else if (!validateEmail(email)) errs.email = 'Enter a valid email'
    if (!password) errs.password = 'Password is required'
    setErrors(errs)
    if (Object.keys(errs).length > 0) return

    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setApiError(err.message || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <div
        className="w-full rounded-[20px] p-9 backdrop-blur-xl"
        style={{
          background: 'linear-gradient(165deg, ' + theme.card + ' 0%, ' + theme.card + 'F2 100%)',
          border: '1px solid ' + theme.border,
          boxShadow: '0 24px 48px rgba(0,0,0,0.4), 0 0 80px ' + theme.accent + '15',
        }}
      >
        <h2 className="text-2xl font-bold mb-1" style={{ color: theme.text }}>Welcome back</h2>
        <p className="text-sm mb-7" style={{ color: theme.muted }}>Sign in to your GraceFinance account</p>

        {apiError && (
          <div className="mb-4 p-3 rounded-lg text-sm" style={{ background: theme.error + '20', color: theme.error }}>
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={function (e) { setEmail(e.target.value) }}
            error={errors.email}
            placeholder="you@example.com"
            icon="✉"
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={function (e) { setPassword(e.target.value) }}
            error={errors.password}
            placeholder="••••••••"
            icon="🔒"
          />

          <div className="flex justify-end -mt-3 mb-5">
            <Link
              to="/forgot-password"
              className="text-[13px] no-underline hover:underline"
              style={{ color: theme.accent }}
            >
              Forgot password?
            </Link>
          </div>

          <Button loading={loading}>Sign In</Button>
        </form>

        <Divider />

        <div className="flex gap-3">
          <SocialButton><GoogleIcon /> Google</SocialButton>
          <SocialButton><AppleIcon /> Apple</SocialButton>
        </div>

        <p className="text-center mt-6 text-sm" style={{ color: theme.muted }}>
          Don't have an account?{' '}
          <Link to="/signup" className="font-semibold no-underline hover:underline" style={{ color: theme.accent }}>
            Sign up free
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
