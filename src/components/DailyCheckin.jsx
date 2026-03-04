import { useState, useEffect } from 'react'
import { useTheme } from '../context/ThemeContext'

var API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000')

/* ═══════════════════════════════════════════════════════════════════════════
   HELPER: Authenticated fetch
   ═══════════════════════════════════════════════════════════════════════════ */

function apiFetch(endpoint, options) {
  var token = localStorage.getItem('grace_token')
  var headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = 'Bearer ' + token

  var config = { headers: headers }
  if (options) {
    for (var k in options) {
      if (k === 'headers') {
        for (var h in options.headers) headers[h] = options.headers[h]
      } else {
        config[k] = options[k]
      }
    }
  }
  config.headers = headers

  return fetch(API_BASE + endpoint, config).then(function (res) {
    if (!res.ok) {
      return res.json().catch(function () { return { detail: 'Request failed' } }).then(function (err) {
        throw new Error(err.detail || 'Request failed (' + res.status + ')')
      })
    }
    return res.json()
  })
}

/* ═══════════════════════════════════════════════════════════════════════════
   DIMENSION CONFIG — colors, icons, labels (UPDATED v2)
   ═══════════════════════════════════════════════════════════════════════════ */

var dimensionConfig = {
  current_stability: {
    label: 'Current Stability',
    color: '#58A6FF',
    icon: '\uD83D\uDEE1\uFE0F',
    description: 'How secure you feel financially right now',
  },
  future_outlook: {
    label: 'Future Outlook',
    color: '#BC8CFF',
    icon: '\uD83D\uDD2E',
    description: 'Your confidence about what\'s ahead',
  },
  purchasing_power: {
    label: 'Purchasing Power',
    color: '#D29922',
    icon: '\uD83D\uDCB0',
    description: 'How far your money goes',
  },
  debt_pressure: {
    label: 'Debt Pressure',
    color: '#F85149',
    icon: '\u26A0\uFE0F',
    description: 'How much debt weighs on your decisions',
  },
  financial_agency: {
    label: 'Financial Agency',
    color: '#3FB950',
    icon: '\uD83D\uDCAA',
    description: 'Whether you feel empowered or stuck',
  },
  category_downgrading: {
    label: 'Spending Shifts',
    color: '#FB923C',
    icon: '\uD83D\uDD04',
    description: 'Changes in what you buy',
  },
  credit_substitution: {
    label: 'Credit Usage',
    color: '#F87171',
    icon: '\uD83D\uDCB3',
    description: 'Shifts toward credit',
  },
  subscription_churn: {
    label: 'Subscription Changes',
    color: '#22D3EE',
    icon: '\u2702\uFE0F',
    description: 'Cutting or keeping services',
  },
  delayed_purchasing: {
    label: 'Purchase Timing',
    color: '#818CF8',
    icon: '\u23F3',
    description: 'Delaying purchases',
  },
  cash_hoarding: {
    label: 'Cash Behavior',
    color: '#FBBF24',
    icon: '\uD83E\uDE99',
    description: 'Holding onto cash',
  },
}

/* ═══════════════════════════════════════════════════════════════════════════
   SCALE LABELS — now just fallbacks, API labels take priority
   ═══════════════════════════════════════════════════════════════════════════ */

function getScaleLabels(question) {
  var low = question.low_label || 'Low'
  var high = question.high_label || 'High'
  return { low: low, high: high }
}

