import { useTheme } from '../context/ThemeContext'

export default function ModeToggle() {
  var ctx = useTheme()
  var theme = ctx.theme
  var themeKey = ctx.themeKey
  var setTheme = ctx.setTheme

  return (
    <button
      onClick={function () { setTheme(themeKey === 'dark' ? 'light' : 'dark') }}
      aria-label="Toggle theme"
      className="flex items-center justify-center cursor-pointer transition-all duration-300"
      style={{
        width: 42,
        height: 42,
        borderRadius: 12,
        border: '1px solid ' + theme.border,
        background: theme.card,
        color: theme.muted,
        fontSize: 18,
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      }}
    >
      {themeKey === 'dark' ? '\u2600' : '\u263E'}
    </button>
  )
}
