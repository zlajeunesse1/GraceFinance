/**
 * SettingsPage — Institutional Redesign
 *
 * Monochrome. Clean toggles. No theme context dependency.
 */

import { useState } from "react"
import { useNavigate } from "react-router-dom"
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

/* ── TOGGLE ── */

function Toggle(props) {
  var active = props.active
  return (
    <div
      onClick={props.onToggle}
      style={{
        width: 40, height: 22, borderRadius: 11, cursor: "pointer",
        background: active ? C.text : C.border,
        position: "relative", transition: "background 0.2s ease",
      }}
    >
      <div style={{
        width: 16, height: 16, borderRadius: "50%",
        background: active ? C.bg : C.dim,
        position: "absolute", top: 3,
        left: active ? 21 : 3,
        transition: "left 0.2s ease",
      }} />
    </div>
  )
}

/* ── THEMES ── */

var THEMES = [
  { id: "dark",       name: "Dark",       desc: "Default" },
  { id: "wealth",     name: "Wealth",     desc: "Green accent" },
  { id: "aggressive", name: "Aggressive", desc: "Red accent" },
  { id: "calm",       name: "Calm",       desc: "Purple accent" },
]

export default function SettingsPage() {
  var navigate = useNavigate()
  var profileHook = useProfile()
  var updateProfile = profileHook.updateProfile

  var themeState = useState("dark")
  var currentTheme = themeState[0]
  var setCurrentTheme = themeState[1]

  var reminderState = useState(true)
  var dailyReminder = reminderState[0]
  var setDailyReminder = reminderState[1]

  var indexState = useState(false)
  var indexOptIn = indexState[0]
  var setIndexOptIn = indexState[1]

  var savedState = useState(false)
  var saved = savedState[0]
  var setSaved = savedState[1]

  async function handleThemeSelect(themeId) {
    setCurrentTheme(themeId)
    await updateProfile({ theme: themeId })
    setSaved(true)
    setTimeout(function () { setSaved(false) }, 1500)
  }

  return (
    <div style={{
      minHeight: "100vh", background: C.bg, color: C.text,
      fontFamily: FONT, display: "flex", flexDirection: "column",
      alignItems: "center", padding: "40px 24px",
    }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');"}</style>

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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 32 }}>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: C.text, margin: 0, letterSpacing: "-0.02em" }}>
            Settings
          </h1>
          {saved && (
            <span style={{ fontSize: 12, color: C.text, fontWeight: 500 }}>Saved</span>
          )}
        </div>

        {/* Theme */}
        <div style={{
          background: C.card, border: "1px solid " + C.border,
          borderRadius: 10, padding: 24, marginBottom: 16,
        }}>
          <div style={{
            fontSize: 11, fontWeight: 500, color: C.muted,
            textTransform: "uppercase", letterSpacing: "0.08em",
            marginBottom: 16,
          }}>
            Theme
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {THEMES.map(function (theme) {
              var isActive = currentTheme === theme.id
              return (
                <div
                  key={theme.id}
                  onClick={function () { handleThemeSelect(theme.id) }}
                  style={{
                    background: C.bg,
                    border: "1px solid " + (isActive ? C.text : C.border),
                    borderRadius: 8, padding: "14px 16px", cursor: "pointer",
                    transition: "all 0.2s ease",
                  }}
                >
                  <span style={{
                    fontSize: 13, fontWeight: isActive ? 600 : 400,
                    color: isActive ? C.text : C.muted,
                    display: "block",
                  }}>
                    {theme.name}
                  </span>
                  <span style={{ fontSize: 11, color: C.dim, marginTop: 2, display: "block" }}>
                    {theme.desc}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Notifications */}
        <div style={{
          background: C.card, border: "1px solid " + C.border,
          borderRadius: 10, padding: 24, marginBottom: 16,
        }}>
          <div style={{
            fontSize: 11, fontWeight: 500, color: C.muted,
            textTransform: "uppercase", letterSpacing: "0.08em",
            marginBottom: 16,
          }}>
            Notifications
          </div>

          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "12px 0", borderBottom: "1px solid " + C.border,
          }}>
            <div>
              <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>Daily check-in reminder</span>
              <p style={{ fontSize: 12, color: C.dim, margin: "4px 0 0" }}>Reminded each morning</p>
            </div>
            <Toggle active={dailyReminder} onToggle={function () { setDailyReminder(!dailyReminder) }} />
          </div>

          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "12px 0",
          }}>
            <div>
              <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>Index participation</span>
              <p style={{ fontSize: 12, color: C.dim, margin: "4px 0 0" }}>Contribute anonymized data to GF-RWI</p>
            </div>
            <Toggle active={indexOptIn} onToggle={function () { setIndexOptIn(!indexOptIn) }} />
          </div>
        </div>

        {/* Data & Export */}
        <div style={{
          background: C.card, border: "1px solid " + C.border,
          borderRadius: 10, padding: 24, marginBottom: 16,
        }}>
          <div style={{
            fontSize: 11, fontWeight: 500, color: C.muted,
            textTransform: "uppercase", letterSpacing: "0.08em",
            marginBottom: 16,
          }}>
            Data
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {["Export check-in data (CSV)", "Export FCS history (CSV)"].map(function (action, i) {
              return (
                <button key={i} style={{
                  padding: "12px 16px", borderRadius: 8, fontSize: 13,
                  fontWeight: 500, fontFamily: FONT, cursor: "pointer",
                  background: "transparent", textAlign: "left",
                  border: "1px solid " + C.border, color: C.dim,
                  transition: "all 0.2s",
                }}
                  onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
                  onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
                >
                  {action}
                </button>
              )
            })}
          </div>
        </div>

        {/* Footer */}
        <p style={{ fontSize: 11, color: C.faint, textAlign: "center", marginTop: 24 }}>
          GraceFinance v1.1.0
        </p>
      </div>
    </div>
  )
}