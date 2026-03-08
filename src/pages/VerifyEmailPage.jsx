/**
 * VerifyEmailPage
 * Handles /verify-email?token=... links from verification emails.
 * Calls backend, shows success or error, redirects to login.
 */

import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'

var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"
var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'

export default function VerifyEmailPage() {
  var [searchParams] = useSearchParams()
  var token = searchParams.get('token')

  var [status, setStatus] = useState('loading') // loading | success | error
  var [message, setMessage] = useState('')

  useEffect(function () {
    if (!token) { setStatus('error'); setMessage('No verification token found. Try clicking the link in your email again.'); return }

    fetch(API_BASE + '/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: token }),
    })
      .then(function (res) { return res.json().then(function (d) { return { ok: res.ok, data: d } }) })
      .then(function (r) {
        if (r.ok) { setStatus('success') }
        else { setStatus('error'); setMessage(r.data.detail || 'Verification failed.') }
      })
      .catch(function () { setStatus('error'); setMessage('Something went wrong. Please try again.') })
  }, [token])

  return (
    <div style={{ minHeight: '100vh', background: '#000', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: FONT, padding: '24px' }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');"}</style>
      <div style={{ maxWidth: 420, width: '100%', textAlign: 'center' }}>

        <div style={{ width: 40, height: 40, border: '1.5px solid #fff', borderRadius: 8, lineHeight: '40px', fontSize: 16, fontWeight: 700, color: '#fff', margin: '0 auto 32px' }}>G</div>

        {/* Loading */}
        {status === 'loading' && (
          <>
            <h2 style={{ fontSize: 22, fontWeight: 600, color: '#fff', margin: '0 0 12px', letterSpacing: '-0.03em' }}>Verifying your email...</h2>
            <p style={{ fontSize: 14, color: '#6b7280', margin: 0 }}>Just a moment.</p>
          </>
        )}

        {/* Success */}
        {status === 'success' && (
          <>
            <div style={{ fontSize: 36, marginBottom: 20 }}>✓</div>
            <h2 style={{ fontSize: 22, fontWeight: 600, color: '#fff', margin: '0 0 12px', letterSpacing: '-0.03em' }}>Email verified</h2>
            <p style={{ fontSize: 14, color: '#9ca3af', lineHeight: 1.7, margin: '0 0 32px' }}>
              Your account is active. You can now sign in to GraceFinance.
            </p>
            <Link to="/login" style={{ display: 'inline-block', padding: '13px 32px', background: '#fff', color: '#000', textDecoration: 'none', borderRadius: 8, fontSize: 14, fontWeight: 700 }}>
              Sign In
            </Link>
          </>
        )}

        {/* Error */}
        {status === 'error' && (
          <>
            <div style={{ fontSize: 36, marginBottom: 20 }}>✕</div>
            <h2 style={{ fontSize: 22, fontWeight: 600, color: '#fff', margin: '0 0 12px', letterSpacing: '-0.03em' }}>Verification failed</h2>
            <p style={{ fontSize: 14, color: '#9ca3af', lineHeight: 1.7, margin: '0 0 32px' }}>{message}</p>
            <Link to="/login" style={{ fontSize: 13, color: '#6b7280', textDecoration: 'none', borderBottom: '1px solid #333', paddingBottom: 2 }}>
              Back to sign in
            </Link>
          </>
        )}

      </div>
    </div>
  )
}