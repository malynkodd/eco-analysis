import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav style={{
      background: 'linear-gradient(135deg, #0f4c81 0%, #1a6baf 100%)',
      padding: '0 24px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      height: '64px',
      boxShadow: '0 2px 16px rgba(15,76,129,0.25)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Лого */}
      <Link to="/" style={{
        color: 'white',
        textDecoration: 'none',
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
      }}>
        <div style={{
          width: '34px', height: '34px',
          background: 'rgba(255,255,255,0.2)',
          borderRadius: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '18px',
        }}>🌿</div>
        <div>
          <div style={{ fontWeight: 700, fontSize: '16px', letterSpacing: '-0.3px' }}>
            Eco Analysis
          </div>
          <div style={{ fontSize: '10px', opacity: 0.7, letterSpacing: '0.5px' }}>
            TECHNICO-ECONOMIC SYSTEM
          </div>
        </div>
      </Link>

        {user && (
  <div style={{ display: 'flex', gap: '4px' }}>
    {[
            { path: '/', label: '📁 Проєкти' },
            { path: '/scenario', label: '🔬 Сценарії' },
            { path: '/multicriteria', label: '🎯 AHP/TOPSIS' },
            ...(user?.role === 'admin' ? [{ path: '/admin', label: '⚙️ Адмін' }] : []),
    ].map(({ path, label }) => (
      <Link
        key={path}
        to={path}
        style={{
          color: 'rgba(255,255,255,0.85)',
          textDecoration: 'none',
          padding: '6px 14px',
          borderRadius: '8px',
          fontSize: '13px',
          fontWeight: 500,
          background: window.location.pathname === path
            ? 'rgba(255,255,255,0.2)' : 'transparent',
          transition: 'background 0.15s',
        }}
      >
        {label}
      </Link>
    ))}
  </div>
)}


      {/* Правий блок */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {user ? (
          <>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              background: 'rgba(255,255,255,0.12)',
              padding: '6px 14px',
              borderRadius: '20px',
              border: '1px solid rgba(255,255,255,0.2)',
            }}>
              <div style={{
                width: '28px', height: '28px',
                background: 'rgba(255,255,255,0.25)',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '13px',
                fontWeight: 700,
                color: 'white',
              }}>
                {user.username[0].toUpperCase()}
              </div>
              <div>
                <div style={{ color: 'white', fontSize: '13px', fontWeight: 600 }}>
                  {user.username}
                </div>
                <div style={{
                  fontSize: '10px',
                  color: 'rgba(255,255,255,0.7)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  {user.role}
                </div>
              </div>
            </div>
            <button
              onClick={handleLogout}
              style={{
                background: 'rgba(255,255,255,0.15)',
                border: '1px solid rgba(255,255,255,0.3)',
                color: 'white',
                padding: '8px 16px',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 500,
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,0.25)'}
              onMouseLeave={e => e.target.style.background = 'rgba(255,255,255,0.15)'}
            >
              Вийти
            </button>
          </>
        ) : (
          <div style={{ display: 'flex', gap: '8px' }}>
            <Link to="/login" style={{
              color: 'rgba(255,255,255,0.9)',
              textDecoration: 'none',
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 500,
            }}>Увійти</Link>
            <Link to="/register" style={{
              background: 'rgba(255,255,255,0.2)',
              color: 'white',
              textDecoration: 'none',
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 500,
              border: '1px solid rgba(255,255,255,0.3)',
            }}>Реєстрація</Link>
          </div>
        )}
      </div>
    </nav>
  )
}