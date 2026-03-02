import { useTheme } from '../context/ThemeContext'
import Logo from './Logo'
import ModeToggle from './ModeToggle'

export default function AuthLayout(props) {
  var ctx = useTheme()
  var theme = ctx.theme

  return (
    <div
      className="min-h-screen w-full flex flex-col items-center justify-center px-5 py-10 relative overflow-hidden transition-all duration-300"
      style={{
        background: theme.dark,
      }}
    >
      <div style={{ position: 'fixed', top: 18, right: 18, zIndex: 50 }}>
        <ModeToggle />
      </div>

      <div className="relative z-10 flex flex-col items-center w-full max-w-[420px] animate-[fadeInUp_0.6s_ease-out]">
        <div className="mb-8">
          <Logo />
        </div>

        {props.children}

        <p className="mt-7 text-xs opacity-60 tracking-wide text-center" style={{ color: theme.muted }}>
          Smarter Finance is Right Around the Corner
        </p>
      </div>
    </div>
  )
}
