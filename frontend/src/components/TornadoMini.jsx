import { useState, useEffect } from 'react'
import { scenarioAPI } from '../api'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'

export default function TornadoMini({ measure, discountRate }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  const PARAM_LABELS = {
    expected_savings:   'Очікувана економія',
    initial_investment: 'Початкові інвестиції',
    discount_rate:      'Ставка дисконтування',
    operational_cost:   'Операційні витрати',
    lifetime_years:     'Термін (років)',
  }

  useEffect(() => {
    if (!measure) return

    let cancelled = false

    const fetchData = async () => {
      setLoading(true)
      try {
        const res = await scenarioAPI.sensitivity({
          base: {
            name: measure.name,
            initial_investment: measure.initial_investment || 500000,
            operational_cost:   measure.operational_cost   || 5000,
            expected_savings:   measure.expected_savings   || 80000,
            lifetime_years:     measure.lifetime_years     || 15,
            discount_rate:      discountRate,
          },
          variation_percent: 20,
          steps: 3,
        })
        if (!cancelled) setData(res.data)
      } catch {
        // ігноруємо помилку
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()

    return () => { cancelled = true }
  }, [measure?.name, discountRate])

  if (loading) return (
    <div className="loader">
      <div className="spinner"></div> Розрахунок...
    </div>
  )
  if (!data) return null

  const chartData = data.results.map(r => ({
    name: PARAM_LABELS[r.parameter] || r.parameter,
    impact: Math.round(r.impact_percent),
  }))

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ left: 140, right: 40, top: 5, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          type="number"
          tickFormatter={v => v.toLocaleString()}
          label={{ value: 'Вплив на NPV (грн)', position: 'insideBottom', offset: -2, fontSize: 11 }}
        />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={135} />
        <Tooltip formatter={v => [v.toLocaleString() + ' ₴', 'Вплив на NPV']} />
        <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
          {chartData.map((_, i) => (
            <Cell
              key={i}
              fill={['#0f4c81','#1a6baf','#6c5ce7','#00b894','#e17055'][i % 5]}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}