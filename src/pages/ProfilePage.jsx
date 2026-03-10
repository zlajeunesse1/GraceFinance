/**
 * ProfilePage — v6 Behavioral Mirror
 * Full reflection of onboarding data. Editable financial snapshot.
 * No dead buttons. This is the user's behavioral safe haven.
 */

import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { useProfile } from "../hooks/useProfile"

var C = { bg: "#000000", card: "#0a0a0a", border: "#1a1a1a", text: "#ffffff", muted: "#9ca3af", dim: "#6b7280", faint: "#4b5563" }
var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

var RISK_OPTIONS = [
  { value: "calm", label: "Conservative", desc: "Prioritize safety and stability" },
  { value: "balanced", label: "Balanced", desc: "Steady growth with managed risk" },
  { value: "aggressive", label: "Growth", desc: "Maximize long-term upside" },
]

var goalOptions = [
  { id: "save", label: "Build Savings", desc: "Grow your cushion and emergency fund" },
  { id: "debt", label: "Reduce Debt", desc: "Pay down what you owe systematically" },
  { id: "track", label: "Understand Spending", desc: "See where your money actually goes" },
  { id: "budget", label: "Create a System", desc: "Build a budget that works for your life" },
  { id: "wealth", label: "Grow Wealth", desc: "Invest, build assets, plan for the future" },
  { id: "habits", label: "Change Behavior", desc: "Break old patterns, build better ones" },
]

function getTierDisplay(tier) {
  var t = (tier || "free").toLowerCase()
  if (t === "premium") return "GracePremium"
  if (t === "pro") return "GracePro"
  return "Free"
}

function formatCurrency(num) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(num)
}

function CurrencyInput(props) {
  var inputRef = useRef(null)
  function handleChange(e) {
    var raw = e.target.value.replace(/[^0-9]/g, "")
    props.onChange(raw === "" ? "" : parseInt(raw, 10))
  }
  return (
    <div style={{ position: "relative", width: "100%" }}>
      <span style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)", fontSize: 14, fontFamily: FONT, color: props.value ? C.text : C.dim, fontWeight: 400, pointerEvents: "none" }}>$</span>
      <input ref={inputRef} type="text" inputMode="numeric" value={props.value === "" ? "" : (typeof props.value === "number" ? props.value.toLocaleString() : props.value)} onChange={handleChange} placeholder={props.placeholder || "0"} style={{
        width: "100%", padding: "12px 0 12px 16px", fontSize: 14, fontFamily: FONT, fontWeight: 400, color: C.text, background: "transparent", border: "none", borderBottom: "1px solid " + C.faint, outline: "none", transition: "border-color 0.2s ease", boxSizing: "border-box", letterSpacing: "-0.01em", fontVariantNumeric: "tabular-nums",
      }} onFocus={function (e) { e.target.style.borderColor = C.text }} onBlur={function (e) { e.target.style.borderColor = C.faint }} />
    </div>
  )
}

