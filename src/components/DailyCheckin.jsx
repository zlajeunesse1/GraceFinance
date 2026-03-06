/**
 * DailyCheckin — v5 Polish
 * Warm completion messages. Clean data collection. FCS-forward.
 */

import { useState, useEffect } from 'react'

var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'

var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"
var C = { bg: "#000000", card: "#0a0a0a", border: "#1a1a1a", text: "#ffffff", muted: "#666666", dim: "#444444", faint: "#333333", error: "#ff4444" }

function authHeaders() { return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + localStorage.getItem('grace_token') } }

var dimensionLabels = {
  current_stability: 'Stability', future_outlook: 'Outlook', purchasing_power: 'Purchasing Power',
  emergency_readiness: 'Emergency Readiness', financial_agency: 'Financial Agency',
  subscription_churn: 'Subscription Shifts', credit_substitution: 'Credit Patterns',
  deferred_spending: 'Spending Timing', debt_accumulation: 'Debt Patterns', financial_avoidance: 'Engagement',
}

function formatDimension(dim) {
  if (!dim) return ''; if (dimensionLabels[dim]) return dimensionLabels[dim]
  return dim.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase() })
}
function getScaleLabels(q) { return { low: q.low_label || 'Low', high: q.high_label || 'High' } }
function getQuestionType(q) { if (!q) return 'scale_5'; if (q.scale_type === 'yes_no_scale') return 'yes_no'; if (q.scale_type === '1-10') return 'slider'; return 'scale_5' }

