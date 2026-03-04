/**
 * IndexPage — Institutional Redesign
 *
 * Bloomberg-inspired. Data-dense, monochrome.
 * No glows, no colored badges. Just the numbers.
 */

import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import useIndexSSE from "../hooks/useIndexSSE"
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts"

var C = {
  bg: "#000000", card: "#0a0a0a", border: "#1a1a1a",
  text: "#ffffff", muted: "#666666", dim: "#444444", faint: "#333333",
}
var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

var API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000")

function apiFetch(endpoint) {
  var token = localStorage.getItem("grace_token")
  var headers = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = "Bearer " + token
  return fetch(API_BASE + endpoint, { headers: headers }).then(function (res) {
    if (!res.ok) throw new Error("Failed: " + endpoint)
    return res.json()
  })
}

function Nav(props) {
  var items = [
    { id: "dashboard", label: "Dashboard", path: "/dashboard" },
    { id: "grace", label: "Grace AI", path: "/grace" },
    { id: "index", label: "Index", path: "/index" },
    { id: "profile", label: "Profile", path: "/profile" },
    { id: "settings", label: "Settings", path: "/settings" },
  ]
  return (
    <div style={{ display: "flex", gap: 0, borderBottom: "1px solid " + C.border, marginBottom: 32 }}>
      {items.map(function (item) {
        var isActive = props.active === item.id
        return (
          <button key={item.id} onClick={function () { props.navigate(item.path) }} style={{
            padding: "12px 20px", fontSize: 13, fontWeight: isActive ? 600 : 400,
            fontFamily: FONT, color: isActive ? C.text : C.dim, background: "transparent",
            border: "none", borderBottom: isActive ? "1px solid " + C.text : "1px solid transparent",
            cursor: "pointer", transition: "color 0.2s ease", letterSpacing: "0.01em", marginBottom: -1,
          }}>{item.label}</button>
        )
      })}
    </div>
  )
}

var TREND_CONFIG = {
  UP: { label: "Up" }, DOWN: { label: "Down" }, FLAT: { label: "Flat" },
}

