/**
 * ProgressionCard.jsx — Behavioral Unlock System
 *
 * "Unlocked because you've built consistency."
 *
 * Renders:
 *   - Next Unlock teaser (prominent, with countdown)
 *   - All tiers with progress bars + lock/unlock status
 *   - Streak fire indicator
 *   - Unlocked feature badges
 *
 * Props:
 *   progression  — object from GET /progression/status
 *   loading      — boolean
 *
 * Drop into: src/components/ProgressionCard.jsx
 */

import { useState, useEffect } from "react"
import { useTheme } from "../context/ThemeContext"

/* ═══════════════════════════════════════════════════
   ANIMATED PROGRESS BAR
   ═══════════════════════════════════════════════════ */

function AnimatedBar(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var pct = props.progress * 100
  var color = props.color || t.accent

  var widthState = useState(0)
  var width = widthState[0]
  var setWidth = widthState[1]

  useEffect(function () {
    var timer = setTimeout(function () { setWidth(pct) }, 100)
    return function () { clearTimeout(timer) }
  }, [pct])

  return (
    <div style={{
      height: 6, background: t.dark, borderRadius: 4,
      overflow: "hidden", border: "1px solid " + t.border + "40",
      position: "relative",
    }}>
      <div style={{
        height: "100%",
        width: width + "%",
        background: "linear-gradient(90deg, " + color + "60, " + color + ")",
        borderRadius: 4,
        transition: "width 1.2s cubic-bezier(0.4, 0, 0.2, 1)",
        boxShadow: width > 0 ? "0 0 10px " + color + "30" : "none",
      }} />
      {/* Shimmer effect on active bars */}
      {width > 0 && width < 100 && (
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
          background: "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.08) 50%, transparent 100%)",
          animation: "shimmer 2.5s infinite",
          borderRadius: 4,
        }} />
      )}
    </div>
  )
}


/* ═══════════════════════════════════════════════════
   NEXT UNLOCK TEASER — The Dopamine Engine
   ═══════════════════════════════════════════════════ */

function NextUnlockTeaser(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var tier = props.tier
  if (!tier) return null

  var pctDone = Math.round(tier.progress * 100)

  return (
    <div style={{
      background: "linear-gradient(135deg, " + tier.color + "08, " + tier.color + "04)",
      border: "1px solid " + tier.color + "25",
      borderRadius: 14, padding: "18px 20px",
      marginBottom: 20, position: "relative", overflow: "hidden",
    }}>
      {/* Pulse glow */}
      <div style={{
        position: "absolute", top: -20, right: -20,
        width: 100, height: 100, borderRadius: "50%",
        background: "radial-gradient(circle, " + tier.color + "12 0%, transparent 70%)",
        animation: "pulse 3s infinite",
        pointerEvents: "none",
      }} />

      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
        <span style={{
          fontSize: 9, fontWeight: 700, color: tier.color,
          textTransform: "uppercase", letterSpacing: "0.12em",
        }}>
          {"\u26A1"} Next Unlock
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <span style={{ fontSize: 24 }}>{tier.icon}</span>
        <div style={{ flex: 1 }}>
          <p style={{
            fontSize: 15, fontWeight: 700, color: t.text,
            margin: "0 0 3px", letterSpacing: "-0.01em",
          }}>
            {tier.name}
          </p>
          <p style={{ fontSize: 12, color: t.muted, margin: 0, lineHeight: 1.5 }}>
            {tier.remaining_label}
          </p>
        </div>
        <div style={{
          textAlign: "center", minWidth: 52,
          background: tier.color + "12", borderRadius: 10, padding: "6px 10px",
        }}>
          <span style={{ fontSize: 18, fontWeight: 800, color: tier.color }}>{pctDone}</span>
          <span style={{ fontSize: 10, color: tier.color + "90" }}>%</span>
        </div>
      </div>

      <AnimatedBar progress={tier.progress} color={tier.color} />
    </div>
  )
}


/* ═══════════════════════════════════════════════════
   TIER ROW
   ═══════════════════════════════════════════════════ */

