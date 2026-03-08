import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"

const TIERS = [
  {
    id: "free",
    name: "Free",
    price: { monthly: 0, yearly: 0 },
    description: "Get started with financial awareness",
    aiLimit: "10 messages / month",
    features: [
      "Daily Financial Confidence Score",
      "5-dimension breakdown",
      "Daily check-ins",
      "10 Grace AI messages/month",
      "GraceFinance Index access",
    ],
    cta: "Current Plan",
    highlighted: false,
  },
  {
    id: "pro",
    name: "Pro",
    price: { monthly: 9.99, yearly: 99 },
    description: "For people serious about building better habits",
    aiLimit: "100 messages / month",
    features: [
      "Everything in Free",
      "100 Grace AI messages/month",
      "Faster FCS updates",
      "Behavioral trend insights",
      "Priority support",
    ],
    cta: "Upgrade to Pro",
    highlighted: true,
    badge: "Most Popular",
  },
  {
    id: "premium",
    name: "Premium",
    price: { monthly: 29.99, yearly: 299.99 },
    description: "Full access. No limits. Total financial clarity.",
    aiLimit: "Unlimited",
    features: [
      "Everything in Pro",
      "Unlimited Grace AI messages",
      "Real-time FCS updates",
      "Advanced behavioral analytics",
      "Early access to new features",
    ],
    cta: "Upgrade to Premium",
    highlighted: false,
  },
]

