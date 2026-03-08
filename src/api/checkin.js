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

const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app';

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

  // ── Tier gating: feature locked (Pro+ or Premium required) ──
  if (response.status === 403) {
    const error = await response.json().catch(() => ({ detail: 'Access denied' }));
    if (error.detail?.code === 'feature_locked') {
      // Redirect to upgrade page with context
      const tier = error.detail.required_tier || 'pro';
      window.location.href = `/upgrade?reason=feature_locked&feature=${error.detail.feature}&tier=${tier}`;
      return;
    }
    throw new Error(error.detail?.message || error.detail || 'Access denied');
  }

  // ── AI message limit reached ──
  if (response.status === 429) {
    const error = await response.json().catch(() => ({ detail: 'Rate limited' }));
    if (error.detail?.code === 'ai_limit_reached') {
      // Return structured error so the Grace chat UI can show an upgrade prompt
      throw {
        isAILimit: true,
        tier: error.detail.tier,
        used: error.detail.used,
        limit: error.detail.limit,
        message: error.detail.message,
      };
    }
    throw new Error(error.detail?.message || error.detail || 'Too many requests');
  }

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
  // Note: history depth is capped by tier (Free=7d, Pro=90d, Premium=365d)
  async getMetrics(days = 30) {
    return apiFetch(`/checkin/metrics?days=${days}`);
  },

  // ── Progression / Unlock System ──
  // Get behavioral unlock tier status.
  // Returns: { tiers, next_unlock, unlocked_features, total_checkins,
  //            current_streak, data_points, unlocked_count, total_tiers }
  async getProgression() {
    return apiFetch('/progression/status');
  },

  // Get the latest GF-RWI index (now includes contributors count)
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