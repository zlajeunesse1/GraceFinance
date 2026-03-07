/**
 * ForgotPasswordPage — Institutional Redesign
 * Minimal centered layout. Clean and fast.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function ForgotPasswordPage() {
  var emailState = useState(''); var email = emailState[0]; var setEmail = emailState[1]
  var errorsState = useState({}); var errors = errorsState[0]; var setErrors = errorsState[1]
  var loadingState = useState(false); var loading = loadingState[0]; var setLoading = loadingState[1]
  var sentState = useState(false); var sent = sentState[0]; var setSent = sentState[1]
  var focusedState = useState(false); var focused = focusedState[0]; var setFocused = focusedState[1]

  function validateEmail(em) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em) }

  async function handleSubmit(e) {
    e.preventDefault()
    var errs = {}
    if (!email.trim()) errs.email = 'Required'
    else if (!validateEmail(email)) errs.email = 'Invalid email'
    setErrors(errs); if (Object.keys(errs).length > 0) return
    setLoading(true)
    try { setSent(true) } catch (err) { setSent(true) } finally { setLoading(false) }
  }

  var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

  return (
    <div style={{ minHeight: '100vh', background: '#000000', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT, padding: '48px 24px' }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder { color: #6b7280 !important; }input:-webkit-autofill { -webkit-box-shadow: 0 0 0 30px #000000 inset !important; -webkit-text-fill-color: #ffffff !important; }"}</style>

      <div style={{ width: '100%', maxWidth: 380 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 48 }}>
          <div style={{ width: 32, height: 32, border: '2px solid #ffffff', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: '#ffffff' }}>G</div>
          <span style={{ fontSize: 15, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.02em' }}>GraceFinance</span>
        </div>

        {!sent ? (
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 600, color: '#ffffff', margin: '0 0 8px', letterSpacing: '-0.02em' }}>Reset password</h2>
            <p style={{ fontSize: 14, color: '#6b7280', margin: '0 0 36px' }}>Enter your email and we'll send a reset link.</p>
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 32 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: errors.email ? '#ff4444' : '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
                  Email {errors.email && ': ' + errors.email}
                </label>
                <input type="email" value={email} onChange={function (e) { setEmail(e.target.value) }} onFocus={function () { setFocused(true) }} onBlur={function () { setFocused(false) }} placeholder="you@example.com" style={{
                  width: '100%', padding: '14px 0', fontSize: 15, fontFamily: FONT, fontWeight: 400, color: '#ffffff', background: 'transparent', border: 'none', borderBottom: '1px solid ' + (errors.email ? '#ff4444' : focused ? '#ffffff' : '#4b5563'), outline: 'none', transition: 'border-color 0.3s ease', letterSpacing: '0.01em',
                }} />
              </div>
              <button type="submit" disabled={loading} style={{ width: '100%', padding: '14px', fontSize: 14, fontWeight: 600, fontFamily: FONT, color: '#000000', background: '#ffffff', border: 'none', borderRadius: 8, cursor: loading ? 'wait' : 'pointer', letterSpacing: '-0.01em', transition: 'opacity 0.2s ease', opacity: loading ? 0.6 : 1 }}
                onMouseEnter={function (e) { if (!loading) e.target.style.opacity = '0.85' }} onMouseLeave={function (e) { if (!loading) e.target.style.opacity = '1' }}
              >{loading ? 'Sending...' : 'Send Reset Link'}</button>
            </form>
          </div>
        ) : (
          <div>
            <div style={{ width: 48, height: 48, border: '2px solid #ffffff', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 24 }}>
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M5 10l3.5 3.5L15 7" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </div>
            <h2 style={{ fontSize: 24, fontWeight: 600, color: '#ffffff', margin: '0 0 8px', letterSpacing: '-0.02em' }}>Check your email</h2>
            <p style={{ fontSize: 14, color: '#6b7280', margin: '0 0 4px', lineHeight: 1.6 }}>If an account exists for</p>
            <p style={{ fontSize: 14, color: '#ffffff', fontWeight: 500, margin: '0 0 32px' }}>{email}</p>
            <p style={{ fontSize: 14, color: '#6b7280', margin: 0, lineHeight: 1.6 }}>you'll receive a password reset link shortly.</p>
          </div>
        )}

        <p style={{ textAlign: 'center', marginTop: 36, fontSize: 13, color: '#6b7280' }}>
          <Link to="/login" style={{ color: '#ffffff', fontWeight: 500, textDecoration: 'none' }}>Back to sign in</Link>
        </p>
      </div>
    </div>
  )
}