export default function UpgradePage() {
  const [interval, setInterval] = useState("monthly")
  const [loading, setLoading] = useState(null)
  const [error, setError] = useState(null)
  const { user } = useAuth()
  const navigate = useNavigate()

  const currentTier = (user?.subscription_tier || "free").toLowerCase()

  const yearlySavings = {
    pro: Math.round((9.99 * 12 - 99) * 10) / 10,
    premium: Math.round((29.99 * 12 - 299.99) * 10) / 10,
  }

  const handleUpgrade = async (tierId) => {
    if (tierId === "free" || tierId === currentTier) return
    setLoading(tierId)
    setError(null)
    try {
      const token = localStorage.getItem("grace_token")
      const res = await fetch(`${getApiBase()}/billing/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tier: tierId, interval }),
      })
      if (!res.ok) throw new Error("Failed to create checkout session")
      const data = await res.json()
      window.location.href = data.checkout_url
    } catch (err) {
      setError("Something went wrong. Please try again.")
    } finally {
      setLoading(null)
    }
  }

  const getApiBase = () => {
    return window.location.hostname === "localhost"
      ? "http://localhost:8000"
      : "https://gracefinance-production.up.railway.app"
  }

  const getPrice = (tier) => {
    if (tier.price.monthly === 0) return "Free"
    const p = interval === "yearly" ? tier.price.yearly / 12 : tier.price.monthly
    return `$${p.toFixed(2)}`
  }

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <button onClick={() => navigate(-1)} style={styles.backBtn}>
          ← Back
        </button>
        <div style={styles.headerText}>
          <h1 style={styles.title}>Upgrade Your Plan</h1>
          <p style={styles.subtitle}>More Grace. More clarity. Less financial noise.</p>
        </div>
      </div>

      {/* Interval Toggle */}
      <div style={styles.toggleWrap}>
        <div style={styles.toggle}>
          <button
            style={{ ...styles.toggleBtn, ...(interval === "monthly" ? styles.toggleActive : {}) }}
            onClick={() => setInterval("monthly")}
          >
            Monthly
          </button>
          <button
            style={{ ...styles.toggleBtn, ...(interval === "yearly" ? styles.toggleActive : {}) }}
            onClick={() => setInterval("yearly")}
          >
            Yearly
            <span style={styles.saveBadge}>Save up to ${yearlySavings.premium}</span>
          </button>
        </div>
      </div>

      {error && <div style={styles.errorBar}>{error}</div>}

      {/* Tier Cards */}
      <div style={styles.cards}>
        {TIERS.map((tier) => {
          const isCurrent = tier.id === currentTier
          const isHighlighted = tier.highlighted
          const isLoading = loading === tier.id

          return (
            <div
              key={tier.id}
              style={{
                ...styles.card,
                ...(isHighlighted ? styles.cardHighlighted : {}),
                ...(isCurrent ? styles.cardCurrent : {}),
              }}
            >
              {tier.badge && <div style={styles.badge}>{tier.badge}</div>}
              {isCurrent && !tier.badge && <div style={styles.currentBadge}>Your Plan</div>}

              <div style={styles.tierName}>{tier.name}</div>
              <div style={styles.priceRow}>
                <span style={styles.price}>{getPrice(tier)}</span>
                {tier.price.monthly > 0 && (
                  <span style={styles.pricePer}>/mo</span>
                )}
              </div>

              {interval === "yearly" && tier.price.monthly > 0 && (
                <div style={styles.yearlyNote}>
                  ${tier.price.yearly}/year · saves ${yearlySavings[tier.id]}
                </div>
              )}

              <p style={styles.tierDesc}>{tier.description}</p>

              {/* AI Usage highlight */}
              <div style={styles.aiHighlight}>
                <span style={styles.aiIcon}>✦</span>
                <span style={styles.aiText}>Grace AI: {tier.aiLimit}</span>
              </div>

              <div style={styles.divider} />

              <ul style={styles.featureList}>
                {tier.features.map((f, i) => (
                  <li key={i} style={styles.featureItem}>
                    <span style={styles.check}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                style={{
                  ...styles.ctaBtn,
                  ...(isHighlighted && !isCurrent ? styles.ctaBtnHighlighted : {}),
                  ...(isCurrent ? styles.ctaBtnDisabled : {}),
                }}
                onClick={() => handleUpgrade(tier.id)}
                disabled={isCurrent || isLoading || tier.id === "free"}
              >
                {isLoading ? (
                  <span style={styles.spinner}>●</span>
                ) : isCurrent ? (
                  "Current Plan"
                ) : (
                  tier.cta
                )}
              </button>
            </div>
          )
        })}
      </div>

      {/* Usage meter for free users */}
      {currentTier === "free" && user?.ai_messages_used !== undefined && (
        <UsageMeter used={user.ai_messages_used} limit={10} />
      )}

      <p style={styles.footer}>
        Cancel anytime. Billed securely through Stripe. No hidden fees.
      </p>
    </div>
  )
}

function UsageMeter({ used, limit }) {
  const pct = Math.min((used / limit) * 100, 100)
  const color = pct >= 90 ? "#ef4444" : pct >= 70 ? "#f59e0b" : "#10b981"

  return (
    <div style={styles.meterWrap}>
      <div style={styles.meterLabel}>
        <span>This month's Grace AI usage</span>
        <span style={{ color }}>{used}/{limit} messages</span>
      </div>
      <div style={styles.meterTrack}>
        <div style={{ ...styles.meterFill, width: `${pct}%`, background: color }} />
      </div>
      {pct >= 100 && (
        <p style={styles.meterWarning}>You've hit your limit. Upgrade to keep coaching with Grace.</p>
      )}
    </div>
  )
}

const styles = {
  page: {
    minHeight: "100vh",
    background: "#0a0a0a",
    color: "#fff",
    fontFamily: "'DM Sans', sans-serif",
    padding: "0 0 60px 0",
  },
  header: {
    padding: "28px 32px 0",
    display: "flex",
    alignItems: "flex-start",
    gap: "20px",
  },
  backBtn: {
    background: "none",
    border: "none",
    color: "#666",
    fontSize: "14px",
    cursor: "pointer",
    padding: "4px 0",
    marginTop: "6px",
    whiteSpace: "nowrap",
  },
  headerText: {
    flex: 1,
  },
  title: {
    fontSize: "28px",
    fontWeight: "700",
    margin: "0 0 6px",
    letterSpacing: "-0.5px",
  },
  subtitle: {
    color: "#666",
    fontSize: "15px",
    margin: 0,
  },
  toggleWrap: {
    display: "flex",
    justifyContent: "center",
    padding: "32px 0 24px",
  },
  toggle: {
    display: "flex",
    background: "#111",
    border: "1px solid #222",
    borderRadius: "10px",
    padding: "4px",
    gap: "4px",
  },
  toggleBtn: {
    background: "none",
    border: "none",
    color: "#666",
    padding: "8px 20px",
    borderRadius: "7px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "500",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    transition: "all 0.2s",
  },
  toggleActive: {
    background: "#1a1a1a",
    color: "#fff",
    border: "1px solid #333",
  },
  saveBadge: {
    background: "rgba(16,185,129,0.15)",
    color: "#10b981",
    fontSize: "11px",
    padding: "2px 7px",
    borderRadius: "20px",
    fontWeight: "600",
  },
  errorBar: {
    margin: "0 32px 16px",
    padding: "12px 16px",
    background: "rgba(239,68,68,0.1)",
    border: "1px solid rgba(239,68,68,0.3)",
    borderRadius: "8px",
    color: "#ef4444",
    fontSize: "14px",
  },
  cards: {
    display: "flex",
    gap: "16px",
    padding: "0 24px",
    maxWidth: "960px",
    margin: "0 auto",
    flexWrap: "wrap",
    justifyContent: "center",
  },
  card: {
    flex: "1 1 260px",
    maxWidth: "300px",
    background: "#111",
    border: "1px solid #1e1e1e",
    borderRadius: "16px",
    padding: "28px 24px",
    position: "relative",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  cardHighlighted: {
    border: "1px solid #fff",
    background: "#141414",
  },
  cardCurrent: {
    border: "1px solid #333",
    opacity: 0.8,
  },
  badge: {
    position: "absolute",
    top: "-12px",
    left: "50%",
    transform: "translateX(-50%)",
    background: "#fff",
    color: "#000",
    fontSize: "11px",
    fontWeight: "700",
    padding: "4px 14px",
    borderRadius: "20px",
    letterSpacing: "0.5px",
    whiteSpace: "nowrap",
  },
  currentBadge: {
    position: "absolute",
    top: "-12px",
    left: "50%",
    transform: "translateX(-50%)",
    background: "#333",
    color: "#999",
    fontSize: "11px",
    fontWeight: "600",
    padding: "4px 14px",
    borderRadius: "20px",
    whiteSpace: "nowrap",
  },
  tierName: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#666",
    textTransform: "uppercase",
    letterSpacing: "1px",
  },
  priceRow: {
    display: "flex",
    alignItems: "baseline",
    gap: "4px",
  },
  price: {
    fontSize: "36px",
    fontWeight: "700",
    letterSpacing: "-1px",
  },
  pricePer: {
    color: "#666",
    fontSize: "14px",
  },
  yearlyNote: {
    fontSize: "12px",
    color: "#10b981",
    marginTop: "-6px",
  },
  tierDesc: {
    fontSize: "13px",
    color: "#666",
    lineHeight: "1.5",
    margin: 0,
  },
  aiHighlight: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    background: "rgba(255,255,255,0.04)",
    border: "1px solid #222",
    borderRadius: "8px",
    padding: "10px 12px",
  },
  aiIcon: {
    color: "#fff",
    fontSize: "12px",
  },
  aiText: {
    fontSize: "13px",
    color: "#ccc",
    fontWeight: "500",
  },
  divider: {
    height: "1px",
    background: "#1e1e1e",
  },
  featureList: {
    listStyle: "none",
    margin: 0,
    padding: 0,
    display: "flex",
    flexDirection: "column",
    gap: "8px",
    flex: 1,
  },
  featureItem: {
    display: "flex",
    gap: "10px",
    fontSize: "13px",
    color: "#aaa",
    alignItems: "flex-start",
    lineHeight: "1.4",
  },
  check: {
    color: "#10b981",
    fontWeight: "700",
    flexShrink: 0,
    marginTop: "1px",
  },
  ctaBtn: {
    width: "100%",
    padding: "13px",
    borderRadius: "9px",
    border: "1px solid #333",
    background: "transparent",
    color: "#fff",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    marginTop: "8px",
    transition: "all 0.2s",
  },
  ctaBtnHighlighted: {
    background: "#fff",
    color: "#000",
    border: "1px solid #fff",
  },
  ctaBtnDisabled: {
    opacity: 0.4,
    cursor: "default",
  },
  spinner: {
    animation: "spin 1s linear infinite",
    display: "inline-block",
  },
  meterWrap: {
    maxWidth: "400px",
    margin: "32px auto 0",
    padding: "0 24px",
  },
  meterLabel: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: "13px",
    color: "#666",
    marginBottom: "8px",
  },
  meterTrack: {
    height: "4px",
    background: "#1e1e1e",
    borderRadius: "4px",
    overflow: "hidden",
  },
  meterFill: {
    height: "100%",
    borderRadius: "4px",
    transition: "width 0.5s ease",
  },
  meterWarning: {
    fontSize: "12px",
    color: "#ef4444",
    marginTop: "8px",
    textAlign: "center",
  },
  footer: {
    textAlign: "center",
    fontSize: "12px",
    color: "#444",
    marginTop: "32px",
    padding: "0 24px",
  },
}