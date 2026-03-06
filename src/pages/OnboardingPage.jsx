/**
 * OnboardingPage — v5 Polish
 * FCS is the hero. Building a financial behavioral profile.
 * 5 steps: Welcome → Goals → Financials → Mission → Snapshot
 */

import { useState, useEffect, useRef } from "react"

var C = { bg: "#000000", card: "#0a0a0a", border: "#1a1a1a", text: "#ffffff", muted: "#666666", dim: "#444444", faint: "#333333" }
var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"
var STEPS = ["welcome", "goals", "financials", "mission", "snapshot"]

var goalOptions = [
  { id: "save", label: "Build Savings", desc: "Grow your cushion and emergency fund" },
  { id: "debt", label: "Reduce Debt", desc: "Pay down what you owe systematically" },
  { id: "track", label: "Understand Spending", desc: "See where your money actually goes" },
  { id: "budget", label: "Create a System", desc: "Build a budget that works for your life" },
  { id: "wealth", label: "Grow Wealth", desc: "Invest, build assets, plan for the future" },
  { id: "habits", label: "Change Behavior", desc: "Break old patterns, build better ones" },
]

function CurrencyInput(props) {
  var inputRef = useRef(null)
  useEffect(function () { if (props.autoFocus && inputRef.current) inputRef.current.focus() }, [props.autoFocus])
  function handleChange(e) { var raw = e.target.value.replace(/[^0-9]/g, ""); props.onChange(raw === "" ? "" : parseInt(raw, 10)) }
  return (
    <div style={{ position: "relative", width: "100%" }}>
      <span style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)", fontSize: 24, fontFamily: FONT, color: props.value ? C.text : C.dim, fontWeight: 400, pointerEvents: "none" }}>$</span>
      <input ref={inputRef} type="text" inputMode="numeric" value={props.value === "" ? "" : props.value.toLocaleString()} onChange={handleChange} placeholder={props.placeholder || "0"} style={{
        width: "100%", padding: "12px 0 12px 20px", fontSize: 24, fontFamily: FONT, fontWeight: 400, color: C.text, background: "transparent", border: "none", borderBottom: "1px solid " + C.faint, outline: "none", transition: "border-color 0.2s ease", boxSizing: "border-box", letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums",
      }} onFocus={function (e) { e.target.style.borderColor = C.text }} onBlur={function (e) { e.target.style.borderColor = C.faint }} />
    </div>
  )
}

function formatCurrency(num) { return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(num) }

