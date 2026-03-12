/**
 * SettingsPage — v7.1 Unhinged Mode Support
 * Grace AI coaching style (now with "Unhinged"), notification scheduling,
 * data exports, session management, account deletion. Zero overlap with Profile.
 *
 * v7.1 CHANGES:
 *   - Added "Unhinged" to COACHING_STYLES with warning description
 *   - Added confirmation modal before activating unhinged mode
 */

import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useProfile } from "../hooks/useProfile"

var C = { bg: "#000000", card: "#0a0a0a", card2: "#0d0d0d", border: "#1a1a1a", border2: "#222222", text: "#ffffff", muted: "#9ca3af", dim: "#6b7280", faint: "#4b5563", accent: "#c8b8ff", accentDim: "#8b7fc7", accentFaint: "rgba(200, 184, 255, 0.06)", green: "#34d399", red: "#ff4444", redDim: "#331111", warn: "#f59e0b", warnDim: "rgba(245, 158, 11, 0.08)", warnBorder: "rgba(245, 158, 11, 0.25)" }
var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

var COACHING_STYLES = [
  { id: "encouraging", label: "Encouraging", desc: "Warm, supportive nudges that celebrate progress" },
  { id: "direct", label: "Direct", desc: "Straight talk, no fluff, action-oriented" },
  { id: "balanced", label: "Balanced", desc: "A mix of honesty and encouragement" },
  { id: "unhinged", label: "Unhinged", desc: "Brutally honest, hilariously blunt, zero filter", badge: "NEW" }
]

var REMINDER_TIMES = [
  { value: "07:00", label: "7:00 AM" },
  { value: "08:00", label: "8:00 AM" },
  { value: "09:00", label: "9:00 AM" },
  { value: "10:00", label: "10:00 AM" },
  { value: "12:00", label: "12:00 PM" },
  { value: "13:00", label: "1:00 PM" },
  { value: "18:00", label: "6:00 PM" },
  { value: "20:00", label: "8:00 PM" }
]

var API_BASE = (function () {
  var host = window.location.hostname
  if (host === "localhost" || host === "127.0.0.1") return "http://localhost:8000"
  return "https://gracefinance-production.up.railway.app"
})()

function Toggle(props) {
  var active = props.active
  return (
    <div onClick={props.onToggle} style={{ width: 40, height: 22, borderRadius: 11, cursor: "pointer", background: active ? C.text : C.border, position: "relative", transition: "background 0.2s ease" }}>
      <div style={{ width: 16, height: 16, borderRadius: "50%", background: active ? C.bg : C.dim, position: "absolute", top: 3, left: active ? 21 : 3, transition: "left 0.2s ease" }} />
    </div>
  )
}

function Toast(props) {
  if (!props.message) return null
  return (
    <div style={{
      position: "fixed", bottom: 32, left: "50%", transform: "translateX(-50%)",
      background: C.card2, border: "1px solid " + C.border2, borderRadius: 10,
      padding: "12px 20px", fontSize: 13, color: C.green, fontFamily: FONT,
      fontWeight: 500, zIndex: 9999, display: "flex", alignItems: "center", gap: 8,
      boxShadow: "0 8px 32px rgba(0,0,0,0.5)", animation: "toastIn 0.3s ease"
    }}>
      <span style={{ fontSize: 14 }}>&#10003;</span>
      {props.message}
    </div>
  )
}

