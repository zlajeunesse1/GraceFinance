import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTheme } from '../context/ThemeContext'
import { useProfile } from '../hooks/useProfile'

function ToggleSwitch({ active, onToggle, t }) {
  return (
    <div
      onClick={onToggle}
      style={{
        width: 44, height: 24, borderRadius: 12, cursor: 'pointer',
        background: active ? t.accent : t.border + '60',
        position: 'relative', transition: 'all 0.3s',
        border: '1px solid ' + (active ? t.accent + '60' : t.border),
      }}
    >
      <div style={{
        width: 18, height: 18, borderRadius: '50%', background: '#fff',
        position: 'absolute', top: 2,
        left: active ? 22 : 2,
        transition: 'left 0.3s',
        boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
      }} />
    </div>
  )
}

var THEMES = [
  { id: 'dark',       name: 'Dark Mode',       desc: 'Default experience',  accent: '#58A6FF' },
  { id: 'wealth',     name: 'Wealth Mode',     desc: 'Muted green accent',  accent: '#3FB950' },
  { id: 'aggressive', name: 'Aggressive Mode', desc: 'Red accent',          accent: '#F85149' },
  { id: 'calm',       name: 'Calm Mode',       desc: 'Soft purple',         accent: '#BC8CFF' },
]

export default function SettingsPage() {
  var ctx = useTheme()
  var t = ctx.theme
  var setTheme = ctx.setTheme
  var currentThemeId = ctx.currentTheme || 'dark'
  var navigate = useNavigate()
  var profileHook = useProfile()
  var updateProfile = profileHook.updateProfile

  var [dailyReminder, setDailyReminder] = useState(true)
  var [indexOptIn, setIndexOptIn] = useState(false)
  var [saved, setSaved] = useState(false)

  async function handleThemeSelect(themeId) {
    // Update local theme immediately for instant feedback
    setTheme(themeId)
    // Persist to backend
    await updateProfile({ theme: themeId })
    setSaved(true)
    setTimeout(function () { setSaved(false) }, 1500)
  }

  var cardStyle = {
    background: t.card, border: '1px solid ' + t.border,
    borderRadius: 16, padding: 24, marginBottom: 16,
  }

  var sectionLabel = {
    fontSize: 14, fontWeight: 700, color: t.muted,
    textTransform: 'uppercase', letterSpacing: '0.08em', margin: '0 0 16px',
  }

  return (
    <div style={{
      minHeight: '100vh', background: t.dark, color: t.text,
      fontFamily: "'DM Sans', -apple-system, sans-serif",
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '40px 20px',
    }}>
      <div style={{ width: '100%', maxWidth: 600 }}>

        <button
          onClick={function () { navigate('/dashboard') }}
          style={{
            background: 'none', border: '1px solid ' + t.border,
            borderRadius: 10, padding: '8px 16px', color: t.muted,
            fontSize: 13, cursor: 'pointer', marginBottom: 32,
          }}
        >
          ← Back to Dashboard
        </button>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: t.text, margin: 0 }}>Settings</h1>
          {saved && (
            <span style={{ fontSize: 12, color: '#16a34a', fontWeight: 600 }}>✓ Saved</span>
          )}
        </div>

        {/* Theme Selection — now actually works */}
        <div style={cardStyle}>
          <h2 style={sectionLabel}>Theme</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {THEMES.map(function (theme) {
              var isActive = currentThemeId === theme.id
              return (
                <div
                  key={theme.id}
                  onClick={function () { handleThemeSelect(theme.id) }}
                  style={{
                    background: t.dark,
                    border: '1px solid ' + (isActive ? theme.accent + '80' : t.border),
                    borderRadius: 12, padding: 16, cursor: 'pointer',
                    transition: 'all 0.2s',
                    boxShadow: isActive ? '0 0 0 1px ' + theme.accent + '40' : 'none',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <div style={{
                      width: 14, height: 14, borderRadius: '50%',
                      background: theme.accent,
                      border: '2px solid ' + theme.accent + '40',
                    }} />
                    <span style={{ fontSize: 13, fontWeight: 600, color: isActive ? theme.accent : t.text }}>
                      {theme.name}
                    </span>
                  </div>
                  <p style={{ fontSize: 11, color: t.muted, margin: 0 }}>{theme.desc}</p>
                </div>
              )
            })}
          </div>
        </div>

        {/* Notifications */}
        <div style={cardStyle}>
          <h2 style={sectionLabel}>Notifications</h2>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid ' + t.border + '40' }}>
            <div>
              <span style={{ fontSize: 13, color: t.text, fontWeight: 500 }}>Daily check-in reminder</span>
              <p style={{ fontSize: 11, color: t.muted, margin: '4px 0 0' }}>Get reminded to check in each morning</p>
            </div>
            <ToggleSwitch active={dailyReminder} onToggle={function () { setDailyReminder(!dailyReminder) }} t={t} />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0' }}>
            <div>
              <span style={{ fontSize: 13, color: t.text, fontWeight: 500 }}>Index participation</span>
              <p style={{ fontSize: 11, color: t.muted, margin: '4px 0 0' }}>Contribute anonymized data to the GF-RWI</p>
            </div>
            <ToggleSwitch active={indexOptIn} onToggle={function () { setIndexOptIn(!indexOptIn) }} t={t} />
          </div>
        </div>

        {/* Data & Export */}
        <div style={cardStyle}>
          <h2 style={sectionLabel}>Data & Export</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {['Export check-in data (CSV)', 'Export FCS history (CSV)'].map(function (action, i) {
              return (
                <button key={i} style={{
                  padding: '12px 16px', borderRadius: 10, fontSize: 13, fontWeight: 500,
                  cursor: 'pointer', background: 'transparent', textAlign: 'left',
                  border: '1px solid ' + t.border, color: t.muted, transition: 'all 0.2s',
                }}>
                  {action}
                </button>
              )
            })}
          </div>
        </div>

        <p style={{ fontSize: 11, color: t.muted + '60', textAlign: 'center', marginTop: 24 }}>
          GraceFinance v1.1.0 — Smarter Finance is Right Around the Corner™
        </p>

      </div>
    </div>
  )
}