import { useState, useEffect, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { useNavigate } from "react-router-dom"
import { useTheme } from "../context/ThemeContext"
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis
} from "recharts"
import Logo from "../components/Logo"
import ModeToggle from "../components/ModeToggle"
import NavBar from "../components/NavBar"
import DailyCheckin from "../components/DailyCheckin"
import OnboardingPage from "./OnboardingPage"
import ProgressionCard from "../components/ProgressionCard"
import StreakEngine from "../components/StreakEngine"

/* AUTHENTICATED FETCH */

var API_BASE = "http://localhost:8000"

function apiFetch(endpoint, options) {
  var token = localStorage.getItem("grace_token")
  var headers = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = "Bearer " + token
  var config = { headers: headers }
  if (options) {
    for (var k in options) {
      if (k === "headers") {
        for (var h in options.headers) headers[h] = options.headers[h]
      } else {
        config[k] = options[k]
      }
    }
  }
  config.headers = headers
  return fetch(API_BASE + endpoint, config).then(function (res) {
    if (!res.ok) throw new Error("Failed to fetch " + endpoint)
    return res.json()
  })
}

/* CONSTANTS & HELPERS */

var dimensionLabels = {
  current_stability: "Stability",
  future_outlook: "Outlook",
  purchasing_power: "Purchasing",
  emergency_readiness: "Emergency",
  income_adequacy: "Income",
}

var dimensionFullLabels = {
  current_stability: "Current Stability",
  future_outlook: "Future Outlook",
  purchasing_power: "Purchasing Power",
  emergency_readiness: "Emergency Readiness",
  income_adequacy: "Income Adequacy",
}

var dimensionIcons = {
  current_stability: "\uD83D\uDEE1\uFE0F",
  future_outlook: "\uD83D\uDD2E",
  purchasing_power: "\uD83D\uDCB0",
  emergency_readiness: "\uD83D\uDEA8",
  income_adequacy: "\uD83D\uDCC8",
}

var dimensionColors = {
  current_stability: "#58A6FF",
  future_outlook: "#BC8CFF",
  purchasing_power: "#D29922",
  emergency_readiness: "#F85149",
  income_adequacy: "#3FB950",
}

var dimensionWeights = {
  current_stability: 0.30,
  future_outlook: 0.25,
  purchasing_power: 0.20,
  emergency_readiness: 0.15,
  income_adequacy: 0.10,
}

var dimensionTips = {
  current_stability: "Set up autopay for your biggest bills. Knowing they're covered reduces stress instantly.",
  future_outlook: "Write down one financial goal you want to hit in 90 days. Clarity drives confidence.",
  purchasing_power: "Track 3 grocery swaps this week. Small wins add up to big savings.",
  emergency_readiness: "Open a separate savings account and auto-transfer even $10/week. Start the habit.",
  income_adequacy: "List one skill you could develop in 6 months that would increase your earning power.",
}

function getScoreColor(score) {
  if (score >= 70) return "#3FB950"
  if (score >= 50) return "#D29922"
  if (score >= 30) return "#FB923C"
  return "#F85149"
}

function getScoreLabel(score) {
  if (score >= 80) return "Strong"
  if (score >= 60) return "Building"
  if (score >= 40) return "Growing"
  if (score >= 20) return "Emerging"
  return "Starting"
}

function getScoreMessage(score) {
  if (score >= 80) return "You're in a strong position. Let's optimize and grow."
  if (score >= 60) return "Solid foundation. You're more aware than most."
  if (score >= 40) return "You're growing. Small consistent moves compound from here."
  if (score >= 20) return "Tough stretch, but you're showing up. That's the first step."
  return "Everyone starts somewhere. The fact that you're here matters."
}

/* SHARED UI COMPONENTS */

function Card(props) {
  var ctx = useTheme()
  var t = ctx.theme
  return (
    <div style={{
      background: t.card, border: "1px solid " + t.border, borderRadius: 16, padding: 24, ...(props.style || {}),
    }}>
      {props.children}
    </div>
  )
}

function SectionTitle(props) {
  var ctx = useTheme()
  var t = ctx.theme
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
      <h3 style={{ fontSize: 16, fontWeight: 600, color: t.text, margin: 0 }}>{props.children}</h3>
      {props.right}
    </div>
  )
}

function Badge(props) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 600, color: props.color, background: props.bg,
      padding: "3px 10px", borderRadius: 20, letterSpacing: 0.5, textTransform: "uppercase",
    }}>
      {props.text}
    </span>
  )
}

/* ═══════════════════════════════════════════════════
   ECOSYSTEM LAYER LABEL — subtle section marker
   Creates the "connected system" feel
   ═══════════════════════════════════════════════════ */

function EcosystemLabel(props) {
  var ctx = useTheme()
  var t = ctx.theme
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 10, marginBottom: 10, marginTop: 6,
    }}>
      <div style={{
        width: 3, height: 16, borderRadius: 2,
        background: "linear-gradient(180deg, " + (props.color || t.accent) + ", transparent)",
      }} />
      <span style={{
        fontSize: 9, fontWeight: 700, color: t.muted + "80",
        textTransform: "uppercase", letterSpacing: "0.15em",
      }}>
        {props.label}
      </span>
      <div style={{ flex: 1, height: 1, background: t.border + "30" }} />
    </div>
  )
}

/* ANIMATED NUMBER */

