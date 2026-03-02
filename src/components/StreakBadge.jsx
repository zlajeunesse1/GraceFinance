/**
 * StreakBadge — Displays the user's check-in streak.
 *
 * CHANGES:
 *   - [TIER 3] Added zero state: shows "Start your streak" when streak is 0 or null
 *
 * Props:
 *   streak: number (consecutive days)
 *   isMilestone: boolean (triggers extra glow)
 *
 * Place at: src/components/StreakBadge.jsx
 */

import { useTheme } from "../context/ThemeContext"

export default function StreakBadge({ streak, isMilestone }) {
  var t = useTheme().theme

  // Zero/null state
  if (!streak || streak <= 0) {
    return (
      <div style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 16px",
        borderRadius: 100,
        background: "rgba(255, 255, 255, 0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}>
        <span style={{ fontSize: 18 }}>{"\uD83D\uDD25"}</span>
        <span style={{
          fontSize: 14,
          fontWeight: 500,
          color: t.muted || "#94A3B8",
        }}>
          Check in to start your streak
        </span>
      </div>
    )
  }

  var glowColor = isMilestone ? "rgba(34, 211, 167, 0.4)" : "transparent"
  var bgColor = isMilestone
    ? "linear-gradient(135deg, rgba(34, 211, 167, 0.2), rgba(188, 140, 255, 0.15))"
    : "rgba(255, 255, 255, 0.06)"

  return (
    <div style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      padding: "8px 16px",
      borderRadius: 100,
      background: bgColor,
      border: "1px solid " + (isMilestone ? "rgba(34, 211, 167, 0.3)" : "rgba(255,255,255,0.08)"),
      boxShadow: isMilestone ? "0 0 20px " + glowColor : "none",
      transition: "all 0.6s ease",
    }}>
      <span style={{
        fontSize: 18,
        animation: isMilestone ? "streak-pulse 1s ease-in-out infinite" : "none",
      }}>
        {"\uD83D\uDD25"}
      </span>
      <span style={{
        fontSize: 14,
        fontWeight: 600,
        color: isMilestone ? "#22D3A7" : (t.text || "#E2E8F0"),
        letterSpacing: "-0.02em",
      }}>
        {streak}-day streak
      </span>
      {isMilestone && (
        <span style={{
          fontSize: 11,
          fontWeight: 500,
          color: "#BC8CFF",
          padding: "2px 8px",
          background: "rgba(188, 140, 255, 0.15)",
          borderRadius: 6,
        }}>
          milestone
        </span>
      )}
      <style>{
        "@keyframes streak-pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.15); } }"
      }</style>
    </div>
  )
}