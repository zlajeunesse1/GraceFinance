/**
 * BehaviorNudge — One actionable behavior tip.
 *
 * NOT financial advice. Educational/behavioral only.
 * Based on the user's weakest dimension.
 *
 * Props:
 *   nudge: { dimension, label, tip }
 *
 * Place at: src/components/BehaviorNudge.jsx
 */

export default function BehaviorNudge({ nudge }) {
  if (!nudge) return null

  return (
    <div style={{
      padding: "12px 14px",
      borderRadius: 10,
      background: "rgba(88, 166, 255, 0.06)",
      border: "1px solid rgba(88, 166, 255, 0.12)",
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        marginBottom: 6,
      }}>
        <span style={{ fontSize: 14 }}>{"\uD83D\uDCA1"}</span>
        <span style={{
          fontSize: 11,
          fontWeight: 600,
          color: "#58A6FF",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}>
          Tomorrow's Edge
        </span>
        <span style={{
          fontSize: 10,
          color: "rgba(255,255,255,0.3)",
          marginLeft: "auto",
        }}>
          {nudge.label}
        </span>
      </div>
      <p style={{
        fontSize: 13,
        color: "rgba(255,255,255,0.7)",
        lineHeight: 1.5,
        margin: 0,
      }}>
        {nudge.tip}
      </p>
    </div>
  )
}
