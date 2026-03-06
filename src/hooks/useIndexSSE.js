/**
 * useIndexSSE — Hook for index updates.
 *
 * Polls GET /index/latest every 60 seconds.
 * SSE support can be added later when the backend has an events endpoint.
 *
 * Returns:
 *   indexData: latest index snapshot (or null)
 *   connected: boolean (polling active)
 *   lastUpdated: ISO timestamp of last received update
 *
 * Place at: src/hooks/useIndexSSE.js
 */

import { useState, useEffect, useRef } from "react"

var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'

export default function useIndexSSE() {
  var indexState = useState(null)
  var indexData = indexState[0]
  var setIndexData = indexState[1]

  var connectedState = useState(false)
  var connected = connectedState[0]
  var setConnected = connectedState[1]

  var lastUpdatedState = useState(null)
  var lastUpdated = lastUpdatedState[0]
  var setLastUpdated = lastUpdatedState[1]

  var pollTimerRef = useRef(null)

  useEffect(function () {
    fetchLatest()
    pollTimerRef.current = setInterval(fetchLatest, 60000)

    return function () {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [])

  function fetchLatest() {
    var token = localStorage.getItem("grace_token")
    var headers = { "Content-Type": "application/json" }
    if (token) headers["Authorization"] = "Bearer " + token

    fetch(API_BASE + "/index/latest", { headers: headers })
      .then(function (res) {
        if (!res.ok) throw new Error("Failed")
        return res.json()
      })
      .then(function (data) {
        if (data.published) {
          setIndexData({
            gfci: data.gfci_composite,
            fcs: data.fcs_average,
            users: data.user_count,
            trend: data.trend_direction,
            slope_3d: data.gci_slope_3d,
            slope_7d: data.gci_slope_7d,
            volatility: data.gci_volatility_7d,
          })
          setLastUpdated(data.index_date)
          setConnected(true)
        }
      })
      .catch(function () {
        setConnected(false)
      })
  }

  return {
    indexData: indexData,
    connected: connected,
    lastUpdated: lastUpdated,
  }
}