export default function OnboardingPage(props) {
  var stepState = useState("welcome"); var step = stepState[0]; var setStep = stepState[1]
  var goalsState = useState([]); var selectedGoals = goalsState[0]; var setSelectedGoals = goalsState[1]
  var incomeState = useState(""); var income = incomeState[0]; var setIncome = incomeState[1]
  var expensesState = useState(""); var expenses = expensesState[0]; var setExpenses = expensesState[1]
  var debtState = useState(""); var debt = debtState[0]; var setDebt = debtState[1]
  var missionState = useState(""); var mission = missionState[0]; var setMission = missionState[1]
  var transState = useState(false); var transitioning = transState[0]; var setTransitioning = transState[1]
  var mountedState = useState(false); var mounted = mountedState[0]; var setMounted = mountedState[1]

  useEffect(function () { setTimeout(function () { setMounted(true) }, 100) }, [])

  var stepIndex = STEPS.indexOf(step)
  var progress = step === "welcome" ? 0 : step === "snapshot" ? 100 : (stepIndex / (STEPS.length - 1)) * 100

  function goNext(nextStep) { setTransitioning(true); setTimeout(function () { setStep(nextStep); setTransitioning(false) }, 250) }
  function toggleGoal(id) { if (selectedGoals.indexOf(id) >= 0) { setSelectedGoals(selectedGoals.filter(function (g) { return g !== id })) } else { setSelectedGoals(selectedGoals.concat([id])) } }
  function handleComplete() {
    var data = { goals: selectedGoals, income: income, expenses: expenses, debt: debt, mission: mission }
    localStorage.setItem("grace-onboarding-complete", "true"); localStorage.setItem("grace-onboarding-data", JSON.stringify(data))
    if (props.onComplete) props.onComplete(data)
  }
  function handleSkip() { localStorage.setItem("grace-onboarding-complete", "true"); if (props.onComplete) props.onComplete(null) }

  var incomeVal = income === "" ? 0 : income; var expensesVal = expenses === "" ? 0 : expenses; var debtVal = debt === "" ? 0 : debt
  var available = incomeVal - expensesVal; var savingsRate = incomeVal > 0 ? ((available / incomeVal) * 100).toFixed(0) : 0

  var headingStyle = { fontSize: 28, fontWeight: 300, color: C.text, letterSpacing: "-0.03em", lineHeight: 1.25, margin: "0 0 12px", fontFamily: FONT }
  var subStyle = { fontSize: 14, color: C.dim, lineHeight: 1.7, margin: "0 0 36px", fontFamily: FONT }
  var labelStyle = { fontSize: 11, fontWeight: 500, color: C.muted, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8, display: "block", fontFamily: FONT }
  var btnStyle = { padding: "14px 48px", fontSize: 14, fontWeight: 600, fontFamily: FONT, color: "#000000", background: "#ffffff", border: "none", borderRadius: 8, cursor: "pointer", transition: "opacity 0.2s ease", letterSpacing: "-0.01em" }
  var btnDisabled = { opacity: 0.25, pointerEvents: "none" }

  return (
    <div style={{ minHeight: "100vh", width: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: FONT, position: "relative", padding: "60px 24px", boxSizing: "border-box", background: C.bg, color: C.text }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');::placeholder { color: #444444 !important; }"}</style>

      {step !== "snapshot" && step !== "welcome" && (
        <div style={{ position: "fixed", top: 24, right: 28, zIndex: 50 }}>
          <button onClick={handleSkip} style={{ background: "transparent", border: "none", color: C.dim, fontSize: 12, fontFamily: FONT, cursor: "pointer", transition: "color 0.2s" }}
            onMouseEnter={function (e) { e.target.style.color = C.text }} onMouseLeave={function (e) { e.target.style.color = C.dim }}>Skip for now</button>
        </div>
      )}

      {step !== "welcome" && (<div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: 2, background: C.border, zIndex: 100 }}><div style={{ height: "100%", width: progress + "%", background: C.text, transition: "width 0.4s ease" }} /></div>)}

      <div style={{ opacity: transitioning ? 0 : (mounted ? 1 : 0), transform: transitioning ? "translateY(8px)" : "translateY(0)", transition: "opacity 0.25s ease, transform 0.25s ease", display: "flex", flexDirection: "column", alignItems: "center", width: "100%", maxWidth: 520 }}>

        {step === "welcome" && (
          <div style={{ textAlign: "center", maxWidth: 440 }}>
            <div style={{ width: 40, height: 40, border: "1.5px solid " + C.text, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 700, margin: "0 auto 40px" }}>G</div>
            <h1 style={{ fontSize: 36, fontWeight: 300, color: C.text, letterSpacing: "-0.03em", lineHeight: 1.2, margin: "0 0 16px" }}>
              Meet your<br /><span style={{ fontWeight: 600 }}>Financial Confidence Score.</span>
            </h1>
            <p style={{ fontSize: 15, color: C.dim, lineHeight: 1.7, margin: "0 0 12px", maxWidth: 380, marginLeft: "auto", marginRight: "auto" }}>
              The FCS measures your real relationship with money — not your credit, not your net worth, but how confident you are in your financial life. It's built from your daily check-ins and gets smarter every time you show up.
            </p>
            <p style={{ fontSize: 13, color: C.faint, lineHeight: 1.6, margin: "0 0 44px", maxWidth: 380, marginLeft: "auto", marginRight: "auto" }}>
              Your anonymized behavioral data also powers the GFCI — a real-time financial confidence indicator for the population.
            </p>
            <button onClick={function () { goNext("goals") }} style={btnStyle} onMouseEnter={function (e) { e.target.style.opacity = "0.85" }} onMouseLeave={function (e) { e.target.style.opacity = "1" }}>Build My Profile</button>
            <p style={{ fontSize: 11, color: C.faint, marginTop: 20, letterSpacing: "0.02em" }}>Free forever · Your data stays yours · Takes 60 seconds</p>
          </div>
        )}

        {step === "goals" && (
          <div style={{ width: "100%" }}>
            <div style={labelStyle}>Step 1 of 4</div>
            <h2 style={headingStyle}>What matters most to you <span style={{ fontWeight: 600 }}>right now?</span></h2>
            <p style={subStyle}>Pick as many as apply. This helps Grace tailor your check-ins and coaching.</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 36 }}>
              {goalOptions.map(function (goal) {
                var isSelected = selectedGoals.indexOf(goal.id) >= 0
                return (<button key={goal.id} onClick={function () { toggleGoal(goal.id) }} style={{ display: "flex", flexDirection: "column", padding: "16px", borderRadius: 8, textAlign: "left", border: "1px solid " + (isSelected ? C.text : C.border), background: isSelected ? "#0d0d0d" : "transparent", cursor: "pointer", transition: "all 0.15s ease" }}>
                  <span style={{ fontSize: 14, fontWeight: isSelected ? 600 : 400, color: isSelected ? C.text : C.muted, marginBottom: 4, fontFamily: FONT }}>{goal.label}</span>
                  <span style={{ fontSize: 12, color: C.dim, lineHeight: 1.4, fontFamily: FONT }}>{goal.desc}</span>
                </button>)
              })}
            </div>
            <div style={{ textAlign: "center" }}>
              <button onClick={function () { goNext("financials") }} style={selectedGoals.length > 0 ? btnStyle : Object.assign({}, btnStyle, btnDisabled)} onMouseEnter={function (e) { if (selectedGoals.length > 0) e.target.style.opacity = "0.85" }} onMouseLeave={function (e) { e.target.style.opacity = "1" }}>Continue</button>
            </div>
          </div>
        )}

        {step === "financials" && (
          <div style={{ width: "100%" }}>
            <div style={labelStyle}>Step 2 of 4</div>
            <h2 style={headingStyle}>Your <span style={{ fontWeight: 600 }}>monthly snapshot.</span></h2>
            <p style={subStyle}>This calibrates your Financial Confidence Score. Estimates are perfectly fine — the picture sharpens with every check-in.</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 32, marginBottom: 40 }}>
              <div><label style={labelStyle}>Monthly income (after tax)</label><CurrencyInput value={income} onChange={setIncome} placeholder="4,500" autoFocus /></div>
              <div><label style={labelStyle}>Monthly expenses</label><CurrencyInput value={expenses} onChange={setExpenses} placeholder="3,200" /></div>
              <div><label style={labelStyle}>Total debt (enter 0 if none)</label><CurrencyInput value={debt} onChange={setDebt} placeholder="0" /></div>
            </div>
            <div style={{ textAlign: "center" }}>
              <button onClick={function () { goNext("mission") }} style={income !== "" && expenses !== "" && debt !== "" ? btnStyle : Object.assign({}, btnStyle, btnDisabled)} onMouseEnter={function (e) { if (income !== "" && expenses !== "" && debt !== "") e.target.style.opacity = "0.85" }} onMouseLeave={function (e) { e.target.style.opacity = "1" }}>Continue</button>
            </div>
          </div>
        )}

        {step === "mission" && (
          <div style={{ width: "100%" }}>
            <div style={labelStyle}>Step 3 of 4</div>
            <h2 style={headingStyle}>What are you <span style={{ fontWeight: 600 }}>working toward?</span></h2>
            <p style={subStyle}>A home. Freedom from debt. Your family's future. Grace uses this to make your coaching personal.</p>
            <textarea value={mission} onChange={function (e) { setMission(e.target.value) }} placeholder="I want to save $15,000 for a down payment on my first home..." autoFocus style={{ width: "100%", padding: "16px 0", fontSize: 15, fontFamily: FONT, color: C.text, background: "transparent", border: "none", borderBottom: "1px solid " + C.faint, outline: "none", minHeight: 100, resize: "vertical", lineHeight: 1.7, boxSizing: "border-box", transition: "border-color 0.2s ease" }}
              onFocus={function (e) { e.target.style.borderColor = C.text }} onBlur={function (e) { e.target.style.borderColor = C.faint }} />
            <div style={{ textAlign: "center", marginTop: 36 }}>
              <button onClick={function () { goNext("snapshot") }} style={btnStyle} onMouseEnter={function (e) { e.target.style.opacity = "0.85" }} onMouseLeave={function (e) { e.target.style.opacity = "1" }}>{mission.trim() ? "Continue" : "Skip for now"}</button>
            </div>
          </div>
        )}

        {step === "snapshot" && (
          <div style={{ width: "100%", maxWidth: 480 }}>
            <div style={{ textAlign: "center", marginBottom: 36 }}>
              <div style={labelStyle}>Your Starting Point</div>
              <h2 style={{ fontSize: 28, fontWeight: 300, color: C.text, letterSpacing: "-0.03em", lineHeight: 1.3, margin: "8px 0 0" }}>
                {available >= 0 ? "You're ready to start tracking." : "Every journey starts with clarity."}
              </h2>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
              {[{ label: "Monthly Income", value: formatCurrency(incomeVal) }, { label: "Monthly Expenses", value: formatCurrency(expensesVal) }, { label: "Available Monthly", value: formatCurrency(available) }, { label: "Total Debt", value: formatCurrency(debtVal) }].map(function (item) {
                return (<div key={item.label} style={{ background: C.card, borderRadius: 8, padding: "18px 16px", border: "1px solid " + C.border }}>
                  <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: C.dim, marginBottom: 6, fontWeight: 500 }}>{item.label}</div>
                  <div style={{ fontSize: 22, fontWeight: 400, color: C.text, letterSpacing: "-0.02em", fontVariantNumeric: "tabular-nums" }}>{item.value}</div>
                </div>)
              })}
            </div>
            {incomeVal > 0 && (
              <div style={{ background: C.card, borderRadius: 8, padding: "18px 16px", border: "1px solid " + C.border, marginBottom: 24 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: C.dim, marginBottom: 4, fontWeight: 500 }}>Savings Rate</div>
                    <div style={{ fontSize: 13, color: C.muted, lineHeight: 1.6 }}>{parseInt(savingsRate) > 0 ? formatCurrency(available) + " per month working for your future." : "Your expenses are running ahead of income. That's exactly what we're here to help with."}</div>
                  </div>
                  <div style={{ fontSize: 32, fontWeight: 300, color: C.text, letterSpacing: "-0.03em", fontVariantNumeric: "tabular-nums", marginLeft: 20, flexShrink: 0 }}>{savingsRate}%</div>
                </div>
              </div>
            )}
            {mission.trim() && (
              <div style={{ background: C.card, borderRadius: 8, padding: "18px 16px", border: "1px solid " + C.border, marginBottom: 24 }}>
                <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: C.dim, marginBottom: 8, fontWeight: 500 }}>Your Goal</div>
                <p style={{ fontSize: 14, color: C.muted, lineHeight: 1.7, margin: 0, fontStyle: "italic" }}>"{mission}"</p>
              </div>
            )}
            <div style={{ borderTop: "1px solid " + C.border, paddingTop: 20, marginBottom: 32 }}>
              <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: C.dim, marginBottom: 12, fontWeight: 500 }}>How it works</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  "Daily check-ins build your Financial Confidence Score across five behavioral dimensions.",
                  "Grace AI coaches you based on patterns in your data — not generic advice.",
                  "Your anonymized profile contributes to the GFCI — a population-level confidence indicator.",
                ].map(function (item, i) {
                  return (<div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                    <span style={{ fontSize: 12, color: C.faint, fontWeight: 500, fontVariantNumeric: "tabular-nums", flexShrink: 0, width: 18, textAlign: "right" }}>{(i + 1) + "."}</span>
                    <span style={{ fontSize: 13, color: C.muted, lineHeight: 1.6 }}>{item}</span>
                  </div>)
                })}
              </div>
            </div>
            <div style={{ textAlign: "center" }}>
              <button onClick={handleComplete} style={Object.assign({}, btnStyle, { padding: "16px 56px", fontSize: 15 })} onMouseEnter={function (e) { e.target.style.opacity = "0.85" }} onMouseLeave={function (e) { e.target.style.opacity = "1" }}>Start Tracking My FCS</button>
              <p style={{ fontSize: 11, color: C.faint, marginTop: 16, letterSpacing: "0.04em", textTransform: "uppercase" }}>GraceFinance</p>
            </div>
          </div>
        )}
      </div>

      {step !== "welcome" && step !== "snapshot" && (
        <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 40 }}>
          {STEPS.slice(1, -1).map(function (s, i) { var idx = STEPS.indexOf(step) - 1; return (<div key={s} style={{ width: i === idx ? 20 : 6, height: 3, borderRadius: 2, background: i <= idx ? C.text : C.border, transition: "all 0.3s ease" }} />) })}
        </div>
      )}
    </div>
  )
}