function TierRow(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var tier = props.tier
  var isUnlocked = tier.is_unlocked

  var expandedState = useState(false)
  var expanded = expandedState[0]
  var setExpanded = expandedState[1]

  var pct = Math.round(tier.progress * 100)

  return (
    <div
      onClick={function () { if (isUnlocked) setExpanded(!expanded) }}
      style={{
        background: isUnlocked ? t.card : t.dark + "80",
        border: "1px solid " + (isUnlocked ? tier.color + "30" : t.border + "30"),
        borderRadius: 12, padding: "14px 16px",
        cursor: isUnlocked ? "pointer" : "default",
        transition: "all 0.3s ease",
        opacity: isUnlocked ? 1 : 0.7,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {/* Lock / Icon */}
        <div style={{
          width: 38, height: 38, borderRadius: 10,
          background: isUnlocked ? tier.color + "15" : t.border + "20",
          display: "flex", alignItems: "center", justifyContent: "center",
          border: "1px solid " + (isUnlocked ? tier.color + "30" : t.border + "40"),
          fontSize: 18, transition: "all 0.3s",
        }}>
          {isUnlocked ? tier.icon : "\uD83D\uDD12"}
        </div>

        {/* Name + Progress */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{
              fontSize: 13, fontWeight: 600,
              color: isUnlocked ? t.text : t.muted,
            }}>
              {tier.name}
            </span>
            {isUnlocked && (
              <span style={{
                fontSize: 9, fontWeight: 700, color: "#3FB950",
                background: "#3FB95015", padding: "2px 7px",
                borderRadius: 8, textTransform: "uppercase", letterSpacing: "0.06em",
              }}>
                Unlocked
              </span>
            )}
          </div>

          {!isUnlocked && (
            <div style={{ marginTop: 2 }}>
              <AnimatedBar progress={tier.progress} color={tier.color} />
              <p style={{ fontSize: 10, color: t.muted + "90", margin: "4px 0 0" }}>
                {tier.remaining_label} {" \u2022 "} {pct}% complete
              </p>
            </div>
          )}

          {isUnlocked && !expanded && (
            <p style={{ fontSize: 11, color: t.muted, margin: 0 }}>
              {tier.description}
            </p>
          )}
        </div>

        {/* Expand chevron for unlocked tiers */}
        {isUnlocked && (
          <span style={{
            fontSize: 12, color: t.muted, transition: "transform 0.2s",
            transform: expanded ? "rotate(180deg)" : "rotate(0)",
          }}>
            {"\u25BC"}
          </span>
        )}
      </div>

      {/* Expanded: show unlocked features */}
      {expanded && isUnlocked && (
        <div style={{
          marginTop: 12, paddingTop: 12,
          borderTop: "1px solid " + t.border + "30",
        }}>
          <p style={{ fontSize: 11, color: t.muted, margin: "0 0 8px", fontWeight: 600 }}>
            Unlocked Features:
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {tier.unlocks.map(function (feature) {
              return (
                <span key={feature} style={{
                  fontSize: 10, fontWeight: 500,
                  color: tier.color, background: tier.color + "12",
                  padding: "3px 10px", borderRadius: 8,
                  border: "1px solid " + tier.color + "20",
                }}>
                  {"\u2713 " + feature.replace(/_/g, " ")}
                </span>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}


/* ═══════════════════════════════════════════════════
   MAIN PROGRESSION CARD
   ═══════════════════════════════════════════════════ */

export default function ProgressionCard(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var progression = props.progression
  var loading = props.loading

  if (loading || !progression) {
    return (
      <div style={{
        background: t.card, border: "1px solid " + t.border, borderRadius: 16, padding: 24,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 16, height: 16, borderRadius: "50%",
            border: "2px solid " + t.accent, borderTopColor: "transparent",
            animation: "spin 0.8s linear infinite",
          }} />
          <span style={{ fontSize: 13, color: t.muted }}>Loading progression...</span>
        </div>
      </div>
    )
  }

  var tiers = progression.tiers || []
  var nextUnlock = progression.next_unlock
  var unlockedCount = progression.unlocked_count || 0
  var totalTiers = progression.total_tiers || tiers.length
  var streak = progression.current_streak || 0
  var dataPoints = progression.data_points || 0

  return (
    <div style={{
      background: t.card, border: "1px solid " + t.border, borderRadius: 16, padding: 24,
      position: "relative", overflow: "hidden",
    }}>
      {/* Shimmer keyframe injection */}
      <style dangerouslySetInnerHTML={{ __html: "\n        @keyframes shimmer { 0% { transform: translateX(-100%); } 100% { transform: translateX(200%); } }\n        @keyframes pulse { 0%,100% { opacity: 0.5; } 50% { opacity: 1; } }\n        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }\n        @keyframes glow { 0%,100% { box-shadow: 0 0 4px rgba(251,191,36,0.3); } 50% { box-shadow: 0 0 12px rgba(251,191,36,0.6); } }\n      " }} />

      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 18,
      }}>
        <div>
          <h3 style={{ fontSize: 16, fontWeight: 600, color: t.text, margin: 0 }}>
            Your Journey
          </h3>
          <p style={{ fontSize: 11, color: t.muted, margin: "3px 0 0" }}>
            Your behavior powers every unlock
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Streak badge */}
          {streak > 0 && (
            <div style={{
              display: "flex", alignItems: "center", gap: 4,
              background: streak >= 7 ? "#FBBF2415" : t.border + "20",
              border: "1px solid " + (streak >= 7 ? "#FBBF2430" : t.border + "40"),
              borderRadius: 20, padding: "4px 10px",
              animation: streak >= 7 ? "glow 2s infinite" : "none",
            }}>
              <span style={{ fontSize: 12 }}>{"\uD83D\uDD25"}</span>
              <span style={{
                fontSize: 11, fontWeight: 700,
                color: streak >= 7 ? "#FBBF24" : t.muted,
              }}>
                {streak}d
              </span>
            </div>
          )}

          {/* Tier count badge */}
          <span style={{
            fontSize: 11, fontWeight: 600,
            color: t.accent, background: t.accent + "15",
            padding: "4px 10px", borderRadius: 20,
          }}>
            {unlockedCount + " / " + totalTiers}
          </span>
        </div>
      </div>

      {/* Quick stats row */}
      <div style={{
        display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 18,
      }}>
        {[
          { label: "Check-ins", value: progression.total_checkins || 0, icon: "\uD83D\uDC3E" },
          { label: "Streak", value: streak + "d", icon: "\uD83D\uDD25" },
          { label: "Data Points", value: dataPoints, icon: "\uD83D\uDCCA" },
        ].map(function (s) {
          return (
            <div key={s.label} style={{
              background: t.dark, border: "1px solid " + t.border + "50",
              borderRadius: 10, padding: "10px 12px", textAlign: "center",
            }}>
              <span style={{ fontSize: 12 }}>{s.icon}</span>
              <p style={{ fontSize: 16, fontWeight: 700, color: t.text, margin: "3px 0 1px" }}>{s.value}</p>
              <p style={{ fontSize: 9, color: t.muted, margin: 0, textTransform: "uppercase", letterSpacing: "0.06em" }}>{s.label}</p>
            </div>
          )
        })}
      </div>

      {/* Next Unlock Teaser */}
      <NextUnlockTeaser tier={nextUnlock} />

      {/* Tier List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {tiers.map(function (tier) {
          return <TierRow key={tier.id} tier={tier} />
        })}
      </div>

      {/* All unlocked message */}
      {unlockedCount === totalTiers && (
        <div style={{
          marginTop: 16, textAlign: "center", padding: "16px",
          background: "#3FB95008", border: "1px solid #3FB95020", borderRadius: 12,
        }}>
          <span style={{ fontSize: 20 }}>{"\uD83C\uDFC6"}</span>
          <p style={{ fontSize: 14, fontWeight: 700, color: "#3FB950", margin: "6px 0 4px" }}>
            All tiers unlocked!
          </p>
          <p style={{ fontSize: 12, color: t.muted, margin: 0 }}>
            Your consistency built this. Keep checking in to maintain your insights.
          </p>
        </div>
      )}
    </div>
  )
}