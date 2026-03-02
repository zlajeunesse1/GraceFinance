import { useState, useEffect, useRef } from "react";

const STEPS = ["welcome", "income", "expenses", "debt", "goal", "snapshot"];

const encouragements = {
  income: [
    "That's real money working for you every month.",
    "Solid foundation. Let's make every dollar count.",
    "Now let's see where it's going.",
  ],
  expenses: [
    "Good — knowing this is half the battle.",
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
};

function getEncouragement(step, value) {
  if (step === "debt" && value === 0) {
    const arr = encouragements.debtZero;
    return arr[Math.floor(Math.random() * arr.length)];
  }
  const arr = encouragements[step];
  if (!arr) return "";
  return arr[Math.floor(Math.random() * arr.length)];
}

function formatCurrency(num) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num);
}

function CurrencyInput({ value, onChange, placeholder, autoFocus }) {
  const inputRef = useRef(null);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const handleChange = (e) => {
    const raw = e.target.value.replace(/[^0-9]/g, "");
    onChange(raw === "" ? "" : parseInt(raw, 10));
  };

  return (
    <div style={{
      position: "relative",
      width: "100%",
      maxWidth: 360,
    }}>
      <span style={{
        position: "absolute",
        left: 20,
        top: "50%",
        transform: "translateY(-50%)",
        fontSize: 28,
        fontFamily: "'DM Sans', sans-serif",
        color: value ? "#1a1a1a" : "#aaa",
        fontWeight: 600,
        pointerEvents: "none",
      }}>$</span>
      <input
        ref={inputRef}
        type="text"
        inputMode="numeric"
        value={value === "" ? "" : value.toLocaleString()}
        onChange={handleChange}
        placeholder={placeholder || "0"}
        style={{
          width: "100%",
          padding: "18px 20px 18px 44px",
          fontSize: 28,
          fontFamily: "'DM Sans', sans-serif",
          fontWeight: 600,
          color: "#1a1a1a",
          background: "#f7f7f5",
          border: "2px solid #e0ddd8",
          borderRadius: 14,
          outline: "none",
          transition: "border-color 0.2s ease, box-shadow 0.2s ease",
          boxSizing: "border-box",
        }}
        onFocus={(e) => {
          e.target.style.borderColor = "#1a1a1a";
          e.target.style.boxShadow = "0 0 0 4px rgba(26,26,26,0.08)";
        }}
        onBlur={(e) => {
          e.target.style.borderColor = "#e0ddd8";
          e.target.style.boxShadow = "none";
        }}
      />
    </div>
  );
}

