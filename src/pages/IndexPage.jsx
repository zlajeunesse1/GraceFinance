/**
 * IndexPage — GFCI Institutional Dashboard
 *
 * Wired to:
 *   GET /index/latest   → Current GFCI composite + trend
 *   GET /index/history  → 30-day trend data for chart
 *   GET /index/methodology → Public methodology
 *
 * Design: Bloomberg-inspired. Data-dense, monochrome.
 */

import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from "recharts"

var C = {
  bg: "#000000", card: "#0a0a0a", border: "#1a1a1a",
  text: "#ffffff", muted: "#666666", dim: "#444444", faint: "#333333",
}
var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

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

function Card(props) {
  return (
    <div style={{
      background: C.card, border: "1px solid " + C.border,
      borderRadius: 10, padding: 24, ...(props.style || {}),
    }}>
      {props.children}
    </div>
  )
}

function Label(props) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 500, color: C.muted,
      textTransform: "uppercase", letterSpacing: "0.08em", fontFamily: FONT,
    }}>
      {props.children}
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
  if (direction === "UP") return "Trending Up"
  if (direction === "DOWN") return "Trending Down"
  return "Flat"
}

function getIndexHealthLabel(value) {
  if (value >= 70) return "Strong Confidence"
  if (value >= 55) return "Moderate Confidence"
  if (value >= 40) return "Mixed Signals"
  if (value >= 25) return "Elevated Stress"
  return "High Stress"
}

