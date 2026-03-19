import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { projectAPI } from '../api'

const MEASURE_TYPES = [
  { value: 'insulation', label: '🏠 Утеплення' },
  { value: 'equipment',  label: '⚙️ Заміна обладнання' },
  { value: 'treatment',  label: '🌊 Очисні споруди' },
  { value: 'renewable',  label: '☀️ Відновлювана енергетика' },
]

// Шаблони типових значень для кожного типу заходу
const TEMPLATES = {
  insulation: {
    name: 'Утеплення фасаду',
    initial_investment: '500000',
    operational_cost: '3000',
    expected_savings: '75000',
    lifetime_years: '25',
    emission_reduction: '40',
  },
  equipment: {
    name: 'Заміна котла на енергоефективний',
    initial_investment: '300000',
    operational_cost: '10000',
    expected_savings: '60000',
    lifetime_years: '15',
    emission_reduction: '30',
  },
  treatment: {
    name: 'Модернізація очисних споруд',
    initial_investment: '1200000',
    operational_cost: '25000',
    expected_savings: '120000',
    lifetime_years: '20',
    emission_reduction: '50',
  },
  renewable: {
    name: 'Сонячна електростанція',
    initial_investment: '800000',
    operational_cost: '5000',
    expected_savings: '100000',
    lifetime_years: '25',
    emission_reduction: '80',
  },
}

const emptyForm = {
  name: '',
  measure_type: 'insulation',
  initial_investment: '',
  operational_cost: '',
  expected_savings: '',
  lifetime_years: '',
  emission_reduction: '',
}

