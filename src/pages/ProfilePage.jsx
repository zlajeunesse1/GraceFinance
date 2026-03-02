import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { useProfile } from '../hooks/useProfile'

function CompletionRing({ score, accent }) {
  var radius = 26
  var circumference = 2 * Math.PI * radius
  var offset = circumference - (score / 100) * circumference
  var color = score < 40 ? '#ef4444' : score < 75 ? '#f59e0b' : accent

  return (
    <div style={{ position: 'relative', width: 64, height: 64 }}>
      <svg width="64" height="64" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="32" cy="32" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="5" />
        <circle
          cx="32" cy="32" r={radius} fill="none"
          stroke={color} strokeWidth="5"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 12, fontWeight: 700, color: '#f8fafc',
      }}>
        {score}%
      </div>
    </div>
  )
}

function OptionGrid({ options, value, onChange, disabled, t }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
      {options.map(function (opt) {
        var isActive = value === opt.value
        return (
          <button
            key={opt.value}
            onClick={function () { onChange(opt.value) }}
            disabled={disabled}
            style={{
              padding: '11px 14px',
              borderRadius: 10,
              border: isActive ? '1.5px solid ' + t.accent : '1px solid ' + t.border,
              background: isActive ? t.accent + '18' : t.card,
              color: isActive ? t.accent : t.muted,
              textAlign: 'left',
              cursor: disabled ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s ease',
              opacity: disabled ? 0.6 : 1,
            }}
          >
            <div style={{ fontSize: 13, fontWeight: 600 }}>{opt.label}</div>
            {opt.desc && (
              <div style={{ fontSize: 11, marginTop: 2, opacity: 0.6 }}>{opt.desc}</div>
            )}
          </button>
        )
      })}
    </div>
  )
}

var RISK_OPTIONS = [
  { value: 'calm',       label: 'Calm',       desc: 'Safety first' },
  { value: 'balanced',   label: 'Balanced',   desc: 'Steady growth' },
  { value: 'aggressive', label: 'Aggressive', desc: 'Max upside' },
]

