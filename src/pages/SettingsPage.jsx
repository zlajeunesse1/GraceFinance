/**
 * SettingsPage — v6 Clean Machine
 * Every button works. No dead UI. Data exports + account management.
 */

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
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

export default function SettingsPage() {
  var navigate = useNavigate()
  var auth = useAuth(); var logout = auth.logout
  var profileHook = useProfile(); var updateProfile = profileHook.updateProfile

  var reminderState = useState(true); var dailyReminder = reminderState[0]; var setDailyReminder = reminderState[1]

  var exportingCheckinsState = useState(false); var exportingCheckins = exportingCheckinsState[0]; var setExportingCheckins = exportingCheckinsState[1]
  var exportingFCSState = useState(false); var exportingFCS = exportingFCSState[0]; var setExportingFCS = exportingFCSState[1]

  /* Delete account flow */
  var deleteStageState = useState("idle"); var deleteStage = deleteStageState[0]; var setDeleteStage = deleteStageState[1]
  var deleteInputState = useState(""); var deleteInput = deleteInputState[0]; var setDeleteInput = deleteInputState[1]
  var deletingState = useState(false); var deleting = deletingState[0]; var setDeleting = deletingState[1]
  var deleteErrorState = useState(""); var deleteError = deleteErrorState[0]; var setDeleteError = deleteErrorState[1]

  var cardStyle = { background: C.card, border: "1px solid " + C.border, borderRadius: 12, padding: 24, marginBottom: 16 }
  var sectionLabel = { fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }

  function exportBtnStyle(isExporting) {
    return {
      padding: "12px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT,
      cursor: isExporting ? "not-allowed" : "pointer", background: "transparent", textAlign: "left",
      border: "1px solid " + C.border, color: C.dim, transition: "all 0.2s", opacity: isExporting ? 0.5 : 1, width: "100%",
    }
  }

  function handleDeleteAccount() {
    if (deleteStage === "idle") {
      setDeleteStage("confirm")
      return
    }
    if (deleteStage === "confirm" && deleteInput === "DELETE") {
      setDeleting(true)
      setDeleteError("")
      var token = localStorage.getItem("grace_token")
      fetch(API_BASE + "/api/profile/account", {
        method: "DELETE",
        headers: { Authorization: "Bearer " + token },
      })
        .then(function (res) {
          if (!res.ok) throw new Error("Delete failed (" + res.status + ")")
          /* Clear local data and redirect */
          localStorage.removeItem("grace_token")
          localStorage.removeItem("grace-onboarding-complete")
          localStorage.removeItem("grace-onboarding-data")
          if (logout) logout()
          navigate("/")
        })
        .catch(function (err) {
          console.error("Delete error:", err)
          setDeleteError("Failed to delete account. Please try again or contact support.")
          setDeleting(false)
        })
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: FONT, display: "flex", flexDirection: "column", alignItems: "center", padding: "40px 24px" }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder { color: #6b7280 !important; }"}</style>
      <div style={{ width: "100%", maxWidth: 560 }}>
        <button onClick={function () { navigate("/dashboard") }} style={{ background: "transparent", border: "1px solid " + C.border, borderRadius: 6, padding: "8px 16px", color: C.dim, fontSize: 12, fontFamily: FONT, cursor: "pointer", marginBottom: 32, transition: "all 0.2s" }}
          onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
          onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
        >Dashboard</button>

        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: C.text, margin: "0 0 6px", letterSpacing: "-0.02em" }}>Settings</h1>
          <p style={{ fontSize: 13, color: C.dim, margin: 0 }}>Manage your notifications, data, and account.</p>
        </div>

        {/* ── Notifications ── */}
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

        {/* ── Data Exports ── */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Your Data</div>
          <p style={{ fontSize: 13, color: C.dim, lineHeight: 1.7, margin: "0 0 16px" }}>
            Your data belongs to you. Export it anytime.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <button disabled={exportingCheckins} onClick={function () { downloadCSV("checkins", "gracefinance_checkins.csv", setExportingCheckins) }} style={exportBtnStyle(exportingCheckins)}
              onMouseEnter={function (e) { if (!exportingCheckins) { e.target.style.color = C.text; e.target.style.borderColor = C.faint } }}
              onMouseLeave={function (e) { if (!exportingCheckins) { e.target.style.color = C.dim; e.target.style.borderColor = C.border } }}
            >{exportingCheckins ? "Exporting..." : "Export check-in history (CSV)"}</button>
            <button disabled={exportingFCS} onClick={function () { downloadCSV("fcs-trend", "gracefinance_fcs_trend.csv", setExportingFCS) }} style={exportBtnStyle(exportingFCS)}
              onMouseEnter={function (e) { if (!exportingFCS) { e.target.style.color = C.text; e.target.style.borderColor = C.faint } }}
              onMouseLeave={function (e) { if (!exportingFCS) { e.target.style.color = C.dim; e.target.style.borderColor = C.border } }}
            >{exportingFCS ? "Exporting..." : "Export FCS trend data (CSV)"}</button>
          </div>
        </div>

        {/* ── Danger Zone ── */}
        <div style={Object.assign({}, cardStyle, { border: "1px solid " + (deleteStage === "confirm" ? "#331111" : C.border) })}>
          <div style={sectionLabel}>Account</div>
          {deleteStage === "idle" && (
            <button onClick={handleDeleteAccount} style={{
              padding: "12px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT,
              cursor: "pointer", background: "transparent", textAlign: "left", width: "100%",
              border: "1px solid #331111", color: "#ff4444", transition: "all 0.2s",
            }}
              onMouseEnter={function (e) { e.target.style.borderColor = "#ff4444"; e.target.style.background = "#0a0000" }}
              onMouseLeave={function (e) { e.target.style.borderColor = "#331111"; e.target.style.background = "transparent" }}
            >Delete my account and all data</button>
          )}
          {deleteStage === "confirm" && (
            <div>
              <p style={{ fontSize: 13, color: "#ff4444", lineHeight: 1.7, margin: "0 0 12px" }}>
                This is permanent. All your check-ins, FCS history, and profile data will be erased. This cannot be undone.
              </p>
              <p style={{ fontSize: 12, color: C.dim, margin: "0 0 12px" }}>
                Type <span style={{ color: C.text, fontWeight: 600 }}>DELETE</span> to confirm.
              </p>
              <input value={deleteInput} onChange={function (e) { setDeleteInput(e.target.value) }} placeholder="Type DELETE" style={{
                width: "100%", padding: "10px 0", fontSize: 14, fontFamily: FONT, color: C.text, background: "transparent",
                border: "none", borderBottom: "1px solid #331111", outline: "none", boxSizing: "border-box",
                marginBottom: 16, letterSpacing: "0.05em",
              }} onFocus={function (e) { e.target.style.borderColor = "#ff4444" }} onBlur={function (e) { e.target.style.borderColor = "#331111" }} />
              <div style={{ display: "flex", gap: 10 }}>
                <button onClick={function () { setDeleteStage("idle"); setDeleteInput(""); setDeleteError("") }} style={{
                  flex: 1, padding: "10px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT,
                  cursor: "pointer", background: "transparent", border: "1px solid " + C.border, color: C.dim, transition: "all 0.2s",
                }}
                  onMouseEnter={function (e) { e.target.style.color = C.text }}
                  onMouseLeave={function (e) { e.target.style.color = C.dim }}
                >Cancel</button>
                <button onClick={handleDeleteAccount} disabled={deleteInput !== "DELETE" || deleting} style={{
                  flex: 1, padding: "10px", borderRadius: 8, fontSize: 13, fontWeight: 600, fontFamily: FONT,
                  cursor: (deleteInput !== "DELETE" || deleting) ? "not-allowed" : "pointer",
                  background: deleteInput === "DELETE" ? "#ff4444" : "transparent",
                  border: "1px solid #ff4444",
                  color: deleteInput === "DELETE" ? "#000000" : "#ff4444",
                  transition: "all 0.2s", opacity: (deleteInput !== "DELETE" || deleting) ? 0.4 : 1,
                }}>{deleting ? "Deleting..." : "Delete Forever"}</button>
              </div>
              {deleteError && (<p style={{ color: "#ff4444", fontSize: 12, marginTop: 10 }}>{deleteError}</p>)}
            </div>
          )}
        </div>

        <p style={{ fontSize: 11, color: C.faint, textAlign: "center", marginTop: 24 }}>GraceFinance v6.0</p>
      </div>
    </div>
  )
}