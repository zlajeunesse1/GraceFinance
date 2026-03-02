/**
 * ContributionStatus — Shows the user's contribution to the Index pipeline.
 *
 * Props:
 *   status: "queued" | "counted" | "pending"
 *   message: string
 *   nextUpdateWindow: string ("later today" | "tomorrow morning")
 *
 * Place at: src/components/ContributionStatus.jsx
 */

export default function ContributionStatus({ status, message, nextUpdateWindow }) {
  var statusConfig = {
    queued: { icon: "\u23F3", label: "Queued", color: "#BC8CFF", bg: "rgba(188, 140, 255, 0.1)" },
    counted: { icon: "\u2705", label: "Counted", color: "#3FB950", bg: "rgba(63, 185, 80, 0.1)" },
    pending: { icon: "\u23F3", label: "Pending", color: "#D29922", bg: "rgba(210, 153, 34, 0.1)" },
    processing: { icon: "\u2699\uFE0F", label: "Processing", color: "#58A6FF", bg: "rgba(88, 166, 255, 0.1)" },
  }

  var config = statusConfig[status] || statusConfig.queued

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "10px 14px",
      borderRadius: 10,
      background: config.bg,
      border: "1px solid " + config.color + "20",
    }}>
      <span style={{ fontSize: 16 }}>{config.icon}</span>
      <div style={{ flex: 1 }}>
        <div style={{
          fontSize: 12,
          fontWeight: 600,
          color: config.color,
          marginBottom: 2,
        }}>
          {config.label} for Index
        </div>
        <div style={{
          fontSize: 11,
          color: "rgba(255,255,255,0.5)",
          lineHeight: 1.3,
        }}>
          {message}
          {nextUpdateWindow && (
            <span style={{ color: "rgba(255,255,255,0.35)" }}>
              {" \u00B7 Next update: " + nextUpdateWindow}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
