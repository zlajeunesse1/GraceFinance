import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import AuthLayout from '../components/AuthLayout'
import Input from '../components/Input'
import Button from '../components/Button'
import { SocialButton, GoogleIcon, AppleIcon, Divider } from '../components/SocialAuth'

export default function SignupPage() {
  var navigate = useNavigate()
  var auth = useAuth()
  var signup = auth.signup
  var ctx = useTheme()
  var theme = ctx.theme

  var nameState = useState('')
  var name = nameState[0]
  var setName = nameState[1]

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
    if (!name.trim()) errs.name = 'Name is required'
    if (!email.trim()) errs.email = 'Email is required'
    else if (!validateEmail(email)) errs.email = 'Enter a valid email'
    if (!password) errs.password = 'Password is required'
    else if (password.length < 8) errs.password = 'At least 8 characters'
    setErrors(errs)
    if (Object.keys(errs).length > 0) return

    setLoading(true)
    try {
      await signup(name, email, password)
      navigate('/dashboard')
    } catch (err) {
      setApiError(err.message || 'Signup failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <div className="w-full rounded-[20px] p-9 backdrop-blur-xl"
        style={{
          background: 'linear-gradient(165deg, ' + theme.card + ' 0%, ' + theme.card + 'F2 100%)',
          border: '1px solid ' + theme.border,
          boxShadow: '0 24px 48px rgba(0,0,0,0.4), 0 0 80px ' + theme.accent + '15',
        }}>
        <h2 className="text-2xl font-bold mb-1" style={{ color: theme.text }}>Get started</h2>
        <p className="text-sm mb-7" style={{ color: theme.muted }}>Create your GraceFinance account</p>

        {apiError && (
          <div className="mb-4 p-3 rounded-lg text-sm" style={{ background: theme.error + '20', color: theme.error }}>
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <Input label="Full Name" type="text" value={name}
            onChange={function (e) { setName(e.target.value) }}
            error={errors.name} placeholder="Your name" />
          <Input label="Email" type="email" value={email}
            onChange={function (e) { setEmail(e.target.value) }}
            error={errors.email} placeholder="you@example.com" />
          <Input label="Password" type="password" value={password}
            onChange={function (e) { setPassword(e.target.value) }}
            error={errors.password} placeholder="Min 8 characters" />

          <Button loading={loading}>Create Account</Button>
        </form>

        <Divider />

        <div className="flex gap-3">
          <SocialButton><GoogleIcon /> Google</SocialButton>
          <SocialButton><AppleIcon /> Apple</SocialButton>
        </div>

        <p className="text-center mt-6 text-sm" style={{ color: theme.muted }}>
          Already have an account?{' '}
          <Link to="/login" className="font-semibold no-underline hover:underline" style={{ color: theme.accent }}>
            Sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  )
}
