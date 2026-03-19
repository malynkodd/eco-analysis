import axios from 'axios'

// Базовий axios з токеном
const api = axios.create({ baseURL: '/', timeout: 30000 })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Перехоплювач відповідей: 401 → очищаємо токен і редіректимо на логін
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // Уникаємо нескінченного циклу на сторінці логіну
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

// ─── Auth ──────────────────────────────────────────────
export const authAPI = {
  login: (username, password) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return api.post('/api/auth/login', form)
  },
  register: (data) => api.post('/api/auth/register', data),
  me: () => api.get('/api/auth/me'),
}

// ─── Projects ──────────────────────────────────────────
export const projectAPI = {
  getAll: () => api.get('/api/projects/'),
  getOne: (id) => api.get(`/api/projects/${id}`),
  create: (data) => api.post('/api/projects/', data),
  delete: (id) => api.delete(`/api/projects/${id}`),
  addMeasure: (projectId, data) =>
    api.post(`/api/projects/${projectId}/measures`, data),
  deleteMeasure: (projectId, measureId) =>
    api.delete(`/api/projects/${projectId}/measures/${measureId}`),
  // Затвердження/відхилення проєкту (тільки менеджер/адмін)
  updateStatus: (id, newStatus, comment) =>
    api.patch(`/api/projects/${id}/status`, { status: newStatus, manager_comment: comment || null }),
  approve: (id) =>
    api.patch(`/api/projects/${id}/approve`),
  reject: (id, comment) =>
    api.patch(`/api/projects/${id}/reject`, { status: 'rejected', manager_comment: comment || null }),
}

// ─── Admin (user management) ───────────────────────────
export const adminAPI = {
  getUsers: () => api.get('/api/auth/users'),
  changeRole: (userId, role) =>
    api.patch(`/api/auth/users/${userId}/role`, { role }),
}

// ─── Financial ─────────────────────────────────────────
export const financialAPI = {
  analyze: (data) => api.post('/api/financial/analyze', data),
  analyzePortfolio: (data) =>
    api.post('/api/financial/analyze/portfolio', data),
}

// ─── Eco Impact ────────────────────────────────────────
export const ecoAPI = {
  analyze: (data) => api.post('/api/eco/analyze', data),
  analyzePortfolio: (data) =>
    api.post('/api/eco/analyze/portfolio', data),
}

// ─── Multi-Criteria ────────────────────────────────────
export const multiCriteriaAPI = {
  ahp: (data) => api.post('/api/multicriteria/ahp', data),
  topsis: (data) => api.post('/api/multicriteria/topsis', data),
  combined: (data) => api.post('/api/multicriteria/combined', data),
}

// ─── Scenario ──────────────────────────────────────────
export const scenarioAPI = {
  whatif: (data) => api.post('/api/scenario/whatif', data),
  sensitivity: (data) => api.post('/api/scenario/sensitivity', data),
  breakeven: (data) => api.post('/api/scenario/breakeven', data),
}

// ─── Comparison ────────────────────────────────────────
export const comparisonAPI = {
  compare: (data) => api.post('/api/comparison/compare', data),
}

// ─── Reports ───────────────────────────────────────────
export const reportAPI = {
  // PDF звіт
  generate: async (data) => {
    const response = await api.post('/api/reports/generate', data, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'eco_report.pdf')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  // Excel звіт
  generateExcel: async (data) => {
    const response = await api.post('/api/reports/generate/excel', data, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'eco_report.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

// ─── Excel/CSV Export ──────────────────────────────────
/**
 * Генерує та завантажує CSV-файл з результатами аналізу.
 * Файл сумісний з Microsoft Excel (кодування UTF-8 BOM, роздільник ";").
 *
 * @param {object} results  — об'єкт із полями: financial[], eco, comparison
 * @param {string} projectName — назва проєкту (використовується у назві файлу)
 */
export function exportToCSV(results, projectName) {
  const rows = []

  // ── Секція 1: Фінансовий аналіз ──────────────────────
  rows.push(['ФІНАНСОВИЙ АНАЛІЗ'])
  rows.push([
    'Захід', 'NPV (грн)', 'IRR (%)', 'BCR',
    'Окупність (рр.)', 'Диск. окупність (рр.)', 'LCCA (грн)',
  ])
  for (const f of results.financial) {
    rows.push([
      f.name,
      f.npv,
      f.irr >= 0 ? f.irr : 'N/A',
      f.bcr,
      f.simple_payback > 0 ? f.simple_payback : 'N/A',
      f.discounted_payback > 0 ? f.discounted_payback : 'N/A',
      f.lcca,
    ])
  }
  rows.push([])

  // ── Секція 2: Екологічний ефект ───────────────────────
  rows.push(['ЕКОЛОГІЧНИЙ ЕФЕКТ'])
  rows.push([
    'Захід', 'Зменшення CO₂ (т/рік)',
    'Відвернений збиток (грн/рік)', 'Вартість CO₂ (USD/рік)',
  ])
  for (const e of results.eco.results) {
    rows.push([
      e.name,
      e.co2_reduction_tons_per_year,
      e.averted_damage_uah,
      e.total_co2_value_usd,
    ])
  }
  rows.push([
    'РАЗОМ',
    results.eco.total_co2_reduction,
    results.eco.total_averted_damage_uah,
    '',
  ])
  rows.push([])

  // ── Секція 3: Зведений рейтинг ────────────────────────
  rows.push(['ЗВЕДЕНИЙ РЕЙТИНГ'])
  rows.push([
    'Захід', 'Ранг NPV', 'Ранг IRR', 'Ранг BCR',
    'Ранг Payback', 'Ранг CO₂',
    'Ранг AHP', 'Ранг TOPSIS',
    'Консенсусний бал', 'Місце',
  ])
  for (const r of results.comparison.ranking_table) {
    rows.push([
      r.name,
      r.rank_npv, r.rank_irr, r.rank_bcr,
      r.rank_payback, r.rank_co2,
      r.rank_ahp ?? '',
      r.rank_topsis ?? '',
      r.consensus_score,
      r.consensus_rank,
    ])
  }
  rows.push([])

  // ── Секція 4: Pareto-аналіз ───────────────────────────
  rows.push(['PARETO-АНАЛІЗ'])
  rows.push(['Захід', 'NPV (грн)', 'CO₂ (т/рік)', 'Pareto-оптимальний'])
  for (const p of results.comparison.pareto_front) {
    rows.push([p.name, p.npv, p.co2_reduction, p.is_pareto_optimal ? 'Так' : 'Ні'])
  }

  // UTF-8 BOM забезпечує правильне відображення кирилиці в Excel
  const csv = '\uFEFF' + rows.map(r =>
    r.map(cell => {
      const s = String(cell ?? '')
      // Якщо клітинка містить роздільник або лапки — обгортаємо в лапки
      return s.includes(';') || s.includes('"') || s.includes('\n')
        ? `"${s.replace(/"/g, '""')}"` : s
    }).join(';')
  ).join('\n')

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${projectName.replace(/[^\w\u0400-\u04FF]/g, '_')}_аналіз.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
