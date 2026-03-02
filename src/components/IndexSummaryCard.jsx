/**
 * IndexSummaryCard — Compact dashboard widget for the GCI.
 *
 * Shows current GCI value, trend direction, and last updated time.
 * Click navigates to the full Index page.
 *
 * Props:
 *   gci: number
 *   trend: "UP" | "DOWN" | "FLAT"
 *   lastUpdated: ISO string
 *   contributors: number
 *   onClick: function (navigate to Index page)
 *
 * Place at: src/components/IndexSummaryCard.jsx
 */

import { useTheme } from "../context/ThemeContext"

var TREND_CONFIG = {
  UP: { arrow: "\u25B2", color: "#3FB950", label: "Trending Up" },
  DOWN: { arrow: "\u25BC", color: "#F85149", label: "Trending Down" },
  FLAT: { arrow: "\u25B6", color: "rgba(255,255,255,0.4)", label: "Holding Steady" },
}

export default function IndexSummaryCard({ gci, trend, lastUpdated, contributors, onClick }) {
  var t = useTheme().theme
  var config = TREND_CONFIG[trend] || TREND_CONFIG.FLAT

  // Format last updated to relative time
  var timeAgo = ""
  if (lastUpdated) {
    var diff = Date.now() - new Date(lastUpdated).getTime()
    var mins = Math.floor(diff / 60000)
    if (mins < 1) timeAgo = "just now"
    else if (mins < 60) timeAgo = mins + "m ago"
    else if (mins < 1440) timeAgo = Math.floor(mins / 60) + "h ago"
    else timeAgo = Math.floor(mins / 1440) + "d ago"
  }

  return (
    <div
      onClick={onClick}
      style={{
        padding: "16px 18px",
        borderRadius: 14,
        background: "linear-gradient(165deg, rgba(17, 24, 39, 0.95), rgba(15, 20, 35, 0.9))",
        border: "1px solid rgba(255, 255, 255, 0.06)",
        cursor: onClick ? "pointer" : "default",
        transition: "all 0.2s ease",
        position: "relative",
        overflow: "hidden",
      }}
      onMouseEnter={function (e) {
        e.currentTarget.style.borderColor = "rgba(34, 211, 167, 0.2)"
        e.currentTarget.style.transform = "translateY(-1px)"
      }}
      onMouseLeave={function (e) {
        e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)"
        e.currentTarget.style.transform = "translateY(0)"
      }}
    >
      {/* Subtle gradient glow */}
      <div style={{
        position: "absolute",
        top: -30,
        right: -30,
        width: 80,
        height: 80,
        borderRadius: "50%",
        background: "radial-gradient(circle, " + config.color + "10 0%, transparent 70%)",
        pointerEvents: "none",
      }} />

      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        marginBottom: 10,
      }}>
        <div>
          <div style={{
            fontSize: 11,
            fontWeight: 600,
            color: "rgba(255,255,255,0.4)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            marginBottom: 4,
          }}>
            Grace Composite Index
          </div>
          <div style={{
            display: "flex",
            alignItems: "baseline",
            gap: 8,
          }}>
            <span style={{
              fontSize: 28,
              fontWeight: 700,
              color: t.text || "#E2E8F0",
              letterSpacing: "-0.02em",
            }}>
              {gci != null ? gci.toFixed(1) : "--"}
            </span>
            <span style={{
              fontSize: 14,
              fontWeight: 600,
              color: config.color,
            }}>
              {config.arrow}
            </span>
          </div>
        </div>
        <div style={{
          padding: "4px 8px",
          borderRadius: 6,
          background: config.color + "15",
          fontSize: 11,
          fontWeight: 500,
          color: config.color,
        }}>
          {config.label}
        </div>
      </div>

      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        <span style={{
          fontSize: 11,
          color: "rgba(255,255,255,0.3)",
        }}>
          {timeAgo ? "Updated " + timeAgo : "No data yet"}
        </span>
        {contributors > 0 && (
          <span style={{
            fontSize: 11,
            color: "rgba(255,255,255,0.25)",
          }}>
            {contributors + " contributor" + (contributors !== 1 ? "s" : "") + " today"}
          </span>
        )}
      </div>

      {onClick && (
        <div style={{
          marginTop: 10,
          fontSize: 12,
          fontWeight: 500,
          color: "#22D3A7",
          opacity: 0.7,
        }}>
          {"View full Index \u2192"}
        </div>
      )}
    </div>
  )
}
