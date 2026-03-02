import { useState, useEffect } from 'react';
import { checkinApi } from '../api/checkin';

// ── Scale input component ──────────────────────────────────
function ScaleInput({ question, value, onChange }) {
  const max = question.scale_max;
  const labels = getScaleLabels(question);

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-center gap-2">
        {Array.from({ length: max }, (_, i) => i + 1).map((num) => (
          <button
            key={num}
            onClick={() => onChange(num)}
            className={`
              relative flex-1 h-12 rounded-xl font-semibold text-sm transition-all duration-200
              ${value === num
                ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-500/30 scale-105'
                : 'bg-zinc-800/60 text-zinc-400 hover:bg-zinc-700/80 hover:text-zinc-200'
              }
            `}
          >
            {num}
          </button>
        ))}
      </div>
      {labels && (
        <div className="flex justify-between text-xs text-zinc-500 px-1">
          <span>{labels.low}</span>
          <span>{labels.high}</span>
        </div>
      )}
    </div>
  );
}

// ── Get human-readable scale labels ──────────────────────────
function getScaleLabels(question) {
  if (question.scale_type === '1-5') return { low: 'Not at all', high: 'Very much' };
  if (question.scale_type === '1-10') return { low: 'Not at all', high: 'Extremely' };
  if (question.scale_type === 'yes_no_scale') return { low: 'Definitely yes', high: 'Definitely no' };
  return null;
}

// ── Dimension badge ──────────────────────────────────────────
function DimensionBadge({ dimension }) {
  const colors = {
    current_stability: 'bg-blue-500/20 text-blue-400',
    future_outlook: 'bg-purple-500/20 text-purple-400',
    purchasing_power: 'bg-amber-500/20 text-amber-400',
    emergency_readiness: 'bg-red-500/20 text-red-400',
    income_adequacy: 'bg-emerald-500/20 text-emerald-400',
    category_downgrading: 'bg-orange-500/20 text-orange-400',
    credit_substitution: 'bg-rose-500/20 text-rose-400',
    subscription_churn: 'bg-cyan-500/20 text-cyan-400',
    delayed_purchasing: 'bg-indigo-500/20 text-indigo-400',
    cash_hoarding: 'bg-yellow-500/20 text-yellow-400',
  };
  const label = dimension.replace(/_/g, ' ');
  return (
    <span className={`inline-block px-2.5 py-1 rounded-full text-xs font-medium capitalize ${colors[dimension] || 'bg-zinc-700 text-zinc-400'}`}>
      {label}
    </span>
  );
}

