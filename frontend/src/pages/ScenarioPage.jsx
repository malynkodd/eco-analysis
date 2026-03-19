import { useState, useEffect } from 'react'
import { scenarioAPI } from '../api'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Cell
} from 'recharts'

const STORAGE_KEY = 'eco_scenarios'

const DEFAULT_BASE = {
  name: 'Аналіз заходу',
  initial_investment: 500000,
  operational_cost: 5000,
  expected_savings: 80000,
  lifetime_years: 15,
  discount_rate: 0.1,
}

export default function ScenarioPage() {
  const [base, setBase] = useState(DEFAULT_BASE)
  const [activeTab, setActiveTab] = useState('whatif')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // What-if
  const [whatifResults, setWhatifResults] = useState(null)

  // Sensitivity
  const [sensitivityResult, setSensitivityResult] = useState(null)
  const [variation, setVariation] = useState(20)

  // Break-even
  const [breakevenResult, setBreakevenResult] = useState(null)

  // ─── Збереження сценаріїв ─────────────────────────
  const [savedScenarios, setSavedScenarios] = useState(() => {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') }
    catch { return [] }
  })
  const [showScenarios, setShowScenarios] = useState(false)

  const saveScenario = () => {
    const name = prompt('Назва сценарію:', base.name)
    if (!name) return
    const scenario = { ...base, _savedName: name, _savedAt: new Date().toISOString() }
    const updated = [scenario, ...savedScenarios].slice(0, 10) // зберігаємо до 10
    setSavedScenarios(updated)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
  }

  const loadScenario = (scenario) => {
    const { _savedName, _savedAt, ...baseData } = scenario
    setBase(baseData)
    setWhatifResults(null)
    setSensitivityResult(null)
    setBreakevenResult(null)
    setShowScenarios(false)
  }

  const deleteScenario = (idx) => {
    const updated = savedScenarios.filter((_, i) => i !== idx)
    setSavedScenarios(updated)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated))
  }

  const handleBaseChange = (field, value) => {
    setBase(prev => ({
      ...prev,
      [field]: field === 'lifetime_years'
        ? parseInt(value) || 1
        : parseFloat(value) || 0
    }))
  }

  const runWhatIf = async () => {
    setLoading(true)
    setError('')
    try {
      const changes = [
        { parameter: 'expected_savings', new_value: base.expected_savings * 1.2 },
        { parameter: 'expected_savings', new_value: base.expected_savings * 0.8 },
        { parameter: 'initial_investment', new_value: base.initial_investment * 1.2 },
        { parameter: 'initial_investment', new_value: base.initial_investment * 0.8 },
        { parameter: 'discount_rate', new_value: base.discount_rate + 0.05 },
        { parameter: 'discount_rate', new_value: Math.max(0.01, base.discount_rate - 0.05) },
      ]
      const res = await scenarioAPI.whatif({ base, changes })
      setWhatifResults(res.data)
    } catch (e) {
      setError('Помилка аналізу')
    } finally {
      setLoading(false)
    }
  }

  const runSensitivity = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await scenarioAPI.sensitivity({
        base,
        variation_percent: variation,
        steps: 5
      })
      setSensitivityResult(res.data)
    } catch {
      setError('Помилка аналізу чутливості')
    } finally {
      setLoading(false)
    }
  }

  const runBreakeven = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await scenarioAPI.breakeven({ base })
      setBreakevenResult(res.data)
    } catch {
      setError('Помилка Break-even аналізу')
    } finally {
      setLoading(false)
    }
  }

  const PARAM_LABELS = {
    expected_savings: 'Економія/рік',
    initial_investment: 'Інвестиції',
    discount_rate: 'Ставка дискон.',
    operational_cost: 'Витрати/рік',
    lifetime_years: 'Термін (років)',
  }

  const tabs = [
    { key: 'whatif', label: '🔀 What-if' },
    { key: 'sensitivity', label: '📊 Sensitivity' },
    { key: 'breakeven', label: '⚖️ Break-even' },
  ]

  return (
    <div className="container" style={{ paddingTop: '32px', paddingBottom: '40px' }}>

      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '26px', fontWeight: 700, color: '#0f4c81' }}>
          🔬 Сценарне моделювання
        </h1>
        <p style={{ color: '#718096', marginTop: '4px' }}>
          What-if аналіз, аналіз чутливості та Break-even
        </p>
      </div>

      {/* Базові параметри */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">⚙️ Базові параметри заходу</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-outline btn-sm"
              onClick={saveScenario}
              title="Зберегти поточні параметри як сценарій"
            >
              💾 Зберегти сценарій
            </button>
            {savedScenarios.length > 0 && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setShowScenarios(!showScenarios)}
                title="Завантажити збережений сценарій"
              >
                📂 Завантажити ({savedScenarios.length})
              </button>
            )}
          </div>
        </div>

        {/* Список збережених сценаріїв */}
        {showScenarios && savedScenarios.length > 0 && (
          <div style={{
            background: '#f7fafd', border: '1px solid #e2e8f0',
            borderRadius: '8px', padding: '12px', marginBottom: '16px',
          }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: '#718096', marginBottom: '8px', textTransform: 'uppercase' }}>
              Збережені сценарії:
            </div>
            {savedScenarios.map((s, idx) => (
              <div key={idx} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 12px', background: 'white', borderRadius: '6px',
                marginBottom: '6px', border: '1px solid #e2e8f0',
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '13px' }}>{s._savedName}</div>
                  <div style={{ fontSize: '11px', color: '#718096' }}>
                    Інвестиції: {s.initial_investment?.toLocaleString()} ₴ ·
                    Економія: {s.expected_savings?.toLocaleString()} ₴/рік ·
                    {new Date(s._savedAt).toLocaleDateString('uk-UA')}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => loadScenario(s)}
                  >
                    Завантажити
                  </button>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => deleteScenario(idx)}
                    aria-label={`Видалити сценарій ${s._savedName}`}
                  >
                    🗑
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="grid-3">
          {[
            { field: 'initial_investment', label: 'Початкові інвестиції (грн)', step: 10000 },
            { field: 'operational_cost', label: 'Операційні витрати/рік (грн)', step: 1000 },
            { field: 'expected_savings', label: 'Очікувана економія/рік (грн)', step: 1000 },
            { field: 'lifetime_years', label: 'Термін експлуатації (років)', step: 1 },
            { field: 'discount_rate', label: 'Ставка дисконтування (частки)', step: 0.01 },
          ].map(({ field, label, step }) => (
            <div className="form-group" key={field}>
              <label>{label}</label>
              <input
                type="number"
                step={step}
                value={base[field]}
                onChange={e => handleBaseChange(field, e.target.value)}
              />
            </div>
          ))}
          <div style={{ display: 'flex', alignItems: 'flex-end', paddingBottom: '16px' }}>
            <div style={{
              background: '#dbeafe',
              borderRadius: '10px',
              padding: '12px 16px',
              width: '100%',
            }}>
              <div style={{ fontSize: '11px', color: '#1e40af', fontWeight: 600 }}>
                БАЗОВИЙ NPV (орієнтовно)
              </div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#0f4c81' }}>
                {(() => {
                  const cf = base.expected_savings - base.operational_cost
                  const npv = -base.initial_investment +
                    Array.from({ length: base.lifetime_years },
                      (_, t) => cf / Math.pow(1 + base.discount_rate, t + 1)
                    ).reduce((a, b) => a + b, 0)
                  return (npv > 0 ? '+' : '') + Math.round(npv).toLocaleString() + ' ₴'
                })()}
              </div>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

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

      {/* ─── What-if ───────────────────────────────── */}
      {activeTab === 'whatif' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">🔀 What-if аналіз</span>
            <button
              className="btn btn-primary"
              onClick={runWhatIf}
              disabled={loading}
            >
              {loading ? '⏳...' : '▶ Запустити'}
            </button>
          </div>
          <p style={{ color: '#718096', fontSize: '13px', marginBottom: '20px' }}>
            Автоматично перераховує NPV при зміні кожного параметру на ±20%
            та при зміні ставки дисконтування ±5%
          </p>

          {whatifResults && (
            <div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Параметр</th>
                      <th>Зміна</th>
                      <th>Оригінал</th>
                      <th>Нове значення</th>
                      <th>NPV до</th>
                      <th>NPV після</th>
                      <th>Зміна NPV</th>
                    </tr>
                  </thead>
                  <tbody>
                    {whatifResults.map((r, i) => (
                      <tr key={i}>
                        <td><strong>{PARAM_LABELS[r.parameter_changed] || r.parameter_changed}</strong></td>
                        <td>
                          <span className={`badge ${r.new_value > r.original_value ? 'badge-blue' : 'badge-yellow'}`}>
                            {r.new_value > r.original_value ? '▲ +' : '▼ '}
                            {Math.abs(((r.new_value - r.original_value) / r.original_value) * 100).toFixed(0)}%
                          </span>
                        </td>
                        <td>{r.original_value.toLocaleString()}</td>
                        <td>{r.new_value.toLocaleString()}</td>
                        <td>{Math.round(r.original_npv).toLocaleString()} ₴</td>
                        <td style={{ color: r.new_npv > 0 ? '#065f46' : '#991b1b' }}>
                          {Math.round(r.new_npv).toLocaleString()} ₴
                        </td>
                        <td>
                          <span className={`badge ${r.npv_change > 0 ? 'badge-green' : 'badge-red'}`}>
                            {r.npv_change > 0 ? '+' : ''}{Math.round(r.npv_change).toLocaleString()} ₴
                            ({r.npv_change_percent > 0 ? '+' : ''}{r.npv_change_percent.toFixed(1)}%)
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ─── Sensitivity ───────────────────────────── */}
      {activeTab === 'sensitivity' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">📊 Аналіз чутливості (Tornado Chart)</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <label style={{ marginBottom: 0, textTransform: 'none', fontSize: '13px' }}>
                  Варіація:
                </label>
                <input
                  type="range" min="5" max="50" step="5"
                  value={variation}
                  onChange={e => setVariation(parseInt(e.target.value))}
                  style={{ width: '100px', marginBottom: 0 }}
                />
                <strong style={{ color: '#0f4c81' }}>±{variation}%</strong>
              </div>
              <button
                className="btn btn-primary"
                onClick={runSensitivity}
                disabled={loading}
              >
                {loading ? '⏳...' : '▶ Запустити'}
              </button>
            </div>
          </div>

          {sensitivityResult && (
            <div>
              <div style={{
                background: '#f7fafd',
                borderRadius: '10px',
                padding: '12px 20px',
                marginBottom: '20px',
                display: 'flex',
                gap: '32px',
              }}>
                <div>
                  <div style={{ fontSize: '12px', color: '#718096' }}>Базовий NPV</div>
                  <div style={{ fontSize: '20px', fontWeight: 700, color: '#0f4c81' }}>
                    {Math.round(sensitivityResult.base_npv).toLocaleString()} ₴
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '12px', color: '#718096' }}>Найвпливовіший фактор</div>
                  <div style={{ fontSize: '18px', fontWeight: 700, color: '#6c5ce7' }}>
                    {PARAM_LABELS[sensitivityResult.results[0]?.parameter] || sensitivityResult.results[0]?.parameter}
                  </div>
                </div>
              </div>

              {/* Tornado Chart */}
              <h4 style={{ color: '#0f4c81', marginBottom: '16px', fontSize: '14px' }}>
                Tornado Chart — вплив на NPV (грн)
              </h4>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={sensitivityResult.results.map(r => ({
                    name: PARAM_LABELS[r.parameter] || r.parameter,
                    impact: Math.round(r.impact_percent),
                  }))}
                  layout="vertical"
                  margin={{ left: 120, right: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tickFormatter={v => v.toLocaleString()} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} />
                  <Tooltip formatter={v => [v.toLocaleString() + ' ₴', 'Вплив на NPV']} />
                  <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
                    {sensitivityResult.results.map((_, i) => (
                      <Cell
                        key={i}
                        fill={['#0f4c81','#1a6baf','#6c5ce7','#00b894','#e17055'][i % 5]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* ─── Break-even ────────────────────────────── */}
      {activeTab === 'breakeven' && (
        <div className="card">
          <div className="card-header">
            <span className="card-title">⚖️ Break-even аналіз</span>
            <button
              className="btn btn-primary"
              onClick={runBreakeven}
              disabled={loading}
            >
              {loading ? '⏳...' : '▶ Запустити'}
            </button>
          </div>
          <p style={{ color: '#718096', fontSize: '13px', marginBottom: '20px' }}>
            Знаходить порогові значення параметрів при яких NPV = 0
          </p>

          {breakevenResult && (
            <div>
              <div className="grid-4" style={{ marginBottom: '24px' }}>
                <div className="stat-card green">
                  <div className="stat-label">Базовий NPV</div>
                  <div className="stat-value" style={{ fontSize: '16px' }}>
                    {Math.round(breakevenResult.base_npv).toLocaleString()} ₴
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Мін. економія</div>
                  <div className="stat-value" style={{ fontSize: '16px' }}>
                    {Math.round(breakevenResult.breakeven_savings).toLocaleString()} ₴
                  </div>
                  <div style={{ fontSize: '11px', color: '#718096', marginTop: '4px' }}>
                    при якій NPV = 0
                  </div>
                </div>
                <div className="stat-card purple">
                  <div className="stat-label">Макс. інвестиція</div>
                  <div className="stat-value" style={{ fontSize: '16px' }}>
                    {Math.round(breakevenResult.breakeven_investment).toLocaleString()} ₴
                  </div>
                  <div style={{ fontSize: '11px', color: '#718096', marginTop: '4px' }}>
                    при якій NPV = 0
                  </div>
                </div>
                <div className="stat-card orange">
                  <div className="stat-label">Макс. ставка (IRR)</div>
                  <div className="stat-value" style={{ fontSize: '16px' }}>
                    {breakevenResult.breakeven_discount_rate}%
                  </div>
                </div>
              </div>

              {/* Порівняння з поточними */}
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Параметр</th>
                      <th>Поточне значення</th>
                      <th>Break-even значення</th>
                      <th>Запас міцності</th>
                      <th>Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td>Економія/рік</td>
                      <td>{base.expected_savings.toLocaleString()} ₴</td>
                      <td>{Math.round(breakevenResult.breakeven_savings).toLocaleString()} ₴</td>
                      <td style={{ color: '#065f46' }}>
                        +{Math.round(((base.expected_savings - breakevenResult.breakeven_savings)
                          / breakevenResult.breakeven_savings) * 100).toFixed(1)}%
                      </td>
                      <td><span className="badge badge-green">✓ Є запас</span></td>
                    </tr>
                    <tr>
                      <td>Початкові інвестиції</td>
                      <td>{base.initial_investment.toLocaleString()} ₴</td>
                      <td>{Math.round(breakevenResult.breakeven_investment).toLocaleString()} ₴</td>
                      <td style={{ color: '#065f46' }}>
                        {Math.round(((breakevenResult.breakeven_investment - base.initial_investment)
                          / base.initial_investment) * 100).toFixed(1)}% ліміт
                      </td>
                      <td><span className="badge badge-green">✓ Є запас</span></td>
                    </tr>
                    <tr>
                      <td>Ставка дисконтування</td>
                      <td>{(base.discount_rate * 100).toFixed(1)}%</td>
                      <td>{breakevenResult.breakeven_discount_rate}%</td>
                      <td style={{ color: '#065f46' }}>
                        +{(breakevenResult.breakeven_discount_rate - base.discount_rate * 100).toFixed(1)}%
                      </td>
                      <td><span className="badge badge-green">✓ Є запас</span></td>
                    </tr>
                    <tr>
                      <td>Мін. термін окупності</td>
                      <td>{base.lifetime_years} р.</td>
                      <td>{breakevenResult.breakeven_years} р.</td>
                      <td>{base.lifetime_years - breakevenResult.breakeven_years} р. запас</td>
                      <td>
                        <span className={`badge ${
                          breakevenResult.breakeven_years <= base.lifetime_years
                            ? 'badge-green' : 'badge-red'
                        }`}>
                          {breakevenResult.breakeven_years <= base.lifetime_years ? '✓ OK' : '✗ Не окупається'}
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}