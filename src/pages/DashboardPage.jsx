/**
 * DashboardPage — v5 Polish
 *
 * Tone: Warm, empowering, premium. FCS is THE indicator.
 * Design: Monochrome. Black/white. Data speaks.
 */

import { useState, useEffect } from "react"
import { useAuth } from "../context/AuthContext"
import { useNavigate } from "react-router-dom"
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid
} from "recharts"
import DailyCheckin from "../components/DailyCheckin"
import OnboardingPage from "./OnboardingPage"

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
    if (!res.ok) throw new Error("Failed to fetch " + endpoint)
    return res.json()
  })
}

var C = {
  bg: "#000000", card: "#0a0a0a", border: "#1a1a1a",
  text: "#ffffff", muted: "#666666", dim: "#444444", faint: "#333333",
  accent: "#e8e8e8",
}
var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

var dimensionLabels = {
  current_stability: "Stability", future_outlook: "Outlook",
  purchasing_power: "Purchasing Power", emergency_readiness: "Emergency Readiness",
  financial_agency: "Financial Agency",
}
var dimensionWeights = {
  current_stability: 0.30, future_outlook: 0.25,
  purchasing_power: 0.20, emergency_readiness: 0.15, financial_agency: 0.10,
}
var dimensionTips = {
  current_stability: "Automate your biggest bill this week. One less thing to think about builds real stability.",
  future_outlook: "Set one 90-day financial target. People who write goals down are 42% more likely to hit them.",
  purchasing_power: "Notice where your money goes this week — awareness alone shifts spending patterns.",
  emergency_readiness: "Move even $10 to a separate account today. The habit matters more than the amount.",
  financial_agency: "Spend 5 minutes reviewing your finances this week. Small actions compound into confidence.",
}

function getScoreLabel(score) {
  if (score >= 80) return "Thriving"
  if (score >= 65) return "Strong"
  if (score >= 50) return "Building"
  if (score >= 35) return "Growing"
  if (score >= 20) return "Emerging"
  return "Starting"
}

function getScoreMessage(score) {
  if (score >= 80) return "You're in a strong position. Let's keep the momentum going."
  if (score >= 65) return "Solid foundation — you're more financially aware than most people."
  if (score >= 50) return "You're building something real. Small consistent moves compound over time."
  if (score >= 35) return "You're in the arena and showing up. That's where change starts."
  if (score >= 20) return "Tough stretch — but the fact that you're here says everything."
  return "Every journey starts with a first step. You just took yours."
}

function Card(props) {
  return (<div style={{ background: C.card, border: "1px solid " + C.border, borderRadius: 12, padding: 24, ...(props.style || {}) }}>{props.children}</div>)
}
function Label(props) {
  return (<span style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: FONT }}>{props.children}</span>)
}

