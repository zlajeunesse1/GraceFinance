import { useState } from "react";

const TIERS = {
  free: {
    name: "Free",
    priceMonthly: 0,
    priceYearly: 0,
    tagline: "Get started with financial awareness",
    aiLabel: "Grace AI: 10 messages / month",
    features: [
      "Daily Financial Confidence Score",
      "5-dimension breakdown",
      "Daily check-ins",
      "10 Grace AI messages/month",
      "GraceFinance Index access",
    ],
    cta: "Current Plan",
    highlight: false,
  },
  pro: {
    name: "Pro",
    priceMonthly: 9.99,
    priceYearly: 99,
    tagline: "For people serious about building better habits",
    aiLabel: "Grace AI: 100 messages / month",
    features: [
      "Everything in Free",
      "100 Grace AI messages/month",
      "FCS trend history (90 days)",
      "Behavioral trend insights",
      "Data export (CSV & PDF)",
      "Priority support",
    ],
    cta: null, // dynamic based on current tier
    highlight: true,
  },
  premium: {
    name: "Premium",
    priceMonthly: 29.99,
    priceYearly: 299.99,
    tagline: "Full access. No limits. Total financial clarity.",
    aiLabel: "Grace AI: Unlimited",
    features: [
      "Everything in Pro",
      "Unlimited Grace AI messages",
      "Advanced behavioral analytics",
      "BSI insights & pattern detection",
      "Full FCS history (365 days)",
      "Early access to new features",
    ],
    cta: null,
    highlight: false,
  },
};

const API_BASE =
  window.location.hostname === "localhost"
    ? "http://localhost:8000"
    : "https://gracefinance-production.up.railway.app";

