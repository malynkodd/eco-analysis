import { useState } from 'react'
import { multiCriteriaAPI } from '../api'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts'

const SAATY_SCALE = [
  { value: 1/9, label: '1/9 — Абсолютно гірше' },
  { value: 1/7, label: '1/7 — Дуже сильно гірше' },
  { value: 1/5, label: '1/5 — Сильно гірше' },
  { value: 1/3, label: '1/3 — Трохи гірше' },
  { value: 1,   label: '1 — Рівнозначно' },
  { value: 3,   label: '3 — Трохи краще' },
  { value: 5,   label: '5 — Сильно краще' },
  { value: 7,   label: '7 — Дуже сильно краще' },
  { value: 9,   label: '9 — Абсолютно краще' },
]

const COLORS = ['#0f4c81', '#00b894', '#6c5ce7', '#e17055', '#fdcb6e']

const DEFAULT_CRITERIA = ['Вартість', 'Еко-ефект', 'Окупність', 'Соц. вплив']
const DEFAULT_ALTERNATIVES = [
  { name: 'Утеплення',      'Вартість': 8, 'Еко-ефект': 7, 'Окупність': 8, 'Соц. вплив': 6 },
  { name: 'Сонячні панелі', 'Вартість': 5, 'Еко-ефект': 9, 'Окупність': 5, 'Соц. вплив': 8 },
  { name: 'Заміна котла',   'Вартість': 7, 'Еко-ефект': 6, 'Окупність': 7, 'Соц. вплив': 5 },
]

function buildIdentityMatrix(n) {
  return Array.from({ length: n }, (_, i) =>
    Array.from({ length: n }, (_, j) => (i === j ? 1 : 1))
  )
}

