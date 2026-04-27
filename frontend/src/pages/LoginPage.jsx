import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authAPI } from '../api'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authAPI.login(username, password)
      login(res.data.access_token, {
        username: res.data.username,
        role: res.data.role
      })
      navigate('/')
    } catch {
      setError('Невірний логін або пароль')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: 'calc(100vh - 64px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #f6f8fb 0%, #eff6ff 100%)',
      padding: '20px',
    }}>
      <div style={{ width: '100%', maxWidth: '420px' }}>

        {/* Лого блок */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            width: '64px', height: '64px',
            background: 'linear-gradient(135deg, #1d4ed8, #3b82f6)',
            borderRadius: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '28px',
            margin: '0 auto 16px',
            boxShadow: '0 8px 24px rgba(15,76,129,0.3)',
          }}>🌿</div>
          <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#1d4ed8' }}>
            Вхід в систему
          </h1>
          <p style={{ color: '#718096', fontSize: '14px', marginTop: '6px' }}>
            Eco Analysis — Техніко-економічний аналіз
          </p>
        </div>

        {/* Картка */}
        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '32px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
          border: '1px solid #e2e8f0',
        }}>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Логін</label>
              <input
                type="text"
                placeholder="Введіть логін"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Пароль</label>
              <input
                type="password"
                placeholder="Введіть пароль"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <div className="alert alert-error">⚠️ {error}</div>
            )}

            <button
              type="submit"
              className="btn btn-primary btn-lg"
              style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }}
              disabled={loading}
            >
              {loading ? (
                <><div className="spinner" style={{ width: '16px', height: '16px' }}></div> Завантаження...</>
              ) : '→ Увійти'}
            </button>
          </form>

          <div style={{
            textAlign: 'center',
            marginTop: '24px',
            paddingTop: '24px',
            borderTop: '1px solid #e2e8f0',
            fontSize: '13px',
            color: '#718096',
          }}>
            Немає акаунту?{' '}
            <Link to="/register" style={{ color: '#1d4ed8', fontWeight: 600 }}>
              Зареєструватись
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}