export default function PricingPage({ currentTier = "free" }) {
  const [interval, setInterval] = useState("monthly");
  const [loading, setLoading] = useState(null);

  const yearlySavings = (tier) => {
    const monthly = tier.priceMonthly * 12;
    const yearly = tier.priceYearly;
    return monthly > 0 ? (monthly - yearly).toFixed(2) : 0;
  };

  const totalYearlySavings = Object.values(TIERS).reduce(
    (sum, t) => sum + parseFloat(yearlySavings(t)),
    0
  );

  const handleUpgrade = async (tierKey) => {
    const token = localStorage.getItem("grace_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }

    setLoading(tierKey);
    try {
      const res = await fetch(`${API_BASE}/billing/checkout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ tier: tierKey, interval }),
      });

      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (err) {
      console.error("Checkout error:", err);
    } finally {
      setLoading(null);
    }
  };

  const getCtaLabel = (tierKey) => {
    const tierRank = { free: 0, pro: 1, premium: 2 };
    const currentRank = tierRank[currentTier] ?? 0;
    const targetRank = tierRank[tierKey] ?? 0;

    if (targetRank === currentRank) return "Current Plan";
    if (targetRank < currentRank) return "Current Plan"; // no downgrades here
    return `Upgrade to ${TIERS[tierKey].name}`;
  };

  const isCurrentOrLower = (tierKey) => {
    const tierRank = { free: 0, pro: 1, premium: 2 };
    return (tierRank[tierKey] ?? 0) <= (tierRank[currentTier] ?? 0);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a0a0a",
        padding: "60px 20px",
        fontFamily:
          "'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif",
      }}
    >
      {/* Interval Toggle */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: "12px",
          marginBottom: "48px",
        }}
      >
        <div
          style={{
            display: "flex",
            background: "#1a1a1a",
            borderRadius: "10px",
            padding: "4px",
            border: "1px solid #2a2a2a",
          }}
        >
          <button
            onClick={() => setInterval("monthly")}
            style={{
              padding: "10px 24px",
              borderRadius: "8px",
              border: "none",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: 600,
              background: interval === "monthly" ? "#222" : "transparent",
              color: interval === "monthly" ? "#fff" : "#666",
              transition: "all 0.2s",
            }}
          >
            Monthly
          </button>
          <button
            onClick={() => setInterval("yearly")}
            style={{
              padding: "10px 24px",
              borderRadius: "8px",
              border: "none",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: 600,
              background: interval === "yearly" ? "#222" : "transparent",
              color: interval === "yearly" ? "#fff" : "#666",
              transition: "all 0.2s",
            }}
          >
            Yearly
          </button>
        </div>
        {interval === "yearly" && (
          <span
            style={{
              background: "linear-gradient(135deg, #10b981, #059669)",
              color: "#fff",
              padding: "4px 12px",
              borderRadius: "20px",
              fontSize: "12px",
              fontWeight: 700,
              letterSpacing: "0.02em",
            }}
          >
            Save up to ${totalYearlySavings.toFixed(0)}
          </span>
        )}
      </div>

      {/* Tier Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "20px",
          maxWidth: "960px",
          margin: "0 auto",
        }}
      >
        {Object.entries(TIERS).map(([key, tier]) => {
          const isHighlight = tier.highlight;
          const price =
            interval === "yearly" && tier.priceYearly > 0
              ? (tier.priceYearly / 12).toFixed(2)
              : tier.priceMonthly;
          const isCurrent = isCurrentOrLower(key);

          return (
            <div
              key={key}
              style={{
                background: "#111",
                border: isHighlight
                  ? "1px solid #10b981"
                  : "1px solid #1e1e1e",
                borderRadius: "16px",
                padding: "32px 28px",
                display: "flex",
                flexDirection: "column",
                position: "relative",
                transition: "border-color 0.3s, transform 0.2s",
              }}
            >
              {/* Most Popular Badge */}
              {isHighlight && (
                <div
                  style={{
                    position: "absolute",
                    top: "-12px",
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: "#111",
                    border: "1px solid #10b981",
                    borderRadius: "20px",
                    padding: "4px 16px",
                    fontSize: "11px",
                    fontWeight: 700,
                    color: "#10b981",
                    letterSpacing: "0.05em",
                    textTransform: "uppercase",
                    whiteSpace: "nowrap",
                  }}
                >
                  Most Popular
                </div>
              )}

              {/* Tier Name */}
              <div
                style={{
                  fontSize: "12px",
                  fontWeight: 700,
                  color: "#666",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  marginBottom: "12px",
                }}
              >
                {tier.name}
              </div>

              {/* Price */}
              <div
                style={{
                  display: "flex",
                  alignItems: "baseline",
                  gap: "4px",
                  marginBottom: "8px",
                }}
              >
                {tier.priceMonthly === 0 ? (
                  <span
                    style={{
                      fontSize: "42px",
                      fontWeight: 800,
                      color: "#fff",
                      lineHeight: 1,
                    }}
                  >
                    Free
                  </span>
                ) : (
                  <>
                    <span
                      style={{
                        fontSize: "42px",
                        fontWeight: 800,
                        color: "#fff",
                        lineHeight: 1,
                      }}
                    >
                      ${price}
                    </span>
                    <span style={{ fontSize: "14px", color: "#555" }}>/mo</span>
                  </>
                )}
              </div>

              {/* Yearly note */}
              {interval === "yearly" && tier.priceYearly > 0 && (
                <div
                  style={{
                    fontSize: "12px",
                    color: "#10b981",
                    marginBottom: "8px",
                  }}
                >
                  Billed ${tier.priceYearly}/year — save $
                  {yearlySavings(tier)}
                </div>
              )}

              {/* Tagline */}
              <div
                style={{
                  fontSize: "13px",
                  color: "#555",
                  marginBottom: "24px",
                  lineHeight: 1.5,
                }}
              >
                {tier.tagline}
              </div>

              {/* AI Badge */}
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  background: "#1a1a1a",
                  border: "1px solid #2a2a2a",
                  borderRadius: "10px",
                  padding: "10px 16px",
                  marginBottom: "24px",
                  fontSize: "13px",
                  color: "#ccc",
                  fontWeight: 500,
                }}
              >
                <span style={{ fontSize: "14px" }}>✦</span>
                {tier.aiLabel}
              </div>

              {/* Features */}
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                  flex: 1,
                  marginBottom: "28px",
                }}
              >
                {tier.features.map((feature, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "10px",
                      fontSize: "13px",
                      color: "#bbb",
                      lineHeight: 1.4,
                    }}
                  >
                    <span
                      style={{
                        color: "#10b981",
                        fontSize: "14px",
                        flexShrink: 0,
                        marginTop: "1px",
                      }}
                    >
                      ✓
                    </span>
                    {feature}
                  </div>
                ))}
              </div>

              {/* CTA Button */}
              <button
                onClick={() => !isCurrent && handleUpgrade(key)}
                disabled={isCurrent || loading === key}
                style={{
                  width: "100%",
                  padding: "14px",
                  borderRadius: "10px",
                  border: "none",
                  cursor: isCurrent ? "default" : "pointer",
                  fontSize: "14px",
                  fontWeight: 700,
                  transition: "all 0.2s",
                  background: isCurrent
                    ? "#1a1a1a"
                    : isHighlight
                    ? "linear-gradient(135deg, #10b981, #059669)"
                    : "#fff",
                  color: isCurrent ? "#555" : isHighlight ? "#fff" : "#000",
                  opacity: loading === key ? 0.6 : 1,
                }}
              >
                {loading === key ? "Redirecting..." : getCtaLabel(key)}
              </button>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div
        style={{
          textAlign: "center",
          marginTop: "32px",
          fontSize: "12px",
          color: "#444",
        }}
      >
        Cancel anytime. Billed securely through Stripe. No hidden fees.
      </div>
    </div>
  );
}