import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authAPI } from '../api'

export default function RegisterPage() {
  // role is always 'analyst' — managers are assigned by admin only
  const [form, setForm] = useState({
    email: '', username: '', password: '', role: 'analyst'
  })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const validate = () => {
    const e = {}
    if (!form.email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/))
      e.email = 'Невірний формат email'
    if (form.username.length < 3)
      e.username = 'Логін мінімум 3 символи'
    if (form.password.length < 6)
      e.password = 'Пароль мінімум 6 символів'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleChange = e => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setServerError('')
    if (!validate()) return
    setLoading(true)
    try {
      await authAPI.register(form)
      setSuccess('Акаунт створено! Перенаправляємо...')
      setTimeout(() => navigate('/login'), 1500)
    } catch (err) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') {
        setServerError(detail)
      } else if (Array.isArray(detail)) {
        setServerError(detail.map(d => d.msg).join(', '))
      } else {
        setServerError('Помилка реєстрації. Спробуйте ще раз.')
      }
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
      background: 'linear-gradient(135deg, #f0f4f8 0%, #e8f0fe 100%)',
      padding: '20px',
    }}>
      <div style={{ width: '100%', maxWidth: '440px' }}>

        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            width: '64px', height: '64px',
            background: 'linear-gradient(135deg, #0f4c81, #1a6baf)',
            borderRadius: '20px',
            display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontSize: '28px',
            margin: '0 auto 16px',
            boxShadow: '0 8px 24px rgba(15,76,129,0.3)',
          }}>📝</div>
          <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#0f4c81' }}>
            Реєстрація
          </h1>
          <p style={{ color: '#718096', fontSize: '14px', marginTop: '6px' }}>
            Створіть акаунт для роботи з системою
          </p>
        </div>

        <div style={{
          background: 'white',
          borderRadius: '16px',
          padding: '32px',
          boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
          border: '1px solid #e2e8f0',
        }}>
          <form onSubmit={handleSubmit}>

            {/* Email */}
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                name="email"
                placeholder="your@email.com"
                value={form.email}
                onChange={handleChange}
                style={errors.email ? { borderColor: '#e17055' } : {}}
              />
              {errors.email && (
                <div style={{ color: '#e17055', fontSize: '12px', marginTop: '4px' }}>
                  ⚠ {errors.email}
                </div>
              )}
            </div>

            {/* Логін */}
            <div className="form-group">
              <label>Логін</label>
              <input
                type="text"
                name="username"
                placeholder="Мінімум 3 символи"
                value={form.username}
                onChange={handleChange}
                style={errors.username ? { borderColor: '#e17055' } : {}}
              />
              {errors.username && (
                <div style={{ color: '#e17055', fontSize: '12px', marginTop: '4px' }}>
                  ⚠ {errors.username}
                </div>
              )}
            </div>

            {/* Пароль */}
            <div className="form-group">
              <label>Пароль</label>
              <input
                type="password"
                name="password"
                placeholder="Мінімум 6 символів"
                value={form.password}
                onChange={handleChange}
                style={errors.password ? { borderColor: '#e17055' } : {}}
              />
              {errors.password && (
                <div style={{ color: '#e17055', fontSize: '12px', marginTop: '4px' }}>
                  ⚠ {errors.password}
                </div>
              )}
            </div>

            {/* Роль: тільки аналітик — менеджера призначає адмін */}
            <div className="form-group">
              <label>Роль</label>
              <div style={{
                padding: '10px 14px',
                background: '#f0f4f8',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontSize: '14px',
                color: '#374151',
              }}>
                👨‍💼 Аналітик — створення проєктів і запуск аналізу
              </div>
              <div style={{ fontSize: '12px', color: '#718096', marginTop: '6px' }}>
                💡 Роль менеджера присвоює тільки адміністратор системи
              </div>
            </div>

            {serverError && (
              <div className="alert alert-error">⚠️ {serverError}</div>
            )}
            {success && (
              <div className="alert alert-success">✓ {success}</div>
            )}

            <button
              type="submit"
              className="btn btn-primary btn-lg"
              style={{ width: '100%', justifyContent: 'center', marginTop: '8px' }}
              disabled={loading}
            >
              {loading
                ? <><div className="spinner" style={{ width: '16px', height: '16px' }}></div> Реєстрація...</>
                : '→ Зареєструватись'
              }
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
            Вже є акаунт?{' '}
            <Link to="/login" style={{ color: '#0f4c81', fontWeight: 600 }}>
              Увійти
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}