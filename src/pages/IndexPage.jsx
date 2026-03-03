/**
 * IndexPage — Dedicated page for the Grace Composite Index.
 *
 * CHANGES:
 *   - [TIER 1] Fixed prop leak: replaced raw `activePage="index" /` with <NavBar /> component
 *   - [TIER 3] Changed "Live" badge to "Beta" when limited contributors
 *
 * Place at: src/pages/IndexPage.jsx
 */

import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useTheme } from "../context/ThemeContext"
import { useAuth } from "../context/AuthContext"
import Logo from "../components/Logo"
import ModeToggle from "../components/ModeToggle"
import NavBar from "../components/NavBar"

import useIndexSSE from "../hooks/useIndexSSE"
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts"

var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'

function apiFetch(endpoint) {
  var token = localStorage.getItem("grace_token")
  var headers = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = "Bearer " + token
  return fetch(API_BASE + endpoint, { headers: headers }).then(function (res) {
    if (!res.ok) throw new Error("Failed: " + endpoint)
    return res.json()
  })
}

var TREND_CONFIG = {
  UP: { arrow: "\u25B2", color: "#3FB950", label: "Trending Up", glow: "rgba(63, 185, 80, 0.15)" },
  DOWN: { arrow: "\u25BC", color: "#F85149", label: "Trending Down", glow: "rgba(248, 81, 73, 0.15)" },
  FLAT: { arrow: "\u25B6", color: "rgba(255,255,255,0.4)", label: "Holding Steady", glow: "transparent" },
}

