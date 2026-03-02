import { useState } from 'react'

export default function Button({ children, onClick, loading, type = 'submit', variant = 'primary' }) {
  const [hovered, setHovered] = useState(false)
  const isPrimary = variant === 'primary'

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={loading}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="w-full rounded-[10px] text-[15px] font-semibold cursor-pointer transition-all duration-200 flex items-center justify-center gap-2 tracking-[0.01em]"
      style={{
        padding: '13px 24px',
        background: isPrimary ? (hovered ? '#1AB892' : '#22D3A7') : 'transparent',
        color: isPrimary ? '#0B0F1A' : '#22D3A7',
        border: isPrimary ? 'none' : '1.5px solid #22D3A7',
        boxShadow: isPrimary && hovered ? '0 4px 20px rgba(34, 211, 167, 0.3)' : 'none',
        opacity: loading ? 0.7 : 1,
        cursor: loading ? 'wait' : 'pointer',
      }}
    >
      {loading && (
        <svg width="18" height="18" viewBox="0 0 18 18" style={{ animation: 'spin 0.8s linear infinite' }}>
          <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="2.5" fill="none" strokeDasharray="32" strokeDashoffset="12" strokeLinecap="round" />
        </svg>
      )}
      {children}
    </button>
  )
}
