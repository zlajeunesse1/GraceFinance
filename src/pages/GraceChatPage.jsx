/**
 * GraceChatPage — Full-page Grace AI Coach chat.
 *
 * CHANGES:
 *   - [TIER 2] Updated tagline from "Smarter Finance is Right Around the Corner™" 
 *              to "The Behavioral Finance Company"
 *
 * Place at: src/pages/GraceChatPage.jsx
 */

import { useNavigate } from 'react-router-dom'
import GraceChat from '../components/GraceChat.jsx'
import { useTheme } from '../context/ThemeContext'

export default function GraceChatPage() {
  var ctx = useTheme()
  var t = ctx.theme
  var navigate = useNavigate()

  return (
    <div style={{
      minHeight: '100vh',
      background: t.dark,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
    }}>
      {/* Header */}
      <div style={{
        width: '100%',
        maxWidth: 700,
        padding: '24px 20px 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <button
          onClick={function () { navigate('/dashboard') }}
          style={{
            background: 'none',
            border: '1px solid ' + t.border,
            borderRadius: 10,
            padding: '8px 16px',
            color: t.muted,
            fontSize: 13,
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
          onMouseEnter={function (e) {
            e.target.style.borderColor = t.accent
            e.target.style.color = t.accent
          }}
          onMouseLeave={function (e) {
            e.target.style.borderColor = t.border
            e.target.style.color = t.muted
          }}
        >
          ← Dashboard
        </button>

        <div style={{ textAlign: 'right' }}>
          <p style={{
            color: t.text,
            fontSize: 15,
            fontWeight: 700,
            margin: 0,
          }}>
            GraceFinance
          </p>
          <p style={{
            color: t.muted,
            fontSize: 11,
            margin: '2px 0 0',
            fontStyle: 'italic',
          }}>
            The Behavioral Finance Company
          </p>
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
    </div>
  )
}