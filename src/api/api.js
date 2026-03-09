/**
 * api.js — Centralized API fetch utility for GraceFinance.
 *
 * FIX #4 (CRITICAL): Handles 401 Unauthorized globally.
 * When the JWT expires mid-session, this automatically clears
 * the token and redirects to /login instead of silently failing.
 *
 * Usage:
 *   import { apiFetch } from '../utils/api'
 *   const data = await apiFetch('/me/metrics')
 *   const data = await apiFetch('/checkin/submit', { method: 'POST', body: JSON.stringify(payload) })
 */

var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'

/**
 * Fetch wrapper with automatic auth headers and 401 handling.
 *
 * - Injects Bearer token from localStorage
 * - On 401: clears token, redirects to /login
 * - On 403 with "Email not verified": redirects to /verify
 * - Returns parsed JSON on success
 * - Throws on other errors
 */
export function apiFetch(endpoint, options) {
  var token = localStorage.getItem('grace_token')
  var headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = 'Bearer ' + token

  var config = { headers: headers }
  if (options) {
    for (var k in options) {
      if (k === 'headers') {
        for (var h in options.headers) headers[h] = options.headers[h]
      } else {
        config[k] = options[k]
      }
    }
  }
  config.headers = headers

  return fetch(API_BASE + endpoint, config).then(function (res) {
    // ── 401: Token expired or invalid — force re-login ──
    if (res.status === 401) {
      localStorage.removeItem('grace_token')
      localStorage.removeItem('grace-onboarding-complete')
      localStorage.removeItem('grace-onboarding-data')
      // Only redirect if we're not already on login/signup
      var path = window.location.pathname
      if (path !== '/login' && path !== '/signup' && path !== '/verify-email') {
        window.location.href = '/login'
      }
      throw new Error('Session expired. Please log in again.')
    }

    // ── 403: Could be email not verified ──
    if (res.status === 403) {
      return res.json().then(function (data) {
        if (data.detail && data.detail.toLowerCase().indexOf('email not verified') !== -1) {
          // Redirect to a verify page or show message
          window.location.href = '/verify-email'
          throw new Error('Email not verified.')
        }
        throw new Error(data.detail || 'Forbidden')
      })
    }

    if (!res.ok) {
      return res.json().then(function (data) {
        throw new Error(data.detail || 'Request failed: ' + endpoint)
      }).catch(function (err) {
        if (err.message) throw err
        throw new Error('Request failed: ' + endpoint)
      })
    }

    return res.json()
  })
}

/**
 * Convenience: build auth headers for components that need raw fetch.
 * Prefer apiFetch() over this when possible.
 */
export function authHeaders() {
  var token = localStorage.getItem('grace_token')
  var headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = 'Bearer ' + token
  return headers
}

export { API_BASE }