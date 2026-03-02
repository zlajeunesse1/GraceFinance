import { useTheme } from '../context/ThemeContext'

export function PawIcon(props) {
  var size = props.size || 44
  var color = props.color
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <path
        d="M50 90c-1.5 0-3-.7-3.8-2C41 80 32 72 28.5 67.5c-6-7.8-8-14-6.5-20 1.8-7.5 8-12.5 16-12.5 5 0 9 2 11.5 5 2.5-3 6.5-5 11.5-5 8 0 14.2 5 16 12.5 1.5 6-.5 12.2-6.5 20C67 72 58.5 80 53.3 88c-.8 1.3-2.3 2-3.8 2h1z"
        fill={color} opacity="0.9"
      />
      <path
        d="M50 83c-.5 0-1-.3-1.3-.7-1.5-2.5-3.2-4.5-4.2-5.5.7.2 1.5.7 2.5 1.5.8.7 1.7 1.5 2.4 2.5.4-.8 1.2-1.6 2.4-2.5 1-.8 1.8-1.3 2.5-1.5-1 1-2.7 3-4.2 5.5-.2.4-.6.7-1.1.7z"
        fill={color === '#F1F5F9' ? '#0B0F1A' : '#F5F7FA'}
        opacity="0.5"
      />
      <ellipse cx="24" cy="30" rx="9" ry="11.5" transform="rotate(-15 24 30)" fill={color} opacity="0.85" />
      <ellipse cx="39" cy="22" rx="8" ry="10.5" transform="rotate(-5 39 22)" fill={color} opacity="0.85" />
      <ellipse cx="61" cy="22" rx="8" ry="10.5" transform="rotate(5 61 22)" fill={color} opacity="0.85" />
      <ellipse cx="76" cy="30" rx="9" ry="11.5" transform="rotate(15 76 30)" fill={color} opacity="0.85" />
    </svg>
  )
}

export default function Logo(props) {
  var size = props.size || 44
  var ctx = useTheme()
  var theme = ctx.theme
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <PawIcon size={size} color={theme.paw} />
      <span style={{ fontSize: size * 0.59, fontWeight: 700, color: theme.text, letterSpacing: -0.5 }}>
        Grace<span style={{ fontWeight: 400, color: theme.logoSub }}>Finance</span>
      </span>
    </div>
  )
}