export default function IndexPage() {
  var t = useTheme().theme
  var auth = useAuth()
  var user = auth.user
  var logout = auth.logout
  var navigate = useNavigate()

  var mountedState = useState(false)
  var mounted = mountedState[0]
  var setMounted = mountedState[1]

  var summaryState = useState(null)
  var summary = summaryState[0]
  var setSummary = summaryState[1]

  var historyState = useState([])
  var history = historyState[0]
  var setHistory = historyState[1]

  var sse = useIndexSSE()

  useEffect(function () {
    setMounted(true)
    loadData()
  }, [])

  // Refresh when SSE gets new data
  useEffect(function () {
    if (sse.indexData) {
      loadData()
    }
  }, [sse.lastUpdated])

  function loadData() {
    apiFetch("/api/v1/index/summary")
      .then(function (data) { setSummary(data) })
      .catch(function () {})

    apiFetch("/api/v1/index/history?range=30d")
      .then(function (data) {
        if (data && data.data) setHistory(data.data)
      })
      .catch(function () {})
  }

  function handleLogout() {
    logout()
    navigate("/login")
  }

  var current = summary ? summary.current : null
  var trend = current ? current.trend_direction : "FLAT"
  var trendConfig = TREND_CONFIG[trend] || TREND_CONFIG.FLAT
  var contrib = summary ? summary.user_contribution : null
  var changelog = summary ? summary.changelog : []

  // Format last updated
  var lastUpdatedStr = ""
  if (summary && summary.last_updated_at) {
    var d = new Date(summary.last_updated_at)
    lastUpdatedStr = d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) +
      " at " + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  }

  // Chart data
  var chartData = history.map(function (item) {
    return {
      date: item.date,
      gci: item.gci ? parseFloat(item.gci) : null,
    }
  })

  return (
    <div style={{
      minHeight: "100vh",
      background: t.dark || "#0B0F1A",
      color: t.text || "#E2E8F0",
      fontFamily: "'DM Sans', -apple-system, sans-serif",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet" />

      <div style={{ maxWidth: 800, margin: "0 auto", padding: "24px 20px 60px" }}>

        {/* Header */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20,
          opacity: mounted ? 1 : 0, transition: "all 0.5s ease",
        }}>
          <Logo size={36} />
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <ModeToggle />
            <button onClick={handleLogout} style={{
              padding: "8px 16px", fontSize: 13, fontWeight: 500, cursor: "pointer",
              background: "transparent", border: "1px solid " + (t.border || "#334155"), borderRadius: 10, color: t.muted || "#64748B",
            }}>
              Sign out
            </button>
          </div>
        </div>

        {/* Nav */}
        <div style={{ marginBottom: 24 }}>
          <NavBar navigate={navigate} activePage="index" />
        </div>

        {/* Hero: GCI Value */}
        <div style={{
          padding: "32px 28px",
          borderRadius: 18,
          background: "linear-gradient(165deg, rgba(17, 24, 39, 0.98), rgba(15, 20, 35, 0.95))",
          border: "1px solid rgba(255,255,255,0.06)",
          marginBottom: 20,
          position: "relative",
          overflow: "hidden",
          opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(20px)",
          transition: "all 0.6s ease 0.1s",
        }}>
          {/* Background glow */}
          <div style={{
            position: "absolute", top: -50, right: -50,
            width: 200, height: 200, borderRadius: "50%",
            background: "radial-gradient(circle, " + trendConfig.glow + " 0%, transparent 70%)",
            pointerEvents: "none",
          }} />

          <div style={{
            fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.4)",
            textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8,
          }}>
            Grace Composite Index
          </div>

          <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 4 }}>
            <span style={{
              fontSize: 48, fontWeight: 700, letterSpacing: "-0.03em",
              color: t.text || "#E2E8F0",
            }}>
              {current ? current.gci.toFixed(1) : "--"}
            </span>
            <span style={{ fontSize: 20, fontWeight: 600, color: trendConfig.color }}>
              {trendConfig.arrow + " " + trendConfig.label}
            </span>
          </div>

          {current && current.gci_slope_7d && (
            <div style={{ fontSize: 13, color: "rgba(255,255,255,0.4)", marginBottom: 12 }}>
              {"7-day slope: " + (current.gci_slope_7d > 0 ? "+" : "") + current.gci_slope_7d.toFixed(2) + " pts/day"}
            </div>
          )}

          {/* Sub-indexes */}
          {current && (
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {[
                { label: "Consumer Stress", value: current.csi, color: "#F85149" },
                { label: "Spending Pressure", value: current.dpi, color: "#D29922" },
                { label: "Financial Resilience", value: current.frs, color: "#3FB950" },
              ].map(function (sub) {
                return (
                  <div key={sub.label} style={{
                    padding: "6px 12px", borderRadius: 8,
                    background: sub.color + "10",
                    border: "1px solid " + sub.color + "20",
                  }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: sub.color, marginBottom: 2 }}>
                      {sub.label}
                    </div>
                    <div style={{ fontSize: 16, fontWeight: 600, color: t.text || "#E2E8F0" }}>
                      {sub.value.toFixed(1)}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          <div style={{
            marginTop: 12, fontSize: 11, color: "rgba(255,255,255,0.25)",
            display: "flex", justifyContent: "space-between",
          }}>
            <span>{lastUpdatedStr ? "Last updated: " + lastUpdatedStr : "No data published yet"}</span>
            <span>
              {"Next update: " + (summary ? summary.next_update_window : "...")}
              {sse.connected && (
                <span style={{ color: "#D29922", marginLeft: 8 }}>{"\u25CF"} Beta</span>
              )}
            </span>
          </div>
        </div>

        {/* 30-Day Chart */}
        {chartData.length > 1 && (
          <div style={{
            padding: "20px",
            borderRadius: 14,
            background: "rgba(17, 24, 39, 0.6)",
            border: "1px solid rgba(255,255,255,0.06)",
            marginBottom: 20,
            opacity: mounted ? 1 : 0,
            transition: "all 0.6s ease 0.2s",
          }}>
            <div style={{
              fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.4)",
              textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12,
            }}>
              30-Day Trend
            </div>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="gciGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22D3A7" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22D3A7" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  tick={{ fill: "rgba(255,255,255,0.2)", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={function (d) {
                    return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                  }}
                />
                <YAxis hide domain={["dataMin - 5", "dataMax + 5"]} />
                <Tooltip
                  contentStyle={{
                    background: "#1E293B", border: "1px solid #334155",
                    borderRadius: 8, fontSize: 12, color: "#E2E8F0",
                  }}
                  labelFormatter={function (d) {
                    return new Date(d).toLocaleDateString("en-US", {
                      weekday: "short", month: "short", day: "numeric",
                    })
                  }}
                  formatter={function (val) { return [val.toFixed(1), "GCI"] }}
                />
                <Area
                  type="monotone" dataKey="gci" stroke="#22D3A7" strokeWidth={2}
                  fill="url(#gciGradient)" dot={false} activeDot={{ r: 4, fill: "#22D3A7" }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Your Contribution Panel */}
        {contrib && contrib.status !== "none" && (
          <div style={{
            padding: "18px 20px",
            borderRadius: 14,
            background: "rgba(34, 211, 167, 0.04)",
            border: "1px solid rgba(34, 211, 167, 0.12)",
            marginBottom: 20,
            opacity: mounted ? 1 : 0,
            transition: "all 0.6s ease 0.3s",
          }}>
            <div style={{
              fontSize: 12, fontWeight: 600, color: "#22D3A7",
              textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 10,
            }}>
              Your Contribution
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <span style={{ fontSize: 18 }}>
                {contrib.status === "counted" ? "\u2705" : "\u23F3"}
              </span>
              <span style={{ fontSize: 14, fontWeight: 500, color: t.text || "#E2E8F0" }}>
                {contrib.status === "counted"
                  ? "Counted in today's update"
                  : "Queued for next update"}
              </span>
            </div>
            {contrib.expected_direction && (
              <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", marginLeft: 28 }}>
                {"Expected direction of influence: "}
                <span style={{
                  fontWeight: 600,
                  color: contrib.expected_direction === "up" ? "#3FB950"
                    : contrib.expected_direction === "down" ? "#D29922"
                    : "rgba(255,255,255,0.4)",
                }}>
                  {contrib.expected_direction === "up" ? "\u2191 Positive"
                    : contrib.expected_direction === "down" ? "\u2193 Negative"
                    : "\u2192 Neutral"}
                </span>
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.25)", marginLeft: 6 }}>
                  (based on your FCS score)
                </span>
              </div>
            )}
          </div>
        )}

        {/* Changelog */}
        {changelog.length > 0 && (
          <div style={{
            padding: "18px 20px",
            borderRadius: 14,
            background: "rgba(17, 24, 39, 0.6)",
            border: "1px solid rgba(255,255,255,0.06)",
            marginBottom: 20,
            opacity: mounted ? 1 : 0,
            transition: "all 0.6s ease 0.4s",
          }}>
            <div style={{
              fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.4)",
              textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 12,
            }}>
              What Changed Since Last Update
            </div>
            {changelog.map(function (entry, i) {
              var dirColor = entry.direction === "up" ? "#3FB950"
                : entry.direction === "down" ? "#F85149"
                : "rgba(255,255,255,0.4)"
              return (
                <div key={i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "8px 0",
                  borderBottom: i < changelog.length - 1 ? "1px solid rgba(255,255,255,0.04)" : "none",
                }}>
                  <span style={{ fontSize: 13, color: "rgba(255,255,255,0.7)" }}>
                    {entry.metric}
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: dirColor }}>
                    {(entry.direction === "up" ? "+" : entry.direction === "down" ? "-" : "") + entry.delta.toFixed(1)}
                    {" " + (entry.direction === "up" ? "\u2191" : entry.direction === "down" ? "\u2193" : "\u2192")}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {/* Privacy disclaimer */}
        <div style={{
          padding: "14px 16px",
          borderRadius: 12,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.04)",
          opacity: mounted ? 1 : 0,
          transition: "all 0.6s ease 0.5s",
        }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 6, marginBottom: 4,
          }}>
            <span style={{ fontSize: 13 }}>{"\uD83D\uDD12"}</span>
            <span style={{
              fontSize: 11, fontWeight: 600, color: "rgba(255,255,255,0.35)",
              textTransform: "uppercase", letterSpacing: "0.04em",
            }}>
              Privacy
            </span>
          </div>
          <p style={{
            fontSize: 12, color: "rgba(255,255,255,0.3)", lineHeight: 1.5, margin: 0,
          }}>
            The GCI aggregates anonymous check-in data across all GraceFinance users.
            No individual data is identifiable. Your personal scores are visible only to you.
            The Index reflects community-wide financial sentiment — not any single person's situation.
          </p>
        </div>

        {/* Contributors badge */}
        {summary && summary.active_contributors_today > 0 && (
          <div style={{
            textAlign: "center", marginTop: 16,
            fontSize: 11, color: "rgba(255,255,255,0.2)",
          }}>
            {summary.active_contributors_today + " people checked in today"}
          </div>
        )}
      </div>
    </div>
  )
}