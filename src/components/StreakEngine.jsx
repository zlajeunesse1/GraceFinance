/**
 * StreakEngine.jsx — The Dopamine Bar
 *
 * Sits at the top of the dashboard between the nav and the check-in.
 * Shows:
 *   - Current streak with fire animation
 *   - Next unlock teaser with remaining count
 *   - "Alive" pulse indicator
 *   - Time until next check-in resets (midnight countdown)
 *
 * Props:
 *   streak       — number (days)
 *   nextUnlock   — tier object from progression (or null)
 *   checkedInToday — boolean
 *   dataPoints   — number
 *
 * Drop into: src/components/StreakEngine.jsx
 */

import { useState, useEffect } from "react"
import { useTheme } from "../context/ThemeContext"

function StreakEngine(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var streak = props.streak || 0
  var nextUnlock = props.nextUnlock
  var checkedInToday = props.checkedInToday || false
  var dataPoints = props.dataPoints || 0

  // ── Countdown to midnight (next check-in availability) ──
  var countdownState = useState("")
  var countdown = countdownState[0]
  var setCountdown = countdownState[1]

  useEffect(function () {
    function updateCountdown() {
      var now = new Date()
      var midnight = new Date(now)
      midnight.setHours(24, 0, 0, 0)
      var diff = midnight - now
      var hours = Math.floor(diff / 3600000)
      var mins = Math.floor((diff % 3600000) / 60000)
      setCountdown(hours + "h " + mins + "m")
    }
    updateCountdown()
    var interval = setInterval(updateCountdown, 60000)
    return function () { clearInterval(interval) }
  }, [])

  // ── Streak tier (visual intensity) ──
  var streakColor = streak >= 30 ? "#FBBF24" : streak >= 14 ? "#F97316" : streak >= 7 ? "#FB923C" : streak >= 3 ? "#58A6FF" : t.muted
  var streakLabel = streak >= 30 ? "Legendary" : streak >= 14 ? "On Fire" : streak >= 7 ? "Hot Streak" : streak >= 3 ? "Building" : streak > 0 ? "Started" : "Begin Today"

  // ── Streak fire dots (visual representation) ──
  var maxDots = 30
  var activeDots = Math.min(streak, maxDots)

  return (
    <div style={{
      background: t.card, border: "1px solid " + t.border,
      borderRadius: 14, padding: "16px 20px",
      position: "relative", overflow: "hidden",
    }}>
      {/* Keyframes */}
      <style dangerouslySetInnerHTML={{ __html: "\n        @keyframes streakPulse { 0%,100% { opacity: 0.6; } 50% { opacity: 1; } }\n        @keyframes fireGlow { 0%,100% { text-shadow: 0 0 4px rgba(251,191,36,0.3); } 50% { text-shadow: 0 0 12px rgba(251,191,36,0.7); } }\n      " }} />

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>

        {/* Left: Streak */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            animation: streak >= 7 ? "fireGlow 2s infinite" : "none",
          }}>
            <span style={{ fontSize: streak >= 7 ? 24 : 20 }}>{"\uD83D\uDD25"}</span>
            <span style={{
              fontSize: 22, fontWeight: 800, color: streakColor,
              letterSpacing: "-0.5px", fontVariantNumeric: "tabular-nums",
            }}>
              {streak}
            </span>
            <span style={{
              fontSize: 11, fontWeight: 600, color: streakColor + "B0",
              textTransform: "uppercase", letterSpacing: "0.06em",
            }}>
              {streakLabel}
            </span>
          </div>

          {/* Streak dots */}
          <div style={{ display: "flex", gap: 2, alignItems: "center" }}>
            {Array.from({ length: Math.min(14, maxDots) }).map(function (_, i) {
              var active = i < activeDots
              return (
                <div key={i} style={{
                  width: 4, height: active ? 12 : 6,
                  borderRadius: 2,
                  background: active ? streakColor : t.border + "50",
                  transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
                  transitionDelay: (i * 30) + "ms",
                  opacity: active ? 1 : 0.4,
                }} />
              )
            })}
            {streak > 14 && (
              <span style={{ fontSize: 9, color: streakColor, fontWeight: 700, marginLeft: 2 }}>
                +{streak - 14}
              </span>
            )}
          </div>
        </div>

        {/* Center: Next Unlock Teaser */}
        {nextUnlock && (
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            background: nextUnlock.color + "08",
            border: "1px solid " + nextUnlock.color + "20",
            borderRadius: 10, padding: "6px 14px",
          }}>
            <span style={{ fontSize: 14 }}>{nextUnlock.icon}</span>
            <div>
              <p style={{
                fontSize: 10, fontWeight: 700, color: nextUnlock.color,
                margin: 0, textTransform: "uppercase", letterSpacing: "0.06em",
              }}>
                {nextUnlock.remaining_label}
              </p>
              <p style={{ fontSize: 10, color: t.muted, margin: "1px 0 0" }}>
                until {nextUnlock.name}
              </p>
            </div>
            <div style={{
              width: 30, height: 30, borderRadius: 8,
              background: nextUnlock.color + "12",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <span style={{ fontSize: 11, fontWeight: 800, color: nextUnlock.color }}>
                {Math.round(nextUnlock.progress * 100)}%
              </span>
            </div>
          </div>
        )}

        {/* Right: Status */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {checkedInToday ? (
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{
                width: 7, height: 7, borderRadius: "50%", background: "#3FB950",
                boxShadow: "0 0 6px #3FB95060",
                animation: "streakPulse 2s infinite",
              }} />
              <span style={{ fontSize: 11, color: "#3FB950", fontWeight: 600 }}>
                Checked in today
              </span>
            </div>
          ) : (
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{
                width: 7, height: 7, borderRadius: "50%", background: "#D29922",
                animation: "streakPulse 1.5s infinite",
              }} />
              <span style={{ fontSize: 11, color: "#D29922", fontWeight: 600 }}>
                Check in to keep your streak!
              </span>
            </div>
          )}

          {/* Midnight countdown */}
          <div style={{
            fontSize: 10, color: t.muted + "80",
            background: t.border + "15", borderRadius: 8,
            padding: "3px 8px",
          }}>
            {"Resets in " + countdown}
          </div>
        </div>

      </div>
    </div>
  )
}

export default StreakEngine