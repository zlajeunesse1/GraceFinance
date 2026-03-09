/**
 * SignupPage — v6.4
 * FIX: LegalModal fetches actual static HTML files (terms.html, privacy.html)
 *      instead of hitting a JSON API endpoint that doesn't exist.
 * FIX: Renders HTML content properly with styled container.
 * KEPT: Checkbox validation, pricing link, verify pending flow.
 */

import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import useResponsive from '../hooks/useResponsive'

var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'

var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

/**
 * LegalModal — loads static HTML legal pages and renders them.
 *
 * Fetch order:
 *   1. Try frontend static path: /static/legal/{type}.html
 *   2. Fallback to backend:      API_BASE/static/legal/{type}.html
 *
 * Renders the HTML inside a styled, scrollable modal.
 */
function LegalModal(props) {
  var type = props.type
  var onClose = props.onClose
  var contentState = useState(null); var content = contentState[0]; var setContent = contentState[1]
  var loadingState = useState(true); var isLoading = loadingState[0]; var setIsLoading = loadingState[1]
  var errorState = useState(false); var hasError = errorState[0]; var setHasError = errorState[1]

  var titles = { terms: "Terms of Service", privacy: "Privacy Policy", refund: "Refund Policy" }

  // Map type to filename
  var fileMap = { terms: "terms.html", privacy: "privacy.html", refund: "refund.html" }
  var filename = fileMap[type] || type + ".html"

  useEffect(function () {
    setIsLoading(true)
    setHasError(false)
    setContent(null)

    // Try frontend static path first, then backend
    var frontendUrl = "/static/legal/" + filename
    var backendUrl = API_BASE + "/static/legal/" + filename

    fetch(frontendUrl)
      .then(function (res) {
        if (!res.ok) throw new Error("Frontend 404")
        return res.text()
      })
      .then(function (html) {
        setContent(html)
        setIsLoading(false)
      })
      .catch(function () {
        // Fallback: try backend static serving
        fetch(backendUrl)
          .then(function (res) {
            if (!res.ok) throw new Error("Backend 404")
            return res.text()
          })
          .then(function (html) {
            setContent(html)
            setIsLoading(false)
          })
          .catch(function () {
            // Final fallback: try the old JSON endpoint
            fetch(API_BASE + "/legal/" + type)
              .then(function (res) {
                if (!res.ok) throw new Error("API 404")
                return res.json()
              })
              .then(function (data) {
                // Convert JSON to displayable text
                if (data.sections) {
                  var html = data.sections.map(function (s) {
                    var out = ''
                    if (s.title) out += '<h3 style="color:#fff;font-size:14px;font-weight:600;margin:0 0 8px">' + s.title + '</h3>'
                    if (s.content) out += '<p style="color:#ccc;font-size:13px;line-height:1.8;margin:0 0 12px;white-space:pre-wrap">' + s.content + '</p>'
                    if (s.items) {
                      out += s.items.map(function (item) {
                        return '<p style="color:#aaa;font-size:12px;line-height:1.7;margin:6px 0 0 16px">• ' + item + '</p>'
                      }).join('')
                    }
                    return '<div style="margin-bottom:20px">' + out + '</div>'
                  }).join('')
                  setContent(html)
                } else if (typeof data === 'string') {
                  setContent('<p style="color:#ccc;font-size:13px;line-height:1.8;white-space:pre-wrap">' + data + '</p>')
                } else {
                  setContent('<pre style="color:#ccc;font-size:11px;line-height:1.6;white-space:pre-wrap;word-break:break-word">' + JSON.stringify(data, null, 2) + '</pre>')
                }
                setIsLoading(false)
              })
              .catch(function () {
                setHasError(true)
                setIsLoading(false)
              })
          })
      })
  }, [type])

  // Styles injected into the HTML content container to make raw legal HTML look good on dark bg
  var contentStyles = "\
    .legal-content { color: #ccc; font-size: 13px; line-height: 1.8; font-family: " + FONT + "; }\
    .legal-content h1 { color: #fff; font-size: 18px; font-weight: 600; margin: 0 0 16px; }\
    .legal-content h2 { color: #fff; font-size: 15px; font-weight: 600; margin: 24px 0 10px; }\
    .legal-content h3 { color: #fff; font-size: 14px; font-weight: 600; margin: 20px 0 8px; }\
    .legal-content p { color: #ccc; margin: 0 0 12px; }\
    .legal-content ul, .legal-content ol { color: #aaa; padding-left: 20px; margin: 0 0 12px; }\
    .legal-content li { margin-bottom: 6px; font-size: 12px; line-height: 1.7; }\
    .legal-content a { color: #60a5fa; text-decoration: underline; }\
    .legal-content strong { color: #fff; }\
    .legal-content table { border-collapse: collapse; width: 100%; margin: 12px 0; }\
    .legal-content th, .legal-content td { border: 1px solid #333; padding: 8px 12px; font-size: 12px; text-align: left; }\
    .legal-content th { background: #111; color: #fff; }\
    .legal-content td { color: #ccc; }\
  "

  function renderContent() {
    if (isLoading) return <p style={{ color: '#9ca3af', fontSize: 13 }}>Loading...</p>
    if (hasError) return <p style={{ color: '#ef4444', fontSize: 13 }}>Failed to load. Please try again.</p>
    if (!content) return <p style={{ color: '#ef4444', fontSize: 13 }}>No content available.</p>

    return (
      <>
        <style>{contentStyles}</style>
        <div className="legal-content" dangerouslySetInnerHTML={{ __html: content }} />
      </>
    )
  }

  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div onClick={function (e) { e.stopPropagation() }} style={{ width: '100%', maxWidth: 560, maxHeight: '80vh', background: '#0a0a0a', border: '1px solid #222', borderRadius: 12, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid #1a1a1a', flexShrink: 0 }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: '#fff', fontFamily: FONT }}>{titles[type] || type}</span>
          <button onClick={onClose} style={{ background: 'transparent', border: '1px solid #333', borderRadius: 6, padding: '4px 12px', color: '#888', fontSize: 12, fontFamily: FONT, cursor: 'pointer' }}>Close</button>
        </div>
        <div style={{ padding: 20, overflowY: 'auto', flex: 1, fontFamily: FONT }}>{renderContent()}</div>
        <div style={{ padding: '12px 20px', borderTop: '1px solid #1a1a1a', flexShrink: 0, textAlign: 'center' }}>
          <p style={{ fontSize: 11, color: '#555', margin: 0, fontFamily: FONT }}>GraceFinance · Grace Holdings LLC</p>
        </div>
      </div>
    </div>
  )
}

export default function SignupPage() {
  var navigate = useNavigate(); var auth = useAuth(); var signup = auth.signup
  var screen = useResponsive()
  var nameState = useState(''); var name = nameState[0]; var setName = nameState[1]
  var emailState = useState(''); var email = emailState[0]; var setEmail = emailState[1]
  var passwordState = useState(''); var password = passwordState[0]; var setPassword = passwordState[1]
  var dobState = useState(''); var dob = dobState[0]; var setDob = dobState[1]
  var errorsState = useState({}); var errors = errorsState[0]; var setErrors = errorsState[1]
  var loadingState = useState(false); var loading = loadingState[0]; var setLoading = loadingState[1]
  var apiErrorState = useState(''); var apiError = apiErrorState[0]; var setApiError = apiErrorState[1]
  var focusedState = useState(null); var focused = focusedState[0]; var setFocused = focusedState[1]
  var agreedState = useState(false); var agreed = agreedState[0]; var setAgreed = agreedState[1]
  var verifyPendingState = useState(false); var verifyPending = verifyPendingState[0]; var setVerifyPending = verifyPendingState[1]
  var resendLoadingState = useState(false); var resendLoading = resendLoadingState[0]; var setResendLoading = resendLoadingState[1]
  var resendSentState = useState(false); var resendSent = resendSentState[0]; var setResendSent = resendSentState[1]
  var legalModalState = useState(null); var legalModal = legalModalState[0]; var setLegalModal = legalModalState[1]

  function validateEmail(em) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(em) }

  function calculateAge(dobStr) {
    if (!dobStr) return 0
    var today = new Date(); var birth = new Date(dobStr)
    var age = today.getFullYear() - birth.getFullYear()
    var m = today.getMonth() - birth.getMonth()
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--
    return age
  }

  async function handleSubmit(e) {
    e.preventDefault(); setApiError('')
    var errs = {}
    if (!name.trim()) errs.name = 'Required'
    if (!email.trim()) errs.email = 'Required'
    else if (!validateEmail(email)) errs.email = 'Invalid email'
    if (!password) errs.password = 'Required'
    else if (password.length < 8) errs.password = 'Min 8 characters'
    if (!dob) errs.dob = 'Required'
    else if (calculateAge(dob) < 18) errs.dob = 'Must be 18 or older'
    if (!agreed) errs.agreed = 'You must agree to continue'
    setErrors(errs); if (Object.keys(errs).length > 0) return
    setLoading(true)
    try { await signup(name, email, password, dob); setVerifyPending(true) }
    catch (err) { setApiError(err.message || 'Signup failed. Try again.') }
    finally { setLoading(false) }
  }

  async function handleResend() {
    setResendLoading(true)
    try {
      await fetch(API_BASE + '/auth/resend-verification', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: email }) })
      setResendSent(true)
    } catch (e) { }
    finally { setResendLoading(false) }
  }

  var inputStyle = function (field) { return { width: '100%', padding: '14px 0', fontSize: 15, fontFamily: FONT, fontWeight: 400, color: '#ffffff', background: 'transparent', border: 'none', borderBottom: '1px solid ' + (errors[field] ? '#ff4444' : focused === field ? '#ffffff' : '#4b5563'), outline: 'none', transition: 'border-color 0.3s ease', letterSpacing: '0.01em' } }
  var labelStyle = function (field) { return { display: 'block', fontSize: 11, fontWeight: 500, color: errors[field] ? '#ff4444' : '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4, fontFamily: FONT } }

  if (verifyPending) {
    return (
      <div style={{ minHeight: '100vh', background: '#000000', fontFamily: FONT, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
        <style>{"@import url('https://fonts.cdnfonts.com/css/geist');"}</style>
        <div style={{ maxWidth: 420, width: '100%', textAlign: 'center' }}>
          <div style={{ width: 48, height: 48, border: '1.5px solid #ffffff', borderRadius: 12, lineHeight: '48px', fontSize: 20, fontWeight: 700, color: '#ffffff', margin: '0 auto 32px', textAlign: 'center' }}>G</div>
          <h2 style={{ fontSize: 26, fontWeight: 600, color: '#ffffff', margin: '0 0 12px', letterSpacing: '-0.03em' }}>Check your inbox</h2>
          <p style={{ fontSize: 14, color: '#9ca3af', lineHeight: 1.7, margin: '0 0 6px' }}>We sent a verification link to</p>
          <p style={{ fontSize: 14, color: '#ffffff', fontWeight: 600, margin: '0 0 28px' }}>{email}</p>
          <p style={{ fontSize: 13, color: '#6b7280', lineHeight: 1.7, margin: '0 0 32px' }}>Click the link to activate your account. Check spam if you don't see it within a minute.</p>
          <div style={{ padding: '18px 20px', background: '#0a0a0a', border: '1px solid #1a1a1a', borderRadius: 10, marginBottom: 32 }}>
            <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 12px' }}>Didn't get it?</p>
            {resendSent ? <p style={{ fontSize: 13, color: '#10b981', margin: 0, fontWeight: 600 }}>✓ New link sent</p> : <button onClick={handleResend} disabled={resendLoading} style={{ background: 'transparent', border: '1px solid #333', borderRadius: 6, padding: '8px 18px', color: '#ffffff', fontSize: 13, fontWeight: 500, fontFamily: FONT, cursor: resendLoading ? 'wait' : 'pointer', opacity: resendLoading ? 0.5 : 1 }}>{resendLoading ? 'Sending...' : 'Resend verification email'}</button>}
          </div>
          <Link to="/login" style={{ fontSize: 13, color: '#6b7280', textDecoration: 'none' }}>Back to sign in</Link>
        </div>
      </div>
    )
  }

  var formJSX = (
    <>
      {apiError && (<div style={{ marginBottom: 20, padding: '12px 16px', border: '1px solid #331111', background: '#1a0a0a', borderRadius: 8, fontSize: 13, color: '#ff4444' }}>{apiError}</div>)}
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 22 }}>
          <label style={labelStyle('name')}>Full Name {errors.name && ': ' + errors.name}</label>
          <input type="text" value={name} onChange={function (e) { setName(e.target.value) }} onFocus={function () { setFocused('name') }} onBlur={function () { setFocused(null) }} placeholder="Your name" style={inputStyle('name')} />
        </div>
        <div style={{ marginBottom: 22 }}>
          <label style={labelStyle('email')}>Email {errors.email && ': ' + errors.email}</label>
          <input type="email" value={email} onChange={function (e) { setEmail(e.target.value) }} onFocus={function () { setFocused('email') }} onBlur={function () { setFocused(null) }} placeholder="you@example.com" style={inputStyle('email')} />
        </div>
        <div style={{ marginBottom: 22 }}>
          <label style={labelStyle('password')}>Password {errors.password && ': ' + errors.password}</label>
          <input type="password" value={password} onChange={function (e) { setPassword(e.target.value) }} onFocus={function () { setFocused('password') }} onBlur={function () { setFocused(null) }} placeholder="Min 8 characters" style={inputStyle('password')} />
        </div>
        <div style={{ marginBottom: 24 }}>
          <label style={labelStyle('dob')}>Date of Birth {errors.dob && ': ' + errors.dob}</label>
          <input type="date" value={dob} onChange={function (e) { setDob(e.target.value) }} onFocus={function () { setFocused('dob') }} onBlur={function () { setFocused(null) }} style={{ ...inputStyle('dob'), colorScheme: 'dark' }} />
          <div style={{ fontSize: 11, color: '#4b5563', marginTop: 4, fontFamily: FONT }}>Must be 18 or older</div>
        </div>
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
            <input type="checkbox" checked={agreed}
              onChange={function (e) { setAgreed(e.target.checked); if (e.target.checked) { setErrors(function (prev) { var next = Object.assign({}, prev); delete next.agreed; return next }) } }}
              style={{ width: 16, height: 16, marginTop: 2, accentColor: '#ffffff', cursor: 'pointer', flexShrink: 0 }} />
            <span style={{ fontSize: 12, color: '#9ca3af', lineHeight: 1.5, fontFamily: FONT }}>
              I agree to the{' '}
              <span onClick={function (e) { e.preventDefault(); e.stopPropagation(); setLegalModal('terms') }} style={{ color: '#ffffff', textDecoration: 'underline', cursor: 'pointer' }}>Terms of Service</span>
              {' '}and{' '}
              <span onClick={function (e) { e.preventDefault(); e.stopPropagation(); setLegalModal('privacy') }} style={{ color: '#ffffff', textDecoration: 'underline', cursor: 'pointer' }}>Privacy Policy</span>
            </span>
          </label>
          {errors.agreed && (<div style={{ fontSize: 11, color: '#ff4444', marginTop: 6, marginLeft: 26, fontFamily: FONT }}>{errors.agreed}</div>)}
        </div>
        <button type="submit" disabled={loading} style={{ width: '100%', padding: '14px', fontSize: 14, fontWeight: 600, fontFamily: FONT, color: '#000000', background: '#ffffff', border: 'none', borderRadius: 8, cursor: loading ? 'wait' : 'pointer', letterSpacing: '-0.01em', transition: 'opacity 0.2s ease', opacity: loading ? 0.6 : 1 }} onMouseEnter={function (e) { if (!loading) e.target.style.opacity = '0.85' }} onMouseLeave={function (e) { if (!loading) e.target.style.opacity = '1' }}>{loading ? 'Creating account...' : 'Get Started'}</button>
      </form>
      <p style={{ textAlign: 'center', marginTop: 28, fontSize: 13, color: '#6b7280' }}>Already tracking?{' '}<Link to="/login" style={{ color: '#ffffff', fontWeight: 500, textDecoration: 'none' }}>Sign in</Link></p>
      <p style={{ textAlign: 'center', marginTop: 12, fontSize: 12, color: '#4b5563' }}><Link to="/pricing" style={{ color: '#6b7280', textDecoration: 'none' }}>See our plans →</Link></p>
    </>
  )

  if (screen.isMobile || screen.isTablet) {
    return (
      <div style={{ minHeight: '100vh', background: '#000000', fontFamily: FONT, display: 'flex', flexDirection: 'column' }}>
        <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder { color: #6b7280 !important; }input:-webkit-autofill { -webkit-box-shadow: 0 0 0 30px #000000 inset !important; -webkit-text-fill-color: #ffffff !important; }"}</style>
        <div style={{ padding: '32px 24px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
            <div style={{ width: 28, height: 28, border: '1.5px solid #ffffff', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700, color: '#ffffff' }}>G</div>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.02em' }}>GraceFinance</span>
          </div>
          <h1 style={{ fontSize: 28, fontWeight: 300, color: '#ffffff', lineHeight: 1.2, letterSpacing: '-0.03em', margin: '0 0 10px' }}>Know your <span style={{ fontWeight: 600 }}>financial confidence.</span></h1>
          <p style={{ fontSize: 13, color: '#9ca3af', lineHeight: 1.6, margin: 0 }}>Your FCS measures how you interact with money, daily.</p>
        </div>
        <div style={{ flex: 1, padding: '8px 24px 40px' }}>
          <p style={{ fontSize: 13, color: '#6b7280', margin: '0 0 20px' }}>Know your Financial Confidence Score in minutes.</p>
          {formJSX}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 36, paddingTop: 20, borderTop: '1px solid #1a1a1a' }}>
            {[{ num: '5', label: 'Dimensions' }, { num: '< 2min', label: 'Check-in' }, { num: '24/7', label: 'AI Coach' }].map(function (stat) { return (<div key={stat.label} style={{ textAlign: 'center' }}><div style={{ fontSize: 18, fontWeight: 600, color: '#ffffff' }}>{stat.num}</div><div style={{ fontSize: 10, color: '#6b7280', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{stat.label}</div></div>) })}
          </div>
        </div>
        {legalModal && <LegalModal type={legalModal} onClose={function () { setLegalModal(null) }} />}
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
          <h1 style={{ fontSize: 44, fontWeight: 300, color: '#ffffff', lineHeight: 1.15, letterSpacing: '-0.03em', margin: 0 }}>Know your<br /><span style={{ fontWeight: 600 }}>financial confidence.</span></h1>
          <p style={{ fontSize: 16, color: '#9ca3af', lineHeight: 1.7, marginTop: 24, maxWidth: 360, fontWeight: 400 }}>Your Financial Confidence Score measures how you interact with money, daily. Not a credit score. Not a budget. A behavioral signal that gets smarter over time.</p>
        </div>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', gap: 32, marginBottom: 32 }}>
            {[{ num: '5', label: 'Behavioral dimensions' }, { num: '< 2min', label: 'Daily check-in' }, { num: '24/7', label: 'AI coaching' }].map(function (stat) { return (<div key={stat.label}><div style={{ fontSize: 20, fontWeight: 600, color: '#ffffff', letterSpacing: '-0.02em' }}>{stat.num}</div><div style={{ fontSize: 11, color: '#6b7280', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{stat.label}</div></div>) })}
          </div>
          <div style={{ borderTop: '1px solid #1a1a1a', paddingTop: 20 }}><p style={{ fontSize: 12, color: '#6b7280', margin: 0, letterSpacing: '0.02em' }}>Where Financial Confidence Is Measured</p></div>
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px', overflowY: 'auto' }}>
        <div style={{ width: '100%', maxWidth: 380 }}>
          <div style={{ marginBottom: 40 }}>
            <h2 style={{ fontSize: 24, fontWeight: 600, color: '#ffffff', margin: '0 0 8px', letterSpacing: '-0.02em' }}>Create your account</h2>
            <p style={{ fontSize: 14, color: '#6b7280', margin: 0 }}>Know your Financial Confidence Score in minutes.</p>
          </div>
          {formJSX}
        </div>
      </div>
      {legalModal && <LegalModal type={legalModal} onClose={function () { setLegalModal(null) }} />}
    </div>
  )
}