function UnhingedConfirmModal(props) {
  if (!props.show) return null
  return (
    <div style={{
      position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 10000,
      background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center",
      padding: 24, animation: "toastIn 0.2s ease"
    }} onClick={props.onCancel}>
      <div onClick={function (e) { e.stopPropagation() }} style={{
        background: C.card, border: "1px solid " + C.border2, borderRadius: 14,
        padding: 28, maxWidth: 400, width: "100%",
        boxShadow: "0 16px 48px rgba(0,0,0,0.6)"
      }}>
        <div style={{ fontSize: 28, marginBottom: 12, textAlign: "center" }}>&#128293;</div>
        <h3 style={{ fontSize: 16, fontWeight: 700, color: C.text, margin: "0 0 8px", textAlign: "center", fontFamily: FONT }}>Enable Unhinged Mode?</h3>
        <p style={{ fontSize: 13, color: C.muted, lineHeight: 1.7, margin: "0 0 20px", textAlign: "center" }}>
          Grace will be brutally honest, hilariously blunt, and hold absolutely nothing back. Same behavioral insights, zero filter on delivery. You can switch back anytime.
        </p>
        <p style={{ fontSize: 11, color: C.warn, lineHeight: 1.6, margin: "0 0 20px", textAlign: "center", padding: "10px 14px", background: C.warnDim, border: "1px solid " + C.warnBorder, borderRadius: 8 }}>
          Grace will roast your spending habits. If you're not ready to laugh at yourself, maybe stick with Balanced.
        </p>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={props.onCancel} style={{
            flex: 1, padding: "11px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT,
            cursor: "pointer", background: "transparent", border: "1px solid " + C.border, color: C.dim, transition: "all 0.2s"
          }}
            onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
            onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
          >Nevermind</button>
          <button onClick={props.onConfirm} style={{
            flex: 1, padding: "11px", borderRadius: 8, fontSize: 13, fontWeight: 700, fontFamily: FONT,
            cursor: "pointer", background: C.text, border: "none", color: C.bg, transition: "all 0.2s"
          }}
            onMouseEnter={function (e) { e.target.style.opacity = "0.85" }}
            onMouseLeave={function (e) { e.target.style.opacity = "1" }}
          >Let's Go</button>
        </div>
      </div>
    </div>
  )
}

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
      alert("Export failed. Please try again.")
    })
    .finally(function () {
      setLoading(false)
    })
}

