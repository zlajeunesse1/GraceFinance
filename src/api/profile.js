/**
 * GraceFinance - Profile API (v6.1)
 * Matches your existing auth pattern:
 * - Token key: 'grace_token' (matches AuthContext)
 * - Base URL: auto-detects localhost vs production
 * - No user_id ever sent to backend
 *
 * CHANGES FROM v6:
 *   - Convention: var declarations, function expressions (matches codebase)
 */

var API_BASE = (function () {
  var host = window.location.hostname
  if (host === "localhost" || host === "127.0.0.1") return "http://localhost:8000"
  return "https://gracefinance-production.up.railway.app"
})()

function getAuthHeaders() {
  var token = localStorage.getItem("grace_token")
  if (!token) throw new Error("No session found. Please log in.")
  return {
    "Content-Type": "application/json",
    "Authorization": "Bearer " + token,
  }
}

function handleResponse(res) {
  if (!res.ok) {
    return res.json()
      .catch(function () { return { detail: "Unknown error" } })
      .then(function (errBody) {
        throw new Error(errBody.detail || "Request failed: " + res.status)
      })
  }
  return res.json()
}

export var profileApi = {
  /**
   * GET /api/profile
   * Auto-creates profile on first access.
   */
  get: function () {
    return fetch(API_BASE + "/api/profile", {
      method: "GET",
      headers: getAuthHeaders(),
    }).then(handleResponse)
  },

  /**
   * PATCH /api/profile
   * Partial update — only sends fields you pass in.
   * Never sends user_id.
   */
  update: function (payload) {
    /* Strip undefined so we only send what changed */
    var clean = {}
    var keys = Object.keys(payload)
    for (var i = 0; i < keys.length; i++) {
      if (payload[keys[i]] !== undefined) {
        clean[keys[i]] = payload[keys[i]]
      }
    }
    return fetch(API_BASE + "/api/profile", {
      method: "PATCH",
      headers: getAuthHeaders(),
      body: JSON.stringify(clean),
    }).then(handleResponse)
  },
}