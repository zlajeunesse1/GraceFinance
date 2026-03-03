import { useState, useEffect, useRef } from 'react'
import { useTheme } from '../context/ThemeContext'

var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'

function apiFetch(endpoint, options) {
  var token = localStorage.getItem('grace_token')
  var headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = 'Bearer ' + token

  var config = { headers: headers }
  if (options) {
    for (var k in options) {
      if (k === 'headers') {
        for (var h in options.headers) headers[h] = options.headers[h]
      } else {
        config[k] = options[k]
      }
    }
  }
  config.headers = headers

  return fetch(API_BASE + endpoint, config).then(function (res) {
    if (!res.ok) {
      return res.json().catch(function () { return { detail: 'Request failed' } }).then(function (err) {
        throw new Error(err.detail || 'Request failed (' + res.status + ')')
      })
    }
    return res.json()
  })
}

/* GRACE PAW AVATAR */

function GraceAvatar(props) {
  var size = props.size || 36
  var ctx = useTheme()
  var t = ctx.theme

  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: 'linear-gradient(135deg, #1a1a2e, #16213e)',
      border: '2px solid ' + t.accent + '40',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
      boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
    }}>
      <svg width={size * 0.55} height={size * 0.55} viewBox="0 0 64 64" fill="none">
        <ellipse cx="32" cy="40" rx="13" ry="11" fill={t.accent} opacity="0.9" />
        <ellipse cx="19" cy="23" rx="6.5" ry="7.5" fill={t.accent} opacity="0.8" transform="rotate(-15 19 23)" />
        <ellipse cx="45" cy="23" rx="6.5" ry="7.5" fill={t.accent} opacity="0.8" transform="rotate(15 45 23)" />
        <ellipse cx="13" cy="34" rx="5.5" ry="6.5" fill={t.accent} opacity="0.7" transform="rotate(-30 13 34)" />
        <ellipse cx="51" cy="34" rx="5.5" ry="6.5" fill={t.accent} opacity="0.7" transform="rotate(30 51 34)" />
      </svg>
    </div>
  )
}

/* TYPING INDICATOR */

function TypingIndicator() {
  var ctx = useTheme()
  var t = ctx.theme

  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 16 }}>
      <GraceAvatar size={32} />
      <div style={{
        background: 'rgba(188,140,255,0.08)', border: '1px solid rgba(188,140,255,0.15)',
        borderRadius: '16px 16px 16px 4px', padding: '12px 18px',
      }}>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          {[0, 1, 2].map(function (i) {
            return (
              <div key={i} style={{
                width: 7, height: 7, borderRadius: '50%', background: '#BC8CFF',
                animation: 'gracePulse 1.4s infinite',
                animationDelay: i * 0.2 + 's',
                opacity: 0.4,
              }} />
            )
          })}
        </div>
      </div>
      <style>{"@keyframes gracePulse { 0%, 60%, 100% { opacity: 0.4; transform: scale(1); } 30% { opacity: 1; transform: scale(1.2); } }"}</style>
    </div>
  )
}

/* MAIN GRACE CHAT COMPONENT */

