// ─── Check-In API ──────────────────────────────────────────────
// All check-in related API calls to the FastAPI backend.
//
// Endpoints:
//   GET  /checkin/questions    → Get today's questions
//   POST /checkin/submit       → Submit answers, returns metrics snapshot
//   GET  /checkin/metrics      → Get FCS history (trend chart only)
//   GET  /me/metrics           → Canonical UserMetricsSnapshot (all dashboard tiles)
//   GET  /progression/status   → Behavioral unlock tier status
//   GET  /index/latest         → Get current GF-RWI
//   GET  /index/history        → Get GF-RWI trend
//   POST /index/compute        → Trigger index computation
// ──────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem('grace_token');
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Something went wrong' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export const checkinApi = {
  // Get today's check-in questions
  async getQuestions() {
    return apiFetch('/checkin/questions');
  },

  // Submit check-in answers
  // answers: [{ question_id: "CS-1", raw_value: 4 }, ...]
  // Returns: { message, responses_saved, fcs_snapshot, metrics: UserMetricsSnapshot, reward }
  async submitAnswers(answers) {
    return apiFetch('/checkin/submit', {
      method: 'POST',
      body: JSON.stringify({ answers }),
    });
  },

  // Get canonical UserMetricsSnapshot — use this for ALL dashboard tiles.
  // Returns: { fcs_total, dimensions, streak_count, checkins_this_week,
  //            last_checkin_at, delta_vs_last, updated_at }
  // All fields are null (never 0) when no check-in data exists yet.
  async getUserMetrics() {
    return apiFetch('/me/metrics');
  },

  // Get user's FCS metric history — use this for the trend chart only.
  async getMetrics(days = 30) {
    return apiFetch(`/checkin/metrics?days=${days}`);
  },

  // ── NEW: Progression / Unlock System ──
  // Get behavioral unlock tier status.
  // Returns: { tiers, next_unlock, unlocked_features, total_checkins,
  //            current_streak, data_points, unlocked_count, total_tiers }
  async getProgression() {
    return apiFetch('/progression/status');
  },

  // Get the latest GF-RWI index
  async getLatestIndex() {
    return apiFetch('/index/latest');
  },

  // Get GF-RWI history for charts
  async getIndexHistory(days = 30) {
    return apiFetch(`/index/history?days=${days}`);
  },

  // Trigger index computation (dev/admin)
  async computeIndex() {
    return apiFetch('/index/compute', { method: 'POST' });
  },
};