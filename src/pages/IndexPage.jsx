/**
 * IndexPage — v5.2
 * ADDED: Live polling every 30 seconds — all users see real-time index updates
 * ADDED: Live indicator dot + pulse animation on value change
 * ADDED: "Last updated X seconds ago" live counter
 */

import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from "recharts"

var C = {
  bg: "#000000", card: "#0a0a0a", border: "#1a1a1a",
  text: "#ffffff", muted: "#9ca3af", dim: "#6b7280", faint: "#4b5563",
  green: "#10b981",
}
var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"
var POLL_INTERVAL = 30000 // 30 seconds

var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'

function apiFetch(endpoint, options) {
  var token = localStorage.getItem("grace_token")
  var headers = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = "Bearer " + token
  var config = { headers: headers }
  if (options) {
    for (var k in options) {
      if (k === "headers") {
        for (var h in options.headers) headers[h] = options.headers[h]
      } else { config[k] = options[k] }
    }
  }
  config.headers = headers
  return fetch(API_BASE + endpoint, config).then(function (res) {
    if (!res.ok) throw new Error("Failed: " + endpoint)
    return res.json()
  })
}

function Card(props) {
  return (<div style={{ background: C.card, border: "1px solid " + C.border, borderRadius: 12, padding: 24, ...(props.style || {}) }}>{props.children}</div>)
}
function Label(props) {
  return (<span style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: FONT, ...(props.style || {}) }}>{props.children}</span>)
}

function ConfidenceBadge(props) {
  var count = props.userCount || 0
  var tier = "Preview"
  var color = C.faint
  var borderColor = "#333333"

  if (count >= 200) {
    tier = "Published"
    color = "#22c55e"
    borderColor = "#166534"
  } else if (count >= 50) {
    tier = "Beta"
    color = "#eab308"
    borderColor = "#854d0e"
  }

  return (
    <span style={{
      display: "inline-block", fontSize: 10, fontWeight: 600, color: color,
      border: "1px solid " + borderColor, borderRadius: 4, padding: "2px 8px",
      textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: FONT,
    }}>{tier}</span>
  )
}

