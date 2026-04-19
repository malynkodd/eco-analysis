import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, Cell
} from 'recharts'
import {
  projectAPI, financialAPI, ecoAPI,
  comparisonAPI, reportAPI, scenarioAPI
} from '../api'
import { useAuth } from '../context/AuthContext'
import TornadoMini from '../components/TornadoMini'

export default function AnalysisPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user, canAnalyze, canReport } = useAuth()

  const [project, setProject]             = useState(null)
  const [results, setResults]             = useState(null)
  const [loading, setLoading]             = useState(false)
  const [error, setError]                 = useState('')
  const [activeTab, setActiveTab]         = useState('financial')
  const [reportLoading, setReportLoading] = useState(false)
  const [discountRate, setDiscountRate]   = useState(0.1)

  useEffect(() => { loadProject() }, [id])

  const loadProject = async () => {
    try {
      const res = await projectAPI.getOne(id)
      setProject(res.data)
    } catch {
      setError('Помилка завантаження проєкту')
    }
  }

  const runAnalysis = async () => {
    setLoading(true)
    setError('')
    try {
      const measures = project.measures

      const financialRes = await financialAPI.analyzePortfolio({
        measures: measures.map(m => ({
          name: m.name,
          initial_investment: m.initial_investment,
          operational_cost: m.operational_cost,
          expected_savings: m.expected_savings,
          lifetime_years: m.lifetime_years,
          discount_rate: discountRate,
        })),
        discount_rate: discountRate,
      })

      // emission_reduction is stored in tons CO2/year.
      // Eco service expects annual_consumption_reduction in kWh (for electricity).
      // Electricity emission factor = 0.37 kg CO2/kWh = 0.00037 t CO2/kWh
      // kWh = tons_CO2 / 0.00037 = tons_CO2 * (1000 / 0.37)
      const ecoRes = await ecoAPI.analyzePortfolio({
        measures: measures.map(m => ({
          name: m.name,
          fuel_type: 'electricity',
          annual_consumption_reduction: m.emission_reduction * (1000 / 0.37),
          co2_price_per_ton: 30,
          damage_coefficient: 100,
        })),
      })

      const comparisonData = financialRes.data.results.map((f, i) => ({
        name: f.name,
        npv: f.npv,
        // financial-service returns irr as {value, converged, iterations};
        // the comparison-service expects a plain Optional[float] percent.
        irr: f.irr?.value ?? null,
        bcr: f.bcr ?? null,
        simple_payback: f.simple_payback ?? null,
        co2_reduction: ecoRes.data.results[i]?.co2_reduction_tons_per_year || 0,
      }))

      const compRes = await comparisonAPI.compare({ measures: comparisonData })

      setResults({
        financial: financialRes.data.results,
        eco: ecoRes.data,
        comparison: compRes.data,
      })
      setActiveTab('financial')
    } catch (err) {
      setError('Помилка аналізу: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const buildReportPayload = async () => {
    let sensitivityData = null
    try {
      const firstMeasure = project.measures[0]
      const sensRes = await scenarioAPI.sensitivity({
        base: {
          name: firstMeasure.name,
          initial_investment: firstMeasure.initial_investment,
          operational_cost: firstMeasure.operational_cost,
          expected_savings: firstMeasure.expected_savings,
          lifetime_years: firstMeasure.lifetime_years,
          discount_rate: discountRate,
        },
        variation_percent: 20,
        steps: 3,
      })
      sensitivityData = sensRes.data.results.map(r => ({
        parameter: r.parameter,
        impact_percent: r.impact_percent,
      }))
    } catch {}

    return {
      project_name: project.name,
      project_description: project.description || '',
      analyst_name: user.username,
      financial_results: results.financial.map(f => ({
        name: f.name,
        npv: f.npv,
        // Report service schema wants plain floats; coerce IRRResult and
        // null-valued optionals so the PDF/Excel renderer has numbers.
        irr: f.irr?.value ?? 0,
        bcr: f.bcr ?? 0,
        simple_payback: f.simple_payback ?? 0,
        discounted_payback: f.discounted_payback ?? 0,
        lcca: f.lcca,
        yearly_details: f.yearly_details || null,
      })),
      eco_results: results.eco.results.map(e => ({
        name: e.name,
        co2_reduction_tons_per_year: e.co2_reduction_tons_per_year,
        averted_damage_uah: e.averted_damage_uah,
        total_co2_value_usd: e.total_co2_value_usd,
      })),
      ranking: results.comparison.ranking_table.map(r => ({
        name: r.name,
        consensus_rank: r.consensus_rank,
        rank_npv: r.rank_npv,
        rank_co2: r.rank_co2,
        rank_ahp: r.rank_ahp || null,
        rank_topsis: r.rank_topsis || null,
      })),
      best_measure: results.comparison.best_consensus,
      recommendation:
        `Based on analysis of ${project.measures.length} measures, ` +
        `${results.comparison.best_consensus} is recommended. ` +
        `Financial leader: ${results.comparison.best_financial}. ` +
        `Ecological leader: ${results.comparison.best_ecological}.`,
      sensitivity_data: sensitivityData,
    }
  }

  const downloadReport = async () => {
    if (!results) return
    setReportLoading(true)
    try {
      const payload = await buildReportPayload()
      await reportAPI.generate(payload)
    } catch {
      setError('Помилка генерації PDF')
    } finally {
      setReportLoading(false)
    }
  }

  const downloadExcel = async () => {
    if (!results) return
    setReportLoading(true)
    try {
      const payload = await buildReportPayload()
      await reportAPI.generateExcel(payload)
    } catch {
      setError('Помилка генерації Excel')
    } finally {
      setReportLoading(false)
    }
  }

  if (!project) return (
    <div className="loader"><div className="spinner"></div> Завантаження...</div>
  )

  const tabs = [
    { key: 'financial',  label: '💰 Фінансовий' },
    { key: 'eco',        label: '🌿 Екологічний' },
    { key: 'comparison', label: '📊 Порівняння' },
    { key: 'charts',     label: '📈 Графіки' },
  ]

  const COLORS = ['#0f4c81', '#00b894', '#6c5ce7', '#e17055', '#fdcb6e']

  return (
    <div className="container" style={{ paddingTop: '32px', paddingBottom: '40px' }}>

      <div className="breadcrumb">
        <a onClick={() => navigate('/')}>Проєкти</a>
        <span className="breadcrumb-sep">›</span>
        <a onClick={() => navigate(`/projects/${id}`)}>{project.name}</a>
        <span className="breadcrumb-sep">›</span>
        <span>Аналіз</span>
      </div>

      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: '24px',
      }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#0f4c81' }}>
          📊 Аналіз: {project.name}
        </h1>

        {results && canReport && (
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              className="btn btn-success btn-lg"
              onClick={downloadReport}
              disabled={reportLoading}
            >
              {reportLoading ? '⏳...' : '📄 PDF'}
            </button>
            <button
              className="btn btn-lg"
              style={{ background: '#1e8449', color: 'white' }}
              onClick={downloadExcel}
              disabled={reportLoading}
            >
              {reportLoading ? '⏳...' : '📊 Excel'}
            </button>
          </div>
        )}
      </div>

      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap' }}>
          <div>
            <label style={{ marginBottom: '6px' }}>Ставка дисконтування</label>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <input
                type="range" min="0.01" max="0.3" step="0.01"
                value={discountRate}
                onChange={e => setDiscountRate(parseFloat(e.target.value))}
                style={{ width: '160px', marginBottom: 0 }}
              />
              <strong style={{ color: '#0f4c81', fontSize: '20px' }}>
                {(discountRate * 100).toFixed(0)}%
              </strong>
            </div>
          </div>

          <div style={{ marginLeft: 'auto', textAlign: 'right' }}>
            <div style={{ fontSize: '13px', color: '#718096', marginBottom: '8px' }}>
              Заходів у портфелі:{' '}
              <strong style={{ color: '#0f4c81' }}>{project.measures.length}</strong>
            </div>
            <button
              className="btn btn-primary btn-lg"
              onClick={runAnalysis}
              disabled={loading || !canAnalyze}
              title={!canAnalyze ? 'Тільки аналітик може запускати аналіз' : ''}
              style={{ opacity: canAnalyze ? 1 : 0.5 }}
            >
              {loading
                ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div className="spinner" style={{ width: '16px', height: '16px' }}></div>
                    Аналіз...
                  </span>
                )
                : '▶ Запустити аналіз'
              }
            </button>
            {!canAnalyze && (
              <div style={{ fontSize: '11px', color: '#e17055', marginTop: '4px' }}>
                Роль менеджера — тільки перегляд
              </div>
            )}
          </div>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {results && (
        <>
          <div className="grid-3" style={{ marginBottom: '8px' }}>
            <div className="stat-card">
              <div className="stat-label">Найкращий фінансово</div>
              <div className="stat-value" style={{ fontSize: '16px' }}>
                💰 {results.comparison.best_financial}
              </div>
            </div>
            <div className="stat-card green">
              <div className="stat-label">Найкращий екологічно</div>
              <div className="stat-value" style={{ fontSize: '16px' }}>
                🌿 {results.comparison.best_ecological}
              </div>
            </div>
            <div className="stat-card purple">
              <div className="stat-label">Консенсусний вибір</div>
              <div className="stat-value" style={{ fontSize: '16px' }}>
                🏆 {results.comparison.best_consensus}
              </div>
            </div>
          </div>

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

          {activeTab === 'financial' && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">💰 Фінансовий аналіз</span>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Захід</th>
                      <th>NPV (грн)</th>
                      <th>IRR (%)</th>
                      <th>BCR</th>
                      <th>Окупність (р.)</th>
                      <th>Диск. окупність</th>
                      <th>LCCA (грн)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.financial.map(f => {
                      const irr = f.irr?.value ?? null
                      return (
                      <tr key={f.name}>
                        <td><strong>{f.name}</strong></td>
                        <td style={{ color: f.npv > 0 ? '#065f46' : '#991b1b', fontWeight: 600 }}>
                          {f.npv.toLocaleString()} ₴
                        </td>
                        <td>
                          {irr == null ? (
                            <span className="badge badge-gray">N/A</span>
                          ) : (
                            <span className={`badge ${irr > discountRate * 100 ? 'badge-green' : 'badge-red'}`}>
                              {irr}%
                            </span>
                          )}
                        </td>
                        <td>
                          {f.bcr == null ? (
                            <span className="badge badge-gray">N/A</span>
                          ) : (
                            <span className={`badge ${f.bcr > 1 ? 'badge-green' : 'badge-red'}`}>
                              {f.bcr}
                            </span>
                          )}
                        </td>
                        <td>{f.simple_payback != null && f.simple_payback > 0 ? f.simple_payback + ' р.' : 'N/A'}</td>
                        <td>{f.discounted_payback != null && f.discounted_payback > 0 ? f.discounted_payback + ' р.' : 'N/A'}</td>
                        <td>{f.lcca.toLocaleString()} ₴</td>
                      </tr>
                    )})}
                  </tbody>
                </table>
              </div>
              <div style={{
                marginTop: '12px', padding: '10px 14px',
                background: '#f7fafd', borderRadius: '8px',
                fontSize: '12px', color: '#718096',
              }}>
                💡 <strong>NPV &gt; 0</strong> = прибутковий.
                <strong> IRR &gt; {(discountRate * 100).toFixed(0)}%</strong> = ефективний.
                <strong> BCR &gt; 1</strong> = вигоди перевищують витрати.
              </div>
            </div>
          )}

          {activeTab === 'eco' && (
            <div className="card">
              <div className="card-header">
                <span className="card-title">🌿 Екологічний ефект</span>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Захід</th>
                      <th>Зменшення CO₂ (т/рік)</th>
                      <th>Відвернений збиток (грн)</th>
                      <th>Вартість CO₂ (USD)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.eco.results.map(e => (
                      <tr key={e.name}>
                        <td><strong>{e.name}</strong></td>
                        <td style={{ color: '#065f46', fontWeight: 600 }}>
                          {e.co2_reduction_tons_per_year} т
                        </td>
                        <td>{e.averted_damage_uah.toLocaleString()} ₴</td>
                        <td>${e.total_co2_value_usd.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div style={{
                marginTop: '12px', padding: '12px 16px',
                background: '#d1fae5', borderRadius: '8px',
                fontSize: '13px', color: '#065f46',
              }}>
                <strong>Разом: </strong>
                {results.eco.total_co2_reduction} т CO₂/рік |{' '}
                {results.eco.total_averted_damage_uah.toLocaleString()} ₴ відвернений збиток
              </div>
            </div>
          )}

          {activeTab === 'comparison' && (
            <div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">📊 Зведений рейтинг</span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Захід</th>
                        <th>Ранг NPV</th>
                        <th>Ранг IRR</th>
                        <th>Ранг BCR</th>
                        <th>Ранг Payback</th>
                        <th>Ранг CO₂</th>
                        <th>Консенсус</th>
                        <th>Місце</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.comparison.ranking_table.map(r => (
                        <tr key={r.name}>
                          <td><strong>{r.name}</strong></td>
                          <td>#{r.rank_npv}</td>
                          <td>#{r.rank_irr}</td>
                          <td>#{r.rank_bcr}</td>
                          <td>#{r.rank_payback}</td>
                          <td>#{r.rank_co2}</td>
                          <td>{r.consensus_score}</td>
                          <td>
                            <span className={`badge ${
                              r.consensus_rank === 1 ? 'badge-green' :
                              r.consensus_rank === 2 ? 'badge-blue' : 'badge-gray'
                            }`}>
                              #{r.consensus_rank}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <span className="card-title">🔷 Pareto-аналіз (NPV vs CO₂)</span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Захід</th>
                        <th>NPV (грн)</th>
                        <th>CO₂ (т/рік)</th>
                        <th>Pareto-оптимальний</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.comparison.pareto_front.map(p => (
                        <tr key={p.name}>
                          <td><strong>{p.name}</strong></td>
                          <td>{p.npv.toLocaleString()} ₴</td>
                          <td>{p.co2_reduction}</td>
                          <td>
                            <span className={`badge ${p.is_pareto_optimal ? 'badge-green' : 'badge-gray'}`}>
                              {p.is_pareto_optimal ? '✓ Так' : '✗ Ні'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {results.comparison.conflicting.length > 0 && (
                  <div className="alert alert-info" style={{ marginTop: '12px' }}>
                    ⚠️ Суперечливі заходи:{' '}
                    <strong>{results.comparison.conflicting.join(', ')}</strong>
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'charts' && (
            <div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">NPV по заходах (грн)</span>
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={results.financial.map(f => ({ name: f.name, NPV: f.npv }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                    <YAxis tickFormatter={v => v.toLocaleString()} />
                    <Tooltip formatter={v => [v.toLocaleString() + ' ₴', 'NPV']} />
                    <Bar dataKey="NPV" radius={[4, 4, 0, 0]}>
                      {results.financial.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="grid-2">
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">IRR (%) по заходах</span>
                  </div>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={results.financial.map(f => ({ name: f.name, IRR: f.irr?.value ?? 0 }))}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis />
                      <Tooltip formatter={v => [v + '%', 'IRR']} />
                      <Bar dataKey="IRR" radius={[4, 4, 0, 0]}>
                        {results.financial.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                <div className="card">
                  <div className="card-header">
                    <span className="card-title" style={{ color: '#065f46' }}>
                      CO₂ зменшення (т/рік)
                    </span>
                  </div>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={results.eco.results.map(e => ({
                      name: e.name, CO2: e.co2_reduction_tons_per_year,
                    }))}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                      <YAxis />
                      <Tooltip formatter={v => [v + ' т', 'CO₂']} />
                      <Bar dataKey="CO2" fill="#00b894" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <span className="card-title">Динаміка NPV по роках</span>
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="year"
                      type="number"
                      domain={['dataMin', 'dataMax']}
                      label={{ value: 'Рік', position: 'insideBottom', offset: -4 }}
                    />
                    <YAxis tickFormatter={v => v.toLocaleString()} />
                    <Tooltip formatter={v => [v.toLocaleString() + ' ₴']} />
                    <Legend />
                    {results.financial.map((f, i) => (
                      <Line
                        key={f.name}
                        data={f.yearly_details?.map(d => ({
                          year: d.year,
                          [f.name]: d.cumulative_discounted,
                        }))}
                        type="monotone"
                        dataKey={f.name}
                        stroke={COLORS[i % COLORS.length]}
                        strokeWidth={2}
                        dot={false}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="card">
                <div className="card-header">
                  <span className="card-title">Radar — порівняння заходів</span>
                </div>
                <ResponsiveContainer width="100%" height={320}>
                  <RadarChart data={[
                    { metric: 'NPV', ...Object.fromEntries(results.financial.map(f => [f.name, Math.max(0, f.npv / 1000)])) },
                    { metric: 'IRR', ...Object.fromEntries(results.financial.map(f => [f.name, Math.max(0, f.irr?.value ?? 0)])) },
                    { metric: 'BCR×10', ...Object.fromEntries(results.financial.map(f => [f.name, Math.max(0, (f.bcr ?? 0) * 10)])) },
                    { metric: 'CO₂', ...Object.fromEntries(results.eco.results.map(e => [e.name, e.co2_reduction_tons_per_year])) },
                    { metric: 'Payback inv', ...Object.fromEntries(results.financial.map(f => [f.name, Math.max(0, 20 - (f.simple_payback ?? 20))])) },
                  ]}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="metric" />
                    {results.financial.map((f, i) => (
                      <Radar
                        key={f.name}
                        name={f.name}
                        dataKey={f.name}
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

              <div className="card">
                <div className="card-header">
                  <span className="card-title">🌪️ Tornado Chart — чутливість NPV</span>
                </div>
                <p style={{ color: '#718096', fontSize: '13px', marginBottom: '16px' }}>
                  Вплив зміни параметрів ±20% на NPV заходу{' '}
                  <strong>{results.financial[0]?.name}</strong>
                </p>
                {results.financial[0] && (
                  <TornadoMini
                    measure={project.measures[0]}
                    discountRate={discountRate}
                  />
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
