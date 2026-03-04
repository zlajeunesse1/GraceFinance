/**
 * GraceChat — Institutional Redesign
 *
 * Stripped: useTheme, GraceAvatar paw, purple bubble colors,
 *           gradient backgrounds, colored badges, BC8CFF accents.
 *
 * Kept: All API logic (intro, chat), suggestions, message flow,
 *       typing indicator, error handling, scroll-to-bottom.
 *
 * Design: Terminal-clean. White-on-black. Grace speaks in gray,
 *         you speak in white. No decoration.
 */

import { useState, useEffect, useRef } from 'react'

var API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://gracefinance-production.up.railway.app'
```
var FONT = "'Geist', 'SF Pro Display', -apple-system, sans-serif"

var C = {
  bg:     "#000000",
  card:   "#0a0a0a",
  border: "#1a1a1a",
  text:   "#ffffff",
  muted:  "#666666",
  dim:    "#444444",
  faint:  "#333333",
  error:  "#ff4444",
}

/* ── Authenticated fetch ── */

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

/* ── Grace avatar (minimal "G" mark, no paw) ── */

function GraceAvatar(props) {
  var size = props.size || 28
  return (
    <div style={{
      width: size, height: size, borderRadius: 6,
      border: '1.5px solid ' + C.faint,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0, fontSize: size * 0.4, fontWeight: 700,
      color: C.text, fontFamily: FONT,
    }}>
      G
    </div>
  )
}

/* ── Typing indicator ── */

function TypingIndicator() {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 16 }}>
      <GraceAvatar size={28} />
      <div style={{
        background: C.card, border: '1px solid ' + C.border,
        borderRadius: '12px 12px 12px 4px', padding: '12px 16px',
      }}>
        <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
          {[0, 1, 2].map(function (i) {
            return (
              <div key={i} style={{
                width: 5, height: 5, borderRadius: '50%', background: C.muted,
                animation: 'graceTyping 1.4s infinite',
                animationDelay: i * 0.2 + 's', opacity: 0.3,
              }} />
            )
          })}
        </div>
      </div>
      <style>{"@keyframes graceTyping { 0%, 60%, 100% { opacity: 0.3; } 30% { opacity: 0.8; } }"}</style>
    </div>
  )
}

/* ══════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════ */

export default function GraceChat() {

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

  var focusedState = useState(false)
  var focused = focusedState[0]
  var setFocused = focusedState[1]

  var chatEndRef = useRef(null)

  useEffect(function () {
    apiFetch('/grace/intro')
      .then(function (data) { setIntro(data) })
      .catch(function () {
        setIntro({
          greeting: "I'm Grace, your financial coach. What's on your mind?",
          suggestions: [
            "Why do I stress about money even when I'm okay?",
            "How do I start building an emergency fund?",
            "I just overspent — help me think through it",
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
      background: C.card, border: '1px solid ' + C.border,
      borderRadius: 10, overflow: 'hidden', display: 'flex',
      flexDirection: 'column', fontFamily: FONT,
    }}>
      <style>{"@import url('https://fonts.cdnfonts.com/css/geist'); ::placeholder { color: #444444 !important; }"}</style>

      {/* Header */}
      <div style={{
        padding: '14px 20px', borderBottom: '1px solid ' + C.border,
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <GraceAvatar size={32} />
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: C.text, letterSpacing: '-0.02em' }}>Grace</span>
            <div style={{ width: 5, height: 5, borderRadius: '50%', background: C.text }} />
          </div>
          <p style={{ fontSize: 11, color: C.dim, margin: '2px 0 0', letterSpacing: '0.02em' }}>
            AI Financial Coach
          </p>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '16px 20px',
        maxHeight: 420, minHeight: 200,
      }}>

        {/* Intro state */}
        {intro && messages.length === 0 && (
          <div>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 16 }}>
              <GraceAvatar size={28} />
              <div style={{
                background: C.card, border: '1px solid ' + C.border,
                borderRadius: '12px 12px 12px 4px', padding: '12px 16px', maxWidth: '85%',
              }}>
                <p style={{ color: C.text, fontSize: 13, lineHeight: 1.7, margin: 0 }}>
                  {intro.greeting}
                </p>
              </div>
            </div>

            {/* Suggestions */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginLeft: 38, marginBottom: 8 }}>
              {intro.suggestions.map(function (s, i) {
                return (
                  <button key={i}
                    onClick={function () { sendMessage(s) }}
                    style={{
                      background: 'transparent',
                      border: '1px solid ' + C.faint,
                      borderRadius: 6, padding: '7px 12px', color: C.muted,
                      fontSize: 12, cursor: 'pointer', transition: 'all 0.15s ease',
                      fontFamily: FONT, whiteSpace: 'nowrap',
                    }}
                    onMouseEnter={function (e) {
                      e.target.style.borderColor = C.muted
                      e.target.style.color = C.text
                    }}
                    onMouseLeave={function (e) {
                      e.target.style.borderColor = C.faint
                      e.target.style.color = C.muted
                    }}
                  >
                    {s}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Message history */}
        {messages.map(function (msg, i) {
          var isUser = msg.role === 'user'

          return (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start', gap: 10,
              justifyContent: isUser ? 'flex-end' : 'flex-start',
              marginBottom: 16,
            }}>
              {!isUser && <GraceAvatar size={28} />}

              <div style={{
                maxWidth: '80%',
                background: isUser ? '#111111' : C.card,
                border: '1px solid ' + (isUser ? '#222222' : C.border),
                borderRadius: isUser ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                padding: '12px 16px',
              }}>
                {!isUser && (
                  <p style={{
                    color: C.dim, fontSize: 10, fontWeight: 600,
                    margin: '0 0 4px', textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                  }}>
                    Grace
                  </p>
                )}
                <p style={{
                  color: C.text, fontSize: 13, margin: 0,
                  lineHeight: 1.7, whiteSpace: 'pre-wrap',
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
            background: C.error + '08', border: '1px solid ' + C.error + '20',
            borderRadius: 8, padding: '10px 14px', marginBottom: 12,
          }}>
            <p style={{ color: C.error, fontSize: 12, margin: 0 }}>
              Grace is having trouble connecting. Try again in a moment.
            </p>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '12px 20px', borderTop: '1px solid ' + C.border,
        display: 'flex', gap: 10, alignItems: 'center',
      }}>
        <input
          value={input}
          onChange={function (e) { setInput(e.target.value) }}
          onKeyDown={function (e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() } }}
          onFocus={function () { setFocused(true) }}
          onBlur={function () { setFocused(false) }}
          placeholder="Ask Grace anything about your finances..."
          disabled={isTyping}
          style={{
            flex: 1, padding: '12px 0', borderRadius: 0,
            border: 'none', borderBottom: '1px solid ' + (focused ? C.text : C.faint),
            background: 'transparent', color: C.text, fontSize: 13,
            outline: 'none', fontFamily: FONT,
            opacity: isTyping ? 0.5 : 1,
            transition: 'border-color 0.2s ease, opacity 0.2s ease',
          }}
        />
        <button
          onClick={function () { sendMessage() }}
          disabled={isTyping || !input.trim()}
          style={{
            padding: '10px 20px', borderRadius: 6, border: 'none',
            background: input.trim() && !isTyping ? C.text : C.border,
            color: input.trim() && !isTyping ? C.bg : C.dim,
            fontSize: 13, fontWeight: 600, fontFamily: FONT,
            cursor: input.trim() && !isTyping ? 'pointer' : 'default',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={function (e) { if (input.trim() && !isTyping) e.target.style.opacity = '0.85' }}
          onMouseLeave={function (e) { e.target.style.opacity = '1' }}
        >
          Send
        </button>
      </div>
    </div>
  )
}