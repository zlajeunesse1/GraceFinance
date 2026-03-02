/**
 * NavBar — Shared navigation bar component.
 * Extracted from DashboardPage for reuse across pages.
 *
 * Props:
 *   navigate: function (from useNavigate)
 *   activePage: string ("dashboard" | "grace" | "index" | "profile" | "settings")
 *
 * Place at: src/components/NavBar.jsx
 */

import { useTheme } from "../context/ThemeContext"

var navItems = [
  { id: "dashboard", label: "Dashboard", icon: "\uD83C\uDFE0", path: "/dashboard" },
  { id: "grace", label: "Grace AI", icon: "\uD83D\uDC3E", path: "/grace" },
  { id: "index", label: "Index", icon: "\uD83D\uDCC8", path: "/index" },
  { id: "profile", label: "Profile", icon: "\uD83D\uDC64", path: "/profile" },
  { id: "settings", label: "Settings", icon: "\u2699\uFE0F", path: "/settings" },
]

export default function NavBar(props) {
  var ctx = useTheme()
  var t = ctx.theme
  var navigate = props.navigate
  var activePage = props.activePage || "dashboard"

  return (
    <nav style={{
      display: "flex", alignItems: "center", gap: 4,
      background: t.card, border: "1px solid " + t.border,
      borderRadius: 12, padding: "4px 6px",
    }}>
      {navItems.map(function (item) {
        var isActive = activePage === item.id
        return (
          <button
            key={item.id}
            onClick={function () { navigate(item.path) }}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 14px", borderRadius: 8, border: "none",
              background: isActive ? t.accent + "18" : "transparent",
              color: isActive ? t.accent : t.muted,
              fontSize: 13, fontWeight: isActive ? 600 : 500,
              cursor: "pointer", transition: "all 0.2s",
              whiteSpace: "nowrap",
            }}
          >
            <span style={{ fontSize: 14 }}>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        )
      })}
    </nav>
  )
}