export default function IndexPage() {
  var auth = useAuth()
  var logout = auth.logout
  var navigate = useNavigate()
  var mountedState = useState(false)
  var mounted = mountedState[0]; var setMounted = mountedState[1]
  var summaryState = useState(null)
  var summary = summaryState[0]; var setSummary = summaryState[1]
  var historyState = useState([])
  var history = historyState[0]; var setHistory = historyState[1]
  var sse = useIndexSSE()

  useEffect(function () { setMounted(true); loadData() }, [])
  useEffect(function () { if (sse.indexData) loadData() }, [sse.lastUpdated])

  function loadData() {
    apiFetch("/api/v1/index/summary").then(function (d) { setSummary(d) }).catch(function () {})
    apiFetch("/api/v1/index/history?range=30d").then(function (d) { if (d && d.data) setHistory(d.data) }).catch(function () {})
  }

  var current = summary ? summary.current : null
  var trend = current ? current.trend_direction : "FLAT"
  var trendConfig = TREND_CONFIG[trend] || TREND_CONFIG.FLAT
  var contrib = summary ? summary.user_contribution : null
  var changelog = summary ? summary.changelog : []
  var lastUpdatedStr = ""
  if (summary && summary.last_updated_at) {
    var d = new Date(summary.last_updated_at)
    lastUpdatedStr = d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + " " + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  }
  var chartData = history.map(function (item) { return { date: item.date, gci: item.gci ? parseFloat(item.gci) : null } })

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: FONT }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');"}</style>
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "24px 24px 60px" }}>

        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, opacity: mounted ? 1 : 0, transition: "opacity 0.5s ease" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 28, height: 28, border: "1.5px solid " + C.text, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700 }}>G</div>
            <span style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.02em" }}>GraceFinance</span>
          </div>
          <button onClick={function () { logout(); navigate("/login") }} style={{ padding: "6px 14px", fontSize: 12, fontWeight: 500, fontFamily: FONT, cursor: "pointer", background: "transparent", border: "1px solid " + C.border, borderRadius: 6, color: C.dim, transition: "all 0.2s" }}
            onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
            onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
          >Sign out</button>
        </div>

        <p style={{ fontSize: 12, color: C.dim, margin: "0 0 20px", letterSpacing: "0.02em" }}>Grace Composite Index</p>
        <Nav navigate={navigate} active="index" />

        {/* Hero */}
        <div style={{ padding: "32px 28px", borderRadius: 10, background: C.card, border: "1px solid " + C.border, marginBottom: 16, opacity: mounted ? 1 : 0, transition: "opacity 0.6s ease 0.1s" }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>GCI Composite</div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginBottom: 8 }}>
            <span style={{ fontSize: 56, fontWeight: 300, letterSpacing: "-0.04em", color: C.text, fontVariantNumeric: "tabular-nums" }}>{current ? current.gci.toFixed(1) : "—"}</span>
            <span style={{ fontSize: 16, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.06em" }}>{trendConfig.label}</span>
          </div>
          {current && current.gci_slope_7d && (
            <div style={{ fontSize: 13, color: C.dim, marginBottom: 16 }}>7d slope: {(current.gci_slope_7d > 0 ? "+" : "") + current.gci_slope_7d.toFixed(2)} pts/day</div>
          )}
          {current && (
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {[{ label: "CSI", value: current.csi }, { label: "DPI", value: current.dpi }, { label: "FRS", value: current.frs }].map(function (sub) {
                return (
                  <div key={sub.label} style={{ padding: "8px 14px", borderRadius: 6, background: C.bg, border: "1px solid " + C.border }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: C.dim, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2 }}>{sub.label}</div>
                    <div style={{ fontSize: 18, fontWeight: 600, color: C.text, fontVariantNumeric: "tabular-nums" }}>{sub.value.toFixed(1)}</div>
                  </div>
                )
              })}
            </div>
          )}
          <div style={{ marginTop: 16, fontSize: 11, color: C.faint, display: "flex", justifyContent: "space-between" }}>
            <span>{lastUpdatedStr ? "Updated " + lastUpdatedStr : "No data published yet"}</span>
            <span>{summary ? "Next: " + summary.next_update_window : ""}{sse.connected && <span style={{ color: C.muted, marginLeft: 8 }}>Beta</span>}</span>
          </div>
        </div>

        {/* Chart */}
        {chartData.length > 1 && (
          <div style={{ padding: 20, borderRadius: 10, background: C.card, border: "1px solid " + C.border, marginBottom: 16, opacity: mounted ? 1 : 0, transition: "opacity 0.6s ease 0.2s" }}>
            <div style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }}>30-Day Trend</div>
            <ResponsiveContainer width="100%" height={160}>
              <AreaChart data={chartData}>
                <defs><linearGradient id="gciGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ffffff" stopOpacity={0.08} /><stop offset="95%" stopColor="#ffffff" stopOpacity={0} /></linearGradient></defs>
                <XAxis dataKey="date" tick={{ fill: C.dim, fontSize: 10, fontFamily: FONT }} axisLine={false} tickLine={false} tickFormatter={function (d) { return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" }) }} />
                <YAxis hide domain={["dataMin - 5", "dataMax + 5"]} />
                <Tooltip contentStyle={{ background: "#111111", border: "1px solid " + C.border, borderRadius: 6, fontSize: 12, color: C.text, fontFamily: FONT }} labelFormatter={function (d) { return new Date(d).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }) }} formatter={function (val) { return [val.toFixed(1), "GCI"] }} />
                <Area type="monotone" dataKey="gci" stroke="#ffffff" strokeWidth={1.5} fill="url(#gciGrad)" dot={false} activeDot={{ r: 3, fill: "#ffffff" }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Contribution */}
        {contrib && contrib.status !== "none" && (
          <div style={{ padding: "18px 20px", borderRadius: 10, background: C.card, border: "1px solid " + C.border, marginBottom: 16, opacity: mounted ? 1 : 0, transition: "opacity 0.6s ease 0.3s" }}>
            <div style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10 }}>Your Contribution</div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: contrib.status === "counted" ? C.text : C.dim, display: "inline-block" }} />
              <span style={{ fontSize: 14, fontWeight: 500, color: C.text }}>{contrib.status === "counted" ? "Counted in today's update" : "Queued for next update"}</span>
            </div>
            {contrib.expected_direction && (
              <div style={{ fontSize: 13, color: C.dim, marginLeft: 16 }}>
                Expected: <span style={{ fontWeight: 600, color: C.text }}>{contrib.expected_direction === "up" ? "Positive" : contrib.expected_direction === "down" ? "Negative" : "Neutral"}</span>
              </div>
            )}
          </div>
        )}

        {/* Changelog */}
        {changelog.length > 0 && (
          <div style={{ padding: "18px 20px", borderRadius: 10, background: C.card, border: "1px solid " + C.border, marginBottom: 16, opacity: mounted ? 1 : 0, transition: "opacity 0.6s ease 0.4s" }}>
            <div style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>Changes</div>
            {changelog.map(function (entry, i) {
              return (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: i < changelog.length - 1 ? "1px solid " + C.border : "none" }}>
                  <span style={{ fontSize: 13, color: C.muted }}>{entry.metric}</span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: C.text, fontVariantNumeric: "tabular-nums" }}>{(entry.direction === "up" ? "+" : entry.direction === "down" ? "-" : "") + entry.delta.toFixed(1)}</span>
                </div>
              )
            })}
          </div>
        )}

        {/* Privacy */}
        <div style={{ padding: "14px 16px", borderRadius: 10, background: C.card, border: "1px solid " + C.border, opacity: mounted ? 1 : 0, transition: "opacity 0.6s ease 0.5s" }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: C.dim, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Privacy</div>
          <p style={{ fontSize: 12, color: C.faint, lineHeight: 1.6, margin: 0 }}>The GCI aggregates anonymous check-in data. No individual data is identifiable. Your scores are visible only to you.</p>
        </div>

        {summary && summary.active_contributors_today > 0 && (
          <div style={{ textAlign: "center", marginTop: 16, fontSize: 11, color: C.faint }}>{summary.active_contributors_today} checked in today</div>
        )}

        <div style={{ borderTop: "1px solid " + C.border, paddingTop: 20, textAlign: "center", marginTop: 32 }}>
          <p style={{ color: C.dim, fontSize: 11, margin: 0, letterSpacing: "0.02em" }}>GraceFinance — The Behavioral Finance Company</p>
        </div>
      </div>
    </div>
  )
}