import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { projectAPI } from '../api'
import { useAuth } from '../context/AuthContext'

const TYPE_LABELS = {
  insulation: { icon: '🏠', label: 'Утеплення', color: '#dbeafe' },
  equipment:  { icon: '⚙️', label: 'Обладнання', color: '#fce7f3' },
  treatment:  { icon: '🌊', label: 'Очисні', color: '#d1fae5' },
  renewable:  { icon: '☀️', label: 'ВДЕ', color: '#fef3c7' },
}

const STATUS_CONFIG = {
  pending:  { label: 'Очікує розгляду', color: '#92400e', bg: '#fef3c7' },
  approved: { label: 'Затверджено',      color: '#065f46', bg: '#d1fae5' },
  rejected: { label: 'Відхилено',        color: '#991b1b', bg: '#fee2e2' },
}

function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-text" />
      <div className="skeleton skeleton-text-short" />
      <div style={{ display: 'flex', gap: '6px', margin: '12px 0' }}>
        <div className="skeleton skeleton-badge" />
        <div className="skeleton skeleton-badge" />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px' }}>
        <div className="skeleton skeleton-badge" />
        <div className="skeleton skeleton-badge" />
      </div>
    </div>
  )
}

// ─── Модальне вікно для коментаря при відхиленні ──────
function RejectModal({ project, onConfirm, onCancel }) {
  const [comment, setComment] = useState('')
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '20px',
    }}>
      <div style={{
        background: 'white', borderRadius: '16px',
        padding: '28px', maxWidth: '460px', width: '100%',
        boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
      }}>
        <h3 style={{ color: '#991b1b', marginBottom: '8px', fontSize: '18px' }}>
          ❌ Відхилити проєкт
        </h3>
        <p style={{ color: '#718096', fontSize: '14px', marginBottom: '20px' }}>
          <strong>«{project.name}»</strong> — аналітику{' '}
          <strong>{project.owner_username}</strong>
        </p>
        <div className="form-group">
          <label>Коментар (необов'язково)</label>
          <textarea
            value={comment}
            onChange={e => setComment(e.target.value)}
            placeholder="Вкажіть причину відхилення або рекомендації..."
            rows={3}
            style={{ resize: 'vertical' }}
            autoFocus
          />
        </div>
        <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
          <button
            className="btn btn-danger"
            style={{ flex: 1 }}
            onClick={() => onConfirm(comment)}
          >
            ❌ Відхилити
          </button>
          <button
            className="btn btn-outline"
            style={{ flex: 1 }}
            onClick={onCancel}
          >
            Скасувати
          </button>
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [projects, setProjects]             = useState([])
  const [showForm, setShowForm]             = useState(false)
  const [form, setForm]                     = useState({ name: '', description: '' })
  const [loading, setLoading]               = useState(true)
  const [error, setError]                   = useState('')
  const [actionLoading, setActionLoading]   = useState({})
  const [search, setSearch]                 = useState('')
  const [filterStatus, setFilterStatus]     = useState('all')
  const [rejectTarget, setRejectTarget]     = useState(null)
  const { user } = useAuth()
  const navigate = useNavigate()

  const canManage = user?.role === 'manager' || user?.role === 'admin'
  const isAnalyst = user?.role === 'analyst'

  useEffect(() => { loadProjects() }, [])

  const loadProjects = async () => {
    try {
      const res = await projectAPI.getAll()
      setProjects(res.data)
    } catch {
      setError('Помилка завантаження')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return
    try {
      const res = await projectAPI.create(form)
      setForm({ name: '', description: '' })
      setShowForm(false)
      navigate(`/projects/${res.data.id}`)
    } catch {
      setError('Помилка створення проєкту')
    }
  }

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!confirm('Видалити проєкт з усіма заходами?')) return
    try {
      await projectAPI.delete(id)
      setProjects(prev => prev.filter(p => p.id !== id))
    } catch {
      setError('Помилка видалення')
    }
  }

  const handleApprove = async (id, e) => {
    e.stopPropagation()
    setActionLoading(prev => ({ ...prev, [id]: true }))
    try {
      const res = await projectAPI.approve(id)
      setProjects(prev => prev.map(p => p.id === id ? res.data : p))
    } catch {
      setError('Помилка затвердження')
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: false }))
    }
  }

  const openRejectModal = (project, e) => {
    e.stopPropagation()
    setRejectTarget(project)
  }

  const handleRejectConfirm = async (comment) => {
    const id = rejectTarget.id
    setRejectTarget(null)
    setActionLoading(prev => ({ ...prev, [id]: true }))
    try {
      const res = await projectAPI.reject(id, comment)
      setProjects(prev => prev.map(p => p.id === id ? res.data : p))
    } catch {
      setError('Помилка відхилення')
    } finally {
      setActionLoading(prev => ({ ...prev, [id]: false }))
    }
  }

  // ─── Фільтрація та пошук ──────────────────────────
  const filteredProjects = useMemo(() => {
    return projects.filter(p => {
      const matchSearch = !search.trim() ||
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        (p.description || '').toLowerCase().includes(search.toLowerCase()) ||
        (canManage && p.owner_username.toLowerCase().includes(search.toLowerCase()))
      const matchStatus = filterStatus === 'all' || p.status === filterStatus
      return matchSearch && matchStatus
    })
  }, [projects, search, filterStatus, canManage])

  // ─── Групування по власнику (для менеджера/адміна) ──
  const grouped = useMemo(() => {
    if (!canManage) return null
    const map = {}
    for (const p of filteredProjects) {
      if (!map[p.owner_username]) map[p.owner_username] = []
      map[p.owner_username].push(p)
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b))
  }, [filteredProjects, canManage])

  const renderProjectCard = (p) => {
    const statusCfg = STATUS_CONFIG[p.status] || STATUS_CONFIG.pending
    const isLoading = actionLoading[p.id]

    return (
      <div
        key={p.id}
        className="card"
        style={{ cursor: 'pointer', position: 'relative', paddingBottom: '16px' }}
        onClick={() => navigate(`/projects/${p.id}`)}
      >
        {/* Кнопка видалення (тільки власник або адмін, не менеджер) */}
        {(isAnalyst || user?.role === 'admin') && (
          <button
            className="btn btn-danger btn-sm"
            style={{ position: 'absolute', top: '16px', right: '16px', padding: '4px 10px' }}
            onClick={e => handleDelete(p.id, e)}
            aria-label={`Видалити проєкт ${p.name}`}
            title="Видалити проєкт"
          >🗑</button>
        )}

        {/* Іконка */}
        <div style={{
          width: '44px', height: '44px',
          background: 'linear-gradient(135deg, #dbeafe, #bfdbfe)',
          borderRadius: '12px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '20px', marginBottom: '12px',
        }}>📁</div>

        <h3 style={{
          fontSize: '15px', fontWeight: 600, color: '#1d4ed8',
          marginBottom: '6px',
          paddingRight: (isAnalyst || user?.role === 'admin') ? '80px' : '8px',
        }}>
          {p.name}
        </h3>

        {/* Автор (видно менеджеру/адміну) */}
        {canManage && (
          <p style={{ fontSize: '11px', color: '#a0aec0', marginBottom: '4px' }}>
            👤 {p.owner_username}
          </p>
        )}

        <p style={{ color: '#718096', fontSize: '12px', marginBottom: '14px' }}>
          {p.description || 'Без опису'}
        </p>

        {/* Коментар менеджера */}
        {p.manager_comment && (
          <div style={{
            background: p.status === 'rejected' ? '#fff1f2' : '#f0fdf4',
            border: `1px solid ${p.status === 'rejected' ? '#fecdd3' : '#bbf7d0'}`,
            borderRadius: '8px',
            padding: '8px 12px',
            marginBottom: '12px',
            fontSize: '12px',
            color: p.status === 'rejected' ? '#991b1b' : '#065f46',
          }}>
            💬 <strong>Коментар:</strong> {p.manager_comment}
          </div>
        )}

        {/* Заходи */}
        <div style={{ marginBottom: '14px' }}>
          {!p.measures?.length ? (
            <span style={{ fontSize: '12px', color: '#a0aec0' }}>Заходів ще немає</span>
          ) : (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {p.measures.map(m => {
                const t = TYPE_LABELS[m.measure_type] || { icon: '📋', color: '#f3f4f6' }
                return (
                  <span key={m.id} style={{
                    fontSize: '11px', padding: '2px 8px',
                    background: t.color, borderRadius: '10px', color: '#374151',
                  }}>
                    {t.icon} {m.name}
                  </span>
                )
              })}
            </div>
          )}
        </div>

        {/* Нижня частина */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          paddingTop: '12px', borderTop: '1px solid #f6f8fb',
        }}>
          <span className="badge badge-blue">
            {p.measures?.length || 0} заходів
          </span>
          <span style={{
            fontSize: '11px', fontWeight: 600, padding: '3px 10px',
            borderRadius: '10px',
            color: statusCfg.color, background: statusCfg.bg,
          }}>
            {statusCfg.label}
          </span>
        </div>

        {/* Кнопки затвердження (менеджер/адмін) */}
        {canManage && (
          <div
            style={{
              display: 'flex', gap: '8px', marginTop: '12px',
              paddingTop: '10px', borderTop: '1px solid #f6f8fb',
            }}
            onClick={e => e.stopPropagation()}
          >
            <button
              className="btn btn-success btn-sm"
              style={{ flex: 1, opacity: p.status === 'approved' ? 0.5 : 1 }}
              disabled={isLoading || p.status === 'approved'}
              onClick={e => handleApprove(p.id, e)}
              aria-label={`Затвердити проєкт ${p.name}`}
            >
              {isLoading ? '...' : '✅ Затвердити'}
            </button>
            <button
              className="btn btn-danger btn-sm"
              style={{ flex: 1, opacity: p.status === 'rejected' ? 0.5 : 1 }}
              disabled={isLoading || p.status === 'rejected'}
              onClick={e => openRejectModal(p, e)}
              aria-label={`Відхилити проєкт ${p.name}`}
            >
              {isLoading ? '...' : '❌ Відхилити'}
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="container" style={{ paddingTop: '32px', paddingBottom: '40px' }}>

      {/* Модальне вікно відхилення */}
      {rejectTarget && (
        <RejectModal
          project={rejectTarget}
          onConfirm={handleRejectConfirm}
          onCancel={() => setRejectTarget(null)}
        />
      )}

      {/* Заголовок */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: '28px',
      }}>
        <div>
          <h1 style={{ fontSize: '26px', fontWeight: 700, color: '#1d4ed8' }}>
            {canManage ? 'Усі проєкти аналітиків' : 'Мої проєкти'}
          </h1>
          <p style={{ color: '#718096', marginTop: '4px' }}>
            Вітаємо, <strong>{user?.username}</strong>!{' '}
            {isAnalyst
              ? 'Оберіть проєкт або створіть новий.'
              : 'Переглядайте та затверджуйте проєкти аналітиків.'}
          </p>
        </div>
        {isAnalyst && (
          <button
            className="btn btn-primary btn-lg"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? '✕ Скасувати' : '+ Новий проєкт'}
          </button>
        )}
      </div>

      {/* Статистика */}
      <div className="grid-4" style={{ marginBottom: '28px' }}>
        <div className="stat-card">
          <div className="stat-label">Всього проєктів</div>
          <div className="stat-value">{projects.length}</div>
        </div>
        <div className="stat-card green">
          <div className="stat-label">Затверджено</div>
          <div className="stat-value">
            {projects.filter(p => p.status === 'approved').length}
          </div>
        </div>
        <div className="stat-card orange">
          <div className="stat-label">Очікують розгляду</div>
          <div className="stat-value">
            {projects.filter(p => p.status === 'pending').length}
          </div>
        </div>
        <div className="stat-card purple">
          <div className="stat-label">Роль</div>
          <div className="stat-value" style={{ fontSize: '14px', textTransform: 'capitalize' }}>
            {user?.role}
          </div>
        </div>
      </div>

      {/* Форма (тільки для аналітика) */}
      {showForm && isAnalyst && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <span className="card-title">📁 Новий проєкт</span>
          </div>
          <form onSubmit={handleCreate}>
            <div className="grid-2">
              <div className="form-group">
                <label>Назва проєкту *</label>
                <input
                  type="text"
                  placeholder="Наприклад: Утеплення школи №5"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  required
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Опис</label>
                <input
                  type="text"
                  placeholder="Короткий опис"
                  value={form.description}
                  onChange={e => setForm({ ...form, description: e.target.value })}
                />
              </div>
            </div>
            <button type="submit" className="btn btn-success">
              ✓ Створити та відкрити
            </button>
          </form>
        </div>
      )}

      {/* Підказка для менеджера */}
      {canManage && (
        <div className="alert alert-info" style={{ marginBottom: '20px' }}>
          👔 Ви в ролі <strong>{user.role}</strong>. Ви бачите всі проєкти аналітиків і можете їх затверджувати або відхиляти.
        </div>
      )}

      {error && (
        <div className="alert alert-error" style={{ cursor: 'pointer' }} onClick={() => setError('')}>
          ⚠️ {error} <span style={{ marginLeft: 'auto', opacity: 0.6 }}>✕</span>
        </div>
      )}

      {/* ─── Пошук і фільтр ─────────────────────────── */}
      {!loading && projects.length > 0 && (
        <div className="search-bar">
          <input
            type="search"
            placeholder={canManage
              ? '🔍 Пошук за назвою, описом або автором...'
              : '🔍 Пошук за назвою або описом...'}
            value={search}
            onChange={e => setSearch(e.target.value)}
            aria-label="Пошук проєктів"
          />
          <select
            value={filterStatus}
            onChange={e => setFilterStatus(e.target.value)}
            aria-label="Фільтр за статусом"
          >
            <option value="all">Всі статуси</option>
            <option value="pending">Очікує розгляду</option>
            <option value="approved">Затверджено</option>
            <option value="rejected">Відхилено</option>
          </select>
          {(search || filterStatus !== 'all') && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => { setSearch(''); setFilterStatus('all') }}
            >
              ✕ Скинути
            </button>
          )}
          <span style={{ color: '#718096', fontSize: '12px', marginLeft: 'auto' }}>
            Показано: {filteredProjects.length} з {projects.length}
          </span>
        </div>
      )}

      {/* ─── Проєкти ────────────────────────────────── */}
      {loading ? (
        <div className="grid-3">
          {[1, 2, 3].map(i => <SkeletonCard key={i} />)}
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">{search || filterStatus !== 'all' ? '🔍' : '📂'}</div>
            <h3>{search || filterStatus !== 'all' ? 'Нічого не знайдено' : 'Проєктів ще немає'}</h3>
            <p>
              {search || filterStatus !== 'all'
                ? 'Спробуйте змінити параметри пошуку'
                : isAnalyst
                  ? 'Натисніть "+ Новий проєкт" щоб почати аналіз'
                  : 'Аналітики ще не створили жодного проєкту'}
            </p>
          </div>
        </div>
      ) : canManage && grouped ? (
        // Менеджер/адмін — проєкти згруповані по аналітику
        grouped.map(([owner, ownerProjects]) => (
          <div key={owner} style={{ marginBottom: '32px' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: '10px',
              marginBottom: '16px',
            }}>
              <div style={{
                width: '32px', height: '32px',
                background: 'linear-gradient(135deg, #1d4ed8, #3b82f6)',
                borderRadius: '50%',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: 'white', fontWeight: 700, fontSize: '14px',
              }}>
                {owner[0].toUpperCase()}
              </div>
              <div>
                <div style={{ fontWeight: 600, color: '#1d4ed8', fontSize: '15px' }}>
                  👤 {owner}
                </div>
                <div style={{ fontSize: '12px', color: '#718096' }}>
                  {ownerProjects.length} проєкт{ownerProjects.length === 1 ? '' : 'ів'} ·{' '}
                  {ownerProjects.filter(p => p.status === 'pending').length} очікують розгляду
                </div>
              </div>
            </div>
            <div className="grid-3">
              {ownerProjects.map(renderProjectCard)}
            </div>
          </div>
        ))
      ) : (
        // Аналітик — власні проєкти
        <div className="grid-3">
          {filteredProjects.map(renderProjectCard)}
        </div>
      )}
    </div>
  )
}