function AnimatedNumber(props) {
  var val = props.value
  var prefix = props.prefix || ""
  var suffix = props.suffix || ""
  var decimals = props.decimals || 0
  var displayState = useState(0)
  var display = displayState[0]
  var setDisplay = displayState[1]

  useEffect(function () {
    var startTime = Date.now()
    var duration = 1000
    function animate() {
      var elapsed = Date.now() - startTime
      var progress = Math.min(elapsed / duration, 1)
      var eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(val * eased)
      if (progress < 1) requestAnimationFrame(animate)
    }
    animate()
  }, [val])

  return <span>{prefix}{decimals > 0 ? display.toFixed(decimals) : Math.round(display)}{suffix}</span>
}

/* FCS SCORE CARD */

function FCSScoreCard(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var score = props.score
  var trend = props.trend
  var checkinCount = props.checkinCount || 0
  var sColor = score != null ? getScoreColor(score) : t.muted
  var label = score != null ? getScoreLabel(score) : "Starting"

  return (
    <Card style={{ textAlign: "center", position: "relative", overflow: "hidden" }}>
      <div style={{
        position: "absolute", top: -40, left: "50%", transform: "translateX(-50%)",
        width: 200, height: 200, borderRadius: "50%",
        background: "radial-gradient(circle, " + sColor + "15 0%, transparent 70%)",
        pointerEvents: "none",
      }} />

      <p style={{
        fontSize: 11, fontWeight: 700, color: t.muted, textTransform: "uppercase",
        letterSpacing: "0.12em", margin: "0 0 16px", position: "relative",
      }}>
        Financial Confidence Score
      </p>

      <div style={{ position: "relative", width: 140, height: 140, margin: "0 auto 16px" }}>
        <svg width="140" height="140" style={{ position: "absolute", top: 0, left: 0 }}>
          <circle cx="70" cy="70" r="60" fill="none" stroke={t.border} strokeWidth="5" />
          <circle
            cx="70" cy="70" r="60" fill="none" stroke={sColor} strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={2 * Math.PI * 60}
            strokeDashoffset={2 * Math.PI * 60 * (1 - (score != null ? score : 0) / 100)}
            style={{
              transition: "stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1)",
              transform: "rotate(-90deg)", transformOrigin: "50% 50%",
              filter: "drop-shadow(0 0 8px " + sColor + "50)",
            }}
          />
        </svg>
        <div style={{
          position: "absolute", top: 0, left: 0, width: "100%", height: "100%",
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        }}>
          <span style={{ fontSize: 36, fontWeight: 800, color: sColor, letterSpacing: -1 }}>
            {score != null
              ? <AnimatedNumber value={score} decimals={1} />
              : <span style={{ color: t.muted }}>—</span>
            }
          </span>
          <span style={{
            fontSize: 10, fontWeight: 700, color: sColor, textTransform: "uppercase",
            letterSpacing: "0.1em", marginTop: 2,
          }}>
            {label}
          </span>
        </div>
      </div>

      {trend !== null && trend !== undefined && (
        <div style={{ marginBottom: 8 }}>
          <span style={{
            fontSize: 13, fontWeight: 600,
            color: trend >= 0 ? "#3FB950" : "#F85149",
          }}>
            {trend >= 0 ? "\u2191 +" : "\u2193 "}{typeof trend === "number" ? trend.toFixed(1) : trend}
          </span>
          <span style={{ fontSize: 12, color: t.muted, marginLeft: 6 }}>vs last check-in</span>
        </div>
      )}

      <p style={{ fontSize: 13, color: t.muted, margin: "8px 0 0", lineHeight: 1.6 }}>
        {score != null ? getScoreMessage(score) : "Complete your first check-in to see your score."}
      </p>

      {checkinCount > 0 && (
        <p style={{ fontSize: 11, color: t.muted + "80", marginTop: 8 }}>
          Based on {checkinCount} check-in responses this week
        </p>
      )}
    </Card>
  )
}

/* DIMENSION BREAKDOWN */