function FadeIn({ children, delay = 0, style = {} }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  return (
    <div
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(18px)",
        transition: "opacity 0.6s ease, transform 0.6s ease",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export default function GraceFinanceOnboarding() {
  const [step, setStep] = useState("welcome");
  const [income, setIncome] = useState("");
  const [expenses, setExpenses] = useState("");
  const [debt, setDebt] = useState("");
  const [goal, setGoal] = useState("");
  const [encouragement, setEncouragement] = useState("");
  const [showEncouragement, setShowEncouragement] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const [snapshotReady, setSnapshotReady] = useState(false);

  const stepIndex = STEPS.indexOf(step);
  const progress = step === "welcome" ? 0 : step === "snapshot" ? 100 : (stepIndex / (STEPS.length - 1)) * 100;

  const goNext = (nextStep, encourageKey, encourageValue) => {
    if (encourageKey) {
      const msg = getEncouragement(encourageKey, encourageValue);
      setEncouragement(msg);
      setShowEncouragement(true);
      setTimeout(() => {
        setShowEncouragement(false);
        setTimeout(() => {
          setTransitioning(true);
          setTimeout(() => {
            setStep(nextStep);
            setTransitioning(false);
          }, 300);
        }, 200);
      }, 1800);
    } else {
      setTransitioning(true);
      setTimeout(() => {
        setStep(nextStep);
        setTransitioning(false);
      }, 300);
    }
  };

  useEffect(() => {
    if (step === "snapshot") {
      setTimeout(() => setSnapshotReady(true), 400);
    }
  }, [step]);

  const incomeVal = income === "" ? 0 : income;
  const expensesVal = expenses === "" ? 0 : expenses;
  const debtVal = debt === "" ? 0 : debt;
  const available = incomeVal - expensesVal;
  const debtFreeMonths = debtVal > 0 && available > 0 ? Math.ceil(debtVal / available) : null;
  const acceleratedMonths = debtFreeMonths ? Math.ceil(debtFreeMonths * 0.7) : null;
  const savingsRate = incomeVal > 0 ? ((available / incomeVal) * 100).toFixed(0) : 0;

  const containerStyle = {
    minHeight: "100vh",
    width: "100%",
    background: step === "welcome"
      ? "linear-gradient(165deg, #1a1a1a 0%, #2d2d2d 40%, #1a1a1a 100%)"
      : step === "snapshot"
      ? "linear-gradient(165deg, #f7f7f5 0%, #ede9e3 100%)"
      : "#fafaf8",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "'DM Sans', sans-serif",
    position: "relative",
    overflow: "hidden",
    padding: "40px 20px",
    boxSizing: "border-box",
  };

  const buttonStyle = {
    padding: "16px 48px",
    fontSize: 17,
    fontWeight: 700,
    fontFamily: "'DM Sans', sans-serif",
    color: step === "welcome" ? "#1a1a1a" : "#fff",
    background: step === "welcome" ? "#f7f7f5" : "#1a1a1a",
    border: "none",
    borderRadius: 12,
    cursor: "pointer",
    transition: "all 0.25s ease",
    letterSpacing: "0.02em",
  };

  const labelStyle = {
    fontSize: 15,
    color: "#888",
    marginBottom: 8,
    fontWeight: 500,
    letterSpacing: "0.03em",
    textTransform: "uppercase",
  };

  const questionStyle = {
    fontSize: 26,
    fontWeight: 700,
    color: "#1a1a1a",
    marginBottom: 8,
    lineHeight: 1.3,
    fontFamily: "'Playfair Display', serif",
  };

  const subTextStyle = {
    fontSize: 14,
    color: "#999",
    marginBottom: 32,
    lineHeight: 1.5,
  };

  return (
    <>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700;800&display=swap" rel="stylesheet" />

      <div style={containerStyle}>
        {/* Progress bar */}
        {step !== "welcome" && (
          <div style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100%",
            height: 4,
            background: "#e8e5e0",
            zIndex: 100,
          }}>
            <div style={{
              height: "100%",
              width: `${progress}%`,
              background: "linear-gradient(90deg, #1a1a1a, #444)",
              transition: "width 0.6s ease",
              borderRadius: "0 2px 2px 0",
            }} />
          </div>
        )}

        {/* Encouragement overlay */}
        {showEncouragement && (
          <div style={{
            position: "fixed",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "rgba(250,250,248,0.97)",
            zIndex: 200,
            padding: 40,
          }}>
            <FadeIn>
              <p style={{
                fontSize: 24,
                fontWeight: 600,
                color: "#1a1a1a",
                textAlign: "center",
                lineHeight: 1.5,
                fontFamily: "'Playfair Display', serif",
                maxWidth: 460,
              }}>
                {encouragement}
              </p>
            </FadeIn>
          </div>
        )}

        {/* Content */}
        <div style={{
          opacity: transitioning ? 0 : 1,
          transform: transitioning ? "translateY(12px)" : "translateY(0)",
          transition: "opacity 0.3s ease, transform 0.3s ease",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          width: "100%",
          maxWidth: 480,
        }}>

          {/* ===== WELCOME ===== */}
          {step === "welcome" && (
            <>
              {/* Decorative dots */}
              <div style={{ position: "absolute", top: 40, left: 40, opacity: 0.08 }}>
                {[...Array(6)].map((_, i) => (
                  <div key={i} style={{
                    width: 6, height: 6, borderRadius: "50%",
                    background: "#fff", marginBottom: 12,
                  }} />
                ))}
              </div>

              <FadeIn delay={200}>
                <div style={{
                  width: 64, height: 64, borderRadius: 16,
                  background: "rgba(255,255,255,0.08)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  marginBottom: 32, fontSize: 28,
                }}>
                  🐾
                </div>
              </FadeIn>

              <FadeIn delay={400}>
                <h1 style={{
                  fontSize: 48,
                  fontWeight: 800,
                  color: "#f7f7f5",
                  fontFamily: "'Playfair Display', serif",
                  letterSpacing: "-0.02em",
                  marginBottom: 4,
                  textAlign: "center",
                  lineHeight: 1.1,
                }}>
                  GraceFinance
                </h1>
              </FadeIn>

              <FadeIn delay={600}>
                <p style={{
                  fontSize: 13,
                  letterSpacing: "0.15em",
                  textTransform: "uppercase",
                  color: "rgba(247,247,245,0.45)",
                  marginBottom: 48,
                  fontWeight: 500,
                }}>
                  Smarter Finance is Right Around the Corner™
                </p>
              </FadeIn>

              <FadeIn delay={800}>
                <p style={{
                  fontSize: 20,
                  color: "rgba(247,247,245,0.75)",
                  textAlign: "center",
                  lineHeight: 1.6,
                  maxWidth: 380,
                  marginBottom: 48,
                  fontFamily: "'Playfair Display', serif",
                }}>
                  Tired of wondering where your money went?
                  <br /><br />
                  <span style={{ color: "rgba(247,247,245,0.5)", fontSize: 17 }}>
                    In 60 seconds, you'll see your money differently.
                  </span>
                </p>
              </FadeIn>

              <FadeIn delay={1100}>
                <button
                  style={buttonStyle}
                  onClick={() => goNext("income")}
                  onMouseEnter={(e) => {
                    e.target.style.transform = "translateY(-2px)";
                    e.target.style.boxShadow = "0 8px 30px rgba(247,247,245,0.15)";
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = "translateY(0)";
                    e.target.style.boxShadow = "none";
                  }}
                >
                  Take Control Now
                </button>
              </FadeIn>

              <FadeIn delay={1400}>
                <p style={{
                  fontSize: 12,
                  color: "rgba(247,247,245,0.25)",
                  marginTop: 24,
                }}>
                  No card required · Free to start · Your data stays yours
                </p>
              </FadeIn>
            </>
          )}

          {/* ===== INCOME ===== */}
          {step === "income" && (
            <>
              <FadeIn delay={100}>
                <p style={labelStyle}>Step 1 of 4</p>
              </FadeIn>
              <FadeIn delay={200}>
                <h2 style={questionStyle}>What do you bring home each month?</h2>
              </FadeIn>
              <FadeIn delay={300}>
                <p style={subTextStyle}>Your total monthly income after taxes.</p>
              </FadeIn>
              <FadeIn delay={400}>
                <CurrencyInput
                  value={income}
                  onChange={setIncome}
                  placeholder="4,500"
                  autoFocus
                />
              </FadeIn>
              <FadeIn delay={500} style={{ marginTop: 32 }}>
                <button
                  style={{
                    ...buttonStyle,
                    opacity: income === "" || income <= 0 ? 0.4 : 1,
                    pointerEvents: income === "" || income <= 0 ? "none" : "auto",
                  }}
                  onClick={() => goNext("expenses", "income", incomeVal)}
                  onMouseEnter={(e) => {
                    e.target.style.transform = "translateY(-2px)";
                    e.target.style.boxShadow = "0 6px 24px rgba(0,0,0,0.12)";
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = "translateY(0)";
                    e.target.style.boxShadow = "none";
                  }}
                >
                  Continue
                </button>
              </FadeIn>
            </>
          )}

          {/* ===== EXPENSES ===== */}
          {step === "expenses" && (
            <>
              <FadeIn delay={100}>
                <p style={labelStyle}>Step 2 of 4</p>
              </FadeIn>
              <FadeIn delay={200}>
                <h2 style={questionStyle}>What goes out every month?</h2>
              </FadeIn>
              <FadeIn delay={300}>
                <p style={subTextStyle}>Rent, bills, groceries, subscriptions — everything.</p>
              </FadeIn>
              <FadeIn delay={400}>
                <CurrencyInput
                  value={expenses}
                  onChange={setExpenses}
                  placeholder="3,200"
                  autoFocus
                />
              </FadeIn>
              <FadeIn delay={500} style={{ marginTop: 32 }}>
                <button
                  style={{
                    ...buttonStyle,
                    opacity: expenses === "" || expenses <= 0 ? 0.4 : 1,
                    pointerEvents: expenses === "" || expenses <= 0 ? "none" : "auto",
                  }}
                  onClick={() => goNext("debt", "expenses", expensesVal)}
                  onMouseEnter={(e) => {
                    e.target.style.transform = "translateY(-2px)";
                    e.target.style.boxShadow = "0 6px 24px rgba(0,0,0,0.12)";
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = "translateY(0)";
                    e.target.style.boxShadow = "none";
                  }}
                >
                  Continue
                </button>
              </FadeIn>
            </>
          )}

          {/* ===== DEBT ===== */}
          {step === "debt" && (
            <>
              <FadeIn delay={100}>
                <p style={labelStyle}>Step 3 of 4</p>
              </FadeIn>
              <FadeIn delay={200}>
                <h2 style={questionStyle}>How much debt are you carrying?</h2>
              </FadeIn>
              <FadeIn delay={300}>
                <p style={subTextStyle}>Credit cards, loans, car payments — the whole picture. Enter $0 if debt-free.</p>
              </FadeIn>
              <FadeIn delay={400}>
                <CurrencyInput
                  value={debt}
                  onChange={setDebt}
                  placeholder="0"
                  autoFocus
                />
              </FadeIn>
              <FadeIn delay={500} style={{ marginTop: 32 }}>
                <button
                  style={{
                    ...buttonStyle,
                    opacity: debt === "" ? 0.4 : 1,
                    pointerEvents: debt === "" ? "none" : "auto",
                  }}
                  onClick={() => goNext("goal", "debt", debtVal)}
                  onMouseEnter={(e) => {
                    e.target.style.transform = "translateY(-2px)";
                    e.target.style.boxShadow = "0 6px 24px rgba(0,0,0,0.12)";
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = "translateY(0)";
                    e.target.style.boxShadow = "none";
                  }}
                >
                  Continue
                </button>
              </FadeIn>
            </>
          )}

          {/* ===== GOAL ===== */}
          {step === "goal" && (
            <>
              <FadeIn delay={100}>
                <p style={labelStyle}>Step 4 of 4</p>
              </FadeIn>
              <FadeIn delay={200}>
                <h2 style={questionStyle}>What are you fighting for?</h2>
              </FadeIn>
              <FadeIn delay={300}>
                <p style={subTextStyle}>
                  A house. An emergency fund. Freedom from debt. Your kids' future.
                  <br />Be ambitious — this is what GraceFinance is built for.
                </p>
              </FadeIn>
              <FadeIn delay={400}>
                <textarea
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="I want to save $15,000 for a down payment on my first home by next year..."
                  autoFocus
                  style={{
                    width: "100%",
                    maxWidth: 360,
                    padding: "16px 20px",
                    fontSize: 16,
                    fontFamily: "'DM Sans', sans-serif",
                    color: "#1a1a1a",
                    background: "#f7f7f5",
                    border: "2px solid #e0ddd8",
                    borderRadius: 14,
                    outline: "none",
                    minHeight: 120,
                    resize: "vertical",
                    lineHeight: 1.6,
                    transition: "border-color 0.2s ease",
                    boxSizing: "border-box",
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = "#1a1a1a";
                    e.target.style.boxShadow = "0 0 0 4px rgba(26,26,26,0.08)";
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = "#e0ddd8";
                    e.target.style.boxShadow = "none";
                  }}
                />
              </FadeIn>
              <FadeIn delay={500} style={{ marginTop: 32 }}>
                <button
                  style={{
                    ...buttonStyle,
                    opacity: !goal.trim() ? 0.4 : 1,
                    pointerEvents: !goal.trim() ? "none" : "auto",
                    padding: "16px 56px",
                  }}
                  onClick={() => goNext("snapshot")}
                  onMouseEnter={(e) => {
                    e.target.style.transform = "translateY(-2px)";
                    e.target.style.boxShadow = "0 6px 24px rgba(0,0,0,0.12)";
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.transform = "translateY(0)";
                    e.target.style.boxShadow = "none";
                  }}
                >
                  Show Me My Path
                </button>
              </FadeIn>
            </>
          )}

          {/* ===== SNAPSHOT ===== */}
          {step === "snapshot" && (
            <div style={{ width: "100%", maxWidth: 480 }}>
              <FadeIn delay={200}>
                <p style={{
                  fontSize: 13,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: "#aaa",
                  marginBottom: 8,
                  textAlign: "center",
                  fontWeight: 500,
                }}>Your Financial Snapshot</p>
              </FadeIn>

              <FadeIn delay={400}>
                <h2 style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: "#1a1a1a",
                  textAlign: "center",
                  fontFamily: "'Playfair Display', serif",
                  marginBottom: 40,
                  lineHeight: 1.3,
                }}>
                  {available > 0
                    ? "You have more power than you think."
                    : "Let's find your breathing room."}
                </h2>
              </FadeIn>

              {/* Stats Grid */}
              <FadeIn delay={600}>
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 12,
                  marginBottom: 24,
                }}>
                  {[
                    { label: "Monthly Income", value: formatCurrency(incomeVal), color: "#2d6a4f" },
                    { label: "Monthly Expenses", value: formatCurrency(expensesVal), color: "#c44536" },
                    { label: "Available Monthly", value: formatCurrency(available), color: available >= 0 ? "#2d6a4f" : "#c44536" },
                    { label: "Total Debt", value: formatCurrency(debtVal), color: debtVal > 0 ? "#c44536" : "#2d6a4f" },
                  ].map((item, i) => (
                    <div key={i} style={{
                      background: "#fff",
                      borderRadius: 14,
                      padding: "20px 18px",
                      border: "1px solid #e8e5e0",
                    }}>
                      <p style={{
                        fontSize: 11,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        color: "#999",
                        marginBottom: 6,
                        fontWeight: 500,
                      }}>{item.label}</p>
                      <p style={{
                        fontSize: 24,
                        fontWeight: 700,
                        color: item.color,
                        fontFamily: "'DM Sans', sans-serif",
                      }}>{item.value}</p>
                    </div>
                  ))}
                </div>
              </FadeIn>

              {/* Insight Card */}
              <FadeIn delay={900}>
                <div style={{
                  background: "linear-gradient(135deg, #1a1a1a, #2d2d2d)",
                  borderRadius: 16,
                  padding: "28px 24px",
                  marginBottom: 16,
                  color: "#f7f7f5",
                }}>
                  <p style={{
                    fontSize: 11,
                    textTransform: "uppercase",
                    letterSpacing: "0.12em",
                    color: "rgba(247,247,245,0.5)",
                    marginBottom: 12,
                    fontWeight: 600,
                  }}>🐾 GraceFinance Insight</p>

                  {debtVal > 0 && available > 0 && (
                    <p style={{ fontSize: 18, lineHeight: 1.6, fontWeight: 500 }}>
                      At your current pace, you could be debt-free in{" "}
                      <span style={{ color: "#f4a261", fontWeight: 700 }}>{debtFreeMonths} months</span>.
                      <br />
                      With GraceFinance optimizing your spending, we'll target{" "}
                      <span style={{ color: "#81b29a", fontWeight: 700 }}>{acceleratedMonths} months</span>.
                    </p>
                  )}

                  {debtVal > 0 && available <= 0 && (
                    <p style={{ fontSize: 18, lineHeight: 1.6, fontWeight: 500 }}>
                      You're spending more than you earn right now. That's exactly why you're here.
                      GraceFinance will help you find the gaps and build a path forward — starting today.
                    </p>
                  )}

                  {debtVal === 0 && available > 0 && (
                    <p style={{ fontSize: 18, lineHeight: 1.6, fontWeight: 500 }}>
                      You're saving{" "}
                      <span style={{ color: "#81b29a", fontWeight: 700 }}>{savingsRate}%</span> of your income.
                      That's {formatCurrency(available)} every month building your future.
                      {parseInt(savingsRate) >= 20
                        ? " You're outperforming most Americans. Let's accelerate."
                        : " Let's push that higher together."}
                    </p>
                  )}

                  {debtVal === 0 && available <= 0 && (
                    <p style={{ fontSize: 18, lineHeight: 1.6, fontWeight: 500 }}>
                      No debt is great. But your expenses are eating everything.
                      Let's find the leaks and redirect that cash to your goal.
                    </p>
                  )}
                </div>
              </FadeIn>

              {/* Goal Card */}
              <FadeIn delay={1100}>
                <div style={{
                  background: "#fff",
                  borderRadius: 14,
                  padding: "22px 24px",
                  border: "1px solid #e8e5e0",
                  marginBottom: 32,
                }}>
                  <p style={{
                    fontSize: 11,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                    color: "#999",
                    marginBottom: 8,
                    fontWeight: 500,
                  }}>Your Mission</p>
                  <p style={{
                    fontSize: 16,
                    color: "#1a1a1a",
                    lineHeight: 1.6,
                    fontStyle: "italic",
                    fontFamily: "'Playfair Display', serif",
                  }}>"{goal}"</p>
                </div>
              </FadeIn>

              {/* CTA */}
              <FadeIn delay={1300}>
                <div style={{ textAlign: "center" }}>
                  <button
                    style={{
                      ...buttonStyle,
                      padding: "18px 64px",
                      fontSize: 18,
                      background: "linear-gradient(135deg, #1a1a1a, #333)",
                      borderRadius: 14,
                    }}
                    onClick={() => alert("🚀 This is where the dashboard loads! Ready to build it next?")}
                    onMouseEnter={(e) => {
                      e.target.style.transform = "translateY(-2px)";
                      e.target.style.boxShadow = "0 8px 32px rgba(0,0,0,0.18)";
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.transform = "translateY(0)";
                      e.target.style.boxShadow = "none";
                    }}
                  >
                    Let's Build My Plan →
                  </button>
                  <p style={{
                    fontSize: 13,
                    color: "#bbb",
                    marginTop: 16,
                  }}>
                    Smarter Finance is Right Around the Corner™
                  </p>
                </div>
              </FadeIn>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