function AnimatedNumber(props) {
  var val = props.value; var decimals = props.decimals || 0
  var s = useState(0); var display = s[0]; var setDisplay = s[1]
  useEffect(function () {
    var start = Date.now()
    function animate() {
      var elapsed = Date.now() - start
      var progress = Math.min(elapsed / 800, 1)
      var eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(val * eased)
      if (progress < 1) requestAnimationFrame(animate)
    }
    animate()
  }, [val])
  return <span>{decimals > 0 ? display.toFixed(decimals) : Math.round(display)}</span>
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

function FCSScore(props) {
  var score = props.score; var trend = props.trend; var checkinCount = props.checkinCount || 0
  var label = score != null ? getScoreLabel(score) : "—"
  var radius = 58; var circumference = 2 * Math.PI * radius
  var offset = circumference - ((score != null ? score : 0) / 100) * circumference

  return (
    <Card style={{ textAlign: "center", padding: "36px 24px" }}>
      <Label>Financial Confidence Score</Label>
      <div style={{ position: "relative", width: 132, height: 132, margin: "24px auto 20px" }}>
        <svg width="132" height="132" style={{ position: "absolute", top: 0, left: 0 }}>
          <circle cx="66" cy="66" r={radius} fill="none" stroke={C.border} strokeWidth="4" />
          <circle cx="66" cy="66" r={radius} fill="none" stroke={C.text} strokeWidth="4" strokeLinecap="round"
            strokeDasharray={circumference} strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)", transform: "rotate(-90deg)", transformOrigin: "50% 50%" }} />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 36, fontWeight: 300, color: C.text, letterSpacing: "-0.03em", fontFamily: FONT, fontVariantNumeric: "tabular-nums" }}>
            {score != null ? <AnimatedNumber value={score} decimals={1} /> : <span style={{ color: C.dim }}>—</span>}
          </span>
          <span style={{ fontSize: 10, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.1em", marginTop: 2 }}>{label}</span>
        </div>
      </div>
      {trend !== null && trend !== undefined && (
        <div style={{ fontSize: 13, color: C.muted, fontFamily: FONT, marginBottom: 4 }}>
          <span style={{ color: C.text, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
            {trend >= 0 ? "+" : ""}{typeof trend === "number" ? trend.toFixed(1) : trend}
          </span>
          <span style={{ marginLeft: 6 }}>since last check-in</span>
        </div>
      )}
      <p style={{ fontSize: 13, color: C.dim, margin: "12px 0 0", lineHeight: 1.7, fontFamily: FONT }}>
        {score != null ? getScoreMessage(score) : "Your Financial Confidence Score will appear after your first check-in."}
      </p>
      {checkinCount > 0 && (
        <p style={{ fontSize: 11, color: C.faint, marginTop: 8, fontFamily: FONT }}>
          Calculated from {checkinCount} responses this week
        </p>
      )}
    </Card>
  )
}

function QuickStats(props) {
  var score = props.score; var checkins = props.checkinCount; var streak = props.streak
  var stats = [
    { label: "FCS", value: score != null ? score.toFixed(1) : "—", sub: score != null ? getScoreLabel(score) : "Check in to start" },
    { label: "Streak", value: streak != null && streak > 0 ? streak + "d" : "0d", sub: streak != null && streak > 0 ? "consecutive days" : "Check in to start" },
    { label: "This Week", value: checkins != null ? String(checkins) : "0", sub: "check-ins completed" },
  ]
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
      {stats.map(function (s) {
        return (
          <Card key={s.label} style={{ padding: "20px" }}>
            <Label>{s.label}</Label>
            <div style={{ fontSize: 28, fontWeight: 600, color: C.text, letterSpacing: "-0.03em", marginTop: 8, fontFamily: FONT, fontVariantNumeric: "tabular-nums" }}>{s.value}</div>
            <div style={{ fontSize: 12, color: C.dim, marginTop: 4, fontFamily: FONT }}>{s.sub}</div>
          </Card>
        )
      })}
    </div>
  )
}

function DimensionBreakdown(props) {
  var metrics = props.metrics || {}
  var dims = ["current_stability", "future_outlook", "purchasing_power", "emergency_readiness", "financial_agency"]
  var weakest = null; var weakestScore = 1.0
  dims.forEach(function (d) { var val = metrics[d]; if (val != null && val < weakestScore) { weakestScore = val; weakest = d } })
  var hasData = dims.some(function (d) { return metrics[d] != null })

  if (!hasData) {
    return (
      <Card>
        <Label>Your Dimensions</Label>
        <p style={{ fontSize: 13, color: C.dim, margin: "16px 0 0", lineHeight: 1.7, fontFamily: FONT }}>
          Your confidence is measured across five dimensions. Complete a check-in to see how you're doing in each area.
        </p>
      </Card>
    )
  }

  return (
    <Card>
      <div style={{ marginBottom: 20 }}><Label>Your Dimensions</Label></div>
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {dims.map(function (dim) {
          var val = metrics[dim]; var pct = val != null ? Math.round(val * 100) : null
          var weight = Math.round(dimensionWeights[dim] * 100)
          return (
            <div key={dim}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ color: C.text, fontSize: 13, fontWeight: 500, fontFamily: FONT }}>{dimensionLabels[dim]}</span>
                  <span style={{ fontSize: 10, color: C.dim, fontFamily: FONT }}>{weight}%</span>
                </div>
                <span style={{ color: pct != null ? C.text : C.dim, fontSize: 14, fontWeight: 600, fontFamily: FONT, fontVariantNumeric: "tabular-nums" }}>{pct != null ? pct : "—"}</span>
              </div>
              <div style={{ height: 4, background: C.border, borderRadius: 2, overflow: "hidden" }}>
                <div style={{ height: "100%", width: (pct != null ? pct : 0) + "%", background: C.text, borderRadius: 2, transition: "width 1s ease", opacity: pct != null ? (pct > 60 ? 1 : pct > 30 ? 0.6 : 0.35) : 0 }} />
              </div>
            </div>
          )
        })}
      </div>
      {weakest && weakestScore < 0.5 && (
        <div style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid " + C.border }}>
          <div style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6, fontFamily: FONT }}>
            Your next move — {dimensionLabels[weakest]}
          </div>
          <p style={{ fontSize: 13, color: C.dim, margin: 0, lineHeight: 1.7, fontFamily: FONT }}>{dimensionTips[weakest]}</p>
        </div>
      )}
    </Card>
  )
}