export default function DailyCheckin(props) {
  var onCheckinComplete = props.onCheckinComplete || null
  var questionsState = useState([]); var questions = questionsState[0]; var setQuestions = questionsState[1]
  var answersState = useState({}); var answers = answersState[0]; var setAnswers = answersState[1]
  var loadingState = useState(true); var loading = loadingState[0]; var setLoading = loadingState[1]
  var errorState = useState(null); var error = errorState[0]; var setError = errorState[1]
  var submittedState = useState(false); var submitted = submittedState[0]; var setSubmitted = submittedState[1]
  var submittingState = useState(false); var submitting = submittingState[0]; var setSubmitting = submittingState[1]
  var indexState = useState(0); var currentIndex = indexState[0]; var setCurrentIndex = indexState[1]
  var resultState = useState(null); var result = resultState[0]; var setResult = resultState[1]
  var isWeeklyState = useState(false); var isWeekly = isWeeklyState[0]; var setIsWeekly = isWeeklyState[1]

  useEffect(function () { fetchQuestions() }, [])

  function fetchQuestions() {
    setLoading(true); setError(null)
    fetch(API_BASE + '/checkin/questions', { headers: authHeaders() })
      .then(function (res) { if (res.status === 401) throw new Error('Please log in to continue'); if (!res.ok) throw new Error('Failed to load questions'); return res.json() })
      .then(function (data) {
        var allQuestions = (data.daily_questions || [])
        if (data.is_weekly_day && data.weekly_questions) { allQuestions = allQuestions.concat(data.weekly_questions); setIsWeekly(true) }
        setQuestions(allQuestions); setLoading(false)
      })
      .catch(function (err) { setError(err.message); setLoading(false) })
  }

  function handleAnswer(questionId, value) { setAnswers(function (prev) { var next = {}; for (var k in prev) next[k] = prev[k]; next[questionId] = value; return next }) }

  function handleSubmit() {
    setSubmitting(true)
    var payload = { answers: Object.keys(answers).map(function (qid) {
      var val = answers[qid]; if (val === 'Yes') val = 5; if (val === 'No') val = 1; if (typeof val === 'string') val = parseInt(val, 10) || 1
      return { question_id: qid, raw_value: val }
    }) }
    fetch(API_BASE + '/checkin/submit', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) })
      .then(function (res) { if (!res.ok) throw new Error('Failed to submit'); return res.json() })
      .then(function (data) { setResult(data); setSubmitted(true); setSubmitting(false); if (onCheckinComplete) onCheckinComplete(data.metrics || null) })
      .catch(function (err) { setError(err.message); setSubmitting(false) })
  }

  var currentQuestion = questions[currentIndex]
  var allAnswered = questions.length > 0 && questions.every(function (q) { return answers[q.question_id] !== undefined && answers[q.question_id] !== null })
  var isLastQuestion = currentIndex === questions.length - 1
  function isAnswered(q) { var a = answers[q.question_id]; if (a === undefined || a === null) return false; if (typeof a === 'string') return a.trim().length > 0; return true }

  var cardStyle = { background: C.card, border: '1px solid ' + C.border, borderRadius: 12, fontFamily: FONT }

  if (loading) {
    return (<div style={Object.assign({}, cardStyle, { padding: 32 })}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{ width: 16, height: 16, border: '2px solid ' + C.faint, borderTopColor: C.text, borderRadius: '50%', animation: 'checkinSpin 0.8s linear infinite' }} />
        <span style={{ fontSize: 13, color: C.muted }}>Preparing your check-in...</span>
      </div>
      <style>{"@keyframes checkinSpin { to { transform: rotate(360deg); } }"}</style>
    </div>)
  }

  if (error) {
    return (<div style={Object.assign({}, cardStyle, { padding: 32, borderColor: C.error + '40' })}>
      <p style={{ fontSize: 13, color: C.error, margin: '0 0 12px' }}>Something went wrong: {error}</p>
      <button onClick={function () { setError(null); fetchQuestions() }} style={{ fontSize: 13, padding: '8px 16px', borderRadius: 6, border: '1px solid ' + C.error + '40', background: 'transparent', color: C.error, cursor: 'pointer', fontFamily: FONT }}>Try again</button>
    </div>)
  }

  if (submitted) {
    var fcsScore = result && result.metrics && result.metrics.fcs_total != null ? result.metrics.fcs_total : (result && result.fcs_snapshot != null ? result.fcs_snapshot : null)
    return (
      <div style={Object.assign({}, cardStyle, { padding: '40px 32px', textAlign: 'center' })}>
        <div style={{ width: 48, height: 48, border: '2px solid ' + C.text, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M5 10l3.5 3.5L15 7" stroke={C.text} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </div>
        <h3 style={{ fontSize: 20, fontWeight: 600, color: C.text, margin: '0 0 8px', letterSpacing: '-0.02em' }}>Check-in recorded.</h3>
        <p style={{ fontSize: 13, color: C.muted, margin: '0 0 28px' }}>Your Financial Confidence Score has been updated. See you tomorrow.</p>
        {result && (
          <div style={{ display: 'flex', justifyContent: 'center', gap: 40, marginBottom: 24 }}>
            <div>
              <div style={{ fontSize: 36, fontWeight: 300, color: C.text, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>{fcsScore != null ? fcsScore.toFixed(1) : '—'}</div>
              <div style={{ fontSize: 11, color: C.dim, marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Your FCS</div>
            </div>
            <div>
              <div style={{ fontSize: 36, fontWeight: 300, color: C.text, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums' }}>{result.responses_saved || 0}</div>
              <div style={{ fontSize: 11, color: C.dim, marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Responses</div>
            </div>
          </div>
        )}
        {fcsScore != null && (
          <div style={{ borderTop: '1px solid ' + C.border, paddingTop: 20, marginTop: 8 }}>
            <div style={{ width: '100%', height: 3, borderRadius: 2, background: C.border, marginBottom: 12 }}>
              <div style={{ height: '100%', borderRadius: 2, width: Math.min(fcsScore, 100) + '%', background: C.text, transition: 'width 1s ease' }} />
            </div>
            <p style={{ fontSize: 13, color: C.muted, margin: 0 }}>
              {fcsScore >= 70 ? "Strong confidence. You're in a great position — keep going." : fcsScore >= 40 ? "Building momentum. Every check-in sharpens the picture." : "Awareness is the foundation. You're doing the right thing by showing up."}
            </p>
          </div>
        )}
        {isWeekly && (<p style={{ fontSize: 11, color: C.dim, marginTop: 16 }}>Weekly behavioral data included — your profile is getting sharper.</p>)}
      </div>
    )
  }

  if (questions.length === 0) {
    return (
      <div style={Object.assign({}, cardStyle, { padding: '40px 32px', textAlign: 'center' })}>
        <div style={{ width: 48, height: 48, border: '2px solid ' + C.text, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px' }}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M5 10l3.5 3.5L15 7" stroke={C.text} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
        </div>
        <h3 style={{ fontSize: 18, fontWeight: 600, color: C.text, margin: '0 0 6px', letterSpacing: '-0.02em' }}>You're all set for today.</h3>
        <p style={{ fontSize: 13, color: C.muted, margin: 0 }}>Your check-in is in the books. Come back tomorrow to keep building your profile.</p>
      </div>
    )
  }

  var qType = getQuestionType(currentQuestion); var answered = isAnswered(currentQuestion)
  var labels = getScaleLabels(currentQuestion); var progress = ((currentIndex + (answered ? 1 : 0)) / questions.length * 100)

  return (
    <div style={Object.assign({}, cardStyle, { overflow: 'hidden' })}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist');"}</style>
      <div style={{ padding: '28px 28px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 11, fontWeight: 500, color: C.muted, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            {currentQuestion.is_weekly ? 'Weekly Behavioral Profile' : 'Daily Check-In'}
          </span>
          <span style={{ fontSize: 12, color: C.dim, fontVariantNumeric: 'tabular-nums' }}>{currentIndex + 1} / {questions.length}</span>
        </div>
        <div style={{ width: '100%', height: 2, borderRadius: 1, background: C.border, marginTop: 12 }}>
          <div style={{ height: '100%', borderRadius: 1, width: progress + '%', background: C.text, transition: 'width 0.4s ease' }} />
        </div>
      </div>
      <div style={{ padding: '12px 28px 28px' }}>
        <span style={{ display: 'inline-block', fontSize: 11, fontWeight: 500, color: C.dim, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 12, padding: '4px 10px', borderRadius: 4, border: '1px solid ' + C.border }}>
          {formatDimension(currentQuestion.dimension)}
        </span>
        <h2 style={{ fontSize: 20, fontWeight: 500, color: C.text, lineHeight: 1.5, margin: '0 0 28px', letterSpacing: '-0.01em' }}>{currentQuestion.question_text}</h2>

        {qType === 'scale_5' && (<div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 11, color: C.dim }}>{labels.low}</span><span style={{ fontSize: 11, color: C.dim }}>{labels.high}</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            {[1, 2, 3, 4, 5].map(function (num) {
              var isSelected = answers[currentQuestion.question_id] === num
              return (<button key={num} onClick={function () { handleAnswer(currentQuestion.question_id, num) }} style={{
                flex: 1, padding: '16px 0', borderRadius: 8, fontSize: 16, fontWeight: isSelected ? 600 : 400, fontFamily: FONT, cursor: 'pointer', transition: 'all 0.15s ease',
                background: isSelected ? C.text : 'transparent', color: isSelected ? C.bg : C.muted, border: '1px solid ' + (isSelected ? C.text : C.faint), fontVariantNumeric: 'tabular-nums',
              }}
                onMouseEnter={function (e) { if (!isSelected) { e.target.style.borderColor = C.muted; e.target.style.color = C.text } }}
                onMouseLeave={function (e) { if (!isSelected) { e.target.style.borderColor = C.faint; e.target.style.color = C.muted } }}
              >{num}</button>)
            })}
          </div>
        </div>)}

        {qType === 'slider' && (<div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
            <span style={{ fontSize: 11, color: C.dim }}>{labels.low}</span><span style={{ fontSize: 11, color: C.dim }}>{labels.high}</span>
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(function (num) {
              var isSelected = answers[currentQuestion.question_id] === num
              return (<button key={num} onClick={function () { handleAnswer(currentQuestion.question_id, num) }} style={{
                flex: 1, padding: '12px 0', borderRadius: 6, fontSize: 13, fontWeight: isSelected ? 600 : 400, fontFamily: FONT, cursor: 'pointer', transition: 'all 0.15s ease',
                background: isSelected ? C.text : 'transparent', color: isSelected ? C.bg : C.muted, border: '1px solid ' + (isSelected ? C.text : C.faint), fontVariantNumeric: 'tabular-nums',
              }}
                onMouseEnter={function (e) { if (!isSelected) { e.target.style.borderColor = C.muted; e.target.style.color = C.text } }}
                onMouseLeave={function (e) { if (!isSelected) { e.target.style.borderColor = C.faint; e.target.style.color = C.muted } }}
              >{num}</button>)
            })}
          </div>
        </div>)}

        {qType === 'yes_no' && (<div style={{ display: 'flex', gap: 12 }}>
          {[{ label: 'Yes', value: 'Yes' }, { label: 'No', value: 'No' }].map(function (opt) {
            var isSelected = answers[currentQuestion.question_id] === opt.value
            return (<button key={opt.value} onClick={function () { handleAnswer(currentQuestion.question_id, opt.value) }} style={{
              flex: 1, padding: '20px 0', borderRadius: 8, fontSize: 15, fontWeight: isSelected ? 600 : 400, fontFamily: FONT, cursor: 'pointer', transition: 'all 0.15s ease',
              background: isSelected ? C.text : 'transparent', color: isSelected ? C.bg : C.muted, border: '1px solid ' + (isSelected ? C.text : C.faint),
            }}
              onMouseEnter={function (e) { if (!isSelected) { e.target.style.borderColor = C.muted; e.target.style.color = C.text } }}
              onMouseLeave={function (e) { if (!isSelected) { e.target.style.borderColor = C.faint; e.target.style.color = C.muted } }}
            >{opt.label}</button>)
          })}
        </div>)}
      </div>

      <div style={{ padding: '0 28px 28px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <button onClick={function () { setCurrentIndex(function (p) { return p - 1 }) }} style={{
          fontSize: 13, padding: '8px 16px', borderRadius: 6, border: '1px solid ' + C.border, background: 'transparent',
          color: C.muted, cursor: 'pointer', fontFamily: FONT, visibility: currentIndex > 0 ? 'visible' : 'hidden', transition: 'all 0.15s ease',
        }}
          onMouseEnter={function (e) { e.target.style.borderColor = C.muted; e.target.style.color = C.text }}
          onMouseLeave={function (e) { e.target.style.borderColor = C.border; e.target.style.color = C.muted }}
        >Back</button>

        {isLastQuestion && allAnswered ? (
          <button onClick={handleSubmit} disabled={submitting} style={{
            fontSize: 14, fontWeight: 600, padding: '12px 28px', borderRadius: 8, border: 'none', fontFamily: FONT,
            background: C.text, color: C.bg, cursor: submitting ? 'wait' : 'pointer', opacity: submitting ? 0.5 : 1, transition: 'opacity 0.2s ease',
          }}
            onMouseEnter={function (e) { if (!submitting) e.target.style.opacity = '0.85' }}
            onMouseLeave={function (e) { if (!submitting) e.target.style.opacity = '1' }}
          >{submitting ? 'Saving...' : 'Complete Check-In'}</button>
        ) : (
          <button onClick={function () { setCurrentIndex(function (p) { return p + 1 }) }} disabled={!answered} style={{
            fontSize: 13, fontWeight: 500, padding: '10px 24px', borderRadius: 6, border: '1px solid ' + (answered ? C.text : C.border),
            background: 'transparent', fontFamily: FONT, color: answered ? C.text : C.dim, cursor: answered ? 'pointer' : 'default', transition: 'all 0.15s ease',
          }}>Next</button>
        )}
      </div>
    </div>
  )
}