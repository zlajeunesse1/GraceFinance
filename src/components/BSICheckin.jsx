/**
 * BSICheckin — Weekly Behavioral Shift Check-In
 * ═══════════════════════════════════════════════
 * Shows a banner on the dashboard Fri-Sun.
 * Expands into a 5-question flow: trigger (yes/no) + motivation (why).
 * Submits to /bsi/submit, shows results with coaching reflections.
 *
 * File: src/components/BSICheckin.jsx
 */

import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"

var API_BASE = window.location.hostname === "localhost"
  ? "http://localhost:8000"
  : "https://gracefinance-production.up.railway.app"

var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

var C = {
  bg: "#000000", card: "#0a0a0a", border: "#1a1a1a",
  text: "#ffffff", muted: "#9ca3af", dim: "#6b7280", faint: "#4b5563",
  green: "#10b981", red: "#ef4444", amber: "#f59e0b",
}

function apiFetch(endpoint, options) {
  var token = localStorage.getItem("grace_token")
  var headers = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = "Bearer " + token
  var config = { headers: headers }
  if (options) {
    for (var k in options) {
      if (k === "headers") { for (var h in options.headers) headers[h] = options.headers[h] }
      else { config[k] = options[k] }
    }
  }
  config.headers = headers
  return fetch(API_BASE + endpoint, config).then(function (res) {
    if (!res.ok) return res.json().catch(function () { return { detail: "Request failed" } }).then(function (err) { throw new Error(err.detail || "Request failed") })
    return res.json()
  })
}


// ═══════════════════════════════════════════
//  MAIN COMPONENT
// ═══════════════════════════════════════════