export default function SettingsPage() {
  var navigate = useNavigate()
  var auth = useAuth(); var logout = auth.logout; var user = auth.user
  var profileHook = useProfile(); var profile = profileHook.profile

  /* Grace AI coaching style */
  var coachingStyleState = useState("balanced"); var coachingStyle = coachingStyleState[0]; var setCoachingStyle = coachingStyleState[1]

  /* Unhinged confirmation modal */
  var unhingedModalState = useState(false); var showUnhingedModal = unhingedModalState[0]; var setShowUnhingedModal = unhingedModalState[1]

  /* Notification prefs */
  var reminderState = useState(true); var dailyReminder = reminderState[0]; var setDailyReminder = reminderState[1]
  var reminderTimeState = useState("13:00"); var reminderTime = reminderTimeState[0]; var setReminderTime = reminderTimeState[1]
  var timeDropdownState = useState(false); var timeDropdownOpen = timeDropdownState[0]; var setTimeDropdownOpen = timeDropdownState[1]

  /* Export states */
  var exportingCheckinsState = useState(false); var exportingCheckins = exportingCheckinsState[0]; var setExportingCheckins = exportingCheckinsState[1]
  var exportingFCSState = useState(false); var exportingFCS = exportingFCSState[0]; var setExportingFCS = exportingFCSState[1]

  /* Delete account flow */
  var deleteStageState = useState("idle"); var deleteStage = deleteStageState[0]; var setDeleteStage = deleteStageState[1]
  var deleteInputState = useState(""); var deleteInput = deleteInputState[0]; var setDeleteInput = deleteInputState[1]
  var deletingState = useState(false); var deleting = deletingState[0]; var setDeleting = deletingState[1]
  var deleteErrorState = useState(""); var deleteError = deleteErrorState[0]; var setDeleteError = deleteErrorState[1]

  /* Toast */
  var toastState = useState(""); var toastMsg = toastState[0]; var setToastMsg = toastState[1]

  /* Animation */
  var mountedState = useState(false); var mounted = mountedState[0]; var setMounted = mountedState[1]

  useEffect(function () {
    setTimeout(function () { setMounted(true) }, 50)
  }, [])

  /* Load saved preferences from backend */
  useEffect(function () {
    var token = localStorage.getItem("grace_token")
    if (!token) return
    fetch(API_BASE + "/api/profile/preferences", {
      headers: { Authorization: "Bearer " + token }
    })
      .then(function (res) { if (res.ok) return res.json(); throw new Error("Failed") })
      .then(function (data) {
        if (data.coaching_style) setCoachingStyle(data.coaching_style)
        if (data.reminder_time) setReminderTime(data.reminder_time)
        if (data.daily_reminder !== undefined) setDailyReminder(data.daily_reminder)
      })
      .catch(function () { /* defaults are fine */ })
  }, [])

  /* Close time dropdown on outside click */
  useEffect(function () {
    if (!timeDropdownOpen) return
    function handleClick() { setTimeDropdownOpen(false) }
    setTimeout(function () { document.addEventListener("click", handleClick) }, 0)
    return function () { document.removeEventListener("click", handleClick) }
  }, [timeDropdownOpen])

  function showToast(msg) {
    setToastMsg(msg)
    setTimeout(function () { setToastMsg("") }, 2400)
  }

  function savePreference(key, value) {
    var token = localStorage.getItem("grace_token")
    var body = {}
    body[key] = value
    fetch(API_BASE + "/api/profile/preferences", {
      method: "PATCH",
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
      body: JSON.stringify(body)
    })
      .then(function (res) {
        if (res.ok) showToast("Preference saved")
      })
      .catch(function () { /* silent fail */ })
  }

  function handleReminderToggle() {
    var next = !dailyReminder
    setDailyReminder(next)
    savePreference("daily_reminder", next)
  }

  function handleReminderTime(value) {
    setReminderTime(value)
    setTimeDropdownOpen(false)
    savePreference("reminder_time", value)
  }

  function handleCoachingStyle(styleId) {
    /* If selecting unhinged and not already on it, show confirmation */
    if (styleId === "unhinged" && coachingStyle !== "unhinged") {
      setShowUnhingedModal(true)
      return
    }
    setCoachingStyle(styleId)
    savePreference("coaching_style", styleId)
  }

  function confirmUnhinged() {
    setShowUnhingedModal(false)
    setCoachingStyle("unhinged")
    savePreference("coaching_style", "unhinged")
  }

  function cancelUnhinged() {
    setShowUnhingedModal(false)
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

  function getSelectedTimeLabel() {
    for (var i = 0; i < REMINDER_TIMES.length; i++) {
      if (REMINDER_TIMES[i].value === reminderTime) return REMINDER_TIMES[i].label
    }
    return "1:00 PM"
  }

  var cardStyle = { background: C.card, border: "1px solid " + C.border, borderRadius: 12, padding: 24, marginBottom: 16 }
  var sectionLabel = { fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }

  function sectionStyle(delay) {
    return {
      opacity: mounted ? 1 : 0,
      transform: mounted ? "translateY(0)" : "translateY(12px)",
      transition: "opacity 0.4s ease " + delay + "s, transform 0.4s ease " + delay + "s"
    }
  }

  function exportBtnStyle(isExporting) {
    return {
      padding: "12px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT,
      cursor: isExporting ? "not-allowed" : "pointer", background: "transparent", textAlign: "left",
      border: "1px solid " + C.border, color: C.dim, transition: "all 0.2s", opacity: isExporting ? 0.5 : 1, width: "100%",
    }
  }

  var userEmail = (profile && profile.email) || (user && user.email) || null

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: FONT, display: "flex", flexDirection: "column", alignItems: "center", padding: "40px 24px" }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder{color:#6b7280!important}@keyframes toastIn{from{opacity:0;transform:translateX(-50%) translateY(12px)}to{opacity:1;transform:translateX(-50%) translateY(0)}}"}</style>

      <Toast message={toastMsg} />
      <UnhingedConfirmModal show={showUnhingedModal} onConfirm={confirmUnhinged} onCancel={cancelUnhinged} />

      <div style={{ width: "100%", maxWidth: 560 }}>

        {/* ── Header ── */}
        <div style={sectionStyle(0)}>
          <div style={{ display: "flex", gap: 8, marginBottom: 32 }}>
            <button onClick={function () { navigate("/dashboard") }} style={{ background: "transparent", border: "1px solid " + C.border, borderRadius: 6, padding: "8px 16px", color: C.dim, fontSize: 12, fontFamily: FONT, cursor: "pointer", transition: "all 0.2s" }}
              onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
              onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
            >Dashboard</button>
            <button onClick={function () { navigate("/profile") }} style={{ background: "transparent", border: "1px solid " + C.border, borderRadius: 6, padding: "8px 16px", color: C.dim, fontSize: 12, fontFamily: FONT, cursor: "pointer", transition: "all 0.2s" }}
              onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
              onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
            >Profile</button>
          </div>

          <div style={{ marginBottom: 32 }}>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: C.text, margin: "0 0 6px", letterSpacing: "-0.02em" }}>Settings</h1>
            <p style={{ fontSize: 13, color: C.dim, margin: 0 }}>Control how GraceFinance works for you.</p>
          </div>
        </div>

        {/* ── Grace AI Coaching Style ── */}
        <div style={sectionStyle(0.05)}>
          <div style={cardStyle}>
            <div style={sectionLabel}>Grace AI</div>
            <p style={{ fontSize: 13, color: C.dim, lineHeight: 1.7, margin: "0 0 16px" }}>
              Choose how Grace coaches you. This shapes the tone of every AI conversation.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {COACHING_STYLES.map(function (style) {
                var isActive = coachingStyle === style.id
                var isUnhinged = style.id === "unhinged"
                return (
                  <button key={style.id} onClick={function () { handleCoachingStyle(style.id) }} style={{
                    padding: "14px 16px", borderRadius: 8, fontSize: 13, fontFamily: FONT,
                    cursor: "pointer", background: isActive ? (isUnhinged ? "rgba(245, 158, 11, 0.06)" : C.accentFaint) : "transparent", textAlign: "left",
                    border: "1px solid " + (isActive ? (isUnhinged ? "rgba(245, 158, 11, 0.35)" : C.accentDim) : C.border), color: isActive ? C.text : C.dim,
                    transition: "all 0.2s", width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center"
                  }}
                    onMouseEnter={function (e) { if (!isActive) { e.currentTarget.style.borderColor = C.faint; e.currentTarget.style.color = C.text } }}
                    onMouseLeave={function (e) { if (!isActive) { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.color = C.dim } }}
                  >
                    <div style={{ pointerEvents: "none" }}>
                      <span style={{ fontWeight: isActive ? 600 : 500, display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
                        {style.label}
                        {style.badge && (
                          <span style={{ fontSize: 9, fontWeight: 700, color: isUnhinged && isActive ? "#f59e0b" : C.warn, background: isUnhinged && isActive ? "rgba(245, 158, 11, 0.15)" : "rgba(245, 158, 11, 0.1)", padding: "2px 6px", borderRadius: 4, letterSpacing: "0.05em" }}>{style.badge}</span>
                        )}
                      </span>
                      <span style={{ fontSize: 11, color: isActive ? C.muted : C.faint, fontWeight: 400 }}>{style.desc}</span>
                    </div>
                    {isActive && (
                      <span style={{ fontSize: 11, color: isUnhinged ? C.warn : C.accent, fontWeight: 600, flexShrink: 0, marginLeft: 12, pointerEvents: "none" }}>&#10003;</span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* ── Notifications ── */}
        <div style={sectionStyle(0.1)}>
          <div style={cardStyle}>
            <div style={sectionLabel}>Notifications</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 0", borderBottom: dailyReminder ? "1px solid " + C.border : "none" }}>
              <div>
                <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>Daily check-in reminder</span>
                <p style={{ fontSize: 12, color: C.dim, margin: "4px 0 0" }}>A gentle nudge to keep your streak alive.</p>
              </div>
              <Toggle active={dailyReminder} onToggle={handleReminderToggle} />
            </div>

            {dailyReminder && (
              <div style={{ paddingTop: 16, animation: "toastIn 0.2s ease" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>Reminder time</span>
                    <p style={{ fontSize: 12, color: C.dim, margin: "4px 0 0" }}>When should we send your daily nudge?</p>
                  </div>
                  <div style={{ position: "relative" }}>
                    <button onClick={function (e) { e.stopPropagation(); setTimeDropdownOpen(!timeDropdownOpen) }} style={{
                      padding: "6px 12px", borderRadius: 6, fontSize: 12, fontWeight: 500, fontFamily: FONT,
                      cursor: "pointer", background: C.card2, border: "1px solid " + (timeDropdownOpen ? C.faint : C.border2), color: C.text,
                      transition: "all 0.2s", minWidth: 90, textAlign: "center"
                    }}
                      onMouseEnter={function (e) { e.target.style.borderColor = C.faint }}
                      onMouseLeave={function (e) { if (!timeDropdownOpen) e.target.style.borderColor = C.border2 }}
                    >{getSelectedTimeLabel()}</button>

                    {timeDropdownOpen && (
                      <div onClick={function (e) { e.stopPropagation() }} style={{
                        position: "absolute", top: "calc(100% + 6px)", right: 0, background: C.card2,
                        border: "1px solid " + C.border2, borderRadius: 8, overflow: "hidden", zIndex: 100,
                        boxShadow: "0 8px 24px rgba(0,0,0,0.5)", minWidth: 120
                      }}>
                        {REMINDER_TIMES.map(function (t) {
                          var isSelected = t.value === reminderTime
                          return (
                            <button key={t.value} onClick={function () { handleReminderTime(t.value) }} style={{
                              display: "block", width: "100%", padding: "10px 14px", fontSize: 12, fontFamily: FONT,
                              background: isSelected ? C.accentFaint : "transparent", color: isSelected ? C.text : C.dim,
                              border: "none", cursor: "pointer", textAlign: "left", transition: "all 0.15s"
                            }}
                              onMouseEnter={function (e) { if (!isSelected) { e.target.style.background = "rgba(255,255,255,0.03)"; e.target.style.color = C.text } }}
                              onMouseLeave={function (e) { if (!isSelected) { e.target.style.background = "transparent"; e.target.style.color = C.dim } }}
                            >{t.label}</button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Data Exports ── */}
        <div style={sectionStyle(0.15)}>
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
        </div>

        {/* ── Session ── */}
        <div style={sectionStyle(0.2)}>
          <div style={cardStyle}>
            <div style={sectionLabel}>Session</div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>Signed in</span>
                {userEmail && <p style={{ fontSize: 12, color: C.dim, margin: "4px 0 0" }}>{userEmail}</p>}
              </div>
              <button onClick={function () { if (logout) logout(); navigate("/") }} style={{
                padding: "8px 14px", borderRadius: 6, fontSize: 12, fontWeight: 500, fontFamily: FONT,
                cursor: "pointer", background: "transparent", border: "1px solid " + C.border, color: C.dim, transition: "all 0.2s"
              }}
                onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
                onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
              >Sign Out</button>
            </div>
          </div>
        </div>

        {/* ── Danger Zone ── */}
        <div style={sectionStyle(0.25)}>
          <div style={Object.assign({}, cardStyle, { border: "1px solid " + (deleteStage === "confirm" ? C.redDim : C.border) })}>
            <div style={sectionLabel}>Danger Zone</div>
            {deleteStage === "idle" && (
              <button onClick={handleDeleteAccount} style={{
                padding: "12px 16px", borderRadius: 8, fontSize: 13, fontWeight: 500, fontFamily: FONT,
                cursor: "pointer", background: "transparent", textAlign: "left", width: "100%",
                border: "1px solid " + C.redDim, color: C.red, transition: "all 0.2s",
              }}
                onMouseEnter={function (e) { e.target.style.borderColor = C.red; e.target.style.background = "#0a0000" }}
                onMouseLeave={function (e) { e.target.style.borderColor = C.redDim; e.target.style.background = "transparent" }}
              >Delete my account and all data</button>
            )}
            {deleteStage === "confirm" && (
              <div>
                <p style={{ fontSize: 13, color: C.red, lineHeight: 1.7, margin: "0 0 12px" }}>
                  This is permanent. All your check-ins, FCS history, and profile data will be erased. This cannot be undone.
                </p>
                <p style={{ fontSize: 12, color: C.dim, margin: "0 0 12px" }}>
                  Type <span style={{ color: C.text, fontWeight: 600 }}>DELETE</span> to confirm.
                </p>
                <input value={deleteInput} onChange={function (e) { setDeleteInput(e.target.value) }} placeholder="Type DELETE" style={{
                  width: "100%", padding: "10px 0", fontSize: 14, fontFamily: FONT, color: C.text, background: "transparent",
                  border: "none", borderBottom: "1px solid " + C.redDim, outline: "none", boxSizing: "border-box",
                  marginBottom: 16, letterSpacing: "0.05em",
                }} onFocus={function (e) { e.target.style.borderColor = C.red }} onBlur={function (e) { e.target.style.borderColor = C.redDim }} />
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
                    background: deleteInput === "DELETE" ? C.red : "transparent",
                    border: "1px solid " + C.red,
                    color: deleteInput === "DELETE" ? C.bg : C.red,
                    transition: "all 0.2s", opacity: (deleteInput !== "DELETE" || deleting) ? 0.4 : 1,
                  }}>{deleting ? "Deleting..." : "Delete Forever"}</button>
                </div>
                {deleteError && (<p style={{ color: C.red, fontSize: 12, marginTop: 10 }}>{deleteError}</p>)}
              </div>
            )}
          </div>
        </div>

        <p style={{ fontSize: 11, color: C.faint, textAlign: "center", marginTop: 24, opacity: mounted ? 1 : 0, transition: "opacity 0.4s ease 0.3s" }}>GraceFinance v7.1</p>
      </div>
    </div>
  )
}