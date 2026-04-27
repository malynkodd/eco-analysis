import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { adminAPI } from '../api'
import { Navigate } from 'react-router-dom'

const ROLE_LABELS = {
  analyst: { label: 'Аналітик', color: '#1d4ed8', bg: '#eff6ff' },
  manager: { label: 'Менеджер', color: '#276749', bg: '#e6ffed' },
  admin:   { label: 'Адмін',    color: '#744210', bg: '#fefcbf' },
}

export default function AdminPage() {
  const { user } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState({})
  const [success, setSuccess] = useState({})

  const isAdmin = user?.role === 'admin'

  useEffect(() => {
    if (!isAdmin) {
      setLoading(false)
      return
    }
    adminAPI.getUsers()
      .then(res => setUsers(res.data))
      .catch(() => setError('Не вдалося завантажити список користувачів'))
      .finally(() => setLoading(false))
  }, [isAdmin])

  if (!isAdmin) return <Navigate to="/" />

  const handleRoleChange = async (userId, newRole) => {
    setSaving(prev => ({ ...prev, [userId]: true }))
    setSuccess(prev => ({ ...prev, [userId]: false }))
    try {
      const res = await adminAPI.changeRole(userId, newRole)
      setUsers(prev => prev.map(u => u.id === userId ? res.data : u))
      setSuccess(prev => ({ ...prev, [userId]: true }))
      setTimeout(() => setSuccess(prev => ({ ...prev, [userId]: false })), 2000)
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Помилка зміни ролі')
      setTimeout(() => setError(''), 3000)
    } finally {
      setSaving(prev => ({ ...prev, [userId]: false }))
    }
  }

  return (
    <div style={{
      minHeight: 'calc(100vh - 64px)',
      background: 'linear-gradient(135deg, #f6f8fb 0%, #eff6ff 100%)',
      padding: '32px 24px',
    }}>
      <div style={{ maxWidth: '900px', margin: '0 auto' }}>

        {/* Header */}
        <div style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '8px' }}>
            <div style={{
              width: '48px', height: '48px',
              background: 'linear-gradient(135deg, #744210, #b7791f)',
              borderRadius: '14px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '22px',
              boxShadow: '0 4px 16px rgba(116,66,16,0.3)',
            }}>⚙️</div>
            <div>
              <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#1a202c', margin: 0 }}>
                Адміністративна панель
              </h1>
              <p style={{ color: '#718096', fontSize: '14px', margin: 0 }}>
                Управління користувачами та ролями
              </p>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="alert alert-error" style={{ marginBottom: '16px' }}>
            ⚠️ {error}
          </div>
        )}

        {/* Users Table */}
        <div style={{
          background: 'white',
          borderRadius: '16px',
          boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
          border: '1px solid #e2e8f0',
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '20px 24px',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#2d3748' }}>
              Користувачі системи
            </h2>
            {!loading && (
              <span style={{
                background: '#eff6ff', color: '#1d4ed8',
                padding: '4px 12px', borderRadius: '20px',
                fontSize: '13px', fontWeight: 600,
              }}>
                {users.length} користувачів
              </span>
            )}
          </div>

          {loading ? (
            <div style={{ padding: '48px', textAlign: 'center', color: '#718096' }}>
              <div className="spinner" style={{ width: '32px', height: '32px', margin: '0 auto 12px' }}></div>
              Завантаження...
            </div>
          ) : users.length === 0 ? (
            <div style={{ padding: '48px', textAlign: 'center', color: '#718096' }}>
              Користувачів не знайдено
            </div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f7fafc' }}>
                  {['ID', 'Логін', 'Email', 'Поточна роль', 'Змінити роль', ''].map(h => (
                    <th key={h} style={{
                      padding: '12px 16px',
                      textAlign: 'left',
                      fontSize: '12px',
                      fontWeight: 600,
                      color: '#718096',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                      borderBottom: '1px solid #e2e8f0',
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {users.map((u, idx) => {
                  const roleInfo = ROLE_LABELS[u.role] || ROLE_LABELS.analyst
                  const isCurrentUser = u.id === user.id
                  return (
                    <tr key={u.id} style={{
                      borderBottom: idx < users.length - 1 ? '1px solid #f6f8fb' : 'none',
                      background: isCurrentUser ? '#fffbeb' : 'white',
                      transition: 'background 0.15s',
                    }}>
                      <td style={{ padding: '14px 16px', color: '#a0aec0', fontSize: '13px' }}>
                        #{u.id}
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div style={{
                            width: '32px', height: '32px',
                            background: 'linear-gradient(135deg, #1d4ed8, #3b82f6)',
                            borderRadius: '50%',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            color: 'white', fontWeight: 700, fontSize: '13px',
                            flexShrink: 0,
                          }}>
                            {u.username[0].toUpperCase()}
                          </div>
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '14px', color: '#2d3748' }}>
                              {u.username}
                            </div>
                            {isCurrentUser && (
                              <div style={{ fontSize: '11px', color: '#b7791f' }}>Це ви</div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td style={{ padding: '14px 16px', color: '#4a5568', fontSize: '13px' }}>
                        {u.email}
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <span style={{
                          background: roleInfo.bg,
                          color: roleInfo.color,
                          padding: '4px 10px',
                          borderRadius: '20px',
                          fontSize: '12px',
                          fontWeight: 600,
                        }}>
                          {roleInfo.label}
                        </span>
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        {isCurrentUser ? (
                          <span style={{ fontSize: '12px', color: '#a0aec0' }}>
                            — не можна змінити свою роль
                          </span>
                        ) : (
                          <select
                            value={u.role}
                            onChange={e => handleRoleChange(u.id, e.target.value)}
                            disabled={saving[u.id]}
                            style={{
                              padding: '6px 10px',
                              borderRadius: '8px',
                              border: '1px solid #e2e8f0',
                              fontSize: '13px',
                              cursor: 'pointer',
                              background: 'white',
                              color: '#2d3748',
                            }}
                          >
                            <option value="analyst">Аналітик</option>
                            <option value="manager">Менеджер</option>
                            <option value="admin">Адмін</option>
                          </select>
                        )}
                      </td>
                      <td style={{ padding: '14px 16px', width: '80px' }}>
                        {saving[u.id] && (
                          <div className="spinner" style={{ width: '16px', height: '16px' }}></div>
                        )}
                        {success[u.id] && (
                          <span style={{ color: '#276749', fontSize: '18px' }}>✓</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Legend */}
        <div style={{
          marginTop: '24px',
          padding: '16px 20px',
          background: 'white',
          borderRadius: '12px',
          border: '1px solid #e2e8f0',
          display: 'flex',
          gap: '24px',
          flexWrap: 'wrap',
        }}>
          <div style={{ fontSize: '12px', color: '#718096', fontWeight: 600, alignSelf: 'center' }}>
            Ролі:
          </div>
          {Object.entries(ROLE_LABELS).map(([key, val]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
              <span style={{
                background: val.bg, color: val.color,
                padding: '2px 10px', borderRadius: '20px', fontSize: '12px', fontWeight: 600,
              }}>{val.label}</span>
              <span style={{ color: '#718096' }}>
                {key === 'analyst' && '— створення проєктів і аналіз'}
                {key === 'manager' && '— перегляд і затвердження проєктів'}
                {key === 'admin' && '— повний доступ + управління користувачами'}
              </span>
            </div>
          ))}
        </div>

      </div>
    </div>
  )
}