function authHeaders() {
  return {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + localStorage.getItem('grace_token'),
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════════════════ */

export default function DailyCheckin(props) {
  var onCheckinComplete = props.onCheckinComplete || null

  var ctx = useTheme()
  var theme = ctx.theme

  var questionsState = useState([])
  var questions = questionsState[0]
  var setQuestions = questionsState[1]

  var answersState = useState({})
  var answers = answersState[0]
  var setAnswers = answersState[1]

  var loadingState = useState(true)
  var loading = loadingState[0]
  var setLoading = loadingState[1]

  var errorState = useState(null)
  var error = errorState[0]
  var setError = errorState[1]

  var submittedState = useState(false)
  var submitted = submittedState[0]
  var setSubmitted = submittedState[1]

  var submittingState = useState(false)
  var submitting = submittingState[0]
  var setSubmitting = submittingState[1]

  var indexState = useState(0)
  var currentIndex = indexState[0]
  var setCurrentIndex = indexState[1]

  var resultState = useState(null)
  var result = resultState[0]
  var setResult = resultState[1]

  var isWeeklyState = useState(false)
  var isWeekly = isWeeklyState[0]
  var setIsWeekly = isWeeklyState[1]

  useEffect(function () {
    fetchQuestions()
  }, [])

  function fetchQuestions() {
    setLoading(true)
    setError(null)
    fetch(API_BASE + '/checkin/questions', {
      headers: authHeaders(),
    })
      .then(function (res) {
        if (res.status === 401) throw new Error('Please log in to check in')
        if (!res.ok) throw new Error('Failed to load questions')
        return res.json()
      })
      .then(function (data) {
        var allQuestions = (data.daily_questions || [])
        if (data.is_weekly_day && data.weekly_questions) {
          allQuestions = allQuestions.concat(data.weekly_questions)
          setIsWeekly(true)
        }
        setQuestions(allQuestions)
        setLoading(false)
      })
      .catch(function (err) {
        setError(err.message)
        setLoading(false)
      })
  }

  function handleAnswer(questionId, value) {
    setAnswers(function (prev) {
      var next = {}
      for (var k in prev) next[k] = prev[k]
      next[questionId] = value
      return next
    })
  }

  function handleSubmit() {
    setSubmitting(true)

    var payload = {
      answers: Object.keys(answers).map(function (qid) {
        var val = answers[qid]
        if (val === 'Yes') val = 5
        if (val === 'No') val = 1
        if (typeof val === 'string') val = parseInt(val, 10) || 1
        return { question_id: qid, raw_value: val }
      }),
    }

    fetch(API_BASE + '/checkin/submit', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        if (!res.ok) throw new Error('Failed to submit')
        return res.json()
      })
      .then(function (data) {
        setResult(data)
        setSubmitted(true)
        setSubmitting(false)

        if (onCheckinComplete) {
          onCheckinComplete(data.metrics || null)
        }
      })
      .catch(function (err) {
        setError(err.message)
        setSubmitting(false)
      })
  }

  var currentQuestion = questions[currentIndex]

  var allAnswered = questions.length > 0 && questions.every(function (q) {
    return answers[q.question_id] !== undefined && answers[q.question_id] !== null
  })

  var isLastQuestion = currentIndex === questions.length - 1

  function isAnswered(q) {
    var a = answers[q.question_id]
    if (a === undefined || a === null) return false
    if (typeof a === 'string') return a.trim().length > 0
    return true
  }

  function formatDimension(dim) {
    if (!dim) return ''
    return dim.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase() })
  }

  function getDimensionColor(dim) {
    var cfg = dimensionConfig[dim]
    return cfg ? cfg.color : theme.accent
  }

  function getQuestionType(q) {
    if (!q) return 'scale'
    if (q.scale_type === 'yes_no_scale') return 'yes_no'
    if (q.scale_type === '1-10') return 'slider'
    return 'scale_5'
  }

  if (loading) {
    return (
      <div className="rounded-2xl p-8 border" style={{ background: theme.card, borderColor: theme.border }}>
        <div className="flex items-center gap-3">
          <div
            className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"
            style={{ borderColor: theme.accent, borderTopColor: 'transparent' }}
          />
          <span className="text-sm" style={{ color: theme.muted }}>Loading today's check-in...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl p-8 border" style={{ background: theme.card, borderColor: theme.error + '50' }}>
        <p className="text-sm mb-3" style={{ color: theme.error }}>
          Couldn't load check-in: {error}
        </p>
        <button
          onClick={function () { setError(null); fetchQuestions() }}
          className="text-sm px-4 py-2 rounded-lg transition-colors cursor-pointer border-none"
          style={{ background: theme.error + '20', color: theme.error }}
        >
          Try again
        </button>
      </div>
    )
  }

  if (submitted) {
    var fcsScore = result && result.metrics && result.metrics.fcs_total != null
      ? result.metrics.fcs_total
      : (result && result.fcs_snapshot != null ? result.fcs_snapshot : null)

    return (
      <div className="rounded-2xl p-8 border" style={{ background: theme.card, borderColor: theme.border }}>
        <div className="text-center">
          <div className="text-4xl mb-4">{'\uD83D\uDC3E'}</div>
          <h3 className="text-xl font-bold mb-2" style={{ color: theme.text }}>Check-in complete!</h3>
          <p className="text-sm mb-6" style={{ color: theme.muted }}>
            Your responses have been saved. Come back tomorrow for new questions.
          </p>

          {result && (
            <div className="flex justify-center gap-8 mb-6">
              <div className="text-center">
                <div className="text-3xl font-bold" style={{ color: theme.accent }}>
                  {fcsScore != null ? fcsScore.toFixed(1) : '—'}
                </div>
                <div className="text-xs mt-1" style={{ color: theme.muted }}>FCS Score</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold" style={{ color: '#60a5fa' }}>
                  {result.responses_saved || 0}
                </div>
                <div className="text-xs mt-1" style={{ color: theme.muted }}>Answers Saved</div>
              </div>
            </div>
          )}

          {fcsScore != null && (
            <div className="mt-4 rounded-xl p-4" style={{
              background: theme.accent + '10',
              border: '1px solid ' + theme.accent + '30',
            }}>
              <div className="w-full h-3 rounded-full mb-3" style={{ background: theme.border + '30' }}>
                <div
                  className="h-full rounded-full transition-all duration-1000"
                  style={{
                    width: Math.min(fcsScore, 100) + '%',
                    background: fcsScore >= 70
                      ? 'linear-gradient(90deg, #34d399, #00C9A7)'
                      : fcsScore >= 40
                        ? 'linear-gradient(90deg, #fbbf24, #fb923c)'
                        : 'linear-gradient(90deg, #f87171, #ef4444)',
                  }}
                />
              </div>
              <p className="text-sm" style={{ color: theme.accent }}>
                {fcsScore >= 70
                  ? "Strong financial confidence — you're in a good place."
                  : fcsScore >= 40
                    ? "Moderate confidence — building momentum. Keep checking in."
                    : "Your score reflects some pressure right now. That's okay — awareness is the first step."}
              </p>
            </div>
          )}

          {isWeekly && (
            <p className="text-xs mt-4" style={{ color: theme.muted }}>
              Weekly behavioral questions included — your BSI score will update shortly.
            </p>
          )}
        </div>
      </div>
    )
  }

  if (questions.length === 0) {
    return (
      <div className="rounded-2xl p-8 border" style={{ background: theme.card, borderColor: theme.border }}>
        <div className="text-center">
          <div className="text-3xl mb-3">{'\u2705'}</div>
          <h3 className="text-lg font-bold mb-1" style={{ color: theme.text }}>All caught up!</h3>
          <p className="text-sm" style={{ color: theme.muted }}>
            You've already completed today's check-in. Come back tomorrow!
          </p>
        </div>
      </div>
    )
  }

  var qType = getQuestionType(currentQuestion)
  var dimColor = getDimensionColor(currentQuestion.dimension)
  var answered = isAnswered(currentQuestion)
  var labels = getScaleLabels(currentQuestion)

  return (
    <div className="rounded-2xl border overflow-hidden" style={{ background: theme.card, borderColor: theme.border }}>

      <div className="px-8 pt-8 pb-4">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="text-lg">{'\uD83D\uDC3E'}</span>
            <h3 className="text-sm font-semibold tracking-wider uppercase" style={{ color: theme.muted }}>
              {currentQuestion.is_weekly ? 'Weekly Behavioral Check-In' : 'Daily Check-In'}
            </h3>
          </div>
          <span className="text-xs font-medium px-3 py-1 rounded-full" style={{
            background: theme.border + '40', color: theme.muted,
          }}>
            {currentIndex + 1} of {questions.length}
          </span>
        </div>
        <div className="mt-4 h-1 rounded-full" style={{ background: theme.border + '40' }}>
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: ((currentIndex + (answered ? 1 : 0)) / questions.length * 100) + '%',
              background: 'linear-gradient(90deg, ' + theme.accent + ', #34d399)',
            }}
          />
        </div>
      </div>

      <div className="px-8 py-6">
        <span
          className="inline-block text-xs font-semibold px-3 py-1 rounded-full mb-4"
          style={{ background: dimColor + '15', color: dimColor }}
        >
          {formatDimension(currentQuestion.dimension)}
        </span>

        <h2 className="text-xl font-bold mb-6 leading-relaxed" style={{ color: theme.text }}>
          {currentQuestion.question_text}
        </h2>

        {qType === 'scale_5' && (
          <div>
            <div className="flex justify-between mb-3">
              <span className="text-xs" style={{ color: theme.muted + '90' }}>{labels.low}</span>
              <span className="text-xs" style={{ color: theme.muted + '90' }}>{labels.high}</span>
            </div>
            <div className="flex gap-3">
              {[1, 2, 3, 4, 5].map(function (num) {
                var isSelected = answers[currentQuestion.question_id] === num
                var pct = (num - 1) / 4
                var color = isSelected ? (pct < 0.33 ? '#f87171' : pct < 0.66 ? '#fbbf24' : '#34d399') : null
                return (
                  <button
                    key={num}
                    onClick={function () { handleAnswer(currentQuestion.question_id, num) }}
                    className="flex-1 py-4 rounded-xl text-base font-semibold transition-all duration-200 cursor-pointer border"
                    style={{
                      background: isSelected ? (color || theme.accent) + '25' : theme.border + '10',
                      borderColor: isSelected ? (color || theme.accent) + '60' : theme.border + '30',
                      color: isSelected ? (color || theme.accent) : theme.muted,
                      transform: isSelected ? 'scale(1.05)' : 'scale(1)',
                    }}
                  >
                    {num}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {qType === 'slider' && (
          <div>
            <div className="flex justify-between mb-3">
              <span className="text-xs" style={{ color: theme.muted + '90' }}>{labels.low}</span>
              <span className="text-xs" style={{ color: theme.muted + '90' }}>{labels.high}</span>
            </div>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(function (num) {
                var isSelected = answers[currentQuestion.question_id] === num
                var pct = (num - 1) / 9
                var color = isSelected ? (pct < 0.33 ? '#f87171' : pct < 0.66 ? '#fbbf24' : '#34d399') : null
                return (
                  <button
                    key={num}
                    onClick={function () { handleAnswer(currentQuestion.question_id, num) }}
                    className="flex-1 py-3 rounded-lg text-sm font-semibold transition-all duration-200 cursor-pointer border"
                    style={{
                      background: isSelected ? (color || theme.accent) + '25' : theme.border + '10',
                      borderColor: isSelected ? (color || theme.accent) + '60' : theme.border + '30',
                      color: isSelected ? (color || theme.accent) : theme.muted,
                      transform: isSelected ? 'scale(1.08)' : 'scale(1)',
                    }}
                  >
                    {num}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {qType === 'yes_no' && (
          <div className="flex gap-4">
            {[
              { label: 'Yes', value: 'Yes', icon: '\uD83D\uDC4D' },
              { label: 'No', value: 'No', icon: '\uD83D\uDC4E' },
            ].map(function (opt) {
              var isSelected = answers[currentQuestion.question_id] === opt.value
              return (
                <button
                  key={opt.value}
                  onClick={function () { handleAnswer(currentQuestion.question_id, opt.value) }}
                  className="flex-1 py-5 rounded-xl text-base font-semibold transition-all duration-200 cursor-pointer border flex flex-col items-center gap-2"
                  style={{
                    background: isSelected ? theme.accent + '18' : theme.border + '10',
                    borderColor: isSelected ? theme.accent + '60' : theme.border + '30',
                    color: isSelected ? theme.accent : theme.text + 'B0',
                    transform: isSelected ? 'scale(1.03)' : 'scale(1)',
                  }}
                >
                  <span className="text-2xl">{opt.icon}</span>
                  <span>{opt.label}</span>
                </button>
              )
            })}
          </div>
        )}
      </div>

      <div className="px-8 pb-8 flex items-center justify-between">
        <button
          onClick={function () { setCurrentIndex(function (p) { return p - 1 }) }}
          className="text-sm px-4 py-2 rounded-lg transition-colors cursor-pointer border-none"
          style={{
            background: theme.border + '20',
            color: theme.muted,
            visibility: currentIndex > 0 ? 'visible' : 'hidden',
          }}
        >
          {'\u2190 Back'}
        </button>

        {isLastQuestion && allAnswered ? (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="text-sm font-semibold px-6 py-3 rounded-xl transition-all duration-200 cursor-pointer border-none"
            style={{
              background: 'linear-gradient(135deg, ' + theme.accent + ', #34d399)',
              color: theme.isDark ? '#0a0f1a' : '#ffffff',
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? 'Saving...' : 'Complete Check-In \u2713'}
          </button>
        ) : (
          <button
            onClick={function () { setCurrentIndex(function (p) { return p + 1 }) }}
            disabled={!answered}
            className="text-sm font-semibold px-6 py-3 rounded-xl transition-all duration-200 cursor-pointer border-none"
            style={{
              background: answered ? theme.accent + '20' : theme.border + '15',
              color: answered ? theme.accent : theme.muted + '60',
              cursor: answered ? 'pointer' : 'default',
            }}
          >
            {'Next \u2192'}
          </button>
        )}
      </div>
    </div>
  )
}