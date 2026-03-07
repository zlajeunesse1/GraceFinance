/**
 * SettingsPage — v5 Polish
 * No theme picker. Clean toggles. Monochrome only.
 */

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useProfile } from "../hooks/useProfile"

var C = { bg: "#000000", card: "#0a0a0a", border: "#1a1a1a", text: "#ffffff", muted: "#9ca3af", dim: "#6b7280", faint: "#4b5563" }
var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

function Toggle(props) {
  var active = props.active
  return (
    <div onClick={props.onToggle} style={{ width: 40, height: 22, borderRadius: 11, cursor: "pointer", background: active ? C.text : C.border, position: "relative", transition: "background 0.2s ease" }}>
      <div style={{ width: 16, height: 16, borderRadius: "50%", background: active ? C.bg : C.dim, position: "absolute", top: 3, left: active ? 21 : 3, transition: "left 0.2s ease" }} />
    </div>
  )
}

export default function SettingsPage() {
  var navigate = useNavigate()
  var profileHook = useProfile(); var updateProfile = profileHook.updateProfile

  var reminderState = useState(true); var dailyReminder = reminderState[0]; var setDailyReminder = reminderState[1]
  var indexState = useState(true); var indexOptIn = indexState[0]; var setIndexOptIn = indexState[1]

  var cardStyle = { background: C.card, border: "1px solid " + C.border, borderRadius: 12, padding: 24, marginBottom: 16 }
  var sectionLabel = { fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: FONT, display: "flex", flexDirection: "column", alignItems: "center", padding: "40px 24px" }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');"}</style>
      <div style={{ width: "100%", maxWidth: 560 }}>
        <button onClick={function () { navigate("/dashboard") }} style={{ background: "transparent", border: "1px solid " + C.border, borderRadius: 6, padding: "8px 16px", color: C.dim, fontSize: 12, fontFamily: FONT, cursor: "pointer", marginBottom: 32, transition: "all 0.2s" }}
          onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
          onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
        >Dashboard</button>

        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: C.text, margin: "0 0 6px", letterSpacing: "-0.02em" }}>Settings</h1>
          <p style={{ fontSize: 13, color: C.dim, margin: 0 }}>Customize your GraceFinance experience.</p>
        </div>

        <div style={cardStyle}>
          <div style={sectionLabel}>Notifications</div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: "1px solid " + C.border }}>
            <div>
              <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>Daily check-in reminder</span>
              <p style={{ fontSize: 12, color: C.dim, margin: "4px 0 0" }}>A gentle nudge each morning to keep your streak alive.</p>
            </div>
            <Toggle active={dailyReminder} onToggle={function () { setDailyReminder(!dailyReminder) }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0" }}>
            <div>
              <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>Index contribution</span>
              <p style={{ fontSize: 12, color: C.dim, margin: "4px 0 0" }}>Your anonymized data helps power the GraceFinance Composite Index, a real-time financial confidence indicator.</p>
            </div>
            <Toggle active={indexOptIn} onToggle={function () { setIndexOptIn(!indexOptIn) }} />
          </div>
        </div>

        <div style={cardStyle}>
          <div style={sectionLabel}>Your Data</div>
          <p style={{ fontSize: 13, color: C.dim, lineHeight: 1.7, margin: "0 0 16px" }}>
            Your data belongs to you. Export it anytime, or delete your account entirely.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {["Export check-in history (CSV)", "Export FCS trend data (CSV)"].map(function (action, i) {
              return (<button key={i} style={{ padding: "12px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT, cursor: "pointer", background: "transparent", textAlign: "left", border: "1px solid " + C.border, color: C.dim, transition: "all 0.2s" }}
                onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
                onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
              >{action}</button>)
            })}
          </div>
        </div>

        <div style={cardStyle}>
          <div style={sectionLabel}>Account</div>
          <button style={{ padding: "12px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT, cursor: "pointer", background: "transparent", textAlign: "left", border: "1px solid #331111", color: "#ff4444", transition: "all 0.2s", width: "100%" }}>
            Delete my account and all data
          </button>
        </div>

        <p style={{ fontSize: 11, color: C.faint, textAlign: "center", marginTop: 24 }}>GraceFinance v4.0.0</p>
      </div>
    </div>
  )
}