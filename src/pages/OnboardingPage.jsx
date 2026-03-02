import { useState, useEffect, useRef } from "react"
import { useTheme } from "../context/ThemeContext"

var STEPS = ["welcome", "goals", "income", "expenses", "debt", "mission", "about", "snapshot"]

var goalOptions = [
  { id: "save", label: "Save More Money", desc: "Build an emergency fund or save for something big" },
  { id: "debt", label: "Pay Off Debt", desc: "Tackle credit cards, loans, or other debts" },
  { id: "track", label: "Track My Spending", desc: "See where my money actually goes" },
  { id: "budget", label: "Build a Budget", desc: "Create a plan and stick to it" },
  { id: "wealth", label: "Build Wealth", desc: "Invest, grow assets, and plan long-term" },
  { id: "habits", label: "Understand My Money Habits", desc: "Break bad patterns, build healthy ones" },
]

var ageOptions = ["18-24", "25-34", "35-44", "45-54", "55+"]

var experienceOptions = [
  { id: "beginner", label: "Beginner", desc: "Just starting my financial journey" },
  { id: "intermediate", label: "Intermediate", desc: "I know the basics but want to improve" },
  { id: "advanced", label: "Advanced", desc: "I actively manage my finances and investments" },
]

var hearOptions = ["Social Media", "Friend / Family", "Google Search", "Reddit", "TikTok", "Other"]

var encouragements = {
  income: [
    "That's real money working for you every month.",
    "Solid foundation. Let's make every dollar count.",
    "Now let's see where it's going.",
  ],
  expenses: [
    "Good \u2014 knowing this is half the battle.",
    "Awareness is the first step to control.",
    "Now let's look at the full picture.",
  ],
  debt: [
    "We've helped people tackle way more. You've got this.",
    "That number has an expiration date. Let's find it.",
    "Every dollar you throw at this is a win.",
  ],
  debtZero: [
    "Debt-free? That's a powerful position to be in.",
    "You're already ahead of most people. Let's build on that.",
  ],
}

function getEncouragement(step, value) {
  if (step === "debt" && value === 0) {
    var arr = encouragements.debtZero
    return arr[Math.floor(Math.random() * arr.length)]
  }
  var arr2 = encouragements[step]
  if (!arr2) return ""
  return arr2[Math.floor(Math.random() * arr2.length)]
}

function formatCurrency(num) {
  return new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 0,
  }).format(num)
}

function CurrencyInput(props) {
  var inputRef = useRef(null)

  useEffect(function () {
    if (props.autoFocus && inputRef.current) inputRef.current.focus()
  }, [props.autoFocus])

  function handleChange(e) {
    var raw = e.target.value.replace(/[^0-9]/g, "")
    props.onChange(raw === "" ? "" : parseInt(raw, 10))
  }

  var ctx = useTheme()
  var t = ctx.theme

  return (
    <div style={{ position: "relative", width: "100%", maxWidth: 360 }}>
      <span style={{
        position: "absolute", left: 20, top: "50%", transform: "translateY(-50%)",
        fontSize: 28, fontFamily: "'DM Sans', sans-serif",
        color: props.value ? t.text : t.muted, fontWeight: 600, pointerEvents: "none",
      }}>$</span>
      <input
        ref={inputRef}
        type="text"
        inputMode="numeric"
        value={props.value === "" ? "" : props.value.toLocaleString()}
        onChange={handleChange}
        placeholder={props.placeholder || "0"}
        style={{
          width: "100%", padding: "18px 20px 18px 44px", fontSize: 28,
          fontFamily: "'DM Sans', sans-serif", fontWeight: 600, color: t.text,
          background: t.dark, border: "2px solid " + t.border, borderRadius: 14,
          outline: "none", transition: "border-color 0.2s ease, box-shadow 0.2s ease",
          boxSizing: "border-box",
        }}
        onFocus={function (e) {
          e.target.style.borderColor = t.accent
          e.target.style.boxShadow = "0 0 0 4px " + t.accent + "20"
        }}
        onBlur={function (e) {
          e.target.style.borderColor = t.border
          e.target.style.boxShadow = "none"
        }}
      />
    </div>
  )
}