function DimensionBreakdown(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var metrics = props.metrics || {}
  var unlockedFeatures = props.unlockedFeatures || []

  var dims = ["current_stability", "future_outlook", "purchasing_power", "emergency_readiness", "income_adequacy"]

  var weakest = null
  var weakestScore = 1.0
  dims.forEach(function (d) {
    var val = metrics[d]
    if (val != null && val < weakestScore) {
      weakestScore = val
      weakest = d
    }
  })

  // Progressive: only show breakdown if stability_breakdown is unlocked
  var hasBreakdown = unlockedFeatures.indexOf("stability_breakdown") >= 0 || unlockedFeatures.indexOf("fcs_score") >= 0

  if (!hasBreakdown) {
    return (
      <Card>
        <SectionTitle right={<Badge text="Locked" color={t.muted} bg={t.border + "30"} />}>
          Your Financial Profile
        </SectionTitle>
        <div style={{ textAlign: "center", padding: "30px 20px" }}>
          <span style={{ fontSize: 32 }}>{"\uD83D\uDD12"}</span>
          <p style={{ fontSize: 14, fontWeight: 600, color: t.text, margin: "10px 0 6px" }}>
            Complete 5 check-ins to unlock
          </p>
          <p style={{ fontSize: 12, color: t.muted, margin: 0, lineHeight: 1.6 }}>
            Your dimension breakdown reveals which areas of your financial life need the most attention.
          </p>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <SectionTitle right={<Badge text="FCS Breakdown" color={t.accent} bg={t.accent + "15"} />}>
        Your Financial Profile
      </SectionTitle>

      <div style={{ display: "flex", flexDirection: "column", gap: 14, marginBottom: 18 }}>
        {dims.map(function (dim) {
          var val = metrics[dim]
          var pct = val != null ? Math.round(val * 100) : null
          var color = dimensionColors[dim]
          var weight = Math.round(dimensionWeights[dim] * 100)

          return (
            <div key={dim}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 16 }}>{dimensionIcons[dim]}</span>
                  <span style={{ color: t.text, fontSize: 13, fontWeight: 500 }}>{dimensionFullLabels[dim]}</span>
                  <span style={{ fontSize: 10, color: t.muted, background: t.border + "40", padding: "1px 6px", borderRadius: 8 }}>
                    {weight + "% weight"}
                  </span>
                </div>
                <span style={{ color: pct != null ? color : t.muted, fontSize: 14, fontWeight: 700 }}>
                  {pct != null ? pct + "%" : "—"}
                </span>
              </div>
              <div style={{
                height: 7, background: t.dark, borderRadius: 4, overflow: "hidden",
                border: "1px solid " + t.border,
              }}>
                <div style={{
                  height: "100%", width: (pct != null ? pct : 0) + "%",
                  background: "linear-gradient(90deg, " + color + "80, " + color + ")",
                  borderRadius: 4, transition: "width 1.2s ease",
                  boxShadow: "0 0 8px " + color + "40",
                }} />
              </div>
            </div>
          )
        })}
      </div>

      {weakest && weakestScore < 0.7 && (
        <div style={{
          background: dimensionColors[weakest] + "0d",
          border: "1px solid " + dimensionColors[weakest] + "25",
          borderRadius: 12, padding: "14px 16px",
        }}>
          <p style={{ color: dimensionColors[weakest], fontSize: 12, fontWeight: 700, margin: "0 0 6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {dimensionIcons[weakest] + " Focus Area: " + dimensionFullLabels[weakest]}
          </p>
          <p style={{ color: t.muted, fontSize: 13, margin: 0, lineHeight: 1.6 }}>
            {dimensionTips[weakest]}
          </p>
        </div>
      )}
    </Card>
  )
}

/* FCS TREND CHART */

function FCSTrendChart(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var snapshots = props.snapshots || []
  var unlockedFeatures = props.unlockedFeatures || []

  // Progressive: trend chart locked until behavioral_trends tier
  var hasTrends = unlockedFeatures.indexOf("trend_analysis") >= 0

  if (snapshots.length < 2 && !hasTrends) {
    return (
      <Card>
        <SectionTitle>Confidence Trend</SectionTitle>
        <div style={{ textAlign: "center", padding: "30px 0" }}>
          <p style={{ fontSize: 32, marginBottom: 8 }}>{"\uD83D\uDCC8"}</p>
          <p style={{ color: t.muted, fontSize: 14, margin: 0 }}>
            Check in for a few days to see your trend.
          </p>
          <p style={{ color: t.muted + "80", fontSize: 12, marginTop: 6 }}>
            Every check-in adds a data point here.
          </p>
        </div>
      </Card>
    )
  }

  if (snapshots.length < 2) {
    return (
      <Card>
        <SectionTitle>Confidence Trend</SectionTitle>
        <div style={{ textAlign: "center", padding: "30px 0" }}>
          <p style={{ fontSize: 32, marginBottom: 8 }}>{"\uD83D\uDCC8"}</p>
          <p style={{ color: t.muted, fontSize: 14, margin: 0 }}>
            Check in for a few days to see your trend.
          </p>
          <p style={{ color: t.muted + "80", fontSize: 12, marginTop: 6 }}>
            Every check-in adds a data point here.
          </p>
        </div>
      </Card>
    )
  }

  var chartData = snapshots.map(function (s, i) {
    var d = new Date(s.computed_at)
    return {
      label: (d.getMonth() + 1) + "/" + d.getDate(),
      fcs: Math.round(s.fcs_composite * 10) / 10,
      stability: Math.round(s.current_stability * 100),
      outlook: Math.round(s.future_outlook * 100),
      index: i,
    }
  })

  var avgFcs = Math.round(chartData.reduce(function (a, b) { return a + b.fcs }, 0) / chartData.length * 10) / 10

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 }}>
        <div>
          <SectionTitle>Confidence Trend</SectionTitle>
          <p style={{ fontSize: 12, color: t.muted, margin: "-12px 0 0" }}>Your FCS score over time</p>
        </div>
        <div style={{
          background: t.accent + "12", border: "1px solid " + t.accent + "30",
          borderRadius: 10, padding: "6px 14px", textAlign: "center",
        }}>
          <p style={{ fontSize: 10, color: t.muted, margin: 0, textTransform: "uppercase" }}>Average</p>
          <p style={{ fontSize: 18, fontWeight: 700, color: t.accent, margin: "2px 0 0" }}>{avgFcs}</p>
        </div>
      </div>

      <div style={{ height: 200 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="fcsGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={t.accent} stopOpacity={0.25} />
                <stop offset="100%" stopColor={t.accent} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={t.border + "60"} />
            <XAxis
              dataKey="label"
              tick={{ fill: t.muted, fontSize: 11 }}
              axisLine={{ stroke: t.border }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: t.muted, fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "rgba(13,17,23,0.95)", border: "1px solid " + t.border,
                borderRadius: 12, padding: "10px 14px",
              }}
              labelStyle={{ color: t.muted, fontSize: 12 }}
              itemStyle={{ color: t.accent, fontSize: 14, fontWeight: 700 }}
              formatter={function (val) { return [val.toFixed(1), "FCS"] }}
            />
            <ReferenceLine
              y={avgFcs} stroke={t.accent} strokeDasharray="4 4" strokeOpacity={0.4}
            />
            <Area
              type="monotone" dataKey="fcs" stroke={t.accent} strokeWidth={2.5}
              fill="url(#fcsGrad)"
              dot={{ r: 4, fill: t.accent, stroke: t.dark, strokeWidth: 2 }}
              activeDot={{ r: 7, stroke: t.accent, strokeWidth: 2, fill: t.dark }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

/* QUICK STAT CARDS */

function QuickStats(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var score = props.score
  var checkins = props.checkinCount
  var bsi = props.bsi
  var weakest = props.weakestDim
  var streak = props.streak
  var dataPoints = props.dataPoints
  var unlockedCount = props.unlockedCount

  var stats = [
    {
      label: "FCS Score",
      value: score != null ? score.toFixed(1) : "—",
      sub: score != null ? getScoreLabel(score) : "Unlock after first check-in",
      color: score != null ? getScoreColor(score) : t.muted,
      icon: "\uD83C\uDFAF",
    },
    {
      label: "Check-ins",
      value: checkins != null ? checkins : "—",
      sub: "this week",
      color: "#58A6FF",
      icon: "\uD83D\uDC3E",
    },
    {
      label: "Streak",
      value: streak != null && streak > 0 ? streak + "d" : "0",
      sub: streak != null && streak > 0 ? "keep it going!" : "check in to start your streak",
      color: streak != null && streak >= 7 ? "#3FB950" : streak != null && streak >= 3 ? "#D29922" : "#58A6FF",
      icon: "\uD83D\uDD25",
    },
    {
      label: "Tiers Unlocked",
      value: unlockedCount != null ? unlockedCount + "/6" : "—",
      sub: dataPoints != null ? dataPoints + " data points" : "",
      color: unlockedCount != null && unlockedCount >= 4 ? "#3FB950" : unlockedCount != null && unlockedCount >= 2 ? "#D29922" : "#58A6FF",
      icon: "\uD83D\uDD13",
    },
  ]

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14 }}>
      {stats.map(function (s) {
        return (
          <Card key={s.label}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 13, color: t.muted, fontWeight: 500 }}>{s.label}</span>
              <span style={{ fontSize: 20 }}>{s.icon}</span>
            </div>
            <span style={{
              fontSize: 26, fontWeight: 700, color: s.color,
              letterSpacing: -0.5, display: "block", marginTop: 8,
            }}>
              {s.value}
            </span>
            <span style={{ fontSize: 12, color: t.muted, marginTop: 4, display: "block" }}>
              {s.sub}
            </span>
          </Card>
        )
      })}
    </div>
  )
}