export default function IndexPage() {
  var auth = useAuth()
  var logout = auth.logout
  var navigate = useNavigate()

  var mountedState = useState(false)
  var mounted = mountedState[0]; var setMounted = mountedState[1]

  var latestState = useState(null)
  var latest = latestState[0]; var setLatest = latestState[1]

  var historyState = useState([])
  var history = historyState[0]; var setHistory = historyState[1]

  var loadingState = useState(true)
  var loading = loadingState[0]; var setLoading = loadingState[1]

  var methodologyState = useState(null)
  var methodology = methodologyState[0]; var setMethodology = methodologyState[1]

  var showMethodState = useState(false)
  var showMethod = showMethodState[0]; var setShowMethod = showMethodState[1]

  useEffect(function () {
    setMounted(true)
    loadData()
  }, [])

  function loadData() {
    setLoading(true)
    Promise.all([
      apiFetch("/index/latest").catch(function () { return null }),
      apiFetch("/index/history?days=30").catch(function () { return { data_points: [] } }),
    ]).then(function (results) {
      setLatest(results[0])
      setHistory(results[1] ? results[1].data_points || [] : [])
      setLoading(false)
    })
  }

  function loadMethodology() {
    if (methodology) {
      setShowMethod(!showMethod)
      return
    }
    apiFetch("/index/methodology").then(function (data) {
      setMethodology(data)
      setShowMethod(true)
    }).catch(function () {})
  }

  function handleCompute() {
    apiFetch("/index/compute").then(function () {
      loadData()
    }).catch(function () {})
  }

  /* Derived state */
  var hasData = latest && latest.published === true
  var gfci = hasData ? latest.gfci_composite : null
  var fcsAvg = hasData ? latest.fcs_average : null
  var userCount = hasData ? latest.user_count : 0
  var trend = hasData ? latest.trend_direction || "FLAT" : "FLAT"
  var slope3d = hasData ? latest.gci_slope_3d : null
  var slope7d = hasData ? latest.gci_slope_7d : null
  var volatility = hasData ? latest.gci_volatility_7d : null

  var chartData = history.map(function (item) {
    return {
      date: item.date,
      gfci: item.gfci ? parseFloat(item.gfci) : null,
      fcs: item.fcs ? parseFloat(item.fcs) : null,
    }
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

        {/* Header */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          marginBottom: 8, opacity: mounted ? 1 : 0, transition: "opacity 0.5s ease",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 28, height: 28, border: "1.5px solid " + C.text, borderRadius: 6,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 12, fontWeight: 700,
            }}>G</div>
            <span style={{ fontSize: 14, fontWeight: 600, letterSpacing: "-0.02em" }}>GraceFinance</span>
          </div>
          <button
            onClick={function () { logout(); navigate("/login") }}
            style={{
              padding: "6px 14px", fontSize: 12, fontWeight: 500, fontFamily: FONT,
              cursor: "pointer", background: "transparent", border: "1px solid " + C.border,
              borderRadius: 6, color: C.dim, transition: "all 0.2s",
            }}
            onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
            onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
          >Sign out</button>
        </div>

        <p style={{ fontSize: 12, color: C.dim, margin: "0 0 20px", letterSpacing: "0.02em" }}>
          Grace Financial Confidence Index
        </p>
        <Nav navigate={navigate} active="index" />

        {/* ── HERO: GFCI Composite ── */}
        <Card style={{ marginBottom: 16, padding: "32px 28px" }}>
          <Label>GFCI Composite</Label>

          <div style={{
            display: "flex", alignItems: "baseline", gap: 16, marginTop: 16, marginBottom: 8,
          }}>
            <span style={{
              fontSize: 56, fontWeight: 300, letterSpacing: "-0.04em",
              color: C.text, fontVariantNumeric: "tabular-nums",
            }}>
              {gfci != null ? gfci.toFixed(1) : "—"}
            </span>
            <span style={{
              fontSize: 16, fontWeight: 500, color: C.muted,
              textTransform: "uppercase", letterSpacing: "0.06em",
            }}>
              {getTrendLabel(trend)}
            </span>
          </div>

          {gfci != null && (
            <p style={{ fontSize: 13, color: C.dim, margin: "0 0 20px" }}>
              {getIndexHealthLabel(gfci)}
            </p>
          )}

          {/* Sub-metrics row */}
          {hasData && (
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16 }}>
              {[
                { label: "FCS Avg", value: fcsAvg, decimals: 1 },
                { label: "Users", value: userCount, decimals: 0 },
                { label: "3d Slope", value: slope3d, decimals: 3, showSign: true },
                { label: "7d Slope", value: slope7d, decimals: 3, showSign: true },
                { label: "Volatility", value: volatility, decimals: 3 },
              ].map(function (item) {
                var display = "—"
                if (item.value != null) {
                  var formatted = item.decimals > 0 ? item.value.toFixed(item.decimals) : String(item.value)
                  if (item.showSign && item.value > 0) formatted = "+" + formatted
                  display = formatted
                }
                return (
                  <div key={item.label} style={{
                    padding: "8px 14px", borderRadius: 6,
                    background: C.bg, border: "1px solid " + C.border,
                  }}>
                    <div style={{
                      fontSize: 10, fontWeight: 500, color: C.dim,
                      textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 2,
                    }}>{item.label}</div>
                    <div style={{
                      fontSize: 16, fontWeight: 600, color: C.text,
                      fontVariantNumeric: "tabular-nums",
                    }}>{display}</div>
                  </div>
                )
              })}
            </div>
          )}

          <div style={{
            fontSize: 11, color: C.faint,
            display: "flex", justifyContent: "space-between",
          }}>
            <span>{lastUpdated ? "Published " + lastUpdated : "No data published yet"}</span>
            <span>{userCount > 0 ? userCount + " contributors" : ""}</span>
          </div>
        </Card>

        {/* ── TREND CHART ── */}
        {chartData.length > 1 ? (
          <Card style={{ marginBottom: 16, padding: 20 }}>
            <div style={{
              display: "flex", justifyContent: "space-between",
              alignItems: "center", marginBottom: 16,
            }}>
              <Label>30-Day Trend</Label>
              {chartAvg && (
                <div style={{ textAlign: "right" }}>
                  <div style={{
                    fontSize: 18, fontWeight: 600, color: C.text,
                    fontFamily: FONT, fontVariantNumeric: "tabular-nums",
                  }}>{chartAvg}</div>
                  <div style={{
                    fontSize: 10, color: C.dim,
                    textTransform: "uppercase", letterSpacing: "0.06em",
                  }}>Average</div>
                </div>
              )}
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gfciGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ffffff" stopOpacity={0.08} />
                    <stop offset="95%" stopColor="#ffffff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="date"
                  tick={{ fill: C.dim, fontSize: 10, fontFamily: FONT }}
                  axisLine={{ stroke: C.border }}
                  tickLine={false}
                  tickFormatter={function (d) {
                    return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric" })
                  }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={{ fill: C.dim, fontSize: 10, fontFamily: FONT }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#111111", border: "1px solid " + C.border,
                    borderRadius: 6, padding: "8px 12px", fontFamily: FONT,
                  }}
                  labelStyle={{ color: C.muted, fontSize: 11 }}
                  itemStyle={{ color: C.text, fontSize: 13, fontWeight: 600 }}
                  labelFormatter={function (d) {
                    return new Date(d).toLocaleDateString("en-US", {
                      weekday: "short", month: "short", day: "numeric",
                    })
                  }}
                  formatter={function (val) { return [val.toFixed(1), "GFCI"] }}
                />
                {chartAvg && (
                  <ReferenceLine y={chartAvg} stroke={C.faint} strokeDasharray="4 4" />
                )}
                <Area
                  type="monotone" dataKey="gfci"
                  stroke="#ffffff" strokeWidth={1.5}
                  fill="url(#gfciGrad)"
                  dot={{ r: 2, fill: "#ffffff", stroke: C.bg, strokeWidth: 2 }}
                  activeDot={{ r: 4, stroke: "#ffffff", strokeWidth: 1, fill: C.bg }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        ) : (
          <Card style={{ marginBottom: 16 }}>
            <Label>30-Day Trend</Label>
            <p style={{ fontSize: 13, color: C.dim, margin: "16px 0 0", lineHeight: 1.6 }}>
              Need at least 2 index computations to show a trend chart.
              {userCount === 0 && " Complete check-ins to start generating the index."}
            </p>
          </Card>
        )}

        {/* ── COMPUTE TRIGGER (Dev) ── */}
        <Card style={{ marginBottom: 16 }}>
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            <div>
              <Label>Index Engine</Label>
              <p style={{ fontSize: 13, color: C.dim, margin: "8px 0 0" }}>
                Trigger a manual GFCI computation from current user data.
              </p>
            </div>
            <button
              onClick={handleCompute}
              style={{
                padding: "10px 20px", fontSize: 13, fontWeight: 600,
                fontFamily: FONT, cursor: "pointer",
                background: C.text, color: C.bg,
                border: "none", borderRadius: 8,
                transition: "opacity 0.2s",
              }}
              onMouseEnter={function (e) { e.target.style.opacity = "0.85" }}
              onMouseLeave={function (e) { e.target.style.opacity = "1" }}
            >
              Compute Now
            </button>
          </div>
        </Card>

        {/* ── METHODOLOGY ── */}
        <Card style={{ marginBottom: 16 }}>
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            cursor: "pointer",
          }} onClick={loadMethodology}>
            <Label>Methodology</Label>
            <span style={{ fontSize: 12, color: C.dim }}>
              {showMethod ? "Hide" : "View"}
            </span>
          </div>

          {showMethod && methodology && (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 13, color: C.muted, lineHeight: 1.7, margin: "0 0 16px" }}>
                {methodology.description}
              </p>

              <div style={{ fontSize: 12, color: C.dim, marginBottom: 8 }}>
                Version {methodology.version} — Computed {methodology.computation_schedule}
              </div>

              {methodology.scoring_engine && (
                <div style={{ marginTop: 12 }}>
                  <div style={{
                    fontSize: 11, fontWeight: 500, color: C.muted,
                    textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8,
                  }}>Pillars</div>
                  {Object.entries(methodology.scoring_engine.pillars).map(function (entry) {
                    var key = entry[0]
                    var val = entry[1]
                    return (
                      <div key={key} style={{
                        display: "flex", justifyContent: "space-between",
                        padding: "6px 0", borderBottom: "1px solid " + C.border,
                      }}>
                        <span style={{ fontSize: 12, color: C.muted }}>
                          {key.replace(/_/g, " ").replace(/\b\w/g, function (c) { return c.toUpperCase() })}
                        </span>
                        <span style={{ fontSize: 12, color: C.text, fontWeight: 500 }}>
                          {Math.round(val.weight * 100)}%
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}

              {methodology.data_integrity && (
                <div style={{ marginTop: 16 }}>
                  <div style={{
                    fontSize: 11, fontWeight: 500, color: C.muted,
                    textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8,
                  }}>Data Integrity</div>
                  {methodology.data_integrity.map(function (item, i) {
                    return (
                      <div key={i} style={{
                        fontSize: 12, color: C.dim, padding: "4px 0",
                        borderBottom: i < methodology.data_integrity.length - 1 ? "1px solid " + C.border : "none",
                      }}>
                        {item}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </Card>

        {/* ── PRIVACY ── */}
        <Card style={{ marginBottom: 16, padding: "14px 16px" }}>
          <div style={{
            fontSize: 11, fontWeight: 500, color: C.dim,
            textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6,
          }}>Privacy</div>
          <p style={{ fontSize: 12, color: C.faint, lineHeight: 1.6, margin: 0 }}>
            The GFCI aggregates anonymous behavioral check-in data. No individual data is
            identifiable. Your scores are visible only to you. The index reflects population-level
            patterns, not individual behavior.
          </p>
        </Card>

        {/* Footer */}
        <div style={{ borderTop: "1px solid " + C.border, paddingTop: 20, textAlign: "center", marginTop: 32 }}>
          <p style={{ color: C.dim, fontSize: 11, margin: 0, letterSpacing: "0.02em" }}>
            GraceFinance — The Behavioral Finance Company
          </p>
        </div>
      </div>
    </div>
  )
}