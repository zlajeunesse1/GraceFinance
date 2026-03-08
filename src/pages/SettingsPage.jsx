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

var API_BASE = (function () {
  var host = window.location.hostname
  if (host === "localhost" || host === "127.0.0.1") return "http://localhost:8000"
  return "https://gracefinance-production.up.railway.app"
})()

export default function SettingsPage() {
  var navigate = useNavigate()
  var profileHook = useProfile(); var updateProfile = profileHook.updateProfile

  var reminderState = useState(true); var dailyReminder = reminderState[0]; var setDailyReminder = reminderState[1]

  var exportingCheckinsState = useState(false); var exportingCheckins = exportingCheckinsState[0]; var setExportingCheckins = exportingCheckinsState[1]
  var exportingFCSState = useState(false); var exportingFCS = exportingFCSState[0]; var setExportingFCS = exportingFCSState[1]

  var cardStyle = { background: C.card, border: "1px solid " + C.border, borderRadius: 12, padding: 24, marginBottom: 16 }
  var sectionLabel = { fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }

  function downloadCSV(endpoint, fallbackFilename, setLoading) {
    setLoading(true)
    var token = localStorage.getItem("grace_token")
    fetch(API_BASE + "/api/export/" + endpoint, {
      headers: { Authorization: "Bearer " + token },
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Export failed (" + res.status + ")")
        var disposition = res.headers.get("Content-Disposition")
        var filename = fallbackFilename
        if (disposition) {
          var match = disposition.match(/filename="?([^"]+)"?/)
          if (match) filename = match[1]
        }
        return res.blob().then(function (blob) { return { blob: blob, filename: filename } })
      })
      .then(function (result) {
        var url = window.URL.createObjectURL(result.blob)
        var a = document.createElement("a")
        a.href = url
        a.download = result.filename
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      })
      .catch(function (err) {
        console.error("Export error:", err)
        alert("Export failed — please try again.")
      })
      .finally(function () {
        setLoading(false)
      })
  }

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
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0" }}>
            <div>
              <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>Daily check-in reminder</span>
              <p style={{ fontSize: 12, color: C.dim, margin: "4px 0 0" }}>A gentle nudge each morning to keep your streak alive.</p>
            </div>
            <Toggle active={dailyReminder} onToggle={function () { setDailyReminder(!dailyReminder) }} />
          </div>
        </div>

        <div style={cardStyle}>
          <div style={sectionLabel}>Your Data</div>
          <p style={{ fontSize: 13, color: C.dim, lineHeight: 1.7, margin: "0 0 16px" }}>
            Your data belongs to you. Export it anytime, or delete your account entirely.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <button disabled={exportingCheckins} onClick={function () { downloadCSV("checkins", "gracefinance_checkins.csv", setExportingCheckins) }} style={{ padding: "12px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT, cursor: "pointer", background: "transparent", textAlign: "left", border: "1px solid " + C.border, color: C.dim, transition: "all 0.2s", opacity: exportingCheckins ? 0.5 : 1 }}
              onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
              onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
            >{exportingCheckins ? "Exporting…" : "Export check-in history (CSV)"}</button>
            <button disabled={exportingFCS} onClick={function () { downloadCSV("fcs-trend", "gracefinance_fcs_trend.csv", setExportingFCS) }} style={{ padding: "12px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT, cursor: "pointer", background: "transparent", textAlign: "left", border: "1px solid " + C.border, color: C.dim, transition: "all 0.2s", opacity: exportingFCS ? 0.5 : 1 }}
              onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
              onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
            >{exportingFCS ? "Exporting…" : "Export FCS trend data (CSV)"}</button>
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