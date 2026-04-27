import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { path: '/',              label: 'Проєкти',    icon: '▦' },
  { path: '/scenario',      label: 'Сценарії',   icon: '◇' },
  { path: '/multicriteria', label: 'AHP / TOPSIS', icon: '◈' },
]

const ROLE_BADGE = {
  admin:   { bg: 'rgba(124, 58, 237, 0.18)',  fg: '#ddd6fe', label: 'Admin'   },
  manager: { bg: 'rgba(14, 166, 116, 0.20)',  fg: '#a7f3d0', label: 'Manager' },
  analyst: { bg: 'rgba(255, 255, 255, 0.14)', fg: '#e0e7ff', label: 'Analyst' },
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const items = user?.role === 'admin'
    ? [...NAV_ITEMS, { path: '/admin', label: 'Адмін', icon: '⚙' }]
    : NAV_ITEMS

  const roleStyle = user ? (ROLE_BADGE[user.role] || ROLE_BADGE.analyst) : null

  return (
    <nav style={navStyle}>
      {/* Brand */}
      <Link to="/" style={brandStyle}>
        <div style={brandMarkStyle}>
          <span style={{ fontSize: 16, lineHeight: 1 }}>◐</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.1 }}>
          <span style={{ fontWeight: 700, fontSize: 15, letterSpacing: '-0.01em' }}>
            Eco Analysis
          </span>
          <span style={{ fontSize: 10, opacity: 0.65, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            Techno-Economic Platform
          </span>
        </div>
      </Link>

      {/* Primary nav */}
      {user && (
        <div style={navListStyle}>
          {items.map(({ path, label, icon }) => {
            const active = location.pathname === path
              || (path !== '/' && location.pathname.startsWith(path))
            return (
              <Link key={path} to={path} style={navLinkStyle(active)}>
                <span style={{ opacity: 0.85, fontSize: 13 }}>{icon}</span>
                <span>{label}</span>
                {active && <span style={navActiveBarStyle} />}
              </Link>
            )
          })}
        </div>
      )}

      {/* Right cluster */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {user ? (
          <>
            <div style={userPillStyle}>
              <div style={avatarStyle}>{user.username[0].toUpperCase()}</div>
              <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
                <span style={{ color: 'white', fontSize: 13, fontWeight: 600 }}>
                  {user.username}
                </span>
                <span style={{ ...rolePillStyle, background: roleStyle.bg, color: roleStyle.fg }}>
                  {roleStyle.label}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              style={logoutBtnStyle}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.18)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')}
            >
              Вийти
            </button>
          </>
        ) : (
          <div style={{ display: 'flex', gap: 8 }}>
            <Link to="/login" style={ghostLinkStyle}>Увійти</Link>
            <Link to="/register" style={primaryLinkStyle}>Реєстрація</Link>
          </div>
        )}
      </div>
    </nav>
  )
}

/* ─── Styles ──────────────────────────────────────────────────────── */

const navStyle = {
  background: '#0b1f47',                   // deep navy — analytics-platform feel
  backgroundImage: 'linear-gradient(180deg, #0d2350 0%, #0b1f47 100%)',
  borderBottom: '1px solid rgba(255,255,255,0.08)',
  padding: '0 22px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 24,
  height: 60,
  boxShadow: '0 1px 0 rgba(0,0,0,0.04)',
  position: 'sticky',
  top: 0,
  zIndex: 100,
}

const brandStyle = {
  color: 'white',
  textDecoration: 'none',
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  padding: '6px 4px',
}

const brandMarkStyle = {
  width: 30, height: 30,
  background: 'linear-gradient(135deg, #3b82f6 0%, #7c3aed 100%)',
  borderRadius: 8,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  color: 'white',
  boxShadow: '0 2px 8px rgba(59, 130, 246, 0.35)',
}

const navListStyle = {
  display: 'flex',
  gap: 2,
  flex: 1,
  justifyContent: 'center',
}

const navLinkStyle = (active) => ({
  position: 'relative',
  color: active ? 'white' : 'rgba(255,255,255,0.65)',
  textDecoration: 'none',
  padding: '8px 14px',
  borderRadius: 6,
  fontSize: 13,
  fontWeight: 500,
  letterSpacing: '-0.005em',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 8,
  background: active ? 'rgba(255,255,255,0.06)' : 'transparent',
  transition: 'background 0.15s ease, color 0.15s ease',
})

const navActiveBarStyle = {
  position: 'absolute',
  left: 12, right: 12, bottom: -10,
  height: 2,
  background: '#60a5fa',
  borderRadius: 2,
}

const userPillStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  background: 'rgba(255,255,255,0.06)',
  padding: '5px 12px 5px 5px',
  borderRadius: 999,
  border: '1px solid rgba(255,255,255,0.10)',
}

const avatarStyle = {
  width: 28, height: 28,
  background: 'linear-gradient(135deg, #3b82f6 0%, #7c3aed 100%)',
  borderRadius: '50%',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: 12.5,
  fontWeight: 700,
  color: 'white',
}

const rolePillStyle = {
  fontSize: 9.5,
  fontWeight: 700,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  padding: '1px 6px',
  borderRadius: 999,
  width: 'fit-content',
  marginTop: 2,
}

const logoutBtnStyle = {
  background: 'rgba(255,255,255,0.06)',
  border: '1px solid rgba(255,255,255,0.14)',
  color: 'white',
  padding: '7px 14px',
  borderRadius: 8,
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 500,
  fontFamily: 'inherit',
  transition: 'background 0.15s ease',
}

const ghostLinkStyle = {
  color: 'rgba(255,255,255,0.85)',
  textDecoration: 'none',
  padding: '7px 14px',
  borderRadius: 8,
  fontSize: 13,
  fontWeight: 500,
}

const primaryLinkStyle = {
  background: 'rgba(255,255,255,0.16)',
  color: 'white',
  textDecoration: 'none',
  padding: '7px 14px',
  borderRadius: 8,
  fontSize: 13,
  fontWeight: 500,
  border: '1px solid rgba(255,255,255,0.24)',
}