export default function GraceChat() {
  var ctx = useTheme()
  var theme = ctx.theme

  var chatState = useState([])
  var messages = chatState[0]
  var setMessages = chatState[1]

  var inputState = useState('')
  var input = inputState[0]
  var setInput = inputState[1]

  var typingState = useState(false)
  var isTyping = typingState[0]
  var setIsTyping = typingState[1]

  var introState = useState(null)
  var intro = introState[0]
  var setIntro = introState[1]

  var errorState = useState(null)
  var error = errorState[0]
  var setError = errorState[1]

  var chatEndRef = useRef(null)

  useEffect(function () {
    apiFetch('/grace/intro')
      .then(function (data) { setIntro(data) })
      .catch(function () {
        setIntro({
          greeting: "Hey there, I'm Grace. I'm your financial coach. What's on your mind?",
          suggestions: [
            "Why do I stress about money even when I'm okay?",
            "How do I start building an emergency fund?",
            "I just overspent - help me not feel terrible",
            "What does my FCS score actually mean?",
            "Help me set a realistic money goal",
          ],
        })
      })
  }, [])

  useEffect(function () {
    if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  function sendMessage(text) {
    var msg = text || input
    if (!msg.trim()) return

    setError(null)
    var userMsg = { role: 'user', content: msg }
    var newMessages = messages.concat([userMsg])
    setMessages(newMessages)
    setInput('')
    setIsTyping(true)

    var apiMessages = newMessages.map(function (m) {
      return { role: m.role, content: m.content }
    })

    apiFetch('/grace/chat', {
      method: 'POST',
      body: JSON.stringify({ messages: apiMessages }),
    })
      .then(function (data) {
        setMessages(function (prev) {
          return prev.concat([{ role: 'assistant', content: data.response }])
        })
        setIsTyping(false)
      })
      .catch(function (err) {
        setError(err.message)
        setIsTyping(false)
      })
  }

  return (
    <div style={{
      background: theme.card, border: '1px solid ' + theme.border,
      borderRadius: 16, overflow: 'hidden', display: 'flex', flexDirection: 'column',
    }}>

      {/* HEADER */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid ' + theme.border,
        display: 'flex', alignItems: 'center', gap: 12,
        background: 'linear-gradient(135deg, rgba(188,140,255,0.05), transparent)',
      }}>
        <GraceAvatar size={40} />
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 15, fontWeight: 700, color: theme.text }}>Grace</span>
            <span style={{
              fontSize: 9, fontWeight: 700, color: '#BC8CFF', background: 'rgba(188,140,255,0.12)',
              padding: '2px 8px', borderRadius: 10, textTransform: 'uppercase', letterSpacing: '0.08em',
            }}>
              AI Coach
            </span>
          </div>
          <p style={{ fontSize: 11, color: theme.muted, margin: '2px 0 0' }}>
            Your financial coach - powered by your real FCS data
          </p>
        </div>
      </div>

      {/* MESSAGES */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '16px 20px',
        maxHeight: 420, minHeight: 200,
      }}>

        {intro && messages.length === 0 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 16 }}>
              <GraceAvatar size={32} />
              <div style={{
                background: 'rgba(188,140,255,0.08)', border: '1px solid rgba(188,140,255,0.15)',
                borderRadius: '16px 16px 16px 4px', padding: '12px 16px', maxWidth: '85%',
              }}>
                <p style={{ color: theme.text, fontSize: 13, lineHeight: 1.7, margin: 0 }}>
                  {intro.greeting}
                </p>
              </div>
            </div>

            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: 8, marginLeft: 42, marginBottom: 8,
            }}>
              {intro.suggestions.map(function (s, i) {
                return (
                  <button
                    key={i}
                    onClick={function () { sendMessage(s) }}
                    style={{
                      background: theme.border + '15', border: '1px solid ' + theme.border + '40',
                      borderRadius: 20, padding: '7px 14px', color: theme.muted,
                      fontSize: 12, cursor: 'pointer', transition: 'all 0.2s',
                      whiteSpace: 'nowrap',
                    }}
                    onMouseEnter={function (e) {
                      e.target.style.background = theme.accent + '15'
                      e.target.style.borderColor = theme.accent + '40'
                      e.target.style.color = theme.accent
                    }}
                    onMouseLeave={function (e) {
                      e.target.style.background = theme.border + '15'
                      e.target.style.borderColor = theme.border + '40'
                      e.target.style.color = theme.muted
                    }}
                  >
                    {s}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {messages.map(function (msg, i) {
          var isUser = msg.role === 'user'

          return (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start', gap: 10,
              justifyContent: isUser ? 'flex-end' : 'flex-start',
              marginBottom: 16,
            }}>
              {!isUser && <GraceAvatar size={32} />}

              <div style={{
                maxWidth: '80%',
                background: isUser
                  ? theme.accent + '15'
                  : 'rgba(188,140,255,0.08)',
                border: '1px solid ' + (isUser
                  ? theme.accent + '30'
                  : 'rgba(188,140,255,0.15)'),
                borderRadius: isUser
                  ? '16px 16px 4px 16px'
                  : '16px 16px 16px 4px',
                padding: '12px 16px',
              }}>
                {!isUser && (
                  <p style={{
                    color: '#BC8CFF', fontSize: 10, fontWeight: 700,
                    margin: '0 0 4px', textTransform: 'uppercase', letterSpacing: '0.06em',
                  }}>
                    Grace
                  </p>
                )}
                <p style={{
                  color: theme.text, fontSize: 13, margin: 0, lineHeight: 1.7,
                  whiteSpace: 'pre-wrap',
                }}>
                  {msg.content}
                </p>
              </div>
            </div>
          )
        })}

        {isTyping && <TypingIndicator />}

        {error && (
          <div style={{
            background: '#F8514910', border: '1px solid #F8514925',
            borderRadius: 12, padding: '10px 14px', marginBottom: 12,
          }}>
            <p style={{ color: '#F85149', fontSize: 12, margin: 0 }}>
              Grace is having trouble connecting. Try again in a moment.
            </p>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* INPUT */}
      <div style={{
        padding: '12px 20px', borderTop: '1px solid ' + theme.border,
        display: 'flex', gap: 10, alignItems: 'center',
      }}>
        <input
          value={input}
          onChange={function (e) { setInput(e.target.value) }}
          onKeyDown={function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
          placeholder="Talk to Grace about anything money-related..."
          disabled={isTyping}
          style={{
            flex: 1, padding: '12px 16px', borderRadius: 12,
            border: '1px solid ' + theme.border, background: theme.dark,
            color: theme.text, fontSize: 13, outline: 'none',
            opacity: isTyping ? 0.6 : 1,
          }}
        />
        <button
          onClick={function () { sendMessage() }}
          disabled={isTyping || !input.trim()}
          style={{
            padding: '12px 20px', borderRadius: 12, border: 'none',
            background: input.trim() && !isTyping
              ? 'linear-gradient(135deg, #BC8CFF, ' + theme.accent + ')'
              : theme.border + '40',
            color: input.trim() && !isTyping ? '#fff' : theme.muted,
            fontSize: 13, fontWeight: 600, cursor: input.trim() && !isTyping ? 'pointer' : 'default',
            transition: 'all 0.2s',
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}