import { createContext, useContext, useState, useEffect } from 'react'

var themes = {
  dark: {
    name: 'Dark',
    isDark: true,
    dark: '#0B0F1A',
    card: '#111827',
    accent: '#58A6FF',
    accentHover: '#4090EE',
    input: '#1E293B',
    border: '#334155',
    text: '#F1F5F9',
    muted: '#94A3B8',
    error: '#F87171',
    paw: '#F1F5F9',
    logoSub: '#94A3B8',
    socialBg: 'rgba(255,255,255,0.04)',
    socialHover: 'rgba(255,255,255,0.08)',
    socialBorder: 'rgba(255,255,255,0.07)',
    socialText: '#CBD5E1',
  },
  wealth: {
    name: 'Wealth',
    isDark: true,
    dark: '#0B0F1A',
    card: '#111827',
    accent: '#22D3A7',
    accentHover: '#1AB892',
    input: '#1E293B',
    border: '#334155',
    text: '#F1F5F9',
    muted: '#94A3B8',
    error: '#F87171',
    paw: '#F1F5F9',
    logoSub: '#94A3B8',
    socialBg: 'rgba(255,255,255,0.04)',
    socialHover: 'rgba(255,255,255,0.08)',
    socialBorder: 'rgba(255,255,255,0.07)',
    socialText: '#CBD5E1',
  },
  aggressive: {
    name: 'Aggressive',
    isDark: true,
    dark: '#0D0A0A',
    card: '#150F0F',
    accent: '#F85149',
    accentHover: '#E03E3B',
    input: '#1E1414',
    border: '#3D2020',
    text: '#F1F5F9',
    muted: '#94A3B8',
    error: '#F87171',
    paw: '#F1F5F9',
    logoSub: '#94A3B8',
    socialBg: 'rgba(255,255,255,0.04)',
    socialHover: 'rgba(255,255,255,0.08)',
    socialBorder: 'rgba(255,255,255,0.07)',
    socialText: '#CBD5E1',
  },
  calm: {
    name: 'Calm',
    isDark: true,
    dark: '#0D0B14',
    card: '#13111E',
    accent: '#BC8CFF',
    accentHover: '#A87AEE',
    input: '#1A1728',
    border: '#2E2A45',
    text: '#F1F5F9',
    muted: '#94A3B8',
    error: '#F87171',
    paw: '#F1F5F9',
    logoSub: '#94A3B8',
    socialBg: 'rgba(255,255,255,0.04)',
    socialHover: 'rgba(255,255,255,0.08)',
    socialBorder: 'rgba(255,255,255,0.07)',
    socialText: '#CBD5E1',
  },
}

var ThemeContext = createContext()

export function ThemeProvider(props) {
  var saved = localStorage.getItem('grace-theme') || 'wealth'
  var initial = themes[saved] ? saved : 'wealth'
  var state = useState(initial)
  var themeKey = state[0]
  var setThemeKey = state[1]
  var theme = themes[themeKey]

  useEffect(function () {
    localStorage.setItem('grace-theme', themeKey)
    var root = document.documentElement
    root.style.setProperty('--grace-dark', theme.dark)
    root.style.setProperty('--grace-card', theme.card)
    root.style.setProperty('--grace-accent', theme.accent)
    root.style.setProperty('--grace-accent-hover', theme.accentHover)
    root.style.setProperty('--grace-input', theme.input)
    root.style.setProperty('--grace-border', theme.border)
    root.style.setProperty('--grace-text', theme.text)
    root.style.setProperty('--grace-muted', theme.muted)
    root.style.setProperty('--grace-error', theme.error)
  }, [themeKey, theme])

  var value = {
    theme: theme,
    themeKey: themeKey,
    currentTheme: themeKey,   // alias so SettingsPage works with either
    setTheme: setThemeKey,
    themes: themes,
  }

  return (
    <ThemeContext.Provider value={value}>
      {props.children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}