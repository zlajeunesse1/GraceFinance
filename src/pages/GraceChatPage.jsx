/**
 * GraceChatPage — Institutional Redesign
 * 
 * Clean, terminal-inspired AI chat interface.
 * Black background, white text, minimal chrome.
 * Feels like talking to a Bloomberg terminal's AI.
 */

import { useNavigate } from 'react-router-dom'
import GraceChat from '../components/GraceChat.jsx'

export default function GraceChatPage() {
  var navigate = useNavigate()

  return (
    <div style={{
      minHeight: '100vh',
      background: '#000000',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      fontFamily: "'Geist', 'SF Pro Display', -apple-system, sans-serif",
    }}>
      <style>{
        "@import url('https://fonts.cdnfonts.com/css/geist');"
      }</style>

      {/* Header */}
      <div style={{
        width: '100%',
        maxWidth: 700,
        padding: '20px 20px 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderBottom: '1px solid #141414',
        paddingBottom: 16,
      }}>
        <button
          onClick={function () { navigate('/dashboard') }}
          style={{
            background: 'transparent',
            border: '1px solid #222222',
            borderRadius: 6,
            padding: '8px 16px',
            color: '#666666',
            fontSize: 13,
            fontWeight: 500,
            fontFamily: "'Geist', 'SF Pro Display', -apple-system, sans-serif",
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            letterSpacing: '0.01em',
          }}
          onMouseEnter={function (e) {
            e.target.style.borderColor = '#444444'
            e.target.style.color = '#ffffff'
          }}
          onMouseLeave={function (e) {
            e.target.style.borderColor = '#222222'
            e.target.style.color = '#666666'
          }}
        >
          Dashboard
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ textAlign: 'right' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'flex-end' }}>
              <span style={{
                fontSize: 14,
                fontWeight: 600,
                color: '#ffffff',
                letterSpacing: '-0.02em',
              }}>
                Grace
              </span>
              <div style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#ffffff',
              }} />
            </div>
            <span style={{
              fontSize: 11,
              color: '#444444',
              letterSpacing: '0.04em',
              textTransform: 'uppercase',
            }}>
              AI Financial Coach
            </span>
          </div>
        </div>
      </div>

      {/* Chat */}
      <div style={{
        width: '100%',
        maxWidth: 700,
        padding: '20px',
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
      }}>
        <GraceChat />
      </div>

      {/* Footer */}
      <div style={{
        width: '100%',
        maxWidth: 700,
        padding: '0 20px 16px',
        textAlign: 'center',
      }}>
        <p style={{
          fontSize: 11,
          color: '#333333',
          margin: 0,
          letterSpacing: '0.02em',
        }}>
          Grace provides behavioral insights, not financial advice. Consult a professional for financial decisions.
        </p>
      </div>
    </div>
  )
}