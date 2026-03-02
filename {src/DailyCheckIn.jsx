import { useState, useEffect } from 'react'

const API_BASE = 'http://127.0.0.1:8000'

export default function DailyCheckin() {
  const [questions, setQuestions] = useState([])
  const [answers, setAnswers] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [insights, setInsights] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(function () {
    fetchQuestions()
  }, [])

  async function fetchQuestions() {
    try {
      setLoading(true)
      const res = await fetch(API_BASE + '/api/checkin/daily-questions')
      if (!res.ok) throw new Error('Failed to load questions')
      const data = await res.json()
      setQuestions(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleAnswer(questionId, value) {
    setAnswers(function (prev) {
      var next = {}
      for (var k in prev) next[k] = prev[k]
      next[questionId] = value
      return next
    })
  }

  async function handleSubmit() {
    setSubmitting(true)
    try {
      var payload = []
      var keys = Object.keys(answers)
      for (var i = 0; i < keys.length; i++) {
        payload.push({
          question_id: keys[i],
          answer: answers[keys[i]],
          timestamp: new Date().toISOString(),
        })
      }
      const res = await fetch(API_BASE + '/api/checkin/submit-answers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error('Failed to submit')
      const data = await res.json()
      setInsights(data.insights || [])
      setSubmitted(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  var currentQuestion = questions[currentIndex]
  var allAnswered = questions.length > 0 && questions.every(function (q) { return answers[q.id] !== undefined })
  var isLastQuestion = currentIndex === questions.length - 1

  function formatCategory(cat) {
    return cat.replace(/_/g, ' ').replace(/\b\w/g, function (c) { return c.toUpperCase() })
  }

  function getCategoryColor(cat) {
    var colors = {
      money_stress: '#f87171',
      spending_habits: '#fb923c',
      money_goals: '#34d399',
      financial_confidence: '#60a5fa',
      life_context: '#a78bfa',
      money_mindset: '#fbbf24',
    }
    return colors[cat] || '#22D3A7'
  }

  if (loading) {
    return (
      <div className="rounded-2xl p-8 border border-grace-border" style={{ background: '#111827' }}>
        <div className="flex items-center gap-3">
          <div
            className="w-5 h-5 border-2 border-t-transparent rounded-full animate-spin"
            style={{ borderColor: '#22D3A7', borderTopColor: 'transparent' }}
          />
          <span className="text-grace-muted text-sm">Loading today's check-in...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl p-8 border border-red-500/30" style={{ background: '#111827' }}>
        <p className="text-red-400 text-sm mb-3">Could not load check-in: {error}</p>
        <button
          onClick={function () { setError(null); fetchQuestions() }}
          className="text-sm px-4 py-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors cursor-pointer border-none"
        >
          Try again
        </button>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="rounded-2xl p-8 border border-grace-border" style={{ background: 'linear-gradient(165deg, #111827 0%, #0f1a2e 100%)' }}>
        <div className="text-center">
          <div className="text-4xl mb-4">🐾</div>
          <h3 className="text-xl font-bold text-white mb-2">Check-in complete!</h3>
          <p className="text-grace-muted text-sm mb-4">
            Your responses have been saved. Come back tomorrow for new questions.
          </p>
          {insights.length > 0 && (
            <div className="mt-6 space-y-3">
              {insights.map(function (insight, i) {
                return (
                  <div key={i} className="rounded-xl p-4 text-left" style={{ background: 'rgba(34, 211, 167, 0.1)', border: '1px solid rgba(34, 211, 167, 0.2)' }}>
                    <p className="text-sm" style={{ color: '#22D3A7' }}>{insight.message}</p>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    )
  }

  if (questions.length === 0) {
    return (
      <div className="rounded-2xl p-8 border border-grace-border" style={{ background: '#111827' }}>
        <p className="text-grace-muted text-sm">No check-in questions available today.</p>
      </div>
    )
  }

  var progressWidth = ((currentIndex + (answers[currentQuestion.id] !== undefined ? 1 : 0)) / questions.length) * 100
  var catColor = getCategoryColor(currentQuestion.category)
  var hasCurrentAnswer = answers[currentQuestion.id] !== undefined

  return (
    <div className="rounded-2xl border border-grace-border overflow-hidden" style={{ background: 'linear-gradient(165deg, #111827 0%, #0f1a2e 100%)' }}>
      <div className="px-8 pt-8 pb-4">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="text-lg">🐾</span>
            <h3 className="text-sm font-semibold tracking-wider uppercase" style={{ color: 'rgba(255,255,255,0.4)' }}>
              Daily Check-In
            </h3>
          </div>
          <span className="text-xs font-medium px-3 py-1 rounded-full" style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)' }}>
            {currentIndex + 1} of {questions.length}
          </span>
        </div>
        <div className="mt-4 h-1 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{ width: progressWidth + '%', background: 'linear-gradient(90deg, #22D3A7, #34d399)' }}
          />
        </div>
      </div>

      <div className="px-8 py-6">
        <span
          className="inline-block text-xs font-semibold px-3 py-1 rounded-full mb-4"
          style={{ background: catColor + '15', color: catColor }}
        >
          {formatCategory(currentQuestion.category)}
        </span>

        <h2 className="text-xl font-bold text-white mb-8 leading-relaxed">
          {currentQuestion.question}
        </h2>

        {currentQuestion.type === 'multiple_choice' && currentQuestion.options && (
          <OptionsList
            options={currentQuestion.options}
            selected={answers[currentQuestion.id]}
            onSelect={function (val) { handleAnswer(currentQuestion.id, val) }}
          />
        )}

        {currentQuestion.type === 'yes_no' && (
          <OptionsList
            options={['Yes', 'No']}
            selected={answers[currentQuestion.id]}
            onSelect={function (val) { handleAnswer(currentQuestion.id, val) }}
          />
        )}

        {currentQuestion.type === 'scale' && currentQuestion.scale_labels && (
          <div>
            <div className="flex justify-between mb-3">
              {Object.entries(currentQuestion.scale_labels).map(function (entry) {
                return (
                  <span key={entry[0]} className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
                    {entry[1]}
                  </span>
                )
              })}
            </div>
            <div className="flex gap-2">
              {[1,2,3,4,5,6,7,8,9,10].map(function (num) {
                var isSelected = answers[currentQuestion.id] === num
                return (
                  <button
                    key={num}
                    onClick={function () { handleAnswer(currentQuestion.id, num) }}
                    className="flex-1 py-3 rounded-lg text-sm font-semibold transition-all duration-200 cursor-pointer border"
                    style={{
                      background: isSelected ? 'rgba(34, 211, 167, 0.2)' : 'rgba(255,255,255,0.03)',
                      borderColor: isSelected ? 'rgba(34, 211, 167, 0.4)' : 'rgba(255,255,255,0.08)',
                      color: isSelected ? '#22D3A7' : 'rgba(255,255,255,0.5)',
                    }}
                  >
                    {num}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {currentQuestion.type === 'open_text' && (
          <textarea
            value={answers[currentQuestion.id] || ''}
            onChange={function (e) { handleAnswer(currentQuestion.id, e.target.value) }}
            placeholder="Share your thoughts..."
            className="w-full p-4 rounded-xl text-sm text-white placeholder-gray-500 resize-none focus:outline-none transition-colors"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              minHeight: 120,
            }}
            maxLength={currentQuestion.max_characters || 500}
          />
        )}
      </div>

      <div className="px-8 pb-8 flex items-center justify-between">
        {currentIndex > 0 ? (
          <button
            onClick={function () { setCurrentIndex(currentIndex - 1) }}
            className="text-sm px-4 py-2 rounded-lg transition-colors cursor-pointer border-none"
            style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.5)' }}
          >
            Back
          </button>
        ) : (
          <div />
        )}

        {isLastQuestion && allAnswered ? (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="text-sm font-semibold px-6 py-3 rounded-xl transition-all duration-200 cursor-pointer border-none"
            style={{
              background: 'linear-gradient(135deg, #22D3A7, #34d399)',
              color: '#0a0f1a',
              opacity: submitting ? 0.6 : 1,
            }}
          >
            {submitting ? 'Saving...' : 'Complete Check-In'}
          </button>
        ) : (
          <button
            onClick={function () { setCurrentIndex(currentIndex + 1) }}
            disabled={!hasCurrentAnswer}
            className="text-sm font-semibold px-6 py-3 rounded-xl transition-all duration-200 cursor-pointer border-none"
            style={{
              background: hasCurrentAnswer ? 'rgba(34, 211, 167, 0.15)' : 'rgba(255,255,255,0.05)',
              color: hasCurrentAnswer ? '#22D3A7' : 'rgba(255,255,255,0.3)',
              cursor: hasCurrentAnswer ? 'pointer' : 'default',
            }}
          >
            Next
          </button>
        )}
      </div>
    </div>
  )
}

function OptionsList(props) {
  var options = props.options
  var selected = props.selected
  var onSelect = props.onSelect

  return (
    <div className="space-y-3">
      {options.map(function (option) {
        var isSelected = selected === option
        return (
          <button
            key={option}
            onClick={function () { onSelect(option) }}
            className="w-full text-left px-5 py-4 rounded-xl text-sm font-medium transition-all duration-200 cursor-pointer border"
            style={{
              background: isSelected ? 'rgba(34, 211, 167, 0.12)' : 'rgba(255,255,255,0.03)',
              borderColor: isSelected ? 'rgba(34, 211, 167, 0.4)' : 'rgba(255,255,255,0.08)',
              color: isSelected ? '#22D3A7' : 'rgba(255,255,255,0.7)',
            }}
          >
            <span className="flex items-center gap-3">
              <span
                className="w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0"
                style={{ borderColor: isSelected ? '#22D3A7' : 'rgba(255,255,255,0.2)' }}
              >
                {isSelected && (
                  <span className="w-2.5 h-2.5 rounded-full" style={{ background: '#22D3A7' }} />
                )}
              </span>
              {option}
            </span>
          </button>
        )
      })}
    </div>
  )
}