// ── Progress bar ─────────────────────────────────────────────
function ProgressBar({ current, total }) {
  const pct = total > 0 ? (current / total) * 100 : 0;
  return (
    <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
      <div
        className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-500 ease-out"
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ── Score reveal after submission ────────────────────────────
function ScoreReveal({ score }) {
  // Guard: score may be null if compute hasn't run yet
  const hasScore = score != null;

  const getScoreColor = (s) => {
    if (s >= 70) return 'text-emerald-400';
    if (s >= 50) return 'text-amber-400';
    return 'text-red-400';
  };

  const getScoreMessage = (s) => {
    if (s >= 80) return "You're in a strong position financially.";
    if (s >= 60) return "You're doing solid — keep building momentum.";
    if (s >= 40) return "There's room to grow. Small steps add up.";
    return "It's a tough stretch — but awareness is the first step.";
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] text-center space-y-6 animate-fadeIn">
      <div className="text-zinc-500 text-sm font-medium uppercase tracking-widest">
        Your Financial Confidence Score
      </div>

      {/* Guard: show — instead of crashing on null.toFixed() */}
      <div className={`text-7xl font-bold tracking-tight ${hasScore ? getScoreColor(score) : 'text-zinc-500'}`}>
        {hasScore ? score.toFixed(1) : '—'}
      </div>

      <div className="w-16 h-0.5 bg-zinc-700 rounded-full" />

      <p className="text-zinc-400 text-lg max-w-sm">
        {hasScore ? getScoreMessage(score) : 'Check in again tomorrow to see your score.'}
      </p>

      <p className="text-zinc-600 text-sm">
        Check in again tomorrow to track your trend.
      </p>
    </div>
  );
}

// ══════════════════════════════════════════
//  MAIN CHECK-IN PAGE
// ══════════════════════════════════════════

export default function CheckIn() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [weeklyQuestions, setWeeklyQuestions] = useState([]);
  const [isWeeklyDay, setIsWeeklyDay] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const allQuestions = [...questions, ...weeklyQuestions];
  const currentQuestion = allQuestions[currentIndex];
  const totalQuestions = allQuestions.length;
  const answeredCount = Object.keys(answers).length;

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await checkinApi.getQuestions();
        setQuestions(data.daily_questions || []);
        setWeeklyQuestions(data.weekly_questions || []);
        setIsWeeklyDay(data.is_weekly_day || false);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function handleAnswer(value) {
    const qid = currentQuestion.question_id;
    setAnswers((prev) => ({ ...prev, [qid]: value }));
    setTimeout(() => {
      if (currentIndex < totalQuestions - 1) {
        setCurrentIndex((prev) => prev + 1);
      }
    }, 300);
  }

  function goBack() {
    if (currentIndex > 0) setCurrentIndex((prev) => prev - 1);
  }

  async function handleSubmit() {
    setSubmitting(true);
    setError(null);
    try {
      const payload = Object.entries(answers).map(([question_id, raw_value]) => ({
        question_id,
        raw_value,
      }));
      const data = await checkinApi.submitAnswers(payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-zinc-500 text-sm">Loading your check-in...</p>
        </div>
      </div>
    );
  }

  if (error && !currentQuestion) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 transition"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // ── Score reveal after submission ──
  // Prefer canonical metrics.fcs_total, fall back to legacy fcs_snapshot
  if (result) {
    const score = result.metrics?.fcs_total ?? result.fcs_snapshot ?? null;
    return (
      <div className="min-h-screen bg-zinc-950 p-6">
        <div className="max-w-lg mx-auto">
          <ScoreReveal score={score} />
        </div>
      </div>
    );
  }

  const allAnswered = answeredCount >= totalQuestions;
  const isLast = currentIndex === totalQuestions - 1;

  return (
    <div className="min-h-screen bg-zinc-950 p-6">
      <div className="max-w-lg mx-auto space-y-8">

        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-white">Daily Check-In</h1>
            <span className="text-zinc-500 text-sm">
              {currentIndex + 1} / {totalQuestions}
            </span>
          </div>
          <ProgressBar current={answeredCount} total={totalQuestions} />

          {isWeeklyDay && weeklyQuestions.length > 0 && currentIndex >= questions.length && (
            <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl px-4 py-2.5">
              <p className="text-purple-400 text-sm font-medium">Weekly behavioral check-in</p>
            </div>
          )}
        </div>

        {currentQuestion && (
          <div className="bg-zinc-900/50 border border-zinc-800/50 rounded-2xl p-6 space-y-6">
            <div className="space-y-3">
              <DimensionBadge dimension={currentQuestion.dimension} />
              <h2 className="text-lg text-white font-medium leading-relaxed">
                {currentQuestion.question_text}
              </h2>
            </div>
            <ScaleInput
              question={currentQuestion}
              value={answers[currentQuestion.question_id] || null}
              onChange={handleAnswer}
            />
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        <div className="flex items-center justify-between gap-4">
          <button
            onClick={goBack}
            disabled={currentIndex === 0}
            className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all ${
              currentIndex === 0 ? 'text-zinc-700 cursor-not-allowed' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
            }`}
          >
            Back
          </button>

          {allAnswered && (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className={`flex-1 py-3 rounded-xl text-sm font-semibold transition-all duration-200 ${
                submitting
                  ? 'bg-zinc-700 text-zinc-500 cursor-wait'
                  : 'bg-emerald-500 text-white hover:bg-emerald-400 shadow-lg shadow-emerald-500/20'
              }`}
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Computing your score...
                </span>
              ) : (
                'Submit Check-In'
              )}
            </button>
          )}

          {!allAnswered && isLast && (
            <p className="text-zinc-600 text-sm">Answer all questions to submit</p>
          )}
        </div>

      </div>
    </div>
  );
}