/* GRACE AI COACHING CARD */

function GraceAICard(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var navigate = props.navigate
  var score = props.score
  var weakest = props.weakestDim
  var metrics = props.metrics || {}

  var greetingState = useState(null)
  var greeting = greetingState[0]
  var setGreeting = greetingState[1]

  useEffect(function () {
    apiFetch("/grace/intro")
      .then(function (data) { setGreeting(data) })
      .catch(function () { setGreeting(null) })
  }, [])

  var insight = ""
  if (score != null && score >= 70) {
    insight = "Your FCS of " + score.toFixed(1) + " is strong. Let's talk about optimizing from here."
  } else if (score != null && score >= 40) {
    insight = "Your FCS of " + score.toFixed(1) + " shows real awareness. Want to explore what's driving it?"
  } else if (score != null && score > 0) {
    insight = "Your FCS of " + score.toFixed(1) + " is your starting point. Let's build from here together."
  } else {
    insight = "Complete your first check-in and I'll have personalized insights ready for you."
  }

  if (weakest && metrics[weakest] != null && metrics[weakest] < 0.5) {
    insight += " Your " + dimensionFullLabels[weakest] + " could use some attention -- I have ideas."
  }

  return (
    <Card style={{ position: "relative", overflow: "hidden" }}>
      <div style={{
        position: "absolute", top: -30, right: -30,
        width: 150, height: 150, borderRadius: "50%",
        background: "radial-gradient(circle, rgba(188,140,255,0.08) 0%, transparent 70%)",
        pointerEvents: "none",
      }} />

      <SectionTitle right={<Badge text="AI Powered" color="#BC8CFF" bg="rgba(188,140,255,0.12)" />}>
        Grace AI Coach
      </SectionTitle>

      <div style={{
        display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 16,
        background: "rgba(188,140,255,0.04)", border: "1px solid rgba(188,140,255,0.12)",
        borderRadius: 14, padding: "16px",
      }}>
        <div style={{
          width: 42, height: 42, borderRadius: "50%", flexShrink: 0,
          background: "linear-gradient(135deg, #1a1a2e, #16213e)",
          border: "2px solid " + t.accent + "40",
          display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
        }}>
          <svg width="23" height="23" viewBox="0 0 64 64" fill="none">
            <ellipse cx="32" cy="40" rx="13" ry="11" fill={t.accent} opacity="0.9" />
            <ellipse cx="19" cy="23" rx="6.5" ry="7.5" fill={t.accent} opacity="0.8" transform="rotate(-15 19 23)" />
            <ellipse cx="45" cy="23" rx="6.5" ry="7.5" fill={t.accent} opacity="0.8" transform="rotate(15 45 23)" />
            <ellipse cx="13" cy="34" rx="5.5" ry="6.5" fill={t.accent} opacity="0.7" transform="rotate(-30 13 34)" />
            <ellipse cx="51" cy="34" rx="5.5" ry="6.5" fill={t.accent} opacity="0.7" transform="rotate(30 51 34)" />
          </svg>
        </div>

        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: t.text }}>Grace</span>
            <span style={{
              width: 6, height: 6, borderRadius: "50%", background: "#3FB950",
              boxShadow: "0 0 6px #3FB95060",
            }} />
            <span style={{ fontSize: 10, color: "#3FB950", fontWeight: 600 }}>Online</span>
          </div>
          <p style={{ color: t.muted, fontSize: 13, lineHeight: 1.6, margin: 0 }}>
            {insight}
          </p>
        </div>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {[
          "I'm stressed about money",
          "Help me understand my score",
          "I need a plan",
        ].map(function (concern, i) {
          return (
            <button
              key={i}
              onClick={function () { navigate("/grace") }}
              style={{
                background: t.border + "15", border: "1px solid " + t.border + "40",
                borderRadius: 20, padding: "6px 12px", color: t.muted,
                fontSize: 11, cursor: "pointer", transition: "all 0.2s",
              }}
              onMouseEnter={function (e) {
                e.target.style.background = "rgba(188,140,255,0.1)"
                e.target.style.borderColor = "rgba(188,140,255,0.3)"
                e.target.style.color = "#BC8CFF"
              }}
              onMouseLeave={function (e) {
                e.target.style.background = t.border + "15"
                e.target.style.borderColor = t.border + "40"
                e.target.style.color = t.muted
              }}
            >
              {concern}
            </button>
          )
        })}
      </div>

      <button
        onClick={function () { navigate("/grace") }}
        style={{
          width: "100%", padding: "14px 20px", borderRadius: 12, border: "none",
          background: "linear-gradient(135deg, #BC8CFF, " + t.accent + ")",
          color: "#fff", fontSize: 14, fontWeight: 700, cursor: "pointer",
          transition: "all 0.3s", letterSpacing: "0.02em",
          boxShadow: "0 4px 16px rgba(188,140,255,0.25)",
        }}
        onMouseEnter={function (e) {
          e.target.style.transform = "translateY(-1px)"
          e.target.style.boxShadow = "0 6px 24px rgba(188,140,255,0.35)"
        }}
        onMouseLeave={function (e) {
          e.target.style.transform = "translateY(0)"
          e.target.style.boxShadow = "0 4px 16px rgba(188,140,255,0.25)"
        }}
      >
        Talk to Grace
      </button>

      <p style={{
        fontSize: 10, color: t.muted + "80", textAlign: "center",
        margin: "10px 0 0", fontStyle: "italic",
      }}>
        Grace provides educational insights, not financial advice.
      </p>
    </Card>
  )
}

