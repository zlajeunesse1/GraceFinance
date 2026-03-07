/**
 * SignupPage — v5 Responsive
 * Desktop: side-by-side. Mobile: stacked, form-first.
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import useResponsive from '../hooks/useResponsive'

export default function SignupPage() {
  var navigate = useNavigate(); var auth = useAuth(); var signup = auth.signup
  var screen = useResponsive()
  var nameState = useState(''); var name = nameState[0]; var setName = nameState[1]
  var emailState = useState(''); var email = emailState[0]; var setEmail = emailState[1]
  var passwordState = useState(''); var password = passwordState[0]; var setPassword = passwordState[1]
  var errorsState = useState({}); var errors = errorsState[0]; var setErrors = errorsState[1]
  var loadingState = useState(false); var loading = loadingState[0]; var setLoading = loadingState[1]
  var apiErrorState = useState(''); var apiError = apiErrorState[0]; var setApiError = apiErrorState[1]
  var focusedState = useState(null); var focused = focusedState[0]; var setFocused = focusedState[1]
  var agreedState = useState(false); var agreed = agreedState[0]; var setAgreed = agreedState[1]

  function validateEmail(em) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em) }

  async function handleSubmit(e) {
    e.preventDefault(); setApiError('')
    var errs = {}
    if (!name.trim()) errs.name = 'Required'
    if (!email.trim()) errs.email = 'Required'
    else if (!validateEmail(email)) errs.email = 'Invalid email'
    if (!password) errs.password = 'Required'
    else if (password.length < 8) errs.password = 'Min 8 characters'
    if (!agreed) errs.agreed = 'You must agree to continue'
    setErrors(errs); if (Object.keys(errs).length > 0) return
    setLoading(true)
    try { await signup(name, email, password); navigate('/dashboard') }
    catch (err) { setApiError(err.message || 'Signup failed. Try again.') }
    finally { setLoading(false) }
  }

  var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"
  var inputStyle = function (field) {
    return { width: '100%', padding: '14px 0', fontSize: 15, fontFamily: FONT, fontWeight: 400, color: '#ffffff', background: 'transparent', border: 'none', borderBottom: '1px solid ' + (errors[field] ? '#ff4444' : focused === field ? '#ffffff' : '#333333'), outline: 'none', transition: 'border-color 0.3s ease', letterSpacing: '0.01em' }
  }
  var labelStyle = function (field) {
    return { display: 'block', fontSize: 11, fontWeight: 500, color: errors[field] ? '#ff4444' : '#666666', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4, fontFamily: FONT }
  }
  var linkStyle = { color: '#888888', textDecoration: 'underline', textUnderlineOffset: '2px' }

  /* ── Terms checkbox (shared between layouts) ── */
  function TermsCheckbox() {
    return (
      <div style={{ marginBottom: 24 }}>
        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={agreed}
            onChange={function (e) { setAgreed(e.target.checked); if (e.target.checked) { setErrors(function (prev) { var next = Object.assign({}, prev); delete next.agreed; return next }) } }}
            style={{ width: 16, height: 16, marginTop: 2, accentColor: '#ffffff', cursor: 'pointer', flexShrink: 0 }}
          />
          <span style={{ fontSize: 12, color: '#666666', lineHeight: 1.5, fontFamily: FONT }}>
            I agree to the{' '}
            <a href="/legal/terms" target="_blank" rel="noopener noreferrer" style={linkStyle}>Terms of Service</a>
            {' '}and{' '}
            <a href="/legal/privacy" target="_blank" rel="noopener noreferrer" style={linkStyle}>Privacy Policy</a>
          </span>
        </label>
        {errors.agreed && (
          <div style={{ fontSize: 11, color: '#ff4444', marginTop: 6, marginLeft: 26, fontFamily: FONT }}>{errors.agreed}</div>
        )}
      </div>
    )
  }

  /* ── Mobile/Tablet layout ── */
  if (screen.isMobile || screen.isTablet) {
    return (
      <div style={{ minHeight: '100vh', background: '#000000', fontFamily: FONT, display: 'flex', flexDirection: 'column' }}>
        <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder { color: #444444 !important; }input:-webkit-autofill { -webkit-box-shadow: 0 0 0 30px #000000 inset !important; -webkit-text-fill-color: #ffffff !important; }"}</style>

        <div style={{ padding: '32px 24px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
            <div style={{ width: 28, height: 28, border: '1.5px solid #ffffff', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#ffffff' }}>G</div>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.02em' }}>GraceFinance</span>
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 300, color: '#ffffff', lineHeight: 1.2, letterSpacing: '-0.03em', margin: '0 0 10px' }}>
            Know your <span style={{ fontWeight: 600 }}>financial confidence.</span>
          </h1>
          <p style={{ fontSize: 13, color: '#666666', lineHeight: 1.6, margin: 0 }}>
            Your FCS measures how you interact with money — daily. A behavioral signal that gets smarter over time.
          </p>
        </div>

        <div style={{ flex: 1, padding: '8px 24px 40px' }}>
          <p style={{ fontSize: 13, color: '#555555', margin: '0 0 20px' }}>Know your Financial Confidence Score in 6 taps.</p>
          {apiError && (<div style={{ marginBottom: 20, padding: '12px 16px', border: '1px solid #331111', background: '#1a0a0a', borderRadius: 8, fontSize: 13, color: '#ff4444' }}>{apiError}</div>)}
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 22 }}>
              <label style={labelStyle('name')}>Full Name {errors.name && '— ' + errors.name}</label>
              <input type="text" value={name} onChange={function (e) { setName(e.target.value) }} onFocus={function () { setFocused('name') }} onBlur={function () { setFocused(null) }} placeholder="Your name" style={inputStyle('name')} />
            </div>
            <div style={{ marginBottom: 22 }}>
              <label style={labelStyle('email')}>Email {errors.email && '— ' + errors.email}</label>
              <input type="email" value={email} onChange={function (e) { setEmail(e.target.value) }} onFocus={function () { setFocused('email') }} onBlur={function () { setFocused(null) }} placeholder="you@example.com" style={inputStyle('email')} />
            </div>
            <div style={{ marginBottom: 24 }}>
              <label style={labelStyle('password')}>Password {errors.password && '— ' + errors.password}</label>
              <input type="password" value={password} onChange={function (e) { setPassword(e.target.value) }} onFocus={function () { setFocused('password') }} onBlur={function () { setFocused(null) }} placeholder="Min 8 characters" style={inputStyle('password')} />
            </div>
            <TermsCheckbox />
            <button type="submit" disabled={loading} style={{ width: '100%', padding: '16px', fontSize: 15, fontWeight: 600, fontFamily: FONT, color: '#000000', background: '#ffffff', border: 'none', borderRadius: 10, cursor: loading ? 'wait' : 'pointer', letterSpacing: '-0.01em', opacity: loading ? 0.6 : 1 }}>
              {loading ? 'Creating account...' : 'Get Started'}
            </button>
          </form>
          <p style={{ textAlign: 'center', marginTop: 28, fontSize: 13, color: '#555555' }}>
            Already tracking?{' '}<Link to="/login" style={{ color: '#ffffff', fontWeight: 500, textDecoration: 'none' }}>Sign in</Link>
          </p>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 36, paddingTop: 20, borderTop: '1px solid #1a1a1a' }}>
            {[{ num: '5', label: 'Dimensions' }, { num: '< 2min', label: 'Check-in' }, { num: '24/7', label: 'AI Coach' }].map(function (stat) {
              return (<div key={stat.label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: '#ffffff' }}>{stat.num}</div>
                <div style={{ fontSize: 10, color: '#555555', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{stat.label}</div>
              </div>)
            })}
          </div>
        </div>
      </div>
    )
  }

  /* ── Desktop (unchanged layout, added terms checkbox) ── */
  return (
    <div style={{ minHeight: '100vh', background: '#000000', display: 'flex', fontFamily: FONT }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder { color: #444444 !important; }input:-webkit-autofill { -webkit-box-shadow: 0 0 0 30px #000000 inset !important; -webkit-text-fill-color: #ffffff !important; }"}</style>

      <div style={{ width: '45%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '48px', borderRight: '1px solid #141414', position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(#111111 1px, transparent 1px), linear-gradient(90deg, #111111 1px, transparent 1px)', backgroundSize: '60px 60px', opacity: 0.4, pointerEvents: 'none' }} />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 80 }}>
            <div style={{ width: 32, height: 32, border: '2px solid #ffffff', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700, color: '#ffffff' }}>G</div>
            <span style={{ fontSize: 15, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.02em' }}>GraceFinance</span>
          </div>
          <h1 style={{ fontSize: 44, fontWeight: 300, color: '#ffffff', lineHeight: 1.15, letterSpacing: '-0.03em', margin: 0 }}>Know your<br /><span style={{ fontWeight: 600 }}>financial confidence.</span></h1>
          <p style={{ fontSize: 16, color: '#666666', lineHeight: 1.7, marginTop: 24, maxWidth: 360, fontWeight: 400 }}>Your Financial Confidence Score measures how you interact with money — daily. Not a credit score. Not a budget. A behavioral signal that gets smarter over time.</p>
        </div>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', gap: 32, marginBottom: 32 }}>
            {[{ num: '5', label: 'Behavioral dimensions' }, { num: '< 2min', label: 'Daily check-in' }, { num: '24/7', label: 'AI coaching' }].map(function (stat) {
              return (<div key={stat.label}><div style={{ fontSize: 20, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.02em' }}>{stat.num}</div><div style={{ fontSize: 11, color: '#555555', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{stat.label}</div></div>)
            })}
          </div>
          <div style={{ borderTop: '1px solid #1a1a1a', paddingTop: 20 }}><p style={{ fontSize: 12, color: '#444444', margin: 0, letterSpacing: '0.02em' }}>Where Financial Confidence Is Measured</p></div>
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px' }}>
        <div style={{ width: '100%', maxWidth: 380 }}>
          <div style={{ marginBottom: 40 }}>
            <h2 style={{ fontSize: 24, fontWeight: 600, color: '#ffffff', margin: '0 0 8px', letterSpacing: '-0.02em' }}>Create your account</h2>
            <p style={{ fontSize: 14, color: '#555555', margin: 0 }}>Know your Financial Confidence Score in 6 taps.</p>
          </div>
          {apiError && (<div style={{ marginBottom: 24, padding: '12px 16px', border: '1px solid #331111', background: '#1a0a0a', borderRadius: 8, fontSize: 13, color: '#ff4444' }}>{apiError}</div>)}
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 28 }}><label style={labelStyle('name')}>Full Name {errors.name && '— ' + errors.name}</label><input type="text" value={name} onChange={function (e) { setName(e.target.value) }} onFocus={function () { setFocused('name') }} onBlur={function () { setFocused(null) }} placeholder="Your name" style={inputStyle('name')} /></div>
            <div style={{ marginBottom: 28 }}><label style={labelStyle('email')}>Email {errors.email && '— ' + errors.email}</label><input type="email" value={email} onChange={function (e) { setEmail(e.target.value) }} onFocus={function () { setFocused('email') }} onBlur={function () { setFocused(null) }} placeholder="you@example.com" style={inputStyle('email')} /></div>
            <div style={{ marginBottom: 32 }}><label style={labelStyle('password')}>Password {errors.password && '— ' + errors.password}</label><input type="password" value={password} onChange={function (e) { setPassword(e.target.value) }} onFocus={function () { setFocused('password') }} onBlur={function () { setFocused(null) }} placeholder="Min 8 characters" style={inputStyle('password')} /></div>
            <TermsCheckbox />
            <button type="submit" disabled={loading} style={{ width: '100%', padding: '14px', fontSize: 14, fontWeight: 600, fontFamily: FONT, color: '#000000', background: '#ffffff', border: 'none', borderRadius: 8, cursor: loading ? 'wait' : 'pointer', letterSpacing: '-0.01em', transition: 'opacity 0.2s ease', opacity: loading ? 0.6 : 1 }}
              onMouseEnter={function (e) { if (!loading) e.target.style.opacity = '0.85' }} onMouseLeave={function (e) { if (!loading) e.target.style.opacity = '1' }}
            >{loading ? 'Creating account...' : 'Get Started'}</button>
          </form>
          <p style={{ textAlign: 'center', marginTop: 32, fontSize: 13, color: '#555555' }}>Already tracking?{' '}<Link to="/login" style={{ color: '#ffffff', fontWeight: 500, textDecoration: 'none' }}>Sign in</Link></p>
        </div>
      </div>
    </div>
  )
}