export default function BSICheckin({ onComplete }) {
  var navigate = useNavigate()

  var [status, setStatus] = useState("loading")  // loading | unavailable | available | active | submitting | results
  var [questions, setQuestions] = useState([])
  var [statusMessage, setStatusMessage] = useState("")
  var [opensIn, setOpensIn] = useState(null)

  // Answer state: { "BX-1": { triggered: true, motivation_id: "BX-1-B" }, ... }
  var [answers, setAnswers] = useState({})
  var [currentStep, setCurrentStep] = useState(0)
  var [results, setResults] = useState(null)
  var [error, setError] = useState(null)

  useEffect(function () {
    apiFetch("/bsi/questions")
      .then(function (data) {
        if (data.already_completed) {
          setStatus("unavailable")
          setStatusMessage("Completed this week ✓")
        } else if (data.available) {
          setStatus("available")
          setQuestions(data.questions)
        } else {
          setStatus("unavailable")
          setStatusMessage(data.message || "Opens Friday")
          setOpensIn(data.opens_in_days || null)
        }
      })
      .catch(function () {
        setStatus("unavailable")
        setStatusMessage("Could not load BSI")
      })
  }, [])

  function handleTrigger(questionId, triggered) {
    setAnswers(function (prev) {
      var next = Object.assign({}, prev)
      next[questionId] = { triggered: triggered, motivation_id: null }
      return next
    })

    // If "No", auto-advance to next question
    if (!triggered) {
      if (currentStep < questions.length - 1) {
        setTimeout(function () { setCurrentStep(function (s) { return s + 1 }) }, 300)
      }
    }
  }

  function handleMotivation(questionId, motivationId) {
    setAnswers(function (prev) {
      var next = Object.assign({}, prev)
      next[questionId] = { triggered: true, motivation_id: motivationId }
      return next
    })

    // Auto-advance after motivation selected
    if (currentStep < questions.length - 1) {
      setTimeout(function () { setCurrentStep(function (s) { return s + 1 }) }, 400)
    }
  }

  function handleSubmit() {
    setStatus("submitting")
    setError(null)

    var payload = questions.map(function (q) {
      var answer = answers[q.question_id] || { triggered: false, motivation_id: null }
      return {
        question_id: q.question_id,
        triggered: answer.triggered,
        motivation_id: answer.motivation_id,
      }
    })

    apiFetch("/bsi/submit", {
      method: "POST",
      body: JSON.stringify({ answers: payload }),
    })
      .then(function (data) {
        setResults(data)
        setStatus("results")
        if (onComplete) onComplete(data)
      })
      .catch(function (err) {
        setError(err.message)
        setStatus("active")
      })
  }

  var allAnswered = questions.length > 0 && questions.every(function (q) {
    var a = answers[q.question_id]
    if (!a) return false
    if (a.triggered && !a.motivation_id) return false
    return true
  })

  // ── Don't render anything if loading ──
  if (status === "loading") return null

  // ── Unavailable state — subtle info bar ──
  if (status === "unavailable") {
    return (
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "12px 16px", marginBottom: 16,
        background: C.card, border: "1px solid " + C.border, borderRadius: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: statusMessage.includes("✓") ? C.green : C.faint }} />
          <span style={{ fontSize: 12, color: C.muted, fontFamily: FONT }}>
            Weekly Behavioral Check-in
          </span>
        </div>
        <span style={{ fontSize: 11, color: C.faint, fontFamily: FONT }}>
          {statusMessage}
          {opensIn && !statusMessage.includes("✓") ? " (" + opensIn + "d)" : ""}
        </span>
      </div>
    )
  }

  // ── Available — show banner ──
  if (status === "available") {
    return (
      <div style={{
        padding: "18px 20px", marginBottom: 16,
        background: "rgba(16,185,129,0.04)",
        border: "1px solid rgba(16,185,129,0.2)",
        borderRadius: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.green }} />
              <span style={{ fontSize: 13, fontWeight: 600, color: C.text, fontFamily: FONT }}>
                Weekly Behavioral Check-in
              </span>
            </div>
            <p style={{ fontSize: 12, color: C.dim, margin: 0, lineHeight: 1.6, fontFamily: FONT }}>
              5 quick questions about your financial behavior this week. Takes about 60 seconds.
            </p>
          </div>
          <button
            onClick={function () { setStatus("active"); setCurrentStep(0) }}
            style={{
              padding: "10px 20px", borderRadius: 7, border: "none",
              background: C.text, color: C.bg,
              fontSize: 13, fontWeight: 700, fontFamily: FONT,
              cursor: "pointer", whiteSpace: "nowrap", flexShrink: 0,
            }}
          >
            Start
          </button>
        </div>
      </div>
    )
  }

  // ── Active — question flow ──
  if (status === "active" || status === "submitting") {
    var q = questions[currentStep]
    var answer = answers[q.question_id] || {}
    var isLast = currentStep === questions.length - 1

    return (
      <div style={{
        padding: "24px", marginBottom: 16,
        background: C.card, border: "1px solid " + C.border, borderRadius: 12,
      }}>
        {/* Progress */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <span style={{ fontSize: 11, color: C.muted, fontFamily: FONT, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Behavioral Check-in
          </span>
          <span style={{ fontSize: 11, color: C.faint, fontFamily: FONT }}>
            {currentStep + 1} of {questions.length}
          </span>
        </div>

        {/* Progress bar */}
        <div style={{ height: 2, background: C.border, borderRadius: 2, marginBottom: 24, overflow: "hidden" }}>
          <div style={{
            height: "100%", borderRadius: 2, background: C.text,
            width: ((currentStep + (allAnswered && isLast ? 1 : 0)) / questions.length * 100) + "%",
            transition: "width 0.4s ease",
          }} />
        </div>

        {/* Pattern label */}
        <div style={{
          display: "inline-block", padding: "4px 10px", borderRadius: 20,
          background: "rgba(255,255,255,0.04)", border: "1px solid " + C.border,
          fontSize: 10, color: C.muted, fontFamily: FONT, fontWeight: 500,
          textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 16,
        }}>
          {q.pattern_label}
        </div>

        {/* Trigger question */}
        <p style={{ fontSize: 15, color: C.text, lineHeight: 1.6, margin: "0 0 20px", fontFamily: FONT, fontWeight: 400 }}>
          {q.trigger_text}
        </p>

        {/* Yes / No buttons */}
        <div style={{ display: "flex", gap: 10, marginBottom: answer.triggered ? 20 : 0 }}>
          <button
            onClick={function () { handleTrigger(q.question_id, true) }}
            style={{
              flex: 1, padding: "12px", borderRadius: 8,
              border: "1px solid " + (answer.triggered === true ? C.text : C.border),
              background: answer.triggered === true ? "rgba(255,255,255,0.06)" : "transparent",
              color: answer.triggered === true ? C.text : C.dim,
              fontSize: 13, fontWeight: 600, fontFamily: FONT, cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            Yes
          </button>
          <button
            onClick={function () { handleTrigger(q.question_id, false) }}
            style={{
              flex: 1, padding: "12px", borderRadius: 8,
              border: "1px solid " + (answer.triggered === false ? C.text : C.border),
              background: answer.triggered === false ? "rgba(255,255,255,0.06)" : "transparent",
              color: answer.triggered === false ? C.text : C.dim,
              fontSize: 13, fontWeight: 600, fontFamily: FONT, cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            No
          </button>
        </div>

        {/* Motivation options — only show if triggered = yes */}
        {answer.triggered === true && q.motivations && (
          <div>
            <p style={{ fontSize: 11, color: C.muted, margin: "0 0 10px", fontFamily: FONT, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              What best describes why?
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {q.motivations.map(function (m) {
                var isSelected = answer.motivation_id === m.id
                return (
                  <button
                    key={m.id}
                    onClick={function () { handleMotivation(q.question_id, m.id) }}
                    style={{
                      padding: "12px 16px", borderRadius: 8, textAlign: "left",
                      border: "1px solid " + (isSelected ? C.text : C.border),
                      background: isSelected ? "rgba(255,255,255,0.06)" : "transparent",
                      color: isSelected ? C.text : C.muted,
                      fontSize: 13, fontFamily: FONT, cursor: "pointer",
                      transition: "all 0.2s ease", lineHeight: 1.5,
                    }}
                  >
                    {m.text}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Navigation */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 24, paddingTop: 16, borderTop: "1px solid " + C.border }}>
          <button
            onClick={function () { if (currentStep > 0) setCurrentStep(function (s) { return s - 1 }) }}
            disabled={currentStep === 0}
            style={{
              padding: "8px 16px", borderRadius: 6,
              border: "1px solid " + C.border, background: "transparent",
              color: currentStep === 0 ? C.faint : C.muted,
              fontSize: 12, fontFamily: FONT, cursor: currentStep === 0 ? "default" : "pointer",
            }}
          >
            Back
          </button>

          {isLast && allAnswered ? (
            <button
              onClick={handleSubmit}
              disabled={status === "submitting"}
              style={{
                padding: "10px 24px", borderRadius: 7, border: "none",
                background: C.text, color: C.bg,
                fontSize: 13, fontWeight: 700, fontFamily: FONT,
                cursor: status === "submitting" ? "wait" : "pointer",
                opacity: status === "submitting" ? 0.6 : 1,
              }}
            >
              {status === "submitting" ? "Analyzing..." : "Submit"}
            </button>
          ) : (
            <button
              onClick={function () { if (currentStep < questions.length - 1) setCurrentStep(function (s) { return s + 1 }) }}
              disabled={!answers[q.question_id]}
              style={{
                padding: "8px 16px", borderRadius: 6,
                border: "1px solid " + (answers[q.question_id] ? C.text : C.border),
                background: "transparent",
                color: answers[q.question_id] ? C.text : C.faint,
                fontSize: 12, fontFamily: FONT,
                cursor: answers[q.question_id] ? "pointer" : "default",
              }}
            >
              Next
            </button>
          )}
        </div>

        {error && (
          <div style={{ marginTop: 12, padding: "10px 14px", background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 8 }}>
            <p style={{ color: C.red, fontSize: 12, margin: 0, fontFamily: FONT }}>{error}</p>
          </div>
        )}
      </div>
    )
  }

  // ── Results ──
  if (status === "results" && results) {
    var bsi = results.bsi_composite
    var bsiColor = bsi > 20 ? C.green : bsi < -20 ? C.red : C.muted
    var interp = results.interpretation || {}

    return (
      <div style={{
        padding: "24px", marginBottom: 16,
        background: C.card, border: "1px solid " + C.border, borderRadius: 12,
      }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{ fontSize: 11, color: C.muted, fontFamily: FONT, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }}>
            Your Behavioral Shift Indicator
          </div>
          <div style={{ fontSize: 48, fontWeight: 700, color: bsiColor, fontFamily: FONT, letterSpacing: "-0.03em" }}>
            {bsi > 0 ? "+" : ""}{bsi.toFixed(0)}
          </div>
          <div style={{ fontSize: 13, color: C.dim, marginTop: 4, fontFamily: FONT }}>
            {interp.emoji} {interp.band}
          </div>
          {results.bsi_delta !== null && results.bsi_delta !== undefined && (
            <div style={{ fontSize: 12, color: results.bsi_delta > 0 ? C.green : results.bsi_delta < 0 ? C.red : C.faint, marginTop: 6, fontFamily: FONT }}>
              {results.bsi_delta > 0 ? "↑" : results.bsi_delta < 0 ? "↓" : "→"} {Math.abs(results.bsi_delta).toFixed(1)} vs last week
            </div>
          )}
        </div>

        {/* Interpretation */}
        <p style={{ fontSize: 13, color: C.muted, lineHeight: 1.7, textAlign: "center", margin: "0 0 24px", fontFamily: FONT }}>
          {interp.message}
        </p>

        {/* Patterns */}
        {results.stress_patterns && results.stress_patterns.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, color: C.red, fontFamily: FONT, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>Stress Signals</div>
            {results.stress_patterns.map(function (p, i) {
              return (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0", borderBottom: "1px solid " + C.border }}>
                  <span style={{ color: C.red, fontSize: 12 }}>⚠</span>
                  <span style={{ color: C.muted, fontSize: 12, fontFamily: FONT }}>{p.label}</span>
                </div>
              )
            })}
          </div>
        )}

        {results.positive_patterns && results.positive_patterns.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 10, color: C.green, fontFamily: FONT, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>Positive Signals</div>
            {results.positive_patterns.map(function (p, i) {
              return (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0", borderBottom: "1px solid " + C.border }}>
                  <span style={{ color: C.green, fontSize: 12 }}>✓</span>
                  <span style={{ color: C.muted, fontSize: 12, fontFamily: FONT }}>{p.label}</span>
                </div>
              )
            })}
          </div>
        )}

        {/* Coaching Reflections */}
        {results.coaching_reflections && results.coaching_reflections.length > 0 && (
          <div style={{
            padding: "16px", marginTop: 16,
            background: "rgba(255,255,255,0.02)", border: "1px solid " + C.border, borderRadius: 8,
          }}>
            <div style={{ fontSize: 10, color: C.muted, fontFamily: FONT, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10 }}>
              How This Connects to Your Score
            </div>
            {results.coaching_reflections.slice(0, 3).map(function (r, i) {
              return (
                <p key={i} style={{ fontSize: 12, color: C.dim, lineHeight: 1.7, margin: i === 0 ? 0 : "10px 0 0", fontFamily: FONT }}>
                  {r.reflection}
                </p>
              )
            })}
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
          <button
            onClick={function () { navigate("/grace") }}
            style={{
              flex: 1, padding: "12px", borderRadius: 8,
              border: "1px solid " + C.border, background: "transparent",
              color: C.muted, fontSize: 12, fontWeight: 600, fontFamily: FONT, cursor: "pointer",
            }}
          >
            Talk to Grace About This
          </button>
          <button
            onClick={function () { setStatus("unavailable"); setStatusMessage("Completed this week ✓") }}
            style={{
              flex: 1, padding: "12px", borderRadius: 8,
              border: "none", background: C.text, color: C.bg,
              fontSize: 12, fontWeight: 600, fontFamily: FONT, cursor: "pointer",
            }}
          >
            Done
          </button>
        </div>
      </div>
    )
  }

  return null
}