/**
 * ProfilePage — Institutional Redesign
 *
 * Monochrome. Underline inputs. No completion ring gimmick.
 * Clean data display with clear save action.
 */

import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useProfile } from "../hooks/useProfile"

/* ── DESIGN TOKENS ── */

var C = {
  bg:     "#000000",
  card:   "#0a0a0a",
  border: "#1a1a1a",
  text:   "#ffffff",
  muted:  "#666666",
  dim:    "#444444",
  faint:  "#333333",
}

var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

/* ── RISK OPTIONS ── */

var RISK_OPTIONS = [
  { value: "calm",       label: "Calm",       desc: "Safety first" },
  { value: "balanced",   label: "Balanced",   desc: "Steady growth" },
  { value: "aggressive", label: "Aggressive", desc: "Max upside" },
]

export default function ProfilePage() {
  var navigate = useNavigate()
  var auth = useAuth()
  var user = auth.user
  var profileHook = useProfile()
  var profile = profileHook.profile
  var isLoading = profileHook.isLoading
  var isSaving = profileHook.isSaving
  var saveError = profileHook.saveError
  var updateProfile = profileHook.updateProfile

  var displayNameState = useState("")
  var displayName = displayNameState[0]
  var setDisplayName = displayNameState[1]

  var timezoneState = useState("America/New_York")
  var timezone = timezoneState[0]
  var setTimezone = timezoneState[1]

  var currencyState = useState("USD")
  var currency = currencyState[0]
  var setCurrency = currencyState[1]

  var riskState = useState("balanced")
  var riskStyle = riskState[0]
  var setRiskStyle = riskState[1]

  var savedState = useState(false)
  var saved = savedState[0]
  var setSaved = savedState[1]

  var focusedState = useState(null)
  var focused = focusedState[0]
  var setFocused = focusedState[1]

  useEffect(function () {
    if (profile) {
      setDisplayName(profile.display_name || "")
      setTimezone(profile.timezone || "America/New_York")
      setCurrency(profile.currency || "USD")
      setRiskStyle(profile.risk_style || "balanced")
    }
  }, [profile])

  async function handleSave() {
    await updateProfile({
      display_name: displayName || null,
      timezone: timezone,
      currency: currency,
      risk_style: riskStyle,
    })
    setSaved(true)
    setTimeout(function () { setSaved(false) }, 2000)
  }

  var inputStyle = function (field) {
    return {
      width: "100%", padding: "12px 0", fontSize: 14,
      fontFamily: FONT, fontWeight: 400, color: C.text,
      background: "transparent", border: "none",
      borderBottom: "1px solid " + (focused === field ? C.text : C.faint),
      outline: "none", transition: "border-color 0.3s ease",
      letterSpacing: "0.01em", boxSizing: "border-box",
    }
  }

  var labelStyle = {
    display: "block", fontSize: 11, fontWeight: 500,
    color: C.muted, textTransform: "uppercase",
    letterSpacing: "0.08em", marginBottom: 4,
  }

  var cardStyle = {
    background: C.card, border: "1px solid " + C.border,
    borderRadius: 10, padding: 24, marginBottom: 16,
  }

  var sectionLabel = {
    fontSize: 11, fontWeight: 500, color: C.muted,
    textTransform: "uppercase", letterSpacing: "0.08em",
    marginBottom: 16,
  }

  if (auth.loading || isLoading) {
    return (
      <div style={{
        minHeight: "100vh", background: C.bg, color: C.dim,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 13, fontFamily: FONT,
      }}>
        Loading...
      </div>
    )
  }

  return (
    <div style={{
      minHeight: "100vh", background: C.bg, color: C.text,
      fontFamily: FONT, display: "flex", flexDirection: "column",
      alignItems: "center", padding: "40px 24px",
    }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');" +
        "::placeholder { color: #444444 !important; }" +
        "input:-webkit-autofill { -webkit-box-shadow: 0 0 0 30px #000000 inset !important; -webkit-text-fill-color: #ffffff !important; }"
      }</style>

      <div style={{ width: "100%", maxWidth: 560 }}>

        {/* Back */}
        <button
          onClick={function () { navigate("/dashboard") }}
          style={{
            background: "transparent", border: "1px solid " + C.border,
            borderRadius: 6, padding: "8px 16px", color: C.dim,
            fontSize: 12, fontFamily: FONT, cursor: "pointer",
            marginBottom: 32, transition: "all 0.2s",
          }}
          onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
          onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
        >
          Dashboard
        </button>

        {/* Title */}
        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: C.text, margin: "0 0 6px", letterSpacing: "-0.02em" }}>
            Profile
          </h1>
          <p style={{ fontSize: 13, color: C.dim, margin: 0 }}>How Grace knows you</p>
        </div>

        {/* Account */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Account</div>
          {[
            { label: "Name", value: user ? ((user.first_name || "") + " " + (user.last_name || "")).trim() || "—" : "—" },
            { label: "Email", value: user ? user.email : "—" },
            { label: "Member since", value: user && user.created_at ? new Date(user.created_at).toLocaleDateString() : "—" },
            { label: "Plan", value: "Free Tier" },
          ].map(function (item, i, arr) {
            return (
              <div key={i} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "11px 0",
                borderBottom: i < arr.length - 1 ? "1px solid " + C.border : "none",
              }}>
                <span style={{ fontSize: 13, color: C.dim }}>{item.label}</span>
                <span style={{ fontSize: 13, color: C.text, fontWeight: 500, fontVariantNumeric: "tabular-nums" }}>
                  {item.value}
                </span>
              </div>
            )
          })}
        </div>

        {/* Identity */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Identity</div>
          <div style={{ marginBottom: 20 }}>
            <label style={labelStyle}>Display Name</label>
            <input
              style={inputStyle("displayName")}
              value={displayName}
              onChange={function (e) { setDisplayName(e.target.value) }}
              onFocus={function () { setFocused("displayName") }}
              onBlur={function () { setFocused(null) }}
              placeholder="How Grace addresses you"
              maxLength={64}
            />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <label style={labelStyle}>Currency</label>
              <input
                style={inputStyle("currency")}
                value={currency}
                onChange={function (e) { setCurrency(e.target.value.toUpperCase()) }}
                onFocus={function () { setFocused("currency") }}
                onBlur={function () { setFocused(null) }}
                maxLength={8} placeholder="USD"
              />
            </div>
            <div>
              <label style={labelStyle}>Timezone</label>
              <input
                style={inputStyle("timezone")}
                value={timezone}
                onChange={function (e) { setTimezone(e.target.value) }}
                onFocus={function () { setFocused("timezone") }}
                onBlur={function () { setFocused(null) }}
                placeholder="America/New_York"
              />
            </div>
          </div>
        </div>

        {/* Financial DNA */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Financial DNA</div>
          <label style={{ ...labelStyle, marginBottom: 12 }}>Risk Style</label>
          <div style={{ display: "flex", gap: 10 }}>
            {RISK_OPTIONS.map(function (opt) {
              var isActive = riskStyle === opt.value
              return (
                <button
                  key={opt.value}
                  onClick={function () { setRiskStyle(opt.value) }}
                  disabled={isSaving}
                  style={{
                    flex: 1, padding: "14px 12px",
                    borderRadius: 8, textAlign: "left",
                    border: "1px solid " + (isActive ? C.text : C.border),
                    background: isActive ? "#111111" : "transparent",
                    cursor: isSaving ? "not-allowed" : "pointer",
                    transition: "all 0.2s ease",
                    opacity: isSaving ? 0.5 : 1,
                  }}
                >
                  <div style={{
                    fontSize: 13, fontWeight: isActive ? 600 : 400,
                    color: isActive ? C.text : C.muted, fontFamily: FONT,
                  }}>
                    {opt.label}
                  </div>
                  <div style={{ fontSize: 11, color: C.dim, marginTop: 2, fontFamily: FONT }}>
                    {opt.desc}
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        {/* Privacy */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Privacy</div>
          <p style={{ fontSize: 13, color: C.dim, lineHeight: 1.7, margin: "0 0 16px" }}>
            Your data is encrypted and never sold. You control access.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {["Export my data (CSV)", "Delete my account"].map(function (action, i) {
              var isDanger = i === 1
              return (
                <button key={i} style={{
                  padding: "12px 16px", borderRadius: 8,
                  fontSize: 13, fontWeight: 500, fontFamily: FONT,
                  cursor: "pointer", textAlign: "left",
                  background: "transparent",
                  border: "1px solid " + (isDanger ? "#331111" : C.border),
                  color: isDanger ? "#ff4444" : C.dim,
                  transition: "all 0.2s",
                }}>
                  {action}
                </button>
              )
            })}
          </div>
        </div>

        {/* Save */}
        <button
          onClick={handleSave}
          disabled={isSaving}
          style={{
            width: "100%", padding: "14px",
            borderRadius: 8, border: "none",
            background: saved ? "#ffffff" : isSaving ? C.faint : "#ffffff",
            color: "#000000",
            fontWeight: 600, fontSize: 14, fontFamily: FONT,
            cursor: isSaving ? "not-allowed" : "pointer",
            transition: "all 0.2s ease",
            opacity: isSaving ? 0.5 : 1,
            letterSpacing: "-0.01em",
            marginTop: 4,
          }}
          onMouseEnter={function (e) { if (!isSaving) e.target.style.opacity = "0.85" }}
          onMouseLeave={function (e) { if (!isSaving) e.target.style.opacity = "1" }}
        >
          {saved ? "Saved" : isSaving ? "Saving..." : "Save Profile"}
        </button>

        {saveError && (
          <p style={{ color: "#ff4444", fontSize: 13, textAlign: "center", marginTop: 10 }}>
            {saveError}
          </p>
        )}
      </div>
    </div>
  )
}