export default function MultiCriteriaPage() {
  const [criteria, setCriteria]         = useState(DEFAULT_CRITERIA)
  const [alternatives, setAlternatives] = useState(DEFAULT_ALTERNATIVES)
  const [matrix, setMatrix]             = useState(buildIdentityMatrix(DEFAULT_CRITERIA.length))
  const [isBenefit, setIsBenefit]       = useState(DEFAULT_CRITERIA.map(() => true))
  const [newCriterion, setNewCriterion] = useState('')
  const [newAltName, setNewAltName]     = useState('')
  const [activeTab, setActiveTab]       = useState('setup')
  const [ahpResult, setAhpResult]       = useState(null)
  const [topsisResult, setTopsisResult] = useState(null)
  const [combinedResult, setCombinedResult] = useState(null)
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState('')

  // ─── Управління критеріями ──────────────────────
  const addCriterion = () => {
    if (!newCriterion.trim() || criteria.includes(newCriterion.trim())) return
    const name = newCriterion.trim()
    const n = criteria.length + 1
    const newMatrix = Array.from({ length: n }, (_, i) =>
      Array.from({ length: n }, (_, j) => {
        if (i === j) return 1
        if (i < criteria.length && j < criteria.length) return matrix[i][j]
        return 1
      })
    )
    setCriteria([...criteria, name])
    setMatrix(newMatrix)
    setIsBenefit([...isBenefit, true])
    setAlternatives(alternatives.map(a => ({ ...a, [name]: 5 })))
    setNewCriterion('')
  }

  const removeCriterion = (idx) => {
    if (criteria.length <= 2) return
    const name = criteria[idx]
    const newCriteria = criteria.filter((_, i) => i !== idx)
    const newMatrix = matrix
      .filter((_, i) => i !== idx)
      .map(row => row.filter((_, j) => j !== idx))
    setCriteria(newCriteria)
    setMatrix(newMatrix)
    setIsBenefit(isBenefit.filter((_, i) => i !== idx))
    setAlternatives(alternatives.map(a => {
      const { [name]: _, ...rest } = a
      return rest
    }))
  }

  // ─── Управління альтернативами ──────────────────
  const addAlternative = () => {
    if (!newAltName.trim()) return
    const alt = { name: newAltName.trim() }
    criteria.forEach(c => { alt[c] = 5 })
    setAlternatives([...alternatives, alt])
    setNewAltName('')
  }

  const removeAlternative = (idx) => {
    if (alternatives.length <= 2) return
    setAlternatives(alternatives.filter((_, i) => i !== idx))
  }

  // ─── Зміна матриці ──────────────────────────────
  const updateMatrix = (i, j, value) => {
    const newMatrix = matrix.map(row => [...row])
    newMatrix[i][j] = value
    newMatrix[j][i] = 1 / value
    setMatrix(newMatrix)
  }

  // ─── Зміна оцінки альтернативи ──────────────────
  const updateAltScore = (altIdx, criterion, value) => {
    setAlternatives(prev => prev.map((a, i) =>
      i === altIdx ? { ...a, [criterion]: parseFloat(value) || 1 } : a
    ))
  }

  // ─── Запуск аналізу ─────────────────────────────
  const runAHP = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await multiCriteriaAPI.ahp({
        criteria,
        comparison_matrix: matrix,
        alternatives,
      })
      setAhpResult(res.data)
      setActiveTab('ahp')
    } catch (e) {
      setError(e.response?.data?.detail || 'Помилка AHP аналізу')
    } finally {
      setLoading(false)
    }
  }

  const runTOPSIS = async () => {
    setLoading(true)
    setError('')
    try {
      const weights = ahpResult
        ? ahpResult.weights
        : criteria.map(() => 1 / criteria.length)

      const res = await multiCriteriaAPI.topsis({
        criteria,
        weights,
        is_benefit: isBenefit,
        alternatives,
      })
      setTopsisResult(res.data)
      setActiveTab('topsis')
    } catch (e) {
      setError(e.response?.data?.detail || 'Помилка TOPSIS аналізу')
    } finally {
      setLoading(false)
    }
  }

  // ─── Експорт матриці AHP в CSV ──────────────────
  const exportAHPMatrix = () => {
    const rows = []
    rows.push(['МАТРИЦЯ ПАРНИХ ПОРІВНЯНЬ AHP'])
    rows.push(['Критерій', ...criteria])
    criteria.forEach((c, i) => {
      rows.push([c, ...criteria.map((_, j) => matrix[i][j].toFixed(4))])
    })
    rows.push([])
    if (ahpResult) {
      rows.push(['ВАГИ КРИТЕРІЇВ'])
      rows.push(['Критерій', 'Вага (%)', 'CR'])
      criteria.forEach((c, i) => {
        rows.push([c, (ahpResult.weights[i] * 100).toFixed(2) + '%', i === 0 ? ahpResult.consistency_ratio : ''])
      })
      rows.push([])
      rows.push(['РЕЙТИНГ АЛЬТЕРНАТИВ (AHP)'])
      rows.push(['Місце', 'Альтернатива', 'Оцінка'])
      ahpResult.ranking.forEach(r => rows.push([r.rank, r.name, r.score.toFixed(4)]))
    }
    if (topsisResult) {
      rows.push([])
      rows.push(['РЕЙТИНГ АЛЬТЕРНАТИВ (TOPSIS)'])
      rows.push(['Місце', 'Альтернатива', 'Коефіцієнт близькості', 'До ідеалу', 'До анти-ідеалу'])
      topsisResult.ranking.forEach(r => rows.push([r.rank, r.name, r.closeness_coefficient.toFixed(4), r.distance_to_ideal.toFixed(4), r.distance_to_anti_ideal.toFixed(4)]))
    }

    const csv = '\uFEFF' + rows.map(r =>
      r.map(cell => {
        const s = String(cell ?? '')
        return s.includes(';') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s
      }).join(';')
    ).join('\n')

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'ahp_topsis_аналіз.csv'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const runCombined = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await multiCriteriaAPI.combined({
        criteria,
        comparison_matrix: matrix,
        is_benefit: isBenefit,
        alternatives,
      })
      setCombinedResult(res.data)
      setAhpResult(res.data.ahp)
      setTopsisResult(res.data.topsis)
      setActiveTab('combined')
    } catch (e) {
      setError(e.response?.data?.detail || 'Помилка комбінованого аналізу')
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { key: 'setup',    label: '⚙️ Налаштування' },
    { key: 'matrix',   label: '📊 Матриця AHP' },
    { key: 'ahp',      label: '🎯 AHP результат' },
    { key: 'topsis',   label: '📐 TOPSIS результат' },
    { key: 'combined', label: '🏆 Комбінований' },
  ]

  return (
    <div className="container" style={{ paddingTop: '32px', paddingBottom: '40px' }}>

      {/* Заголовок */}
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '26px', fontWeight: 700, color: '#0f4c81' }}>
          🎯 Багатокритеріальний аналіз
        </h1>
        <p style={{ color: '#718096', marginTop: '4px' }}>
          Методи AHP (Analytic Hierarchy Process) та TOPSIS для ранжування альтернатив
        </p>
      </div>

      {error && <div className="alert alert-error">⚠️ {error}</div>}

      {/* Кнопки запуску */}
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <button className="btn btn-primary" onClick={runAHP} disabled={loading}>
          {loading ? '⏳...' : '▶ Запустити AHP'}
        </button>
        <button className="btn btn-success" onClick={runTOPSIS} disabled={loading}>
          {loading ? '⏳...' : '▶ Запустити TOPSIS'}
        </button>
        <button
          className="btn"
          style={{ background: '#6c5ce7', color: 'white' }}
          onClick={runCombined}
          disabled={loading}
        >
          {loading ? '⏳...' : '⚡ AHP + TOPSIS разом'}
        </button>
        {(ahpResult || topsisResult) && (
          <button
            className="btn btn-outline btn-sm"
            onClick={exportAHPMatrix}
            title="Завантажити матрицю та результати у форматі CSV"
          >
            📊 Excel / CSV
          </button>
        )}
        <div style={{
          marginLeft: 'auto',
          background: '#dbeafe', borderRadius: '8px',
          padding: '8px 16px', fontSize: '13px', color: '#1e40af',
          display: 'flex', alignItems: 'center',
        }}>
          {criteria.length} критеріїв · {alternatives.length} альтернатив
        </div>
      </div>

      {/* Таби */}
      <div className="tabs">
        {tabs.map(t => (
          <button
            key={t.key}
            className={`tab ${activeTab === t.key ? 'active' : ''}`}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ─── Налаштування ──────────────────────────── */}
      {activeTab === 'setup' && (
        <div>
          {/* Критерії */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">📋 Критерії оцінювання</span>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px', marginBottom: '16px' }}>
              {criteria.map((c, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  background: '#f0f4f8', borderRadius: '10px',
                  padding: '8px 14px', border: '1px solid #e2e8f0',
                }}>
                  <span style={{ fontWeight: 600, color: '#0f4c81' }}>{c}</span>

                  {/* Перемикач вигідний / невигідний */}
                  <div style={{
                    display: 'flex', borderRadius: '6px',
                    overflow: 'hidden', border: '1px solid #e2e8f0',
                  }}>
                    <button
                      type="button"
                      onClick={() => {
                        const nb = [...isBenefit]
                        nb[i] = true
                        setIsBenefit(nb)
                      }}
                      style={{
                        padding: '3px 10px', fontSize: '11px', fontWeight: 600,
                        border: 'none', cursor: 'pointer',
                        background: isBenefit[i] ? '#00b894' : '#f3f4f6',
                        color:      isBenefit[i] ? 'white'   : '#9ca3af',
                        transition: 'all 0.15s',
                      }}
                    >↑ вигідний</button>
                    <button
                      type="button"
                      onClick={() => {
                        const nb = [...isBenefit]
                        nb[i] = false
                        setIsBenefit(nb)
                      }}
                      style={{
                        padding: '3px 10px', fontSize: '11px', fontWeight: 600,
                        border: 'none', cursor: 'pointer',
                        background: !isBenefit[i] ? '#e17055' : '#f3f4f6',
                        color:      !isBenefit[i] ? 'white'   : '#9ca3af',
                        transition: 'all 0.15s',
                      }}
                    >↓ невигідний</button>
                  </div>

                  {criteria.length > 2 && (
                    <button
                      onClick={() => removeCriterion(i)}
                      aria-label={`Видалити критерій ${c}`}
                      title={`Видалити критерій ${c}`}
                      style={{
                        background: 'none', border: 'none',
                        color: '#e17055', cursor: 'pointer',
                        fontSize: '14px', padding: '0', lineHeight: 1,
                      }}
                    >✕</button>
                  )}
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                type="text"
                placeholder="Нова назва критерію..."
                value={newCriterion}
                onChange={e => setNewCriterion(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addCriterion()}
                style={{ maxWidth: '280px', marginBottom: 0 }}
              />
              <button className="btn btn-outline" onClick={addCriterion}>
                + Додати критерій
              </button>
            </div>

            <div style={{
              marginTop: '12px', fontSize: '12px', color: '#718096',
              background: '#f7fafd', padding: '10px 14px', borderRadius: '8px',
            }}>
              💡{' '}
              <span style={{ color: '#00b894', fontWeight: 600 }}>↑ вигідний</span>
              {' '}= більше значення краще (NPV, еко-ефект).{' '}
              <span style={{ color: '#e17055', fontWeight: 600 }}>↓ невигідний</span>
              {' '}= менше значення краще (вартість, термін окупності).
            </div>
          </div>

          {/* Альтернативи */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">🔀 Альтернативи та оцінки (1–10)</span>
            </div>
            <div className="table-wrap" style={{ marginBottom: '16px' }}>
              <table>
                <thead>
                  <tr>
                    <th>Альтернатива</th>
                    {criteria.map(c => <th key={c}>{c}</th>)}
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {alternatives.map((alt, i) => (
                    <tr key={i}>
                      <td>
                        <strong style={{ color: '#0f4c81' }}>{alt.name}</strong>
                      </td>
                      {criteria.map(c => (
                        <td key={c}>
                          <input
                            type="number" min="1" max="10" step="0.5"
                            value={alt[c] ?? 5}
                            onChange={e => updateAltScore(i, c, e.target.value)}
                            style={{
                              width: '70px', marginBottom: 0,
                              padding: '6px 8px', textAlign: 'center',
                            }}
                          />
                        </td>
                      ))}
                      <td>
                        {alternatives.length > 2 && (
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => removeAlternative(i)}
                            aria-label={`Видалити альтернативу ${alt.name}`}
                            title={`Видалити альтернативу ${alt.name}`}
                          >🗑 Видалити</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div style={{ display: 'flex', gap: '10px' }}>
              <input
                type="text"
                placeholder="Назва нової альтернативи..."
                value={newAltName}
                onChange={e => setNewAltName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addAlternative()}
                style={{ maxWidth: '280px', marginBottom: 0 }}
              />
              <button className="btn btn-outline" onClick={addAlternative}>
                + Додати альтернативу
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ─── Матриця AHP ───────────────────────────── */}
      {activeTab === 'matrix' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">📊 Матриця парних порівнянь (шкала Сааті)</span>
          </div>
          <div style={{
            background: '#dbeafe', borderRadius: '10px',
            padding: '12px 16px', marginBottom: '20px',
            fontSize: '13px', color: '#1e40af',
          }}>
            💡 Порівнюйте критерії попарно.{' '}
            <strong>1</strong> = рівнозначні,{' '}
            <strong>3</strong> = трохи важливіший,{' '}
            <strong>5</strong> = суттєво важливіший,{' '}
            <strong>9</strong> = абсолютно важливіший.
            Значення &lt;1 — зворотне відношення.
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th style={{ minWidth: '120px' }}>Критерій</th>
                  {criteria.map(c => <th key={c}>{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {criteria.map((rowC, i) => (
                  <tr key={i}>
                    <td><strong style={{ color: '#0f4c81' }}>{rowC}</strong></td>
                    {criteria.map((colC, j) => (
                      <td key={j} style={{ padding: '6px 8px' }}>
                        {i === j ? (
                          <div style={{
                            width: '80px', textAlign: 'center',
                            background: '#f0f4f8', padding: '6px',
                            borderRadius: '6px', color: '#718096', fontWeight: 600,
                          }}>1</div>
                        ) : i < j ? (
                          <select
                            value={matrix[i][j]}
                            onChange={e => updateMatrix(i, j, parseFloat(e.target.value))}
                            style={{ width: '180px', marginBottom: 0, fontSize: '12px' }}
                          >
                            {SAATY_SCALE.map(s => (
                              <option key={s.value} value={s.value}>{s.label}</option>
                            ))}
                          </select>
                        ) : (
                          <div style={{
                            width: '80px', textAlign: 'center',
                            background: '#f0f4f8', padding: '6px',
                            borderRadius: '6px', color: '#718096', fontSize: '12px',
                          }}>
                            {(1 / matrix[j][i]).toFixed(3)}
                          </div>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '16px', textAlign: 'right' }}>
            <button className="btn btn-primary" onClick={runAHP} disabled={loading}>
              {loading ? '⏳...' : '▶ Запустити AHP з цією матрицею'}
            </button>
          </div>
        </div>
      )}

      {/* ─── AHP результати ────────────────────────── */}
      {activeTab === 'ahp' && ahpResult && (
        <div>
          <div className={`alert ${ahpResult.is_consistent ? 'alert-success' : 'alert-error'}`}
            style={{ marginBottom: ahpResult.is_consistent ? '16px' : '0' }}>
            {ahpResult.is_consistent
              ? `✓ Матриця узгоджена (CR = ${ahpResult.consistency_ratio}) — CR < 0.1`
              : `⚠ Матриця НЕ узгоджена (CR = ${ahpResult.consistency_ratio})`
            }
          </div>
          {!ahpResult.is_consistent && (
            <div style={{
              background: '#fff7ed', border: '1px solid #fed7aa',
              borderRadius: '8px', padding: '12px 16px', marginBottom: '16px',
              fontSize: '13px', color: '#92400e',
            }}>
              <strong>Як виправити:</strong>
              <ul style={{ marginTop: '6px', paddingLeft: '20px', lineHeight: 1.8 }}>
                <li>Перейдіть на вкладку <strong>«Матриця AHP»</strong></li>
                <li>Знайдіть суперечливі порівняння — наприклад, якщо A кращий за B, а B кращий за C, то A повинен бути кращим за C</li>
                <li>Зменшіть розкид значень: уникайте різкого переходу від «1» до «9» між сусідніми критеріями</li>
                <li>Ціль: CR &lt; 0.1 (10% — допустимий рівень неузгодженості за Сааті)</li>
              </ul>
            </div>
          )}

          <div className="grid-2">
            {/* Ваги критеріїв */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">⚖️ Ваги критеріїв</span>
              </div>
              {ahpResult.criteria.map((c, i) => (
                <div key={i} style={{ marginBottom: '12px' }}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    marginBottom: '4px', fontSize: '13px',
                  }}>
                    <span style={{ fontWeight: 500 }}>{c}</span>
                    <strong style={{ color: '#0f4c81' }}>
                      {(ahpResult.weights[i] * 100).toFixed(1)}%
                    </strong>
                  </div>
                  <div style={{
                    height: '8px', background: '#f0f4f8',
                    borderRadius: '4px', overflow: 'hidden',
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${ahpResult.weights[i] * 100}%`,
                      background: COLORS[i % COLORS.length],
                      borderRadius: '4px',
                      transition: 'width 0.5s ease',
                    }} />
                  </div>
                </div>
              ))}

              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={ahpResult.criteria.map((c, i) => ({
                  name: c,
                  weight: parseFloat((ahpResult.weights[i] * 100).toFixed(1))
                }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={v => v + '%'} />
                  <Tooltip formatter={v => [v + '%', 'Вага']} />
                  <Bar dataKey="weight" radius={[4, 4, 0, 0]}>
                    {ahpResult.criteria.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Рейтинг */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">🏆 Рейтинг AHP</span>
              </div>
              {ahpResult.ranking.map((r, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: '12px',
                  padding: '12px', borderRadius: '10px',
                  background: i === 0 ? '#d1fae5' : i === 1 ? '#dbeafe' : '#f3f4f6',
                  marginBottom: '8px',
                }}>
                  <div style={{
                    width: '32px', height: '32px',
                    background: COLORS[i % COLORS.length],
                    borderRadius: '50%', display: 'flex',
                    alignItems: 'center', justifyContent: 'center',
                    color: 'white', fontWeight: 700, fontSize: '14px', flexShrink: 0,
                  }}>{r.rank}</div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: '14px' }}>{r.name}</div>
                    <div style={{ fontSize: '12px', color: '#718096' }}>
                      Зважена оцінка: <strong>{r.score.toFixed(4)}</strong>
                    </div>
                  </div>
                  {i === 0 && <span className="badge badge-green">🥇 Найкращий</span>}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── TOPSIS результати ─────────────────────── */}
      {activeTab === 'topsis' && topsisResult && (
        <div>
          <div className="alert alert-info" style={{ marginBottom: '16px' }}>
            💡 Коефіцієнт близькості: <strong>1.0</strong> = ідеальне рішення,
            <strong> 0.0</strong> = найгірше рішення
          </div>

          <div className="grid-2">
            {/* Рейтинг */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">🏆 Рейтинг TOPSIS</span>
              </div>
              {topsisResult.ranking.map((r, i) => (
                <div key={i} style={{
                  padding: '14px', borderRadius: '10px',
                  background: i === 0 ? '#d1fae5' : i === 1 ? '#dbeafe' : '#f3f4f6',
                  marginBottom: '8px',
                }}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: '8px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{
                        width: '28px', height: '28px',
                        background: COLORS[i % COLORS.length],
                        borderRadius: '50%', display: 'flex',
                        alignItems: 'center', justifyContent: 'center',
                        color: 'white', fontWeight: 700, fontSize: '13px',
                      }}>{r.rank}</div>
                      <strong>{r.name}</strong>
                    </div>
                    {i === 0 && <span className="badge badge-green">🥇 Найкращий</span>}
                  </div>

                  <div style={{ marginBottom: '6px' }}>
                    <div style={{
                      display: 'flex', justifyContent: 'space-between',
                      fontSize: '12px', color: '#718096', marginBottom: '3px',
                    }}>
                      <span>Коефіцієнт близькості</span>
                      <strong style={{ color: '#0f4c81' }}>
                        {r.closeness_coefficient.toFixed(4)}
                      </strong>
                    </div>
                    <div style={{
                      height: '8px', background: 'rgba(0,0,0,0.08)',
                      borderRadius: '4px', overflow: 'hidden',
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${r.closeness_coefficient * 100}%`,
                        background: COLORS[i % COLORS.length],
                        borderRadius: '4px',
                      }} />
                    </div>
                  </div>

                  <div style={{ fontSize: '11px', color: '#718096', display: 'flex', gap: '16px' }}>
                    <span>📍 До ідеалу: {r.distance_to_ideal.toFixed(4)}</span>
                    <span>📍 До анти-ідеалу: {r.distance_to_anti_ideal.toFixed(4)}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Radar */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">📡 Radar — порівняння</span>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={criteria.map((c) => ({
                  metric: c,
                  ...Object.fromEntries(alternatives.map(a => [a.name, a[c] || 0]))
                }))}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12 }} />
                  {alternatives.map((a, i) => (
                    <Radar
                      key={a.name}
                      name={a.name}
                      dataKey={a.name}
                      stroke={COLORS[i % COLORS.length]}
                      fill={COLORS[i % COLORS.length]}
                      fillOpacity={0.15}
                    />
                  ))}
                  <Legend />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Таблиця деталей */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">📋 Деталі TOPSIS</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Місце</th>
                    <th>Альтернатива</th>
                    <th>Коефіцієнт близькості</th>
                    <th>Відстань до ідеалу</th>
                    <th>Відстань до анти-ідеалу</th>
                  </tr>
                </thead>
                <tbody>
                  {topsisResult.ranking.map((r, i) => (
                    <tr key={i}>
                      <td>
                        <span className={`badge ${
                          i === 0 ? 'badge-green' : i === 1 ? 'badge-blue' : 'badge-gray'
                        }`}>#{r.rank}</span>
                      </td>
                      <td><strong>{r.name}</strong></td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{
                            width: '60px', height: '6px',
                            background: '#f0f4f8', borderRadius: '3px', overflow: 'hidden',
                          }}>
                            <div style={{
                              height: '100%',
                              width: `${r.closeness_coefficient * 100}%`,
                              background: COLORS[i % COLORS.length],
                            }} />
                          </div>
                          <strong>{r.closeness_coefficient.toFixed(4)}</strong>
                        </div>
                      </td>
                      <td>{r.distance_to_ideal.toFixed(4)}</td>
                      <td>{r.distance_to_anti_ideal.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ─── Комбінований ──────────────────────────── */}
      {activeTab === 'combined' && combinedResult && (
        <div>
          <div className="alert alert-success" style={{ marginBottom: '20px' }}>
            ✓ AHP визначив ваги критеріїв → TOPSIS використав їх для ранжування
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">⚡ Порівняння AHP vs TOPSIS</span>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Альтернатива</th>
                    <th>AHP оцінка</th>
                    <th>AHP місце</th>
                    <th>TOPSIS коефіцієнт</th>
                    <th>TOPSIS місце</th>
                    <th>Збіг</th>
                  </tr>
                </thead>
                <tbody>
                  {combinedResult.ahp.ranking.map(ahpRow => {
                    const topsisRow = combinedResult.topsis.ranking
                      .find(t => t.name === ahpRow.name)
                    const match = ahpRow.rank === topsisRow?.rank
                    return (
                      <tr key={ahpRow.name}>
                        <td><strong>{ahpRow.name}</strong></td>
                        <td>{ahpRow.score.toFixed(4)}</td>
                        <td>
                          <span className={`badge ${
                            ahpRow.rank === 1 ? 'badge-green' :
                            ahpRow.rank === 2 ? 'badge-blue' : 'badge-gray'
                          }`}>#{ahpRow.rank}</span>
                        </td>
                        <td>{topsisRow?.closeness_coefficient.toFixed(4)}</td>
                        <td>
                          <span className={`badge ${
                            topsisRow?.rank === 1 ? 'badge-green' :
                            topsisRow?.rank === 2 ? 'badge-blue' : 'badge-gray'
                          }`}>#{topsisRow?.rank}</span>
                        </td>
                        <td>
                          <span className={`badge ${match ? 'badge-green' : 'badge-yellow'}`}>
                            {match ? '✓ Збігається' : '≠ Різниться'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">⚖️ Ваги критеріїв від AHP</span>
              <span className={`badge ${
                combinedResult.ahp.is_consistent ? 'badge-green' : 'badge-red'
              }`}>
                CR = {combinedResult.ahp.consistency_ratio}
                {combinedResult.ahp.is_consistent ? ' ✓' : ' ✗'}
              </span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
              {combinedResult.ahp.criteria.map((c, i) => (
                <div key={i} style={{
                  background: '#f0f4f8', borderRadius: '10px',
                  padding: '12px 16px', minWidth: '120px', textAlign: 'center',
                  borderLeft: `4px solid ${COLORS[i % COLORS.length]}`,
                }}>
                  <div style={{ fontSize: '11px', color: '#718096', marginBottom: '4px' }}>
                    {c}
                  </div>
                  <div style={{
                    fontSize: '20px', fontWeight: 700,
                    color: COLORS[i % COLORS.length],
                  }}>
                    {(combinedResult.ahp.weights[i] * 100).toFixed(1)}%
                  </div>
                  <div style={{ fontSize: '10px', marginTop: '4px' }}>
                    <span style={{
                      background: isBenefit[i] ? '#d1fae5' : '#fee2e2',
                      color: isBenefit[i] ? '#065f46' : '#991b1b',
                      padding: '1px 6px', borderRadius: '8px',
                    }}>
                      {isBenefit[i] ? '↑ вигідний' : '↓ невигідний'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Порожні стани */}
      {activeTab === 'ahp' && !ahpResult && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">🎯</div>
            <h3>AHP ще не запущено</h3>
            <p>Налаштуйте критерії і матрицю, потім натисніть "Запустити AHP"</p>
          </div>
        </div>
      )}
      {activeTab === 'topsis' && !topsisResult && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📐</div>
            <h3>TOPSIS ще не запущено</h3>
            <p>Натисніть "Запустити TOPSIS" або "AHP + TOPSIS разом"</p>
          </div>
        </div>
      )}
      {activeTab === 'combined' && !combinedResult && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">⚡</div>
            <h3>Комбінований аналіз ще не запущено</h3>
            <p>Натисніть "AHP + TOPSIS разом"</p>
          </div>
        </div>
      )}
    </div>
  )
}
