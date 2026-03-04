/**
 * useIndexSSE — Hook for real-time index updates via SSE.
 *
 * Connects to GET /events/index via Server-Sent Events.
 * Falls back to polling GET /index/summary on disconnect.
 *
 * Returns:
 *   indexData: latest index snapshot (or null)
 *   connected: boolean (SSE connection status)
 *   lastUpdated: ISO timestamp of last received update
 *
 * Place at: src/hooks/useIndexSSE.js
 */

import { useState, useEffect, useRef } from "react"

var API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000')

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

  var retryCount = useRef(0)
  var eventSourceRef = useRef(null)
  var pollTimerRef = useRef(null)

  useEffect(function () {
    connectSSE()

    return function () {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [])

  function connectSSE() {
    try {
      var es = new EventSource(API_BASE + "/api/v1/events/index")
      eventSourceRef.current = es

      es.addEventListener("index_updated", function (event) {
        try {
          var data = JSON.parse(event.data)
          setIndexData(data)
          setLastUpdated(data.timestamp || new Date().toISOString())
          retryCount.current = 0
        } catch (e) {
          console.warn("Failed to parse SSE index data:", e)
        }
      })

      es.addEventListener("heartbeat", function () {
        // Connection is alive
      })

      es.onopen = function () {
        setConnected(true)
        retryCount.current = 0
        if (pollTimerRef.current) {
          clearInterval(pollTimerRef.current)
          pollTimerRef.current = null
        }
      }

      es.onerror = function () {
        setConnected(false)
        es.close()

        var delay = Math.min(1000 * Math.pow(2, retryCount.current), 30000)
        retryCount.current++

        if (!pollTimerRef.current) {
          startPolling()
        }

        setTimeout(connectSSE, delay)
      }
    } catch (e) {
      setConnected(false)
      startPolling()
    }
  }

  function startPolling() {
    if (pollTimerRef.current) return

    pollTimerRef.current = setInterval(function () {
      var token = localStorage.getItem("grace_token")
      var headers = { "Content-Type": "application/json" }
      if (token) headers["Authorization"] = "Bearer " + token

      fetch(API_BASE + "/api/v1/index/summary", { headers: headers })
        .then(function (res) { return res.json() })
        .then(function (data) {
          if (data.current) {
            setIndexData({
              gci: data.current.gci,
              csi: data.current.csi,
              dpi: data.current.dpi,
              frs: data.current.frs,
              trend: data.current.trend_direction,
              contributors: data.active_contributors_today,
            })
            setLastUpdated(data.last_updated_at)
          }
        })
        .catch(function () {})
    }, 60000)

    var token = localStorage.getItem("grace_token")
    var headers = { "Content-Type": "application/json" }
    if (token) headers["Authorization"] = "Bearer " + token

    fetch(API_BASE + "/api/v1/index/summary", { headers: headers })
      .then(function (res) { return res.json() })
      .then(function (data) {
        if (data.current) {
          setIndexData({
            gci: data.current.gci,
            csi: data.current.csi,
            dpi: data.current.dpi,
            frs: data.current.frs,
            trend: data.current.trend_direction,
            contributors: data.active_contributors_today,
          })
          setLastUpdated(data.last_updated_at)
        }
      })
      .catch(function () {})
  }

  return {
    indexData: indexData,
    connected: connected,
    lastUpdated: lastUpdated,
  }
}