export default function ProfilePage() {
  var navigate = useNavigate()
  var auth = useAuth(); var user = auth.user
  var profileHook = useProfile()
  var profile = profileHook.profile; var isLoading = profileHook.isLoading
  var isSaving = profileHook.isSaving; var saveError = profileHook.saveError; var updateProfile = profileHook.updateProfile

  /* Preferences */
  var displayNameState = useState(""); var displayName = displayNameState[0]; var setDisplayName = displayNameState[1]
  var timezoneState = useState("America/New_York"); var timezone = timezoneState[0]; var setTimezone = timezoneState[1]
  var currencyState = useState("USD"); var currency = currencyState[0]; var setCurrency = currencyState[1]
  var riskState = useState("balanced"); var riskStyle = riskState[0]; var setRiskStyle = riskState[1]

  /* Financial Snapshot — mirrors onboarding */
  var incomeState = useState(""); var income = incomeState[0]; var setIncome = incomeState[1]
  var expensesState = useState(""); var expenses = expensesState[0]; var setExpenses = expensesState[1]
  var debtState = useState(""); var debt = debtState[0]; var setDebt = debtState[1]

  /* Goals & Mission — mirrors onboarding */
  var goalsState = useState([]); var selectedGoals = goalsState[0]; var setSelectedGoals = goalsState[1]
  var missionState = useState(""); var mission = missionState[0]; var setMission = missionState[1]

  /* UI state */
  var savedState = useState(false); var saved = savedState[0]; var setSaved = savedState[1]
  var focusedState = useState(null); var focused = focusedState[0]; var setFocused = focusedState[1]

  var currentTier = (user && user.subscription_tier ? user.subscription_tier : "free").toLowerCase()
  var isPremium = currentTier === "premium"

  /* Computed financial metrics */
  var incomeVal = income === "" ? 0 : income
  var expensesVal = expenses === "" ? 0 : expenses
  var debtVal = debt === "" ? 0 : debt
  var available = incomeVal - expensesVal
  var savingsRate = incomeVal > 0 ? ((available / incomeVal) * 100).toFixed(0) : 0

  useEffect(function () {
    if (profile) {
      setDisplayName(profile.display_name || "")
      setTimezone(profile.timezone || "America/New_York")
      setCurrency(profile.currency || "USD")
      setRiskStyle(profile.risk_style || "balanced")
      /* Load financial fields from profile if available */
      if (profile.income !== undefined && profile.income !== null) setIncome(profile.income)
      if (profile.expenses !== undefined && profile.expenses !== null) setExpenses(profile.expenses)
      if (profile.debt !== undefined && profile.debt !== null) setDebt(profile.debt)
      if (profile.goals && Array.isArray(profile.goals)) setSelectedGoals(profile.goals)
      if (profile.mission) setMission(profile.mission)
    }
    /* Fallback: load from onboarding localStorage if profile fields are empty */
    if (profile && !profile.income && !profile.expenses) {
      try {
        var raw = localStorage.getItem("grace-onboarding-data")
        if (raw) {
          var data = JSON.parse(raw)
          if (data.income && !profile.income) setIncome(data.income)
          if (data.expenses && !profile.expenses) setExpenses(data.expenses)
          if (data.debt !== undefined && !profile.debt) setDebt(data.debt)
          if (data.goals && data.goals.length > 0 && (!profile.goals || profile.goals.length === 0)) setSelectedGoals(data.goals)
          if (data.mission && !profile.mission) setMission(data.mission)
        }
      } catch (e) { /* ignore parse errors */ }
    }
  }, [profile])

  function toggleGoal(id) {
    if (selectedGoals.indexOf(id) >= 0) {
      setSelectedGoals(selectedGoals.filter(function (g) { return g !== id }))
    } else {
      setSelectedGoals(selectedGoals.concat([id]))
    }
  }

  async function handleSave() {
    await updateProfile({
      display_name: displayName || null,
      timezone: timezone,
      currency: currency,
      risk_style: riskStyle,
      income: income === "" ? null : income,
      expenses: expenses === "" ? null : expenses,
      debt: debt === "" ? null : debt,
      goals: selectedGoals,
      mission: mission || null,
    })
    setSaved(true)
    setTimeout(function () { setSaved(false) }, 2000)
  }

  var inputStyle = function (field) {
    return { width: "100%", padding: "12px 0", fontSize: 14, fontFamily: FONT, fontWeight: 400, color: C.text, background: "transparent", border: "none", borderBottom: "1px solid " + (focused === field ? C.text : C.faint), outline: "none", transition: "border-color 0.3s ease", letterSpacing: "0.01em", boxSizing: "border-box" }
  }
  var labelStyle = { display: "block", fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4 }
  var cardStyle = { background: C.card, border: "1px solid " + C.border, borderRadius: 12, padding: 24, marginBottom: 16 }
  var sectionLabel = { fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }

  if (auth.loading || isLoading) {
    return (<div style={{ minHeight: "100vh", background: C.bg, color: C.dim, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontFamily: FONT }}>Loading...</div>)
  }

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: FONT, display: "flex", flexDirection: "column", alignItems: "center", padding: "40px 24px" }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder { color: #6b7280 !important; }input:-webkit-autofill { -webkit-box-shadow: 0 0 0 30px #000000 inset !important; -webkit-text-fill-color: #ffffff !important; }"}</style>
      <div style={{ width: "100%", maxWidth: 560 }}>
        <button onClick={function () { navigate("/dashboard") }} style={{ background: "transparent", border: "1px solid " + C.border, borderRadius: 6, padding: "8px 16px", color: C.dim, fontSize: 12, fontFamily: FONT, cursor: "pointer", marginBottom: 32, transition: "all 0.2s" }}
          onMouseEnter={function (e) { e.target.style.color = C.text; e.target.style.borderColor = C.faint }}
          onMouseLeave={function (e) { e.target.style.color = C.dim; e.target.style.borderColor = C.border }}
        >Dashboard</button>

        <div style={{ marginBottom: 32 }}>
          <h1 style={{ fontSize: 22, fontWeight: 600, color: C.text, margin: "0 0 6px", letterSpacing: "-0.02em" }}>Your Profile</h1>
          <p style={{ fontSize: 13, color: C.dim, margin: 0 }}>Your complete financial picture. Update anytime as your life changes.</p>
        </div>

        {/* ── Account (read-only) ── */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Account</div>
          {[
            { label: "Name", value: user ? ((user.first_name || "") + " " + (user.last_name || "")).trim() || "..." : "..." },
            { label: "Email", value: user ? user.email : "..." },
            { label: "Member since", value: user && user.created_at ? new Date(user.created_at).toLocaleDateString() : "..." },
          ].map(function (item, i) {
            return (<div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "11px 0", borderBottom: "1px solid " + C.border }}>
              <span style={{ fontSize: 13, color: C.dim }}>{item.label}</span>
              <span style={{ fontSize: 13, color: C.text, fontWeight: 500, fontVariantNumeric: "tabular-nums" }}>{item.value}</span>
            </div>)
          })}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "11px 0" }}>
            <span style={{ fontSize: 13, color: C.dim }}>Plan</span>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 13, color: C.text, fontWeight: 500 }}>{getTierDisplay(currentTier)}</span>
              {!isPremium && (
                <button
                  onClick={function () { navigate("/upgrade") }}
                  style={{ background: "transparent", border: "1px solid " + C.border, borderRadius: 6, padding: "4px 10px", color: C.muted, fontSize: 11, fontWeight: 600, fontFamily: FONT, cursor: "pointer", transition: "all 0.2s" }}
                  onMouseEnter={function (e) { e.target.style.borderColor = C.faint; e.target.style.color = C.text }}
                  onMouseLeave={function (e) { e.target.style.borderColor = C.border; e.target.style.color = C.muted }}
                >{currentTier === "pro" ? "Go Premium" : "Upgrade"}</button>
              )}
            </div>
          </div>
        </div>

        {/* ── Preferences ── */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Preferences</div>
          <div style={{ marginBottom: 20 }}>
            <label style={labelStyle}>Display Name</label>
            <input style={inputStyle("displayName")} value={displayName} onChange={function (e) { setDisplayName(e.target.value) }} onFocus={function () { setFocused("displayName") }} onBlur={function () { setFocused(null) }} placeholder="How Grace addresses you" maxLength={64} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div><label style={labelStyle}>Currency</label><input style={inputStyle("currency")} value={currency} onChange={function (e) { setCurrency(e.target.value.toUpperCase()) }} onFocus={function () { setFocused("currency") }} onBlur={function () { setFocused(null) }} maxLength={8} placeholder="USD" /></div>
            <div><label style={labelStyle}>Timezone</label><input style={inputStyle("timezone")} value={timezone} onChange={function (e) { setTimezone(e.target.value) }} onFocus={function () { setFocused("timezone") }} onBlur={function () { setFocused(null) }} placeholder="America/New_York" /></div>
          </div>
        </div>

        {/* ── Financial Snapshot ── */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Financial Snapshot</div>
          <p style={{ fontSize: 13, color: C.dim, lineHeight: 1.7, margin: "0 0 20px" }}>These numbers calibrate your Financial Confidence Score. Update them as your situation changes.</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 20, marginBottom: 20 }}>
            <div><label style={labelStyle}>Monthly Income (after tax)</label><CurrencyInput value={income} onChange={setIncome} placeholder="4,500" /></div>
            <div><label style={labelStyle}>Monthly Expenses</label><CurrencyInput value={expenses} onChange={setExpenses} placeholder="3,200" /></div>
            <div><label style={labelStyle}>Total Debt</label><CurrencyInput value={debt} onChange={setDebt} placeholder="0" /></div>
          </div>
          {/* Computed metrics */}
          {incomeVal > 0 && (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, paddingTop: 16, borderTop: "1px solid " + C.border }}>
              <div style={{ padding: "12px 0" }}>
                <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: C.dim, marginBottom: 4, fontWeight: 500 }}>Available Monthly</div>
                <div style={{ fontSize: 20, fontWeight: 400, color: available >= 0 ? C.text : "#ff4444", letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}>{formatCurrency(available)}</div>
              </div>
              <div style={{ padding: "12px 0" }}>
                <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: C.dim, marginBottom: 4, fontWeight: 500 }}>Savings Rate</div>
                <div style={{ fontSize: 20, fontWeight: 400, color: parseInt(savingsRate) >= 0 ? C.text : "#ff4444", letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}>{savingsRate}%</div>
              </div>
            </div>
          )}
        </div>

        {/* ── Goals ── */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Your Goals</div>
          <p style={{ fontSize: 13, color: C.dim, lineHeight: 1.7, margin: "0 0 16px" }}>What matters most to you right now? Grace tailors your check-ins around these.</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {goalOptions.map(function (goal) {
              var isSelected = selectedGoals.indexOf(goal.id) >= 0
              return (<button key={goal.id} onClick={function () { toggleGoal(goal.id) }} style={{
                display: "flex", flexDirection: "column", padding: "14px", borderRadius: 8, textAlign: "left",
                border: "1px solid " + (isSelected ? C.text : C.border), background: isSelected ? "#0d0d0d" : "transparent",
                cursor: "pointer", transition: "all 0.15s ease",
              }}>
                <span style={{ fontSize: 13, fontWeight: isSelected ? 600 : 400, color: isSelected ? C.text : C.muted, marginBottom: 3, fontFamily: FONT }}>{goal.label}</span>
                <span style={{ fontSize: 11, color: C.dim, lineHeight: 1.4, fontFamily: FONT }}>{goal.desc}</span>
              </button>)
            })}
          </div>
        </div>

        {/* ── Mission ── */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Your Mission</div>
          <p style={{ fontSize: 13, color: C.dim, lineHeight: 1.7, margin: "0 0 12px" }}>What are you working toward? Grace uses this to make your coaching personal.</p>
          <textarea value={mission} onChange={function (e) { setMission(e.target.value) }} placeholder="I want to save $15,000 for a down payment on my first home..." style={{
            width: "100%", padding: "12px 0", fontSize: 14, fontFamily: FONT, color: C.text, background: "transparent",
            border: "none", borderBottom: "1px solid " + C.faint, outline: "none", minHeight: 80, resize: "vertical",
            lineHeight: 1.7, boxSizing: "border-box", transition: "border-color 0.2s ease",
          }} onFocus={function (e) { e.target.style.borderColor = C.text }} onBlur={function (e) { e.target.style.borderColor = C.faint }} />
        </div>

        {/* ── Risk Tolerance ── */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Risk Tolerance</div>
          <div style={{ display: "flex", gap: 10 }}>
            {RISK_OPTIONS.map(function (opt) {
              var isActive = riskStyle === opt.value
              return (<button key={opt.value} onClick={function () { setRiskStyle(opt.value) }} disabled={isSaving} style={{
                flex: 1, padding: "14px 12px", borderRadius: 8, textAlign: "left",
                border: "1px solid " + (isActive ? C.text : C.border), background: isActive ? "#111111" : "transparent",
                cursor: isSaving ? "not-allowed" : "pointer", transition: "all 0.2s ease", opacity: isSaving ? 0.5 : 1,
              }}>
                <div style={{ fontSize: 13, fontWeight: isActive ? 600 : 400, color: isActive ? C.text : C.muted, fontFamily: FONT }}>{opt.label}</div>
                <div style={{ fontSize: 11, color: C.dim, marginTop: 2, fontFamily: FONT }}>{opt.desc}</div>
              </button>)
            })}
          </div>
        </div>

        {/* ── Save ── */}
        <button onClick={handleSave} disabled={isSaving} style={{
          width: "100%", padding: "14px", borderRadius: 8, border: "none", background: "#ffffff", color: "#000000",
          fontWeight: 600, fontSize: 14, fontFamily: FONT, cursor: isSaving ? "not-allowed" : "pointer",
          transition: "all 0.2s ease", opacity: isSaving ? 0.5 : 1, letterSpacing: "-0.01em", marginTop: 4,
        }}
          onMouseEnter={function (e) { if (!isSaving) e.target.style.opacity = "0.85" }}
          onMouseLeave={function (e) { if (!isSaving) e.target.style.opacity = "1" }}
        >{saved ? "Saved" : isSaving ? "Saving..." : "Save Profile"}</button>
        {saveError && (<p style={{ color: "#ff4444", fontSize: 13, textAlign: "center", marginTop: 10 }}>{saveError}</p>)}
      </div>
    </div>
  )
}