/* GRACE INDEX PREVIEW CARD */

function GraceIndexPreview(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var navigate = props.navigate
  var indexData = props.indexData

  var gfRwi = indexData && indexData.gf_rwi_composite ? indexData.gf_rwi_composite : null
  var fcsIndex = indexData && indexData.fcs_value ? indexData.fcs_value : null
  var userCount = indexData && indexData.user_count ? indexData.user_count : 0

  return (
    <Card style={{ position: "relative", overflow: "hidden" }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: gfRwi !== null ? "#3FB950" : "#D29922",
            boxShadow: "0 0 6px " + (gfRwi !== null ? "#3FB95060" : "#D2992260"),
          }} />
          <span style={{
            fontSize: 11, fontWeight: 700, color: t.muted, textTransform: "uppercase", letterSpacing: "0.1em",
          }}>
            Grace Real-World Index
          </span>
        </div>
        <Badge
          text={gfRwi !== null ? "Beta" : "Pending"}
          color={gfRwi !== null ? "#D29922" : "#D29922"}
          bg={gfRwi !== null ? "#D2992212" : "#D2992212"}
        />
      </div>

      {gfRwi !== null ? (
        <div>
          <div style={{ textAlign: "center", marginBottom: 16 }}>
            <span style={{
              fontSize: 42, fontWeight: 800, color: t.text,
              letterSpacing: -2, fontVariantNumeric: "tabular-nums",
            }}>
              <AnimatedNumber value={gfRwi} decimals={2} />
            </span>
            <p style={{ fontSize: 11, color: t.muted, margin: "4px 0 0", textTransform: "uppercase", letterSpacing: "0.08em" }}>
              GF-RWI Composite
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 16 }}>
            {[
              { label: "FCS", value: fcsIndex, color: "#58A6FF" },
              { label: "BSI", value: indexData && indexData.bsi_value, color: "#BC8CFF" },
              { label: "SPI", value: indexData && indexData.spi_value, color: "#3FB950" },
            ].map(function (idx) {
              return (
                <div key={idx.label} style={{
                  background: t.dark, border: "1px solid " + t.border,
                  borderRadius: 10, padding: "10px 12px", textAlign: "center",
                }}>
                  <p style={{ fontSize: 10, color: t.muted, margin: 0, textTransform: "uppercase" }}>{idx.label}</p>
                  <p style={{ fontSize: 18, fontWeight: 700, color: idx.color, margin: "4px 0 0" }}>
                    {idx.value !== null && idx.value !== undefined ? idx.value.toFixed(1) : "—"}
                  </p>
                </div>
              )
            })}
          </div>

          <p style={{ fontSize: 11, color: t.muted + "80", textAlign: "center", margin: 0 }}>
            Powered by {userCount} anonymous contributor{userCount !== 1 ? "s" : ""}
          </p>
        </div>
      ) : (
        <div style={{ textAlign: "center", padding: "20px 0" }}>
          <p style={{ fontSize: 28, marginBottom: 8 }}>{"\uD83D\uDCC8"}</p>
          <p style={{ color: t.text, fontSize: 14, fontWeight: 600, margin: "0 0 6px" }}>
            Index publishes nightly
          </p>
          <p style={{ color: t.muted, fontSize: 12, margin: "0 0 12px", lineHeight: 1.6 }}>
            Your check-in contributed 1 anonymous data point today.
            The GF Real-World Index will be available after the next scheduled publish.
          </p>
          <p style={{ color: t.muted + "80", fontSize: 11, margin: "0 0 16px" }}>
            {userCount > 0
              ? userCount + " contributor" + (userCount !== 1 ? "s" : "") + " so far today"
              : "Be the first to contribute today"}
          </p>
          <button
            onClick={function () { navigate("/index") }}
            style={{
              padding: "10px 20px", borderRadius: 10, border: "1px solid " + t.border,
              background: "transparent", color: t.muted, fontSize: 12, fontWeight: 600,
              cursor: "pointer", transition: "all 0.2s",
            }}
            onMouseEnter={function (e) {
              e.target.style.borderColor = t.accent
              e.target.style.color = t.accent
            }}
            onMouseLeave={function (e) {
              e.target.style.borderColor = t.border
              e.target.style.color = t.muted
            }}
          >
            Learn about the Index
          </button>
        </div>
      )}
    </Card>
  )
}

