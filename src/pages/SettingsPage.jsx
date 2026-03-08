/*
 * GraceFinance — Settings Page (v4.0.0 updated)
 *
 * Changes:
 *   ✅ Removed "Index contribution" toggle (everyone contributes by default)
 *   ✅ Wired CSV export buttons to GET /api/export/checkins & /api/export/fcs-trend
 *
 * Uses your existing hostname-based API_BASE pattern.
 * Drop this into your Settings component file or merge the relevant pieces.
 */

import React, { useState } from "react";

// ── Match your existing runtime hostname check ──
const API_BASE = (() => {
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return "http://localhost:8000";
  }
  return "https://gracefinance-production.up.railway.app"; // ← adjust if your Railway URL differs
})();

function Settings() {
  const [dailyReminder, setDailyReminder] = useState(true);
  const [exportingCheckins, setExportingCheckins] = useState(false);
  const [exportingFCS, setExportingFCS] = useState(false);

  const token = localStorage.getItem("grace_token");

  // ── Generic CSV download helper ──
  const downloadCSV = async (endpoint, fallbackFilename, setLoading) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/export/${endpoint}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error(`Export failed (${res.status})`);

      const disposition = res.headers.get("Content-Disposition");
      let filename = fallbackFilename;
      if (disposition) {
        const match = disposition.match(/filename="?([^"]+)"?/);
        if (match) filename = match[1];
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export error:", err);
      alert("Export failed — please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: "2rem 1rem" }}>
      {/* Back to dashboard */}
      <a href="/dashboard" className="back-link">Dashboard</a>

      <h1 style={{ color: "#fff", marginTop: 12 }}>Settings</h1>
      <p style={{ color: "#888", marginBottom: 24 }}>Customize your GraceFinance experience.</p>

      {/* ─── NOTIFICATIONS ─── */}
      <section className="settings-card">
        <h2 className="section-title">NOTIFICATIONS</h2>

        <div className="settings-row">
          <div>
            <strong style={{ color: "#fff" }}>Daily check-in reminder</strong>
            <p className="settings-desc">
              A gentle nudge each morning to keep your streak alive.
            </p>
          </div>
          {/* Replace with your existing toggle component if you have one */}
          <label className="toggle">
            <input
              type="checkbox"
              checked={dailyReminder}
              onChange={() => setDailyReminder(!dailyReminder)}
              hidden
            />
            <span className={`toggle-track ${dailyReminder ? "active" : ""}`}>
              <span className="toggle-thumb" />
            </span>
          </label>
        </div>

        {/* INDEX CONTRIBUTION TOGGLE — REMOVED
            Everyone now contributes to the GraceFinance Composite Index. */}
      </section>

      {/* ─── YOUR DATA ─── */}
      <section className="settings-card">
        <h2 className="section-title">YOUR DATA</h2>
        <p className="settings-desc" style={{ marginBottom: 12 }}>
          Your data belongs to you. Export it anytime, or delete your account entirely.
        </p>

        <button
          className="export-btn"
          disabled={exportingCheckins}
          onClick={() =>
            downloadCSV("checkins", "gracefinance_checkins.csv", setExportingCheckins)
          }
        >
          {exportingCheckins ? "Exporting…" : "Export check-in history (CSV)"}
        </button>

        <button
          className="export-btn"
          disabled={exportingFCS}
          onClick={() =>
            downloadCSV("fcs-trend", "gracefinance_fcs_trend.csv", setExportingFCS)
          }
        >
          {exportingFCS ? "Exporting…" : "Export FCS trend data (CSV)"}
        </button>
      </section>

      {/* ─── ACCOUNT ─── */}
      <section className="settings-card">
        <h2 className="section-title">ACCOUNT</h2>
        <button
          className="delete-btn"
          onClick={() => {
            if (window.confirm("Are you sure? This will permanently delete your account and all data.")) {
              // TODO: call your delete endpoint
              console.log("Account deletion requested");
            }
          }}
        >
          Delete my account and all data
        </button>
      </section>

      <p style={{ color: "#444", fontSize: 12, textAlign: "center", marginTop: 32 }}>
        GraceFinance v4.0.0
      </p>
    </div>
  );
}

export default Settings;