function FadeIn(props) {
  var delay = props.delay || 0
  var visState = useState(false)
  var visible = visState[0]
  var setVisible = visState[1]

  useEffect(function () {
    var timer = setTimeout(function () { setVisible(true) }, delay)
    return function () { clearTimeout(timer) }
  }, [delay])

  return (
    <div style={{
      opacity: visible ? 1 : 0,
      transform: visible ? "translateY(0)" : "translateY(18px)",
      transition: "opacity 0.6s ease, transform 0.6s ease",
      ...(props.style || {}),
    }}>
      {props.children}
    </div>
  )
}

export default function OnboardingPage(props) {
  var ctx = useTheme()
  var t = ctx.theme

  var stepState = useState("welcome")
  var step = stepState[0]
  var setStep = stepState[1]

  var goalsState = useState([])
  var selectedGoals = goalsState[0]
  var setSelectedGoals = goalsState[1]

  var incomeState = useState("")
  var income = incomeState[0]
  var setIncome = incomeState[1]

  var expensesState = useState("")
  var expenses = expensesState[0]
  var setExpenses = expensesState[1]

  var debtState = useState("")
  var debt = debtState[0]
  var setDebt = debtState[1]

  var missionState = useState("")
  var mission = missionState[0]
  var setMission = missionState[1]

  var ageState = useState("")
  var age = ageState[0]
  var setAge = ageState[1]

  var expState = useState("")
  var experience = expState[0]
  var setExperience = expState[1]

  var hearState = useState("")
  var heardFrom = hearState[0]
  var setHeardFrom = hearState[1]

  var encourageState = useState("")
  var encouragement = encourageState[0]
  var setEncouragement = encourageState[1]

  var showEncState = useState(false)
  var showEncouragement = showEncState[0]
  var setShowEncouragement = showEncState[1]

  var transState = useState(false)
  var transitioning = transState[0]
  var setTransitioning = transState[1]

  var snapState = useState(false)
  var snapshotReady = snapState[0]
  var setSnapshotReady = snapState[1]

  var stepIndex = STEPS.indexOf(step)
  var progress = step === "welcome" ? 0 : step === "snapshot" ? 100 : (stepIndex / (STEPS.length - 1)) * 100

  function goNext(nextStep, encourageKey, encourageValue) {
    if (encourageKey) {
      var msg = getEncouragement(encourageKey, encourageValue)
      setEncouragement(msg)
      setShowEncouragement(true)
      setTimeout(function () {
        setShowEncouragement(false)
        setTimeout(function () {
          setTransitioning(true)
          setTimeout(function () {
            setStep(nextStep)
            setTransitioning(false)
          }, 300)
        }, 200)
      }, 1800)
    } else {
      setTransitioning(true)
      setTimeout(function () {
        setStep(nextStep)
        setTransitioning(false)
      }, 300)
    }
  }

  useEffect(function () {
    if (step === "snapshot") setTimeout(function () { setSnapshotReady(true) }, 400)
  }, [step])

  function toggleGoal(id) {
    if (selectedGoals.indexOf(id) >= 0) {
      setSelectedGoals(selectedGoals.filter(function (g) { return g !== id }))
    } else {
      setSelectedGoals(selectedGoals.concat([id]))
    }
  }

  function handleComplete() {
    var data = {
      goals: selectedGoals, income: income, expenses: expenses, debt: debt,
      mission: mission, age: age, experience: experience, heardFrom: heardFrom,
    }
    localStorage.setItem("grace-onboarding-complete", "true")
    localStorage.setItem("grace-onboarding-data", JSON.stringify(data))
    if (props.onComplete) props.onComplete(data)
  }

  function handleSkip() {
    localStorage.setItem("grace-onboarding-complete", "true")
    if (props.onComplete) props.onComplete(null)
  }

  var incomeVal = income === "" ? 0 : income
  var expensesVal = expenses === "" ? 0 : expenses
  var debtVal = debt === "" ? 0 : debt
  var available = incomeVal - expensesVal
  var debtFreeMonths = debtVal > 0 && available > 0 ? Math.ceil(debtVal / available) : null
  var acceleratedMonths = debtFreeMonths ? Math.ceil(debtFreeMonths * 0.7) : null
  var savingsRate = incomeVal > 0 ? ((available / incomeVal) * 100).toFixed(0) : 0

  var isWelcome = step === "welcome"
  var labelStyle = { fontSize: 13, color: t.muted, marginBottom: 8, fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase" }
  var questionStyle = { fontSize: 26, fontWeight: 700, color: t.text, marginBottom: 8, lineHeight: 1.3 }
  var subTextStyle = { fontSize: 14, color: t.muted, marginBottom: 32, lineHeight: 1.5 }

  var btnStyle = {
    padding: "16px 48px", fontSize: 17, fontWeight: 700, fontFamily: "'DM Sans', sans-serif",
    color: t.isDark ? "#0a0f1a" : "#fff", background: t.accent, border: "none",
    borderRadius: 12, cursor: "pointer", transition: "all 0.25s ease",
    boxShadow: "0 4px 20px " + t.accent + "40",
  }

  var btnDisabled = { opacity: 0.4, pointerEvents: "none" }
  var stepNum = STEPS.indexOf(step)
  var totalInputSteps = 6

  return (
    <div style={{
      minHeight: "100vh", width: "100%", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", fontFamily: "'DM Sans', sans-serif",
      position: "relative", overflow: "hidden", padding: "40px 20px", boxSizing: "border-box",
      background: isWelcome
        ? "radial-gradient(ellipse at 30% 20%, " + t.accentGlow + " 0%, transparent 50%), radial-gradient(ellipse at 70% 80%, " + t.accentGlow + " 0%, transparent 50%), " + t.dark
        : t.dark,
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* Skip button */}
      {step !== "snapshot" && step !== "welcome" && (
        <div style={{ position: "fixed", top: 20, right: 24, zIndex: 50 }}>
          <button onClick={handleSkip} style={{
            background: "none", border: "none", color: t.muted, fontSize: 13, cursor: "pointer",
          }}>
            Skip for now →
          </button>
        </div>
      )}

      {/* Progress bar */}
      {step !== "welcome" && (
        <div style={{ position: "fixed", top: 0, left: 0, width: "100%", height: 4, background: t.border, zIndex: 100 }}>
          <div style={{
            height: "100%", width: progress + "%", background: t.accent,
            transition: "width 0.6s ease", borderRadius: "0 2px 2px 0",
          }} />
        </div>
      )}

      {/* Encouragement overlay */}
      {showEncouragement && (
        <div style={{
          position: "fixed", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
          background: t.dark + "F8", zIndex: 200, padding: 40,
        }}>
          <FadeIn>
            <p style={{
              fontSize: 24, fontWeight: 600, color: t.accent, textAlign: "center",
              lineHeight: 1.5, maxWidth: 460,
            }}>
              {encouragement}
            </p>
          </FadeIn>
        </div>
      )}

      {/* Content */}
      <div style={{
        opacity: transitioning ? 0 : 1, transform: transitioning ? "translateY(12px)" : "translateY(0)",
        transition: "opacity 0.3s ease, transform 0.3s ease",
        display: "flex", flexDirection: "column", alignItems: "center", width: "100%", maxWidth: 520,
      }}>

        {/* WELCOME */}
        {step === "welcome" && (
          <div style={{ textAlign: "center" }}>
            <FadeIn delay={200}>
              <img src="/grace-logo.webp" alt="Grace" style={{
                width: 100, height: 100, borderRadius: "50%", margin: "0 auto 24px", display: "block",
              }} />
            </FadeIn>
            <FadeIn delay={400}>
              <h1 style={{ fontSize: 42, fontWeight: 700, color: t.text, letterSpacing: -0.5, marginBottom: 4 }}>
                GraceFinance
              </h1>
            </FadeIn>
            <FadeIn delay={600}>
              <p style={{ fontSize: 13, letterSpacing: "0.15em", textTransform: "uppercase", color: t.muted, marginBottom: 40, fontWeight: 500 }}>
                Smarter Finance is Right Around the Corner™
              </p>
            </FadeIn>
            <FadeIn delay={800}>
              <p style={{ fontSize: 18, color: t.muted, textAlign: "center", lineHeight: 1.7, maxWidth: 380, margin: "0 auto 40px" }}>
                Tired of wondering where your money went?
                <br /><br />
                <span style={{ fontSize: 15, opacity: 0.7 }}>In 60 seconds, you'll see your money differently.</span>
              </p>
            </FadeIn>
            <FadeIn delay={1100}>
              <button onClick={function () { goNext("goals") }} style={btnStyle}>
                Take Control Now
              </button>
            </FadeIn>
            <FadeIn delay={1400}>
              <p style={{ fontSize: 12, color: t.muted, marginTop: 24, opacity: 0.5 }}>
                No card required · Free to start · Your data stays yours
              </p>
            </FadeIn>
          </div>
        )}

        {/* GOALS */}
        {step === "goals" && (
          <div>
            <FadeIn delay={100}><p style={labelStyle}>Step 1 of {totalInputSteps}</p></FadeIn>
            <FadeIn delay={200}><h2 style={questionStyle}>What brings you to GraceFinance?</h2></FadeIn>
            <FadeIn delay={300}><p style={subTextStyle}>Select all that apply.</p></FadeIn>
            <FadeIn delay={400}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {goalOptions.map(function (goal) {
                  var isSelected = selectedGoals.indexOf(goal.id) >= 0
                  return (
                    <button key={goal.id} onClick={function () { toggleGoal(goal.id) }} style={{
                      display: "flex", flexDirection: "column", padding: 16, borderRadius: 14, textAlign: "left",
                      border: "1.5px solid " + (isSelected ? t.accent : t.border),
                      background: isSelected ? t.accent + "12" : "transparent", cursor: "pointer", transition: "all 0.2s",
                    }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: isSelected ? t.accent : t.text, marginBottom: 4 }}>{goal.label}</span>
                      <span style={{ fontSize: 12, color: t.muted, lineHeight: 1.4 }}>{goal.desc}</span>
                    </button>
                  )
                })}
              </div>
            </FadeIn>
            <FadeIn delay={500} style={{ marginTop: 32, textAlign: "center" }}>
              <button onClick={function () { goNext("income") }}
                style={selectedGoals.length > 0 ? btnStyle : Object.assign({}, btnStyle, btnDisabled)}>
                Continue
              </button>
            </FadeIn>
          </div>
        )}

        {/* INCOME */}
        {step === "income" && (
          <div style={{ textAlign: "center" }}>
            <FadeIn delay={100}><p style={labelStyle}>Step 2 of {totalInputSteps}</p></FadeIn>
            <FadeIn delay={200}><h2 style={questionStyle}>What do you bring home each month?</h2></FadeIn>
            <FadeIn delay={300}><p style={subTextStyle}>Your total monthly income after taxes.</p></FadeIn>
            <FadeIn delay={400}><CurrencyInput value={income} onChange={setIncome} placeholder="4,500" autoFocus /></FadeIn>
            <FadeIn delay={500} style={{ marginTop: 32 }}>
              <button onClick={function () { goNext("expenses", "income", incomeVal) }}
                style={income !== "" && income > 0 ? btnStyle : Object.assign({}, btnStyle, btnDisabled)}>
                Continue
              </button>
            </FadeIn>
          </div>
        )}

        {/* EXPENSES */}
        {step === "expenses" && (
          <div style={{ textAlign: "center" }}>
            <FadeIn delay={100}><p style={labelStyle}>Step 3 of {totalInputSteps}</p></FadeIn>
            <FadeIn delay={200}><h2 style={questionStyle}>What goes out every month?</h2></FadeIn>
            <FadeIn delay={300}><p style={subTextStyle}>Rent, bills, groceries, subscriptions — everything.</p></FadeIn>
            <FadeIn delay={400}><CurrencyInput value={expenses} onChange={setExpenses} placeholder="3,200" autoFocus /></FadeIn>
            <FadeIn delay={500} style={{ marginTop: 32 }}>
              <button onClick={function () { goNext("debt", "expenses", expensesVal) }}
                style={expenses !== "" && expenses > 0 ? btnStyle : Object.assign({}, btnStyle, btnDisabled)}>
                Continue
              </button>
            </FadeIn>
          </div>
        )}

        {/* DEBT */}
        {step === "debt" && (
          <div style={{ textAlign: "center" }}>
            <FadeIn delay={100}><p style={labelStyle}>Step 4 of {totalInputSteps}</p></FadeIn>
            <FadeIn delay={200}><h2 style={questionStyle}>How much debt are you carrying?</h2></FadeIn>
            <FadeIn delay={300}><p style={subTextStyle}>Credit cards, loans, car payments. Enter $0 if debt-free.</p></FadeIn>
            <FadeIn delay={400}><CurrencyInput value={debt} onChange={setDebt} placeholder="0" autoFocus /></FadeIn>
            <FadeIn delay={500} style={{ marginTop: 32 }}>
              <button onClick={function () { goNext("mission", "debt", debtVal) }}
                style={debt !== "" ? btnStyle : Object.assign({}, btnStyle, btnDisabled)}>
                Continue
              </button>
            </FadeIn>
          </div>
        )}

        {/* MISSION */}
        {step === "mission" && (
          <div style={{ textAlign: "center" }}>
            <FadeIn delay={100}><p style={labelStyle}>Step 5 of {totalInputSteps}</p></FadeIn>
            <FadeIn delay={200}><h2 style={questionStyle}>What are you fighting for?</h2></FadeIn>
            <FadeIn delay={300}>
              <p style={subTextStyle}>
                A house. An emergency fund. Freedom from debt. Your kids' future.
                <br />Be ambitious — this is what GraceFinance is built for.
              </p>
            </FadeIn>
            <FadeIn delay={400}>
              <textarea
                value={mission} onChange={function (e) { setMission(e.target.value) }}
                placeholder="I want to save $15,000 for a down payment on my first home by next year..."
                autoFocus
                style={{
                  width: "100%", maxWidth: 400, padding: "16px 20px", fontSize: 16,
                  fontFamily: "'DM Sans', sans-serif", color: t.text, background: t.dark,
                  border: "2px solid " + t.border, borderRadius: 14, outline: "none",
                  minHeight: 120, resize: "vertical", lineHeight: 1.6, boxSizing: "border-box",
                }}
                onFocus={function (e) { e.target.style.borderColor = t.accent }}
                onBlur={function (e) { e.target.style.borderColor = t.border }}
              />
            </FadeIn>
            <FadeIn delay={500} style={{ marginTop: 32 }}>
              <button onClick={function () { goNext("about") }}
                style={mission.trim() ? btnStyle : Object.assign({}, btnStyle, btnDisabled)}>
                Continue
              </button>
            </FadeIn>
          </div>
        )}

        {/* ABOUT */}
        {step === "about" && (
          <div>
            <FadeIn delay={100}><p style={labelStyle}>Step 6 of {totalInputSteps}</p></FadeIn>
            <FadeIn delay={200}><h2 style={questionStyle}>Tell us a bit about yourself</h2></FadeIn>
            <FadeIn delay={300}><p style={subTextStyle}>This helps us tailor your experience.</p></FadeIn>

            <FadeIn delay={400}>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: t.text, display: "block", marginBottom: 10 }}>Age Range</label>
                <div style={{ display: "flex", gap: 8 }}>
                  {ageOptions.map(function (opt) {
                    var sel = age === opt
                    return (
                      <button key={opt} onClick={function () { setAge(opt) }} style={{
                        flex: 1, padding: "10px 0", borderRadius: 10, fontSize: 13, fontWeight: 500,
                        border: "1.5px solid " + (sel ? t.accent : t.border),
                        background: sel ? t.accent + "12" : "transparent",
                        color: sel ? t.accent : t.muted, cursor: "pointer",
                      }}>
                        {opt}
                      </button>
                    )
                  })}
                </div>
              </div>
            </FadeIn>

            <FadeIn delay={500}>
              <div style={{ marginBottom: 24 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: t.text, display: "block", marginBottom: 10 }}>Finance Experience</label>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {experienceOptions.map(function (opt) {
                    var sel = experience === opt.id
                    return (
                      <button key={opt.id} onClick={function () { setExperience(opt.id) }} style={{
                        display: "flex", flexDirection: "column", padding: "14px 16px", borderRadius: 12, textAlign: "left",
                        border: "1.5px solid " + (sel ? t.accent : t.border),
                        background: sel ? t.accent + "12" : "transparent", cursor: "pointer",
                      }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: sel ? t.accent : t.text }}>{opt.label}</span>
                        <span style={{ fontSize: 12, color: t.muted, marginTop: 2 }}>{opt.desc}</span>
                      </button>
                    )
                  })}
                </div>
              </div>
            </FadeIn>

            <FadeIn delay={600}>
              <div style={{ marginBottom: 32 }}>
                <label style={{ fontSize: 13, fontWeight: 600, color: t.text, display: "block", marginBottom: 10 }}>How did you hear about GraceFinance?</label>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {hearOptions.map(function (opt) {
                    var sel = heardFrom === opt
                    return (
                      <button key={opt} onClick={function () { setHeardFrom(opt) }} style={{
                        padding: "10px 16px", borderRadius: 10, fontSize: 13, fontWeight: 500,
                        border: "1.5px solid " + (sel ? t.accent : t.border),
                        background: sel ? t.accent + "12" : "transparent",
                        color: sel ? t.accent : t.muted, cursor: "pointer",
                      }}>
                        {opt}
                      </button>
                    )
                  })}
                </div>
              </div>
            </FadeIn>

            <FadeIn delay={700} style={{ textAlign: "center" }}>
              <button onClick={function () { goNext("snapshot") }} style={btnStyle}>
                Show Me My Path
              </button>
            </FadeIn>
          </div>
        )}

        {/* SNAPSHOT */}
        {step === "snapshot" && (
          <div style={{ width: "100%", maxWidth: 500 }}>
            <FadeIn delay={200}>
              <p style={{ fontSize: 13, letterSpacing: "0.1em", textTransform: "uppercase", color: t.muted, marginBottom: 8, textAlign: "center", fontWeight: 500 }}>
                Your Financial Snapshot
              </p>
            </FadeIn>
            <FadeIn delay={400}>
              <h2 style={{ fontSize: 28, fontWeight: 700, color: t.text, textAlign: "center", marginBottom: 32, lineHeight: 1.3 }}>
                {available > 0 ? "You have more power than you think." : "Let's find your breathing room."}
              </h2>
            </FadeIn>

            <FadeIn delay={600}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
                {[
                  { label: "Monthly Income", value: formatCurrency(incomeVal), color: "#3FB950" },
                  { label: "Monthly Expenses", value: formatCurrency(expensesVal), color: "#F85149" },
                  { label: "Available Monthly", value: formatCurrency(available), color: available >= 0 ? "#3FB950" : "#F85149" },
                  { label: "Total Debt", value: formatCurrency(debtVal), color: debtVal > 0 ? "#F85149" : "#3FB950" },
                ].map(function (item, i) {
                  return (
                    <div key={i} style={{
                      background: t.card, borderRadius: 14, padding: "20px 18px", border: "1px solid " + t.border,
                    }}>
                      <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: t.muted, marginBottom: 6, fontWeight: 500 }}>{item.label}</p>
                      <p style={{ fontSize: 24, fontWeight: 700, color: item.color }}>{item.value}</p>
                    </div>
                  )
                })}
              </div>
            </FadeIn>

            <FadeIn delay={900}>
              <div style={{
                background: t.accent + "10", border: "1px solid " + t.accent + "30",
                borderRadius: 16, padding: "28px 24px", marginBottom: 16,
              }}>
                <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.12em", color: t.accent, marginBottom: 12, fontWeight: 600 }}>
                  🐾 GraceFinance Insight
                </p>
                {debtVal > 0 && available > 0 && (
                  <p style={{ fontSize: 16, lineHeight: 1.6, fontWeight: 500, color: t.text }}>
                    At your current pace, you could be debt-free in <span style={{ color: "#D29922", fontWeight: 700 }}>{debtFreeMonths} months</span>.
                    With GraceFinance optimizing your spending, we'll target <span style={{ color: "#3FB950", fontWeight: 700 }}>{acceleratedMonths} months</span>.
                  </p>
                )}
                {debtVal > 0 && available <= 0 && (
                  <p style={{ fontSize: 16, lineHeight: 1.6, fontWeight: 500, color: t.text }}>
                    You're spending more than you earn right now. That's exactly why you're here. GraceFinance will help you find the gaps and build a path forward.
                  </p>
                )}
                {debtVal === 0 && available > 0 && (
                  <p style={{ fontSize: 16, lineHeight: 1.6, fontWeight: 500, color: t.text }}>
                    You're saving <span style={{ color: "#3FB950", fontWeight: 700 }}>{savingsRate}%</span> of your income.
                    That's {formatCurrency(available)} every month building your future.
                    {parseInt(savingsRate) >= 20 ? " You're outperforming most Americans. Let's accelerate." : " Let's push that higher together."}
                  </p>
                )}
                {debtVal === 0 && available <= 0 && (
                  <p style={{ fontSize: 16, lineHeight: 1.6, fontWeight: 500, color: t.text }}>
                    No debt is great. But your expenses are eating everything. Let's find the leaks and redirect that cash to your goal.
                  </p>
                )}
              </div>
            </FadeIn>

            {mission && (
              <FadeIn delay={1100}>
                <div style={{
                  background: t.card, borderRadius: 14, padding: "22px 24px",
                  border: "1px solid " + t.border, marginBottom: 32,
                }}>
                  <p style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: t.muted, marginBottom: 8, fontWeight: 500 }}>Your Mission</p>
                  <p style={{ fontSize: 16, color: t.text, lineHeight: 1.6, fontStyle: "italic" }}>"{mission}"</p>
                </div>
              </FadeIn>
            )}

            <FadeIn delay={1300}>
              <div style={{ textAlign: "center" }}>
                <button onClick={handleComplete} style={Object.assign({}, btnStyle, { padding: "18px 56px", fontSize: 18 })}>
                  Let's Build My Plan →
                </button>
                <p style={{ fontSize: 13, color: t.muted, marginTop: 16, opacity: 0.6 }}>
                  Smarter Finance is Right Around the Corner™
                </p>
              </div>
            </FadeIn>
          </div>
        )}
      </div>

      {/* Step dots */}
      {step !== "welcome" && step !== "snapshot" && (
        <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 32 }}>
          {STEPS.slice(1, -1).map(function (s, i) {
            var idx = STEPS.indexOf(step) - 1
            return (
              <div key={s} style={{
                width: i === idx ? 24 : 8, height: 8, borderRadius: 4,
                background: i <= idx ? t.accent : t.border, transition: "all 0.3s",
              }} />
            )
          })}
        </div>
      )}
    </div>
  )
}
