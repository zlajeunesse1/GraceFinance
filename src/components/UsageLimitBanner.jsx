/**
 * UsageLimitBanner — shows inside Grace chat when user is near/at AI limit
 * Props:
 *   used: number
 *   limit: number | null  (null = unlimited)
 *   tier: string
 */
import { useNavigate } from "react-router-dom"

export default function UsageLimitBanner({ used, limit, tier }) {
  const navigate = useNavigate()

  if (limit === null) return null  // unlimited — premium
  if (!limit) return null

  const pct = (used / limit) * 100
  const remaining = Math.max(0, limit - used)

  if (pct < 70) return null  // only show when 70%+ used

  const isHit = pct >= 100

  return (
    <div style={{ ...styles.banner, ...(isHit ? styles.bannerCritical : styles.bannerWarn) }}>
      <div style={styles.left}>
        <span style={styles.icon}>{isHit ? "⚠" : "✦"}</span>
        <div>
          <div style={styles.main}>
            {isHit
              ? "You've used all your Grace AI messages this month."
              : `${remaining} Grace AI message${remaining !== 1 ? "s" : ""} left this month.`}
          </div>
          <div style={styles.sub}>
            {isHit
              ? "Upgrade to keep the conversation going."
              : "Upgrade for more coaching time with Grace."}
          </div>
        </div>
      </div>
      <button style={styles.btn} onClick={() => navigate("/upgrade")}>
        Upgrade
      </button>
    </div>
  )
}

const styles = {
  banner: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "16px",
    padding: "14px 18px",
    borderRadius: "10px",
    margin: "0 0 16px 0",
    border: "1px solid",
  },
  bannerWarn: {
    background: "rgba(245,158,11,0.08)",
    borderColor: "rgba(245,158,11,0.25)",
  },
  bannerCritical: {
    background: "rgba(239,68,68,0.08)",
    borderColor: "rgba(239,68,68,0.3)",
  },
  left: {
    display: "flex",
    gap: "12px",
    alignItems: "flex-start",
  },
  icon: {
    fontSize: "16px",
    marginTop: "1px",
    flexShrink: 0,
  },
  main: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#e5e5e5",
    marginBottom: "2px",
  },
  sub: {
    fontSize: "12px",
    color: "#777",
  },
  btn: {
    background: "#fff",
    color: "#000",
    border: "none",
    borderRadius: "7px",
    padding: "8px 16px",
    fontSize: "13px",
    fontWeight: "700",
    cursor: "pointer",
    whiteSpace: "nowrap",
    flexShrink: 0,
  },
}