/**
 * CompletionCard — Post-check-in reward experience.
 *
 * This is the "instant gratification" moment. It composes:
 *   - StreakBadge (streak count)
 *   - Grace mini-summary (personality-driven feedback)
 *   - DeltaChips (score changes per dimension)
 *   - ContributionStatus (index pipeline status)
 *   - BehaviorNudge (one actionable tip)
 *   - Confetti (milestone celebration)
 *
 * Props:
 *   reward: object (from POST /checkins response.reward)
 *   onClose: function
 *   onViewIndex: function (navigate to Index page)
 *
 * Place at: src/components/CompletionCard.jsx
 */

import { useState, useEffect } from "react"
import { useTheme } from "../context/ThemeContext"
import StreakBadge from "./StreakBadge"
import DeltaChips from "./DeltaChips"
import ContributionStatus from "./ContributionStatus"
import BehaviorNudge from "./BehaviorNudge"
import Confetti from "./Confetti"

export default function CompletionCard({ reward, onClose, onViewIndex }) {
  var t = useTheme().theme
  var visibleState = useState(false)
  var visible = visibleState[0]
  var setVisible = visibleState[1]

  var expandedState = useState(false)
  var expanded = expandedState[0]
  var setExpanded = expandedState[1]

  useEffect(function () {
    // Staggered entrance
    var timer = setTimeout(function () { setVisible(true) }, 50)
    return function () { clearTimeout(timer) }
  }, [])

  if (!reward) return null

  var streak = reward.streak || 0
  var isMilestone = reward.streak_is_milestone || false

  return (
    <div style={{
      position: "relative",
      borderRadius: 16,
      overflow: "hidden",
      opacity: visible ? 1 : 0,
      transform: visible ? "translateY(0) scale(1)" : "translateY(20px) scale(0.96)",
      transition: "all 0.5s cubic-bezier(0.16, 1, 0.3, 1)",
    }}>

      {/* Confetti burst */}
      <Confetti active={visible} intense={isMilestone} />

      {/* Card body */}
      <div style={{
        background: "linear-gradient(165deg, rgba(17, 24, 39, 0.98), rgba(15, 20, 35, 0.95))",
        border: "1px solid rgba(255, 255, 255, 0.08)",
        borderRadius: 16,
        padding: "24px 20px",
      }}>

        {/* Header: checkmark + title */}
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
        }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: "linear-gradient(135deg, #22D3A7, #3FB950)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 18,
            animation: "check-pop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.2s both",
          }}>
            {"\u2713"}
          </div>
          <div>
            <div style={{
              fontSize: 16,
              fontWeight: 600,
              color: t.text || "#E2E8F0",
            }}>
              Check-in Complete
            </div>
            <div style={{
              fontSize: 12,
              color: "rgba(255,255,255,0.4)",
              marginTop: 2,
            }}>
              {new Date().toLocaleDateString("en-US", {
                weekday: "long",
                month: "long",
                day: "numeric",
              })}
            </div>
          </div>
        </div>

        {/* Streak */}
        <div style={{ marginBottom: 16 }}>
          <StreakBadge streak={streak} isMilestone={isMilestone} />
        </div>

        {/* Grace mini-summary */}
        <div style={{
          padding: "14px 16px",
          borderRadius: 12,
          background: "rgba(34, 211, 167, 0.06)",
          border: "1px solid rgba(34, 211, 167, 0.1)",
          marginBottom: 16,
          animation: "fade-up 0.5s ease-out 0.3s both",
        }}>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginBottom: 6,
          }}>
            <div style={{
              width: 20,
              height: 20,
              borderRadius: 6,
              background: "linear-gradient(135deg, #22D3A7, #BC8CFF)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 10,
              fontWeight: 700,
            }}>
              G
            </div>
            <span style={{
              fontSize: 11,
              fontWeight: 600,
              color: "#22D3A7",
            }}>
              Grace
            </span>
          </div>
          <p style={{
            fontSize: 14,
            color: "rgba(255, 255, 255, 0.8)",
            lineHeight: 1.55,
            margin: 0,
            fontStyle: "italic",
          }}>
            {reward.grace_summary}
          </p>
        </div>

        {/* Score deltas */}
        <div style={{
          marginBottom: 16,
          animation: "fade-up 0.5s ease-out 0.45s both",
        }}>
          <div style={{
            fontSize: 11,
            fontWeight: 600,
            color: "rgba(255,255,255,0.4)",
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            marginBottom: 8,
          }}>
            What Changed
          </div>
          <DeltaChips deltas={reward.deltas} />
        </div>

        {/* Expandable section */}
        {!expanded && (
          <button
            onClick={function () { setExpanded(true) }}
            style={{
              width: "100%",
              padding: "10px 0",
              background: "transparent",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 10,
              color: "rgba(255,255,255,0.5)",
              fontSize: 13,
              fontWeight: 500,
              cursor: "pointer",
              marginBottom: 12,
              transition: "all 0.2s ease",
            }}
            onMouseEnter={function (e) { e.target.style.borderColor = "rgba(34, 211, 167, 0.3)" }}
            onMouseLeave={function (e) { e.target.style.borderColor = "rgba(255,255,255,0.08)" }}
          >
            {"\u2728 See more details"}
          </button>
        )}

        {expanded && (
          <div style={{
            animation: "fade-up 0.4s ease-out both",
          }}>
            {/* Contribution status */}
            <div style={{ marginBottom: 12 }}>
              <ContributionStatus
                status={reward.contribution.status}
                message={reward.contribution.message}
                nextUpdateWindow={reward.contribution.next_update_window}
              />
            </div>

            {/* Behavior nudge */}
            <div style={{ marginBottom: 16 }}>
              <BehaviorNudge nudge={reward.behavior_nudge} />
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div style={{
          display: "flex",
          gap: 8,
          animation: "fade-up 0.5s ease-out 0.6s both",
        }}>
          <button
            onClick={onViewIndex}
            style={{
              flex: 1,
              padding: "10px 16px",
              borderRadius: 10,
              background: "linear-gradient(135deg, rgba(34, 211, 167, 0.15), rgba(88, 166, 255, 0.1))",
              border: "1px solid rgba(34, 211, 167, 0.2)",
              color: "#22D3A7",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
            onMouseEnter={function (e) { e.target.style.background = "rgba(34, 211, 167, 0.2)" }}
            onMouseLeave={function (e) { e.target.style.background = "linear-gradient(135deg, rgba(34, 211, 167, 0.15), rgba(88, 166, 255, 0.1))" }}
          >
            {"See the Index \u2192"}
          </button>
          <button
            onClick={onClose}
            style={{
              padding: "10px 20px",
              borderRadius: 10,
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "rgba(255,255,255,0.5)",
              fontSize: 13,
              fontWeight: 500,
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            Close
          </button>
        </div>
      </div>

      <style>{
        "@keyframes check-pop { from { transform: scale(0) rotate(-45deg); opacity: 0; } to { transform: scale(1) rotate(0deg); opacity: 1; } }" +
        "@keyframes fade-up { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }"
      }</style>
    </div>
  )
}
