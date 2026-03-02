/**
 * useTodayStatus — Hook to fetch the user's current day status.
 *
 * Fetches GET /me/today and caches the result.
 * Re-fetches after check-in submission.
 *
 * Returns:
 *   status: TodayStatus object (or null)
 *   loading: boolean
 *   refetch: function to refresh
 *
 * Place at: src/hooks/useTodayStatus.js
 */

import { useState, useEffect, useCallback } from "react"

var API_BASE = "http://localhost:8000"

export default function useTodayStatus() {
  var statusState = useState(null)
  var status = statusState[0]
  var setStatus = statusState[1]

  var loadingState = useState(true)
  var loading = loadingState[0]
  var setLoading = loadingState[1]

  var fetchStatus = useCallback(function () {
    setLoading(true)
    var token = localStorage.getItem("grace_token")
    var headers = { "Content-Type": "application/json" }
    if (token) headers["Authorization"] = "Bearer " + token

    fetch(API_BASE + "/api/v1/me/today", { headers: headers })
      .then(function (res) {
        if (!res.ok) throw new Error("Failed to fetch today status")
        return res.json()
      })
      .then(function (data) {
        setStatus(data)
        setLoading(false)
      })
      .catch(function () {
        setLoading(false)
      })
  }, [])

  useEffect(function () {
    fetchStatus()
  }, [fetchStatus])

  return {
    status: status,
    loading: loading,
    refetch: fetchStatus,
  }
}