function LiveIndicator(props) {
  var secondsAgo = props.secondsAgo
  var label = "Live"
  if (secondsAgo !== null && secondsAgo > 5) {
    if (secondsAgo < 60) label = secondsAgo + "s ago"
    else label = Math.floor(secondsAgo / 60) + "m ago"
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <style>{
        "@keyframes livePulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.3); } }"
      }</style>
      <div style={{
        width: 6, height: 6, borderRadius: "50%", background: C.green,
        animation: "livePulse 2s ease-in-out infinite",
      }} />
      <span style={{ fontSize: 10, color: C.green, fontFamily: FONT, fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.06em" }}>
        {label}
      </span>
    </div>
  )
}

function ValueFlash(props) {
  // Briefly flash when value changes
  var value = props.value
  var flashState = useState(false); var flash = flashState[0]; var setFlash = flashState[1]
  var prevRef = useRef(value)

  useEffect(function () {
    if (prevRef.current !== null && value !== null && prevRef.current !== value) {
      setFlash(true)
      var timer = setTimeout(function () { setFlash(false) }, 800)
      prevRef.current = value
      return function () { clearTimeout(timer) }
    }
    prevRef.current = value
  }, [value])

  return (
    <span style={{
      fontSize: 64, fontWeight: 200, letterSpacing: "-0.04em", color: C.text,
      fontVariantNumeric: "tabular-nums", lineHeight: 1,
      transition: "color 0.3s ease",
      textShadow: flash ? "0 0 20px rgba(16,185,129,0.4)" : "none",
    }}>
      {value != null ? value.toFixed(1) : "..."}
    </span>
  )
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

function getTrendLabel(direction) {
  if (direction === "UP") return "Rising"
  if (direction === "DOWN") return "Declining"
  return "Holding Steady"
}

function getIndexHealthLabel(value) {
  if (value >= 75) return "Population confidence is high. Financial behavior is stable and forward-looking."
  if (value >= 60) return "Confidence is solid. Most users are managing their finances with intention."
  if (value >= 45) return "Mixed signals. Some users are building, others are under pressure."
  if (value >= 30) return "Confidence is stressed. Behavioral indicators show increasing caution."
  return "Elevated financial stress across the population."
}

export default function IndexPage() {
  var auth = useAuth(); var logout = auth.logout; var navigate = useNavigate()
  var mountedState = useState(false); var mounted = mountedState[0]; var setMounted = mountedState[1]
  var latestState = useState(null); var latest = latestState[0]; var setLatest = latestState[1]
  var historyState = useState([]); var history = historyState[0]; var setHistory = historyState[1]
  var loadingState = useState(true); var loading = loadingState[0]; var setLoading = loadingState[1]
  var methodologyState = useState(null); var methodology = methodologyState[0]; var setMethodology = methodologyState[1]
  var showMethodState = useState(false); var showMethod = showMethodState[0]; var setShowMethod = showMethodState[1]

  // Live polling state
  var lastFetchState = useState(null); var lastFetch = lastFetchState[0]; var setLastFetch = lastFetchState[1]
  var secondsAgoState = useState(null); var secondsAgo = secondsAgoState[0]; var setSecondsAgo = secondsAgoState[1]

  useEffect(function () { setMounted(true); loadData() }, [])

  // ── Live polling: refresh index every 30 seconds ──
  useEffect(function () {
    var pollTimer = setInterval(function () {
      apiFetch("/index/latest").then(function (data) {
        if (data) { setLatest(data); setLastFetch(Date.now()) }
      }).catch(function () {})
    }, POLL_INTERVAL)

    return function () { clearInterval(pollTimer) }
  }, [])

  // ── "X seconds ago" counter ──
  useEffect(function () {
    var tickTimer = setInterval(function () {
      if (lastFetch) {
        setSecondsAgo(Math.floor((Date.now() - lastFetch) / 1000))
      }
    }, 1000)

    return function () { clearInterval(tickTimer) }
  }, [lastFetch])

  function loadData() {
    setLoading(true)
    Promise.all([
      apiFetch("/index/latest").catch(function () { return null }),
      apiFetch("/index/history?days=30").catch(function () { return { data_points: [] } }),
    ]).then(function (results) {
      setLatest(results[0])
      setHistory(results[1] ? results[1].data_points || [] : [])
      setLoading(false)
      setLastFetch(Date.now())
    })
  }

  function loadMethodology() {
    if (methodology) { setShowMethod(!showMethod); return }
    apiFetch("/index/methodology").then(function (data) { setMethodology(data); setShowMethod(true) }).catch(function () {})
  }

  var clickCountState = useState(0); var clickCount = clickCountState[0]; var setClickCount = clickCountState[1]
  function handleLabelClick() {
    var newCount = clickCount + 1
    setClickCount(newCount)
    if (newCount >= 3) {
      setClickCount(0)
      apiFetch("/index/compute", { method: "POST" }).then(function () { loadData() }).catch(function () {})
    }
    setTimeout(function () { setClickCount(0) }, 1500)
  }

  var hasData = latest && latest.published === true
  var gfci = hasData ? latest.gfci_composite : null
  var fcsAvg = hasData ? latest.fcs_average : null
  var userCount = hasData ? latest.user_count : 0
  var contributors = hasData && latest.contributors ? latest.contributors : userCount
  var trend = hasData ? latest.trend_direction || "FLAT" : "FLAT"
  var slope3d = hasData ? latest.gci_slope_3d : null
  var slope7d = hasData ? latest.gci_slope_7d : null
  var volatility = hasData ? latest.gci_volatility_7d : null

  var chartData = history.map(function (item) {
    return { date: item.date, gfci: item.gfci ? parseFloat(item.gfci) : null }
  }).filter(function (d) { return d.gfci != null })

  var chartAvg = chartData.length > 0
    ? Math.round(chartData.reduce(function (a, b) { return a + b.gfci }, 0) / chartData.length * 10) / 10
    : null

  var lastUpdated = ""
  if (hasData && latest.index_date) {
    var d = new Date(latest.index_date)
    lastUpdated = d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
  }

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: FONT }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');"}</style>
      <div style={{ maxWidth: 800, margin: "0 auto", padding: "24px 24px 60px" }}>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, opacity: mounted ? 1 : 0, transition: "opacity 0.5s ease" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 28, height: 28, border: "1.5px solid " + C.text, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700 }}>G</div>
            <span style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.02em" }}>GraceFinance</span>
          </div>
          <button onClick={function () { logout(); navigate("/login") }} style={{
            padding: "6px 14px", fontSize: 12, fontWeight: 500, fontFamily: FONT, cursor: "pointer", background: "transparent",
            border: "1px solid " + C.border, borderRadius: 6, color: C.dim, transition: "all 0.2s",
          }}
            onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
            onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
          >Sign out</button>
        </div>

        <p style={{ fontSize: 12, color: C.dim, margin: "0 0 20px", letterSpacing: "0.02em" }}>The GraceFinance Composite Index</p>
        <Nav navigate={navigate} active="index" />

        {/* HERO */}
        <Card style={{ marginBottom: 16, padding: "36px 28px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div onClick={handleLabelClick} style={{ cursor: "default" }}>
                <Label>GraceFinance Composite Index</Label>
              </div>
              <ConfidenceBadge userCount={userCount} />
            </div>
            {hasData && <LiveIndicator secondsAgo={secondsAgo} />}
          </div>

          <div style={{ display: "flex", alignItems: "baseline", gap: 16, marginTop: 20, marginBottom: 8 }}>
            <ValueFlash value={gfci} />
            <span style={{ fontSize: 16, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              {hasData ? getTrendLabel(trend) : ""}
            </span>
          </div>

          {gfci != null && (
            <p style={{ fontSize: 13, color: C.dim, margin: "0 0 24px", lineHeight: 1.7 }}>
              {getIndexHealthLabel(gfci)}
            </p>
          )}

          {!hasData && (
            <p style={{ fontSize: 13, color: C.dim, margin: "0 0 24px", lineHeight: 1.7 }}>
              The GraceFinance Composite Index aggregates Financial Confidence Scores across all users into a single real-time indicator. As more people check in, this number becomes a window into how the population really feels about money.
            </p>
          )}

          {hasData && (
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
              {[
                { label: "Avg FCS", value: fcsAvg, decimals: 1 },
                { label: "Contributors", value: contributors, decimals: 0 },
                { label: "3d Trend", value: slope3d, decimals: 3, showSign: true },
                { label: "7d Trend", value: slope7d, decimals: 3, showSign: true },
                { label: "Volatility", value: volatility, decimals: 3 },
              ].map(function (item) {
                var display = "..."
                if (item.value != null) {
                  var formatted = item.decimals > 0 ? item.value.toFixed(item.decimals) : String(item.value)
                  if (item.showSign && item.value > 0) formatted = "+" + formatted
                  display = formatted
                }
                return (
                  <div key={item.label} style={{ padding: "10px 14px", borderRadius: 8, background: C.bg, border: "1px solid " + C.border }}>
                    <div style={{ fontSize: 10, fontWeight: 500, color: C.dim, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 3 }}>{item.label}</div>
                    <div style={{ fontSize: 16, fontWeight: 600, color: C.text, fontVariantNumeric: "tabular-nums" }}>{display}</div>
                  </div>
                )
              })}
            </div>
          )}

          <div style={{ fontSize: 11, color: C.faint, display: "flex", justifyContent: "space-between" }}>
            <span>{lastUpdated ? "Published " + lastUpdated : "Waiting for first computation"}</span>
            <span>{contributors > 0 ? contributors + " active contributor" + (contributors > 1 ? "s" : "") : ""}</span>
          </div>
        </Card>

        {/* CONFIDENCE TIER EXPLANATION */}
        {hasData && userCount < 200 && (
          <Card style={{ marginBottom: 16, padding: "14px 20px" }}>
            <div style={{ fontSize: 11, fontWeight: 500, color: C.dim, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>Index Confidence</div>
            <p style={{ fontSize: 12, color: C.faint, lineHeight: 1.7, margin: 0 }}>
              {userCount < 50
                ? "The Composite Index is in Preview mode. With fewer than 50 active contributors, the index is directional only and may not represent broader population confidence. As the user base grows, the signal strengthens."
                : "The Composite Index is in Beta. With " + userCount + " active contributors, the index provides a meaningful directional signal among engaged GraceFinance users. At 200+ contributors, the index reaches Published status."
              }
            </p>
          </Card>
        )}

        {/* TREND CHART */}
        {chartData.length > 1 ? (
          <Card style={{ marginBottom: 16, padding: 20 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <Label>30-Day Trend</Label>
              {chartAvg && (
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 18, fontWeight: 600, color: C.text, fontFamily: FONT, fontVariantNumeric: "tabular-nums" }}>{chartAvg}</div>
                  <div style={{ fontSize: 10, color: C.dim, textTransform: "uppercase", letterSpacing: "0.06em" }}>Period Avg</div>
                </div>
              )}
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gfciGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ffffff" stopOpacity={0.08} />
                    <stop offset="95%" stopColor="#ffffff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" tick={{ fill: C.dim, fontSize: 10, fontFamily: FONT }} axisLine={{ stroke: C.border }} tickLine={false}
                  tickFormatter={function (d) { return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" }) }} />
                <YAxis domain={[0, 100]} tick={{ fill: C.dim, fontSize: 10, fontFamily: FONT }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: "#111111", border: "1px solid " + C.border, borderRadius: 8, padding: "8px 12px", fontFamily: FONT }}
                  labelStyle={{ color: C.muted, fontSize: 11 }} itemStyle={{ color: C.text, fontSize: 13, fontWeight: 600 }}
                  labelFormatter={function (d) { return new Date(d).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" }) }}
                  formatter={function (val) { return [val.toFixed(1), "Composite Index"] }} />
                {chartAvg && <ReferenceLine y={chartAvg} stroke={C.faint} strokeDasharray="4 4" />}
                <Area type="monotone" dataKey="gfci" stroke="#ffffff" strokeWidth={1.5} fill="url(#gfciGrad)"
                  dot={{ r: 2, fill: "#ffffff", stroke: C.bg, strokeWidth: 2 }}
                  activeDot={{ r: 4, stroke: "#ffffff", strokeWidth: 1, fill: C.bg }} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        ) : (
          <Card style={{ marginBottom: 16 }}>
            <Label>30-Day Trend</Label>
            <p style={{ fontSize: 13, color: C.dim, margin: "16px 0 0", lineHeight: 1.7 }}>
              {hasData
                ? "The trend chart will appear after two or more index computations. Each day adds a new data point."
                : "As users complete daily check-ins, the Composite Index builds a trend line showing how financial confidence moves over time. Like watching a market indicator, but for how people actually feel about money."
              }
            </p>
          </Card>
        )}

        {/* WHAT IS THE COMPOSITE INDEX */}
        <Card style={{ marginBottom: 16 }}>
          <Label>What is the Composite Index?</Label>
          <p style={{ fontSize: 14, color: C.muted, lineHeight: 1.8, margin: "16px 0 0" }}>
            The GraceFinance Composite Index is a macro-level signal that reflects aggregate financial confidence across the platform's user base. Individual FCS scores are stripped of all personally identifiable information, aggregated with all other user scores, and processed into a single composite metric.
          </p>
          <p style={{ fontSize: 13, color: C.dim, lineHeight: 1.7, margin: "12px 0 0" }}>
            Traditional indicators like the Consumer Confidence Index ask people how they feel. The Composite Index measures what people do: whether they're paying bills on time, building savings, managing debt, or pulling back on spending. Every daily check-in from every user contributes an anonymized signal. The result is a financial confidence reading as close to real-time as it gets.
          </p>
        </Card>

        {/* METHODOLOGY */}
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", cursor: "pointer" }} onClick={loadMethodology}>
            <Label>Methodology</Label>
            <span style={{ fontSize: 12, color: C.dim }}>{showMethod ? "Hide" : "View"}</span>
          </div>

          {showMethod && methodology && (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 13, color: C.muted, lineHeight: 1.7, margin: "0 0 16px" }}>{methodology.description}</p>
              <div style={{ fontSize: 12, color: C.dim, marginBottom: 8 }}>Version {methodology.version}. Computed {methodology.computation_schedule}</div>

              {methodology.scoring_engine && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>FCS Pillars</div>
                  {Object.entries(methodology.scoring_engine.pillars).map(function (entry) {
                    var key = entry[0]; var val = entry[1]
                    return (<div key={key} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid " + C.border }}>
                      <span style={{ fontSize: 12, color: C.muted }}>{key.replace(/_/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase() })}</span>
                      <span style={{ fontSize: 12, color: C.text, fontWeight: 500 }}>{Math.round(val.weight * 100)}%</span>
                    </div>)
                  })}
                </div>
              )}

              {methodology.data_integrity && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>Signal Integrity</div>
                  {methodology.data_integrity.map(function (item, i) {
                    return (<div key={i} style={{ fontSize: 12, color: C.dim, padding: "4px 0", borderBottom: i < methodology.data_integrity.length - 1 ? "1px solid " + C.border : "none" }}>{item}</div>)
                  })}
                </div>
              )}
            </div>
          )}
        </Card>

        {/* PRIVACY */}
        <Card style={{ marginBottom: 16, padding: "16px 20px" }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: C.dim, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Privacy and Data</div>
          <p style={{ fontSize: 12, color: C.faint, lineHeight: 1.7, margin: 0 }}>
            The Composite Index is built from anonymized behavioral data. No individual user can be identified from the index. Your Financial Confidence Score is visible only to you. The index reflects collective patterns, never individual behavior.
          </p>
        </Card>

        <div style={{ borderTop: "1px solid " + C.border, paddingTop: 20, textAlign: "center", marginTop: 32 }}>
          <p style={{ color: C.dim, fontSize: 11, margin: 0, letterSpacing: "0.02em" }}>GraceFinance. Where Financial Confidence Is Measured.</p>
        </div>
      </div>
    </div>
  )
}