export default function ProjectPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject]   = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm]         = useState(emptyForm)
  const [loading, setLoading]   = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError]       = useState('')

  useEffect(() => { loadProject() }, [id])

  const loadProject = async () => {
    try {
      const res = await projectAPI.getOne(id)
      setProject(res.data)
    } catch {
      setError('Помилка завантаження проєкту')
    } finally {
      setLoading(false)
    }
  }

  const applyTemplate = (type) => {
    const tmpl = TEMPLATES[type] || {}
    setForm(prev => ({ ...prev, ...tmpl, measure_type: type }))
  }

  const handleTypeChange = (type) => {
    setForm(prev => ({ ...prev, measure_type: type }))
  }

  const handleAddMeasure = async (e) => {
    e.preventDefault()
    setError('')

    const investment = parseFloat(form.initial_investment)
    const opCost = parseFloat(form.operational_cost)
    const savings = parseFloat(form.expected_savings)
    const lifetime = parseInt(form.lifetime_years)
    const emission = parseFloat(form.emission_reduction)

    if (isNaN(investment) || investment < 0) { setError('Введіть коректні початкові інвестиції'); return }
    if (isNaN(opCost)     || opCost < 0)     { setError('Введіть коректні операційні витрати'); return }
    if (isNaN(savings)    || savings <= 0)    { setError('Економія повинна бути більше 0'); return }
    if (isNaN(lifetime)   || lifetime < 1 || lifetime > 50) { setError('Термін: від 1 до 50 років'); return }
    if (isNaN(emission)   || emission < 0)    { setError('Зменшення викидів не може бути від\'ємним'); return }

    setSubmitting(true)
    try {
      await projectAPI.addMeasure(id, {
        ...form,
        initial_investment: investment,
        operational_cost:   opCost,
        expected_savings:   savings,
        lifetime_years:     lifetime,
        emission_reduction: emission,
      })
      setForm(emptyForm)
      setShowForm(false)
      loadProject()
    } catch (err) {
      setError(err.response?.data?.detail || 'Помилка додавання заходу')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteMeasure = async (measureId, measureName) => {
    if (!confirm(`Видалити захід "${measureName}"?`)) return
    setDeletingId(measureId)
    try {
      await projectAPI.deleteMeasure(id, measureId)
      loadProject()
    } catch {
      setError('Помилка видалення заходу')
    } finally {
      setDeletingId(null)
    }
  }

  if (loading) return (
    <div className="container" style={{ paddingTop: '32px' }}>
      <div className="skeleton skeleton-title" style={{ width: '40%', marginBottom: '24px' }} />
      <div className="skeleton-card">
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-text" />
        <div className="skeleton skeleton-text" />
        <div className="skeleton skeleton-text-short" />
      </div>
    </div>
  )

  if (!project) return (
    <div className="container" style={{ paddingTop: '60px', textAlign: 'center', color: '#c0392b' }}>
      Проєкт не знайдено
    </div>
  )

  return (
    <div className="container" style={{ paddingTop: '32px', paddingBottom: '40px' }}>

      {/* Хлібні крихти */}
      <div className="breadcrumb">
        <a onClick={() => navigate('/')}>Проєкти</a>
        <span className="breadcrumb-sep">›</span>
        <span>{project.name}</span>
      </div>

      {/* Заголовок */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'flex-start', marginBottom: '24px',
      }}>
        <div>
          <h1 style={{ color: '#0f4c81', fontSize: '24px', fontWeight: 700 }}>
            📁 {project.name}
          </h1>
          {project.description && (
            <p style={{ color: '#718096', marginTop: '4px' }}>{project.description}</p>
          )}
        </div>
        <div style={{ display: 'flex', gap: '10px', flexShrink: 0 }}>
          <button
            className="btn btn-outline"
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? '✕ Скасувати' : '+ Додати захід'}
          </button>
          {project.measures.length > 0 && (
            <button
              className="btn btn-success"
              onClick={() => navigate(`/projects/${id}/analysis`)}
            >
              📊 Аналіз
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="alert alert-error" style={{ cursor: 'pointer' }} onClick={() => setError('')}>
          ⚠️ {error} <span style={{ marginLeft: 'auto', opacity: 0.6 }}>✕</span>
        </div>
      )}

      {/* ─── Форма додавання заходу ──────────────────── */}
      {showForm && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div className="card-header">
            <span className="card-title">➕ Новий захід</span>
          </div>

          <form onSubmit={handleAddMeasure}>
            <div className="grid-2">
              <div className="form-group">
                <label>Назва заходу *</label>
                <input
                  type="text"
                  placeholder="Наприклад: Утеплення фасаду"
                  value={form.name}
                  onChange={e => setForm({ ...form, name: e.target.value })}
                  required
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label>Тип заходу *</label>
                <select
                  value={form.measure_type}
                  onChange={e => handleTypeChange(e.target.value)}
                >
                  {MEASURE_TYPES.map(t => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Шаблони */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '11px', color: '#718096', textTransform: 'uppercase', fontWeight: 600, marginBottom: '8px' }}>
                Шаблони типових значень:
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {MEASURE_TYPES.map(t => (
                  <button
                    key={t.value}
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => applyTemplate(t.value)}
                    title={`Заповнити типовими значеннями для: ${t.label}`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <div style={{ fontSize: '11px', color: '#a0aec0', marginTop: '6px' }}>
                💡 Натисніть шаблон, щоб заповнити типові значення для цього типу заходу
              </div>
            </div>

            <div className="grid-3">
              <div className="form-group">
                <label>Початкові інвестиції (грн) *</label>
                <input
                  type="number" min="0" step="1000"
                  placeholder="500 000"
                  value={form.initial_investment}
                  onChange={e => setForm({ ...form, initial_investment: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Операційні витрати/рік (грн) *</label>
                <input
                  type="number" min="0" step="100"
                  placeholder="5 000"
                  value={form.operational_cost}
                  onChange={e => setForm({ ...form, operational_cost: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Очікувана економія/рік (грн) *</label>
                <input
                  type="number" min="1" step="1000"
                  placeholder="80 000"
                  value={form.expected_savings}
                  onChange={e => setForm({ ...form, expected_savings: e.target.value })}
                  required
                />
              </div>
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label>Термін експлуатації (1–50 років) *</label>
                <input
                  type="number" min="1" max="50" step="1"
                  placeholder="15"
                  value={form.lifetime_years}
                  onChange={e => setForm({ ...form, lifetime_years: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Зменшення викидів (т CO₂/рік) *</label>
                <input
                  type="number" min="0" step="0.1"
                  placeholder="50"
                  value={form.emission_reduction}
                  onChange={e => setForm({ ...form, emission_reduction: e.target.value })}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-success"
              disabled={submitting}
            >
              {submitting
                ? <><div className="spinner" style={{ width: '14px', height: '14px' }} /> Додавання...</>
                : '✓ Додати захід'}
            </button>
          </form>
        </div>
      )}

      {/* ─── Список заходів ──────────────────────────── */}
      {project.measures.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <h3>Заходів ще немає</h3>
            <p>Додайте хоча б один захід щоб запустити аналіз</p>
            <button
              className="btn btn-primary"
              style={{ marginTop: '16px' }}
              onClick={() => setShowForm(true)}
            >
              + Додати перший захід
            </button>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="card-header">
            <span className="card-title">
              Заходи проєкту ({project.measures.length})
            </span>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Назва</th>
                  <th>Тип</th>
                  <th>Інвестиції (грн)</th>
                  <th>Витрати/рік</th>
                  <th>Економія/рік</th>
                  <th>Термін</th>
                  <th>CO₂ (т/рік)</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {project.measures.map(m => (
                  <tr key={m.id}>
                    <td><strong>{m.name}</strong></td>
                    <td>
                      {MEASURE_TYPES.find(t => t.value === m.measure_type)?.label || m.measure_type}
                    </td>
                    <td>{m.initial_investment.toLocaleString()} ₴</td>
                    <td>{m.operational_cost.toLocaleString()} ₴</td>
                    <td style={{ color: '#065f46', fontWeight: 600 }}>
                      {m.expected_savings.toLocaleString()} ₴
                    </td>
                    <td>{m.lifetime_years} р.</td>
                    <td>{m.emission_reduction}</td>
                    <td>
                      <button
                        className="btn btn-danger btn-sm"
                        style={{ padding: '4px 10px', fontSize: '12px' }}
                        disabled={deletingId === m.id}
                        onClick={() => handleDeleteMeasure(m.id, m.name)}
                        aria-label={`Видалити захід ${m.name}`}
                        title="Видалити захід"
                      >
                        {deletingId === m.id ? '...' : '🗑 Видалити'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '20px', textAlign: 'right' }}>
            <button
              className="btn btn-success btn-lg"
              onClick={() => navigate(`/projects/${id}/analysis`)}
            >
              📊 Запустити повний аналіз →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
