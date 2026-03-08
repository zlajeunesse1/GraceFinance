/**
 * LoginPage — v6.3
 * Clean build with pricing link
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import useResponsive from '../hooks/useResponsive'

var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'

export default function LoginPage() {
  var navigate = useNavigate(); var auth = useAuth(); var login = auth.login
  var screen = useResponsive()
  var emailState = useState(''); var email = emailState[0]; var setEmail = emailState[1]
  var passwordState = useState(''); var password = passwordState[0]; var setPassword = passwordState[1]
  var errorsState = useState({}); var errors = errorsState[0]; var setErrors = errorsState[1]
  var loadingState = useState(false); var loading = loadingState[0]; var setLoading = loadingState[1]
  var apiErrorState = useState(''); var apiError = apiErrorState[0]; var setApiError = apiErrorState[1]
  var focusedState = useState(null); var focused = focusedState[0]; var setFocused = focusedState[1]
  var unverifiedState = useState(false); var unverified = unverifiedState[0]; var setUnverified = unverifiedState[1]
  var resendLoadingState = useState(false); var resendLoading = resendLoadingState[0]; var setResendLoading = resendLoadingState[1]
  var resendSentState = useState(false); var resendSent = resendSentState[0]; var setResendSent = resendSentState[1]

  var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

  function validateEmail(em) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em) }

  async function handleSubmit(e) {
    e.preventDefault(); setApiError(''); setUnverified(false)
    var errs = {}
    if (!email.trim()) errs.email = 'Required'
    else if (!validateEmail(email)) errs.email = 'Invalid email'
    if (!password) errs.password = 'Required'
    setErrors(errs); if (Object.keys(errs).length > 0) return
    setLoading(true)
    try { await login(email, password); navigate('/dashboard') }
    catch (err) {
      var msg = err.message || ''
      if (msg.toLowerCase().includes('verify') || msg.toLowerCase().includes('verif')) {
        setUnverified(true)
      } else {
        setApiError(msg || 'Invalid credentials.')
      }
    }
    finally { setLoading(false) }
  }

  async function handleResend() {
    setResendLoading(true)
    try {
      await fetch(API_BASE + '/auth/resend-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email }),
      })
      setResendSent(true)
    } catch (e) { }
    finally { setResendLoading(false) }
  }

  var inputStyle = function (field) {
    return { width: '100%', padding: '14px 0', fontSize: 15, fontFamily: FONT, fontWeight: 400, color: '#ffffff', background: 'transparent', border: 'none', borderBottom: '1px solid ' + (errors[field] ? '#ff4444' : focused === field ? '#ffffff' : '#4b5563'), outline: 'none', transition: 'border-color 0.3s ease', letterSpacing: '0.01em' }
  }
  var labelStyle = function (field) {
    return { display: 'block', fontSize: 11, fontWeight: 500, color: errors[field] ? '#ff4444' : '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4, fontFamily: FONT }
  }

  var formJSX = (
    <>
      {unverified && (
        <div style={{ marginBottom: 20, padding: '14px 16px', border: '1px solid rgba(245,158,11,0.3)', background: 'rgba(245,158,11,0.06)', borderRadius: 8 }}>
          <p style={{ fontSize: 13, color: '#f59e0b', margin: '0 0 8px', fontWeight: 600 }}>Email not verified</p>
          <p style={{ fontSize: 12, color: '#9ca3af', margin: '0 0 12px', lineHeight: 1.6 }}>Check your inbox for a link from support@gracefinance.co. It may be in spam.</p>
          {resendSent
            ? <p style={{ fontSize: 12, color: '#10b981', margin: 0, fontWeight: 600 }}>✓ New link sent — check your inbox</p>
            : <button onClick={handleResend} disabled={resendLoading} style={{ background: 'transparent', border: '1px solid #333333', borderRadius: 6, padding: '7px 14px', color: '#ffffff', fontSize: 12, fontWeight: 500, fontFamily: FONT, cursor: resendLoading ? 'wait' : 'pointer', opacity: resendLoading ? 0.5 : 1 }}>
              {resendLoading ? 'Sending...' : 'Resend verification email'}
            </button>
          }
        </div>
      )}
      {apiError && !unverified && (<div style={{ marginBottom: 20, padding: '12px 16px', border: '1px solid #331111', background: '#1a0a0a', borderRadius: 8, fontSize: 13, color: '#ff4444' }}>{apiError}</div>)}
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 24 }}>
          <label style={labelStyle('email')}>Email {errors.email && ': ' + errors.email}</label>
          <input type="email" value={email} onChange={function (e) { setEmail(e.target.value) }} onFocus={function () { setFocused('email') }} onBlur={function () { setFocused(null) }} placeholder="you@example.com" style={inputStyle('email')} />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle('password')}>Password {errors.password && ': ' + errors.password}</label>
          <input type="password" value={password} onChange={function (e) { setPassword(e.target.value) }} onFocus={function () { setFocused('password') }} onBlur={function () { setFocused(null) }} placeholder="Enter password" style={inputStyle('password')} />
        </div>
        <div style={{ textAlign: 'right', marginBottom: 28 }}>
          <Link to="/forgot-password" style={{ fontSize: 12, color: '#6b7280', textDecoration: 'none' }}>Forgot password?</Link>
        </div>
        <button type="submit" disabled={loading}
          style={{ width: '100%', padding: '14px', fontSize: 14, fontWeight: 600, fontFamily: FONT, color: '#000000', background: '#ffffff', border: 'none', borderRadius: 8, cursor: loading ? 'wait' : 'pointer', letterSpacing: '-0.01em', transition: 'opacity 0.2s ease', opacity: loading ? 0.6 : 1 }}
          onMouseEnter={function (e) { if (!loading) e.target.style.opacity = '0.85' }}
          onMouseLeave={function (e) { if (!loading) e.target.style.opacity = '1' }}
        >{loading ? 'Signing in...' : 'Sign In'}</button>
      </form>
      <p style={{ textAlign: 'center', marginTop: 32, fontSize: 13, color: '#6b7280' }}>
        New here?{' '}<Link to="/signup" style={{ color: '#ffffff', fontWeight: 500, textDecoration: 'none' }}>Create your account</Link>
      </p>
      <p style={{ textAlign: 'center', marginTop: 12, fontSize: 12, color: '#4b5563' }}>
        <Link to="/pricing" style={{ color: '#6b7280', textDecoration: 'none' }}>See our plans →</Link>
      </p>
    </>
  )

  if (screen.isMobile || screen.isTablet) {
    return (
      <div style={{ minHeight: '100vh', background: '#000000', fontFamily: FONT, display: 'flex', flexDirection: 'column' }}>
        <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder { color: #6b7280 !important; }input:-webkit-autofill { -webkit-box-shadow: 0 0 0 30px #000000 inset !important; -webkit-text-fill-color: #ffffff !important; }"}</style>
        <div style={{ padding: '32px 24px 24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 32 }}>
            <div style={{ width: 28, height: 28, border: '1.5px solid #ffffff', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#ffffff' }}>G</div>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.02em' }}>GraceFinance</span>
          </div>
          <h1 style={{ fontSize: 32, fontWeight: 300, color: '#ffffff', lineHeight: 1.15, letterSpacing: '-0.03em', margin: '0 0 12px' }}>Welcome <span style={{ fontWeight: 600 }}>back.</span></h1>
          <p style={{ fontSize: 14, color: '#9ca3af', lineHeight: 1.6, margin: 0 }}>Your Financial Confidence Score is waiting.</p>
        </div>
        <div style={{ flex: 1, padding: '16px 24px 40px' }}>
          {formJSX}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 40, paddingTop: 20, borderTop: '1px solid #1a1a1a' }}>
            {[{ num: '5', label: 'Dimensions' }, { num: '< 2min', label: 'Check-in' }, { num: '24/7', label: 'AI Coach' }].map(function (stat) {
              return (<div key={stat.label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: '#ffffff' }}>{stat.num}</div>
                <div style={{ fontSize: 10, color: '#6b7280', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{stat.label}</div>
              </div>)
            })}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#000000', display: 'flex', fontFamily: FONT }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder { color: #6b7280 !important; }input:-webkit-autofill { -webkit-box-shadow: 0 0 0 30px #000000 inset !important; -webkit-text-fill-color: #ffffff !important; }"}</style>
      <div style={{ width: '45%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '48px', borderRight: '1px solid #141414', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(#111111 1px, transparent 1px), linear-gradient(90deg, #111111 1px, transparent 1px)', backgroundSize: '60px 60px', opacity: 0.4, pointerEvents: 'none' }} />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 80 }}>
            <div style={{ width: 32, height: 32, border: '2px solid #ffffff', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: '#ffffff' }}>G</div>
            <span style={{ fontSize: 15, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.02em' }}>GraceFinance</span>
          </div>
          <h1 style={{ fontSize: 44, fontWeight: 300, color: '#ffffff', lineHeight: 1.15, letterSpacing: '-0.03em', margin: 0 }}>Welcome<br /><span style={{ fontWeight: 600 }}>back.</span></h1>
          <p style={{ fontSize: 16, color: '#9ca3af', lineHeight: 1.7, marginTop: 24, maxWidth: 360, fontWeight: 400 }}>Your Financial Confidence Score is waiting. Pick up where you left off and keep building the picture of your financial life.</p>
        </div>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', gap: 32, marginBottom: 32 }}>
            {[{ num: '5', label: 'Behavioral dimensions' }, { num: '< 2min', label: 'Daily check-in' }, { num: '24/7', label: 'AI coaching' }].map(function (stat) {
              return (<div key={stat.label}><div style={{ fontSize: 20, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.02em' }}>{stat.num}</div><div style={{ fontSize: 11, color: '#6b7280', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{stat.label}</div></div>)
            })}
          </div>
          <div style={{ borderTop: '1px solid #1a1a1a', paddingTop: 20 }}><p style={{ fontSize: 12, color: '#6b7280', margin: 0, letterSpacing: '0.02em' }}>Where Financial Confidence Is Measured</p></div>
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px' }}>
        <div style={{ width: '100%', maxWidth: 380 }}>
          <div style={{ marginBottom: 40 }}>
            <h2 style={{ fontSize: 24, fontWeight: 600, color: '#ffffff', margin: '0 0 8px', letterSpacing: '-0.02em' }}>Sign in</h2>
            <p style={{ fontSize: 14, color: '#6b7280', margin: 0 }}>Continue tracking your financial confidence.</p>
          </div>
          {formJSX}
        </div>
      </div>
    </div>
  )
}