function TrendChart(props) {
  var snapshots = props.snapshots || []
  if (snapshots.length < 2) {
    return (
      <Card>
        <Label>Your Confidence Over Time</Label>
        <p style={{ fontSize: 13, color: C.dim, margin: "16px 0 0", lineHeight: 1.7, fontFamily: FONT }}>
          Your trend line will appear after a few check-ins. Each day you show up adds a data point — and the pattern tells the real story.
        </p>
      </Card>
    )
  }
  var chartData = snapshots.map(function (s) { var d = new Date(s.computed_at); return { label: (d.getMonth() + 1) + "/" + d.getDate(), fcs: Math.round(s.fcs_composite * 10) / 10 } })
  var avg = Math.round(chartData.reduce(function (a, b) { return a + b.fcs }, 0) / chartData.length * 10) / 10

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <Label>Confidence Trend</Label>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 20, fontWeight: 600, color: C.text, fontFamily: FONT, fontVariantNumeric: "tabular-nums", letterSpacing: "-0.02em" }}>{avg}</div>
          <div style={{ fontSize: 10, color: C.dim, textTransform: "uppercase", letterSpacing: "0.06em" }}>30-Day Avg</div>
        </div>
      </div>
      <div style={{ height: 180 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
            <defs><linearGradient id="fcsGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ffffff" stopOpacity={0.08} /><stop offset="100%" stopColor="#ffffff" stopOpacity={0} /></linearGradient></defs>
            <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
            <XAxis dataKey="label" tick={{ fill: C.dim, fontSize: 10, fontFamily: FONT }} axisLine={{ stroke: C.border }} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fill: C.dim, fontSize: 10, fontFamily: FONT }} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={{ background: "#111111", border: "1px solid " + C.border, borderRadius: 8, padding: "8px 12px", fontFamily: FONT }} labelStyle={{ color: C.muted, fontSize: 11 }} itemStyle={{ color: C.text, fontSize: 13, fontWeight: 600 }} formatter={function (val) { return [val.toFixed(1), "FCS"] }} />
            <ReferenceLine y={avg} stroke={C.faint} strokeDasharray="4 4" />
            <Area type="monotone" dataKey="fcs" stroke="#ffffff" strokeWidth={1.5} fill="url(#fcsGrad)" dot={{ r: 2.5, fill: "#ffffff", stroke: C.bg, strokeWidth: 2 }} activeDot={{ r: 4, stroke: "#ffffff", strokeWidth: 1, fill: C.bg }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function GraceAICard(props) {
  var navigate = props.navigate; var score = props.score; var weakest = props.weakestDim
  var insight = ""
  if (score != null && score >= 70) { insight = "Your FCS is " + score.toFixed(1) + " — that's strong. Let's talk about what to optimize next." }
  else if (score != null && score >= 40) { insight = "Your FCS is " + score.toFixed(1) + " — you're building real awareness. I can help you understand what's driving your score." }
  else if (score != null && score > 0) { insight = "Your FCS is " + score.toFixed(1) + " — this is your starting point. Let's figure out the highest-impact move you can make." }
  else { insight = "Complete a check-in and I'll have personalized insights based on your financial profile." }
  if (weakest && dimensionLabels[weakest]) { insight += " Your " + dimensionLabels[weakest].toLowerCase() + " could use some attention." }

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Label>Grace AI</Label>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 5, height: 5, borderRadius: "50%", background: C.text }} />
          <span style={{ fontSize: 10, color: C.muted, textTransform: "uppercase", letterSpacing: "0.06em" }}>Ready</span>
        </div>
      </div>
      <p style={{ fontSize: 14, color: C.muted, lineHeight: 1.7, margin: "0 0 20px", fontFamily: FONT }}>{insight}</p>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 20 }}>
        {["What's affecting my score?", "Help me build a plan", "I need to talk about money"].map(function (prompt, i) {
          return (
            <button key={i} onClick={function () { navigate("/grace") }} style={{
              background: "transparent", border: "1px solid " + C.border, borderRadius: 6,
              padding: "6px 12px", color: C.dim, fontSize: 12, fontFamily: FONT, cursor: "pointer", transition: "all 0.2s ease",
            }}
              onMouseEnter={function (e) { e.target.style.borderColor = C.faint; e.target.style.color = C.text }}
              onMouseLeave={function (e) { e.target.style.borderColor = C.border; e.target.style.color = C.dim }}
            >{prompt}</button>
          )
        })}
      </div>
      <button onClick={function () { navigate("/grace") }} style={{
        width: "100%", padding: "12px", borderRadius: 8, border: "none",
        background: "#ffffff", color: "#000000", fontSize: 13, fontWeight: 600, fontFamily: FONT,
        cursor: "pointer", transition: "opacity 0.2s ease", letterSpacing: "-0.01em",
      }}
        onMouseEnter={function (e) { e.target.style.opacity = "0.85" }}
        onMouseLeave={function (e) { e.target.style.opacity = "1" }}
      >Talk to Grace</button>
      <p style={{ fontSize: 11, color: C.dim, textAlign: "center", margin: "12px 0 0", fontFamily: FONT }}>
        Behavioral coaching — not financial advice.
      </p>
    </Card>
  )
}