export default function ProfilePage() {
  var navigate = useNavigate()
  var auth = useAuth()
  var user = auth.user
  var ctx = useTheme()
  var t = ctx.theme
  var profileHook = useProfile()
  var profile = profileHook.profile
  var isLoading = profileHook.isLoading
  var isSaving = profileHook.isSaving
  var saveError = profileHook.saveError
  var updateProfile = profileHook.updateProfile

  var [displayName, setDisplayName] = useState('')
  var [timezone, setTimezone] = useState('America/New_York')
  var [currency, setCurrency] = useState('USD')
  var [riskStyle, setRiskStyle] = useState('balanced')
  var [saved, setSaved] = useState(false)

  useEffect(function () {
    if (profile) {
      setDisplayName(profile.display_name || '')
      setTimezone(profile.timezone || 'America/New_York')
      setCurrency(profile.currency || 'USD')
      setRiskStyle(profile.risk_style || 'balanced')
    }
  }, [profile])

  async function handleSave() {
    await updateProfile({
      display_name: displayName || null,
      timezone: timezone,
      currency: currency,
      risk_style: riskStyle,
    })
    setSaved(true)
    setTimeout(function () { setSaved(false) }, 2000)
  }

  var inputStyle = {
    width: '100%', padding: '10px 14px', borderRadius: 8,
    border: '1px solid ' + t.border, background: t.dark, color: t.text,
    fontSize: 13, outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit',
  }

  var labelStyle = { display: 'block', fontSize: 12, fontWeight: 600, color: t.muted, marginBottom: 6 }
  var cardStyle = { background: t.card, border: '1px solid ' + t.border, borderRadius: 16, padding: 24, marginBottom: 14 }
  var sectionLabel = { fontSize: 11, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', color: t.muted, marginBottom: 14 }

  if (auth.loading || isLoading) {
    return (
      <div style={{ minHeight: '100vh', background: t.dark, color: t.muted, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14 }}>
        Loading your profile...
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: t.dark, color: t.text, fontFamily: "'DM Sans', -apple-system, sans-serif", display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 20px' }}>
      <div style={{ width: '100%', maxWidth: 600 }}>

        <button onClick={function () { navigate('/dashboard') }} style={{ background: 'none', border: '1px solid ' + t.border, borderRadius: 10, padding: '8px 16px', color: t.muted, fontSize: 13, cursor: 'pointer', marginBottom: 32 }}>
          ← Back to Dashboard
        </button>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: t.text, margin: 0 }}>Profile</h1>
            <p style={{ fontSize: 13, color: t.muted, margin: '4px 0 0' }}>How Grace knows you</p>
          </div>
          {profile && <CompletionRing score={profile.profile_completion_score} accent={t.accent} />}
        </div>

        {/* Account */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Account</div>
          {[
            { label: 'Name', value: user ? ((user.first_name || '') + ' ' + (user.last_name || '')).trim() || '--' : '--' },
            { label: 'Email', value: user ? user.email : '--' },
            { label: 'Member since', value: user && user.created_at ? new Date(user.created_at).toLocaleDateString() : '--' },
            { label: 'Plan', value: 'Free Tier' },
          ].map(function (item, i, arr) {
            return (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '11px 0', borderBottom: i < arr.length - 1 ? '1px solid ' + t.border + '40' : 'none' }}>
                <span style={{ fontSize: 13, color: t.muted }}>{item.label}</span>
                <span style={{ fontSize: 13, color: t.text, fontWeight: 500 }}>{item.value}</span>
              </div>
            )
          })}
        </div>

        {/* Identity */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Identity</div>
          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>Display Name</label>
            <input style={inputStyle} value={displayName} onChange={function (e) { setDisplayName(e.target.value) }} placeholder="How Grace addresses you" maxLength={64} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={labelStyle}>Currency</label>
              <input style={inputStyle} value={currency} onChange={function (e) { setCurrency(e.target.value.toUpperCase()) }} maxLength={8} placeholder="USD" />
            </div>
            <div>
              <label style={labelStyle}>Timezone</label>
              <input style={inputStyle} value={timezone} onChange={function (e) { setTimezone(e.target.value) }} placeholder="America/New_York" />
            </div>
          </div>
        </div>

        {/* Financial DNA */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Financial DNA</div>
          <label style={{ ...labelStyle, marginBottom: 10 }}>Risk Style</label>
          <OptionGrid options={RISK_OPTIONS} value={riskStyle} onChange={setRiskStyle} disabled={isSaving} t={t} />
        </div>

        {/* Privacy */}
        <div style={cardStyle}>
          <div style={sectionLabel}>Privacy & Data</div>
          <p style={{ fontSize: 13, color: t.muted, lineHeight: 1.7, margin: '0 0 16px' }}>
            Your data is encrypted and never sold. You control what GraceFinance can access.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {['Export my data (CSV)', 'Delete my account'].map(function (action, i) {
              return (
                <button key={i} style={{ padding: '10px 16px', borderRadius: 10, fontSize: 13, fontWeight: 500, cursor: 'pointer', textAlign: 'left', background: 'transparent', border: '1px solid ' + (i === 1 ? '#F8514940' : t.border), color: i === 1 ? '#F85149' : t.muted }}>
                  {action}
                </button>
              )
            })}
          </div>
        </div>

        <button onClick={handleSave} disabled={isSaving} style={{ width: '100%', padding: '13px', borderRadius: 12, border: 'none', background: saved ? '#16a34a' : isSaving ? t.border : t.accent, color: saved || isSaving ? '#f8fafc' : t.dark, fontWeight: 700, fontSize: 15, cursor: isSaving ? 'not-allowed' : 'pointer', transition: 'all 0.2s ease', marginTop: 4 }}>
          {saved ? '✓ Saved' : isSaving ? 'Saving...' : 'Save Profile'}
        </button>

        {saveError && <p style={{ color: '#ef4444', fontSize: 13, textAlign: 'center', marginTop: 10 }}>{saveError}</p>}

      </div>
    </div>
  )
}