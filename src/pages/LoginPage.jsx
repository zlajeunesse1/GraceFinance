/**
 * LoginPage — Institutional Redesign
 * 
 * Design: Monochrome, sharp, confident.
 * Matches SignupPage aesthetic.
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  var navigate = useNavigate()
  var auth = useAuth()
  var login = auth.login

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

  var focusedState = useState(null)
  var focused = focusedState[0]
  var setFocused = focusedState[1]

  function validateEmail(em) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setApiError('')
    var errs = {}
    if (!email.trim()) errs.email = 'Required'
    else if (!validateEmail(email)) errs.email = 'Invalid email'
    if (!password) errs.password = 'Required'
    setErrors(errs)
    if (Object.keys(errs).length > 0) return

    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setApiError(err.message || 'Invalid credentials.')
    } finally {
      setLoading(false)
    }
  }

  var inputStyle = function (field) {
    return {
      width: '100%',
      padding: '14px 0',
      fontSize: 15,
      fontFamily: "'Geist', 'SF Pro Display', -apple-system, sans-serif",
      fontWeight: 400,
      color: '#ffffff',
      background: 'transparent',
      border: 'none',
      borderBottom: '1px solid ' + (errors[field] ? '#ff4444' : focused === field ? '#ffffff' : '#333333'),
      outline: 'none',
      transition: 'border-color 0.3s ease',
      letterSpacing: '0.01em',
    }
  }

  var labelStyle = function (field) {
    return {
      display: 'block',
      fontSize: 11,
      fontWeight: 500,
      color: errors[field] ? '#ff4444' : '#666666',
      textTransform: 'uppercase',
      letterSpacing: '0.08em',
      marginBottom: 4,
      fontFamily: "'Geist', 'SF Pro Display', -apple-system, sans-serif",
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#000000',
      display: 'flex',
      fontFamily: "'Geist', 'SF Pro Display', -apple-system, sans-serif",
    }}>
      <style>{
        "@import url('https://fonts.cdnfonts.com/css/geist');" +
        "::placeholder { color: #444444 !important; }" +
        "input:-webkit-autofill { -webkit-box-shadow: 0 0 0 30px #000000 inset !important; -webkit-text-fill-color: #ffffff !important; }"
      }</style>

      {/* Left — Branding Panel */}
      <div style={{
        width: '45%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '48px',
        borderRight: '1px solid #141414',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: 'linear-gradient(#111111 1px, transparent 1px), linear-gradient(90deg, #111111 1px, transparent 1px)',
          backgroundSize: '60px 60px',
          opacity: 0.4,
          pointerEvents: 'none',
        }} />

        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 80 }}>
            <div style={{
              width: 32,
              height: 32,
              border: '2px solid #ffffff',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 14,
              fontWeight: 700,
              color: '#ffffff',
            }}>
              G
            </div>
            <span style={{
              fontSize: 15,
              fontWeight: 600,
              color: '#ffffff',
              letterSpacing: '-0.02em',
            }}>
              GraceFinance
            </span>
          </div>

          <h1 style={{
            fontSize: 44,
            fontWeight: 300,
            color: '#ffffff',
            lineHeight: 1.15,
            letterSpacing: '-0.03em',
            margin: 0,
          }}>
            Welcome
            <br />
            <span style={{ fontWeight: 600 }}>back.</span>
          </h1>

          <p style={{
            fontSize: 16,
            color: '#666666',
            lineHeight: 1.7,
            marginTop: 24,
            maxWidth: 360,
            fontWeight: 400,
          }}>
            Your daily check-in is ready. Pick up where you left off and 
            keep building your financial awareness.
          </p>
        </div>

        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{
            borderTop: '1px solid #1a1a1a',
            paddingTop: 20,
          }}>
            <p style={{
              fontSize: 12,
              color: '#444444',
              margin: 0,
              letterSpacing: '0.02em',
            }}>
              The Behavioral Finance Company
            </p>
          </div>
        </div>
      </div>

      {/* Right — Form */}
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '48px',
      }}>
        <div style={{ width: '100%', maxWidth: 380 }}>
          <div style={{ marginBottom: 40 }}>
            <h2 style={{
              fontSize: 24,
              fontWeight: 600,
              color: '#ffffff',
              margin: '0 0 8px',
              letterSpacing: '-0.02em',
            }}>
              Sign in
            </h2>
            <p style={{
              fontSize: 14,
              color: '#555555',
              margin: 0,
            }}>
              Continue your financial journey.
            </p>
          </div>

          {apiError && (
            <div style={{
              marginBottom: 24,
              padding: '12px 16px',
              border: '1px solid #331111',
              background: '#1a0a0a',
              borderRadius: 8,
              fontSize: 13,
              color: '#ff4444',
            }}>
              {apiError}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 28 }}>
              <label style={labelStyle('email')}>Email {errors.email && '— ' + errors.email}</label>
              <input
                type="email"
                value={email}
                onChange={function (e) { setEmail(e.target.value) }}
                onFocus={function () { setFocused('email') }}
                onBlur={function () { setFocused(null) }}
                placeholder="you@example.com"
                style={inputStyle('email')}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label style={labelStyle('password')}>Password {errors.password && '— ' + errors.password}</label>
              <input
                type="password"
                value={password}
                onChange={function (e) { setPassword(e.target.value) }}
                onFocus={function () { setFocused('password') }}
                onBlur={function () { setFocused(null) }}
                placeholder="Enter password"
                style={inputStyle('password')}
              />
            </div>

            <div style={{ textAlign: 'right', marginBottom: 32 }}>
              <Link to="/forgot-password" style={{
                fontSize: 12,
                color: '#555555',
                textDecoration: 'none',
                transition: 'color 0.2s',
              }}>
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '14px',
                fontSize: 14,
                fontWeight: 600,
                fontFamily: "'Geist', 'SF Pro Display', -apple-system, sans-serif",
                color: '#000000',
                background: '#ffffff',
                border: 'none',
                borderRadius: 8,
                cursor: loading ? 'wait' : 'pointer',
                letterSpacing: '-0.01em',
                transition: 'opacity 0.2s ease',
                opacity: loading ? 0.6 : 1,
              }}
              onMouseEnter={function (e) { if (!loading) e.target.style.opacity = '0.85' }}
              onMouseLeave={function (e) { if (!loading) e.target.style.opacity = '1' }}
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            margin: '28px 0',
          }}>
            <div style={{ flex: 1, height: 1, background: '#1a1a1a' }} />
            <span style={{ fontSize: 11, color: '#444444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>or</span>
            <div style={{ flex: 1, height: 1, background: '#1a1a1a' }} />
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            {['Google', 'Apple'].map(function (provider) {
              return (
                <button
                  key={provider}
                  style={{
                    flex: 1,
                    padding: '12px',
                    fontSize: 13,
                    fontWeight: 500,
                    fontFamily: "'Geist', 'SF Pro Display', -apple-system, sans-serif",
                    color: '#888888',
                    background: 'transparent',
                    border: '1px solid #222222',
                    borderRadius: 8,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    letterSpacing: '0.01em',
                  }}
                  onMouseEnter={function (e) {
                    e.target.style.borderColor = '#444444'
                    e.target.style.color = '#ffffff'
                  }}
                  onMouseLeave={function (e) {
                    e.target.style.borderColor = '#222222'
                    e.target.style.color = '#888888'
                  }}
                >
                  {provider}
                </button>
              )
            })}
          </div>

          <p style={{
            textAlign: 'center',
            marginTop: 32,
            fontSize: 13,
            color: '#555555',
          }}>
            Don't have an account?{' '}
            <Link to="/signup" style={{
              color: '#ffffff',
              fontWeight: 500,
              textDecoration: 'none',
            }}>
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}