export default function DashboardPage() {
  var auth = useAuth(); var user = auth.user; var logout = auth.logout; var navigate = useNavigate()
  var onboardedState = useState(function () { return localStorage.getItem("grace-onboarding-complete") === "true" })
  var isOnboarded = onboardedState[0]; var setIsOnboarded = onboardedState[1]
  var mountedState = useState(false); var mounted = mountedState[0]; var setMounted = mountedState[1]
  var snapshotState = useState(null); var snapshotData = snapshotState[0]; var setSnapshotData = snapshotState[1]
  var metricsState = useState(null); var metricsData = metricsState[0]; var setMetricsData = metricsState[1]

  useEffect(function () { setMounted(true); loadDashboardData() }, [])

  function loadDashboardData() {
    Promise.all([
      apiFetch("/me/metrics").catch(function () { return null }),
      apiFetch("/checkin/metrics?days=30").catch(function () { return { snapshots: [] } }),
    ]).then(function (results) { setSnapshotData(results[0]); setMetricsData(results[1]) })
  }
  function handleCheckinComplete(freshMetrics) { if (freshMetrics) { setSnapshotData(freshMetrics) } else { loadDashboardData() } }
  if (!isOnboarded) { return <OnboardingPage onComplete={function () { setIsOnboarded(true) }} /> }
  function handleLogout() { logout(); navigate("/login") }

  var snapshots = metricsData && metricsData.snapshots ? metricsData.snapshots : []
  var s = snapshotData
  var currentFCS = s ? s.fcs_total : null; var fcsTrend = s ? s.delta_vs_last : null
  var checkinCount = s ? s.checkins_this_week : null; var streak = s ? s.streak_count : null
  var dims = s && s.dimensions ? s.dimensions : {}
  var currentMetrics = {
    current_stability: dims.stability != null ? dims.stability / 100 : null,
    future_outlook: dims.outlook != null ? dims.outlook / 100 : null,
    purchasing_power: dims.purchasing_power != null ? dims.purchasing_power / 100 : null,
    emergency_readiness: dims.emergency_readiness != null ? dims.emergency_readiness / 100 : null,
    financial_agency: dims.financial_agency != null ? dims.financial_agency / 100 : null,
  }
  var weakestDim = null; var weakestVal = 1.0
  Object.keys(currentMetrics).forEach(function (d) { var v = currentMetrics[d]; if (v != null && v < weakestVal) { weakestVal = v; weakestDim = d } })

  var todayDate = new Date()
  var dateStr = todayDate.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: FONT }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');"}</style>
      <div style={{ maxWidth: 960, margin: "0 auto", padding: "24px 24px 60px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, opacity: mounted ? 1 : 0, transition: "opacity 0.5s ease" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 28, height: 28, border: "1.5px solid " + C.text, borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12, fontWeight: 700 }}>G</div>
            <span style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.02em" }}>GraceFinance</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ fontSize: 12, color: C.dim }}>{user && user.first_name ? user.first_name : ""}</span>
            <button onClick={handleLogout} style={{ padding: "6px 14px", fontSize: 12, fontWeight: 500, fontFamily: FONT, cursor: "pointer", background: "transparent", border: "1px solid " + C.border, borderRadius: 6, color: C.dim, transition: "all 0.2s" }}
              onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
              onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
            >Sign out</button>
          </div>
        </div>
        <p style={{ fontSize: 12, color: C.dim, margin: "0 0 20px", letterSpacing: "0.02em" }}>{dateStr}</p>
        <Nav navigate={navigate} active="dashboard" />
        <div style={{ marginBottom: 28 }}><DailyCheckin onCheckinComplete={handleCheckinComplete} /></div>
        <div style={{ marginBottom: 28 }}><QuickStats score={currentFCS} checkinCount={checkinCount} streak={streak} /></div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 28 }}>
          <FCSScore score={currentFCS} trend={fcsTrend} checkinCount={checkinCount} />
          <DimensionBreakdown metrics={currentMetrics} />
        </div>
        <div style={{ marginBottom: 28 }}><TrendChart snapshots={snapshots} /></div>
        <div style={{ marginBottom: 40 }}><GraceAICard navigate={navigate} score={currentFCS} weakestDim={weakestDim} /></div>
        <div style={{ borderTop: "1px solid " + C.border, paddingTop: 20, textAlign: "center" }}>
          <p style={{ color: C.dim, fontSize: 11, margin: 0, letterSpacing: "0.02em" }}>GraceFinance — Where Financial Confidence Is Measured</p>
        </div>
      </div>
    </div>
  )
}