/* MOMENTUM METER */

function MomentumMeter(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var score = props.score
  var trend = props.trend
  var streak = props.streak
  var checkins = props.checkinCount

  var momentumScore = 0
  if (streak != null && streak > 0) momentumScore += Math.min(streak * 8, 40)
  if (trend !== null && trend > 0) momentumScore += Math.min(trend * 5, 30)
  if (checkins != null && checkins > 0) momentumScore += Math.min(checkins * 5, 30)
  momentumScore = Math.min(momentumScore, 100)

  var momentumLabel = momentumScore >= 70 ? "Strong Momentum"
    : momentumScore >= 40 ? "Building Momentum"
    : momentumScore > 0 ? "Getting Started"
    : "Start Checking In"

  var momentumColor = momentumScore >= 70 ? "#3FB950"
    : momentumScore >= 40 ? "#D29922"
    : momentumScore > 0 ? "#58A6FF"
    : t.muted

  return (
    <Card>
      <SectionTitle right={<Badge text="Momentum" color={momentumColor} bg={momentumColor + "15"} />}>
        Financial Momentum
      </SectionTitle>

      <div style={{
        height: 10, background: t.dark, borderRadius: 6, overflow: "hidden",
        border: "1px solid " + t.border, marginBottom: 12,
      }}>
        <div style={{
          height: "100%", width: momentumScore + "%",
          background: "linear-gradient(90deg, " + momentumColor + "60, " + momentumColor + ")",
          borderRadius: 6, transition: "width 1.5s ease",
          boxShadow: "0 0 12px " + momentumColor + "40",
        }} />
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <span style={{ fontSize: 20, fontWeight: 700, color: momentumColor }}>
            <AnimatedNumber value={momentumScore} />
          </span>
          <span style={{ fontSize: 12, color: t.muted, marginLeft: 6 }}>/100</span>
        </div>
        <span style={{ fontSize: 12, fontWeight: 600, color: momentumColor }}>{momentumLabel}</span>
      </div>

      <div style={{
        display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginTop: 14,
      }}>
        {[
          {
            label: "Streak",
            value: streak != null && streak > 0 ? streak + " days" : "0",
            icon: "\uD83D\uDD25",
            context: streak != null && streak >= 7 ? "On fire!" : streak != null && streak >= 3 ? "Building habit" : "Start today",
          },
          {
            label: "Trend",
            value: trend !== null ? (trend >= 0 ? "+" : "") + trend.toFixed(1) : "—",
            icon: trend != null && trend >= 0 ? "\u2191" : "\u2193",
            context: trend != null && trend > 1 ? "Strong upward" : trend != null && trend >= 0 ? "Steady" : trend != null ? "Normal fluctuation" : "Needs data",
          },
          {
            label: "Engagement",
            value: checkins != null && checkins > 0 ? checkins + " / wk" : "—",
            icon: "\uD83D\uDC3E",
            context: checkins != null && checkins >= 5 ? "Very active" : checkins != null && checkins >= 3 ? "Good rhythm" : "Keep checking in",
          },
        ].map(function (m) {
          return (
            <div key={m.label} style={{
              background: t.dark, border: "1px solid " + t.border,
              borderRadius: 10, padding: "10px", textAlign: "center",
            }}>
              <span style={{ fontSize: 14 }}>{m.icon}</span>
              <p style={{ fontSize: 14, fontWeight: 700, color: t.text, margin: "4px 0 2px" }}>{m.value}</p>
              <p style={{ fontSize: 10, color: t.muted, margin: 0, textTransform: "uppercase" }}>{m.label}</p>
              {m.context && (
                <p style={{ fontSize: 9, color: t.muted + "80", margin: "2px 0 0" }}>{m.context}</p>
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}

/* RADAR CHART — progressive disclosure */

function DimensionRadar(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var metrics = props.metrics || {}
  var checkinCount = props.checkinCount || 0

  var hasEnoughData = checkinCount >= 7

  var data = [
    { dimension: "Stability", value: metrics.current_stability != null ? Math.round(metrics.current_stability * 100) : 0 },
    { dimension: "Outlook", value: metrics.future_outlook != null ? Math.round(metrics.future_outlook * 100) : 0 },
    { dimension: "Purchasing", value: metrics.purchasing_power != null ? Math.round(metrics.purchasing_power * 100) : 0 },
    { dimension: "Emergency", value: metrics.emergency_readiness != null ? Math.round(metrics.emergency_readiness * 100) : 0 },
    { dimension: "Income", value: metrics.income_adequacy != null ? Math.round(metrics.income_adequacy * 100) : 0 },
  ]

  if (!hasEnoughData) {
    return (
      <Card>
        <SectionTitle>Dimension Overview</SectionTitle>
        <div style={{
          textAlign: "center", padding: "40px 20px",
          background: "rgba(255,255,255,0.02)", borderRadius: 12,
          border: "1px dashed " + t.border,
        }}>
          <p style={{ fontSize: 32, marginBottom: 8 }}>{"\uD83D\uDD12"}</p>
          <p style={{ color: t.text, fontSize: 15, fontWeight: 600, margin: "0 0 8px" }}>
            Unlock Your Dimension Map
          </p>
          <p style={{ color: t.muted, fontSize: 13, margin: "0 0 16px", lineHeight: 1.6 }}>
            Complete {7 - checkinCount} more check-in{7 - checkinCount !== 1 ? "s" : ""} to reveal your full behavioral profile across all 5 dimensions.
          </p>
          <div style={{
            display: "flex", justifyContent: "center", gap: 4,
          }}>
            {[1,2,3,4,5,6,7].map(function(n) {
              return (
                <div key={n} style={{
                  width: 28, height: 6, borderRadius: 3,
                  background: n <= checkinCount ? t.accent : t.border,
                  transition: "background 0.3s ease",
                }} />
              )
            })}
          </div>
          <p style={{ fontSize: 11, color: t.muted, marginTop: 10 }}>
            {checkinCount} of 7 check-ins completed
          </p>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <SectionTitle>Dimension Overview</SectionTitle>
      <div style={{ height: 260 }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={data}>
            <PolarGrid stroke={t.border + "60"} />
            <PolarAngleAxis
              dataKey="dimension"
              tick={{ fill: t.muted, fontSize: 11 }}
            />
            <PolarRadiusAxis
              domain={[0, 100]}
              tick={false}
              axisLine={false}
            />
            <Radar
              dataKey="value"
              stroke={t.accent}
              fill={t.accent}
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}


/* ═══════════════════════════════════════════════════════════════
   MAIN DASHBOARD — The Behavioral Ecosystem
   ═══════════════════════════════════════════════════════════════ */

export default function DashboardPage() {
  var auth = useAuth()
  var user = auth.user
  var logout = auth.logout
  var navigate = useNavigate()
  var ctx = useTheme()
  var t = ctx.theme

  var onboardedState = useState(function () {
    return localStorage.getItem("grace-onboarding-complete") === "true"
  })
  var isOnboarded = onboardedState[0]
  var setIsOnboarded = onboardedState[1]

  var mountedState = useState(false)
  var mounted = mountedState[0]
  var setMounted = mountedState[1]

  var snapshotState = useState(null)
  var snapshotData = snapshotState[0]
  var setSnapshotData = snapshotState[1]

  var metricsState = useState(null)
  var metricsData = metricsState[0]
  var setMetricsData = metricsState[1]

  var indexState = useState(null)
  var indexData = indexState[0]
  var setIndexData = indexState[1]

  /* ── NEW: Progression state ── */
  var progressionState = useState(null)
  var progressionData = progressionState[0]
  var setProgressionData = progressionState[1]

  var progressionLoadingState = useState(true)
  var progressionLoading = progressionLoadingState[0]
  var setProgressionLoading = progressionLoadingState[1]

  var dataLoadedState = useState(false)
  var dataLoaded = dataLoadedState[0]
  var setDataLoaded = dataLoadedState[1]

  useEffect(function () {
    setMounted(true)
    loadDashboardData()
  }, [])

  function loadDashboardData() {
    Promise.all([
      apiFetch("/me/metrics").catch(function () { return null }),
      apiFetch("/checkin/metrics?days=30").catch(function () { return { snapshots: [] } }),
      apiFetch("/index/latest").catch(function () { return null }),
      apiFetch("/progression/status").catch(function () { return null }),
    ]).then(function (results) {
      setSnapshotData(results[0])
      setMetricsData(results[1])
      setIndexData(results[2])
      setProgressionData(results[3])
      setProgressionLoading(false)
      setDataLoaded(true)
    })
  }

  function handleCheckinComplete(freshMetrics) {
    if (freshMetrics) {
      setSnapshotData(freshMetrics)
    }
    // Always reload progression after check-in (unlock status may have changed)
    apiFetch("/progression/status")
      .then(function (data) { setProgressionData(data) })
      .catch(function () {})
    if (!freshMetrics) {
      loadDashboardData()
    }
  }

  if (!isOnboarded) {
    return <OnboardingPage onComplete={function () { setIsOnboarded(true) }} />
  }

  function handleLogout() {
    logout()
    navigate("/login")
  }

  var snapshots = metricsData && metricsData.snapshots ? metricsData.snapshots : []
  var s = snapshotData

  var currentFCS = s ? s.fcs_total : null
  var fcsTrend = s ? s.delta_vs_last : null
  var checkinCount = s ? s.checkins_this_week : null
  var streak = s ? s.streak_count : null
  var bsiScore = null

  var dims = s && s.dimensions ? s.dimensions : {}
  var currentMetrics = {
    current_stability: dims.stability != null ? dims.stability / 100 : null,
    future_outlook: dims.outlook != null ? dims.outlook / 100 : null,
    purchasing_power: dims.purchasing_power != null ? dims.purchasing_power / 100 : null,
    emergency_readiness: dims.emergency_readiness != null ? dims.emergency_readiness / 100 : null,
    income_adequacy: dims.income_adequacy != null ? dims.income_adequacy / 100 : null,
  }

  var weakestDim = null
  var weakestVal = 1.0
  Object.keys(currentMetrics).forEach(function (d) {
    var v = currentMetrics[d]
    if (v != null && v < weakestVal) { weakestVal = v; weakestDim = d }
  })

  /* ── Progression-derived values ── */
  var unlockedFeatures = progressionData ? progressionData.unlocked_features || [] : []
  var nextUnlock = progressionData ? progressionData.next_unlock : null
  var dataPoints = progressionData ? progressionData.data_points || 0 : 0
  var unlockedCount = progressionData ? progressionData.unlocked_count || 0 : 0
  var checkedInToday = s && s.last_checkin_at ? (
    new Date(s.last_checkin_at).toDateString() === new Date().toDateString()
  ) : false

  var todayDate = new Date()
  var dateStr = todayDate.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })

  return (
    <div style={{ minHeight: "100vh", background: t.dark, color: t.text, fontFamily: "'DM Sans', -apple-system, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet" />

      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "24px 20px 60px" }}>

        {/* ═══ HEADER ═══ */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20,
          opacity: mounted ? 1 : 0, transform: mounted ? "translateY(0)" : "translateY(-10px)", transition: "all 0.5s ease",
        }}>
          <div>
            <Logo size={36} />
            <p style={{ fontSize: 13, color: t.muted, margin: 0, marginTop: 8 }}>
              {"Welcome back, " + (user && user.first_name ? user.first_name : "there") + " \u00B7 "}
              <span style={{ color: t.accent }}>{dateStr}</span>
            </p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <ModeToggle />
            <button onClick={handleLogout} style={{
              padding: "8px 16px", fontSize: 13, fontWeight: 500, cursor: "pointer",
              background: "transparent", border: "1px solid " + t.border, borderRadius: 10, color: t.muted,
              transition: "all 0.2s",
            }}>
              Sign out
            </button>
          </div>
        </div>

        {/* ═══ NAVIGATION ═══ */}
        <div style={{
          marginBottom: 16, opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(-5px)", transition: "all 0.5s ease 0.05s",
        }}>
          <NavBar navigate={navigate} activePage="dashboard" />
        </div>

        {/* ═══ STREAK ENGINE — The Dopamine Bar ═══ */}
        <div style={{
          marginBottom: 20, opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(10px)", transition: "all 0.5s ease 0.08s",
        }}>
          <StreakEngine
            streak={streak || 0}
            nextUnlock={nextUnlock}
            checkedInToday={checkedInToday}
            dataPoints={dataPoints}
          />
        </div>

        {/* ═══ INPUT LAYER: Daily Check-In ═══ */}
        <EcosystemLabel label="Input Layer" color="#3FB950" />
        <div style={{
          marginBottom: 24, opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(20px)", transition: "all 0.6s ease 0.1s",
        }}>
          <DailyCheckin onCheckinComplete={handleCheckinComplete} />
        </div>

        {/* ═══ SNAPSHOT: Quick Stats ═══ */}
        <EcosystemLabel label="Snapshot" color="#58A6FF" />
        <div style={{
          marginBottom: 24, opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(20px)", transition: "all 0.6s ease 0.15s",
        }}>
          <QuickStats
            score={currentFCS}
            checkinCount={checkinCount}
            bsi={bsiScore}
            weakestDim={weakestDim}
            metrics={currentMetrics}
            streak={streak}
            dataPoints={dataPoints}
            unlockedCount={unlockedCount}
          />
        </div>

        {/* ═══ SCORE LAYER: FCS + Radar ═══ */}
        <EcosystemLabel label="Score Layer" color={t.accent} />
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24,
          opacity: mounted ? 1 : 0, transition: "all 0.6s ease 0.2s",
        }}>
          <FCSScoreCard
            score={currentFCS}
            trend={fcsTrend}
            checkinCount={checkinCount}
          />
          <DimensionRadar metrics={currentMetrics} checkinCount={checkinCount} />
        </div>

        {/* ═══ TREND LAYER: FCS Over Time ═══ */}
        <EcosystemLabel label="Trend Layer" color="#D29922" />
        <div style={{
          marginBottom: 24, opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(20px)", transition: "all 0.6s ease 0.25s",
        }}>
          <FCSTrendChart snapshots={snapshots} unlockedFeatures={unlockedFeatures} />
        </div>

        {/* ═══ INSIGHT LAYER: Breakdown + Grace AI ═══ */}
        <EcosystemLabel label="Insight Layer" color="#BC8CFF" />
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24,
          opacity: mounted ? 1 : 0, transition: "all 0.6s ease 0.3s",
        }}>
          <DimensionBreakdown metrics={currentMetrics} unlockedFeatures={unlockedFeatures} />
          <GraceAICard
            navigate={navigate}
            score={currentFCS}
            weakestDim={weakestDim}
            metrics={currentMetrics}
          />
        </div>

        {/* ═══ PROGRESSION LAYER: Unlocks + Index ═══ */}
        <EcosystemLabel label="Progression Layer" color="#3FB950" />
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24,
          opacity: mounted ? 1 : 0, transition: "all 0.6s ease 0.35s",
        }}>
          <ProgressionCard
            progression={progressionData}
            loading={progressionLoading}
          />
          <GraceIndexPreview navigate={navigate} indexData={indexData} />
        </div>

        {/* ═══ MOMENTUM ═══ */}
        <div style={{
          marginBottom: 24, opacity: mounted ? 1 : 0,
          transform: mounted ? "translateY(0)" : "translateY(20px)", transition: "all 0.6s ease 0.4s",
        }}>
          <MomentumMeter
            score={currentFCS}
            trend={fcsTrend}
            streak={streak}
            checkinCount={checkinCount}
          />
        </div>

        {/* ═══ FOOTER ═══ */}
        <div style={{ textAlign: "center", paddingTop: 16 }}>
          <p style={{ color: t.border, fontSize: 12, margin: 0 }}>
            {"GraceFinance \u00B7 Built with purpose \u00B7 In memory of Grace \uD83D\uDC3E"}
          </p>
        </div>

      </div>
    </div>
  )
}