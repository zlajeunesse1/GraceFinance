/**
 * ErrorBoundary — Catches React rendering errors and shows a fallback UI.
 *
 * Wrap around App or individual dashboard cards to prevent white screens.
 *
 * Place at: src/components/ErrorBoundary.jsx
 */

import { Component } from "react"

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error: error }
  }

  componentDidCatch(error, errorInfo) {
    console.error("[GraceFinance] Error caught by boundary:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      // Compact card-level fallback if used on individual cards
      if (this.props.compact) {
        return (
          <div style={{
            padding: "24px",
            borderRadius: 16,
            background: "rgba(248, 81, 73, 0.04)",
            border: "1px solid rgba(248, 81, 73, 0.15)",
            textAlign: "center",
          }}>
            <p style={{ fontSize: 20, marginBottom: 8 }}>{"\u26A0\uFE0F"}</p>
            <p style={{ fontSize: 14, fontWeight: 600, color: "#F1F5F9", margin: "0 0 6px" }}>
              Something went wrong
            </p>
            <p style={{ fontSize: 12, color: "#94A3B8", margin: "0 0 12px" }}>
              This section couldn't load. Try refreshing.
            </p>
            <button
              onClick={function () { window.location.reload() }}
              style={{
                padding: "8px 20px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.1)",
                background: "transparent", color: "#94A3B8", fontSize: 12, fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Refresh
            </button>
          </div>
        )
      }

      // Full-page fallback
      return (
        <div style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#0B0F1A",
          color: "#F1F5F9",
          fontFamily: "'DM Sans', -apple-system, sans-serif",
          padding: 40,
          textAlign: "center",
        }}>
          <div style={{
            width: 80, height: 80, borderRadius: 20,
            background: "rgba(248, 81, 73, 0.1)",
            border: "1px solid rgba(248, 81, 73, 0.2)",
            display: "flex", alignItems: "center", justifyContent: "center",
            marginBottom: 24, fontSize: 36,
          }}>
            {"\uD83D\uDC3E"}
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>
            Something went wrong
          </h1>
          <p style={{ fontSize: 14, color: "#94A3B8", marginBottom: 24, maxWidth: 400, lineHeight: 1.6 }}>
            Grace hit an unexpected error. Your data is safe — try refreshing the page.
          </p>
          <button
            onClick={function () { window.location.reload() }}
            style={{
              padding: "14px 32px", borderRadius: 12, border: "none",
              background: "linear-gradient(135deg, #58A6FF, #22D3A7)",
              color: "#fff", fontSize: 14, fontWeight: 700,
              cursor: "pointer", marginBottom: 12,
            }}
          >
            Refresh Page
          </button>
          <button
            onClick={function () { window.location.href = "/dashboard" }}
            style={{
              padding: "10px 24px", borderRadius: 10, border: "1px solid #334155",
              background: "transparent", color: "#94A3B8", fontSize: 13, fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Go to Dashboard
          </button>
        </div>
      )
    }

    return this.props.children
  }
}