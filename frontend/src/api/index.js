import axios from 'axios'

// ─── Client ───────────────────────────────────────────────
// All backend endpoints live under /api/v1. The server-side envelope
// `{data, error, meta}` is unwrapped by the response interceptor below,
// so the rest of the codebase still treats `response.data` as the
// business payload.
const api = axios.create({ baseURL: '/', timeout: 30000 })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ─── Envelope unwrap + 401 redirect ───────────────────────
function isEnvelope(body) {
  return body
    && typeof body === 'object'
    && 'data' in body
    && 'error' in body
    && 'meta' in body
}

api.interceptors.response.use(
  res => {
    // Binary downloads (PDF / Excel) must stay untouched.
    if (res.config.responseType === 'blob') return res
    if (isEnvelope(res.data)) res.data = res.data.data
    return res
  },
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    // Normalise envelope error into the legacy `.detail` surface so existing
    // pages can keep reading `err.response.data.detail`.
    const body = err.response?.data
    if (isEnvelope(body) && body.error) {
      err.response.data = {
        detail: body.error.message,
        code: body.error.code,
        details: body.error.details,
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
    return api.post('/api/v1/auth/login', form)
  },
  // The backend always registers new users as 'analyst'; the client does
  // not send a role to avoid privilege-escalation attempts.
  register: ({ email, username, password }) =>
    api.post('/api/v1/auth/register', { email, username, password }),
  me: () => api.get('/api/v1/auth/me'),
}

// ─── Projects ──────────────────────────────────────────
export const projectAPI = {
  getAll: (params = {}) => api.get('/api/v1/projects/', { params }),
  getOne: (id) => api.get(`/api/v1/projects/${id}`),
  create: (data) => api.post('/api/v1/projects/', data),
  delete: (id) => api.delete(`/api/v1/projects/${id}`),
  addMeasure: (projectId, data) =>
    api.post(`/api/v1/projects/${projectId}/measures`, data),
  deleteMeasure: (projectId, measureId) =>
    api.delete(`/api/v1/projects/${projectId}/measures/${measureId}`),
  // Manager / admin approval workflow.
  updateStatus: (id, newStatus, comment) =>
    api.patch(`/api/v1/projects/${id}/status`, {
      status: newStatus,
      manager_comment: comment || null,
    }),
  approve: (id) => api.patch(`/api/v1/projects/${id}/approve`),
  reject: (id, comment) =>
    api.patch(`/api/v1/projects/${id}/reject`, {
      status: 'rejected',
      manager_comment: comment || null,
    }),
  // Server-side orchestration: runs financial + eco + AHP + TOPSIS +
  // sensitivity + comparison in one call. Used when the client wants a
  // single round-trip instead of the sequenced per-service calls.
  analyzeFull: (id, options = {}) =>
    api.post(`/api/v1/projects/${id}/analyze/full`, options),
}

// ─── Admin (user management) ───────────────────────────
export const adminAPI = {
  getUsers: () => api.get('/api/v1/auth/users'),
  changeRole: (userId, role) =>
    api.patch(`/api/v1/auth/users/${userId}/role`, { role }),
}

// ─── Financial ─────────────────────────────────────────
export const financialAPI = {
  analyze: (data) => api.post('/api/v1/financial/analyze', data),
  analyzePortfolio: (data) =>
    api.post('/api/v1/financial/analyze/portfolio', data),
}

// ─── Eco Impact ────────────────────────────────────────
export const ecoAPI = {
  analyze: (data) => api.post('/api/v1/eco/analyze', data),
  analyzePortfolio: (data) =>
    api.post('/api/v1/eco/analyze/portfolio', data),
}

// ─── Multi-Criteria ────────────────────────────────────
export const multiCriteriaAPI = {
  ahp: (data) => api.post('/api/v1/multicriteria/ahp', data),
  topsis: (data) => api.post('/api/v1/multicriteria/topsis', data),
  combined: (data) => api.post('/api/v1/multicriteria/combined', data),
}

// ─── Scenario ──────────────────────────────────────────
export const scenarioAPI = {
  whatif: (data) => api.post('/api/v1/scenario/whatif', data),
  sensitivity: (data) => api.post('/api/v1/scenario/sensitivity', data),
  breakeven: (data) => api.post('/api/v1/scenario/breakeven', data),
}

// ─── Comparison ────────────────────────────────────────
// Stateless body-driven comparison: the page has already run financial +
// eco analyses client-side and passes the fused measure rows directly.
export const comparisonAPI = {
  compare: (data) => api.post('/api/v1/comparison/compare', data),
}

// ─── Reports ───────────────────────────────────────────
// Body-driven PDF / Excel generation: the page assembles the ReportInput
// from the in-memory analysis results and streams back a binary blob.
async function downloadBinary(url, body, filename) {
  const response = await api.post(url, body, { responseType: 'blob' })
  const href = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = href
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(href)
}

export const reportAPI = {
  generate: (data) =>
    downloadBinary('/api/v1/reports/generate', data, 'eco_report.pdf'),
  generateExcel: (data) =>
    downloadBinary('/api/v1/reports/generate/excel', data, 'eco_report.xlsx'),
}

// ─── CSV client-side export ─────────────────────────────
// Generates a UTF-8 BOM CSV so Excel renders Cyrillic correctly.
export function exportToCSV(results, projectName) {
  const rows = []

  rows.push(['ФІНАНСОВИЙ АНАЛІЗ'])
  rows.push([
    'Захід', 'NPV (грн)', 'IRR (%)', 'BCR',
    'Окупність (рр.)', 'Диск. окупність (рр.)', 'LCCA (грн)',
  ])
  for (const f of results.financial) {
    const irr = f.irr && typeof f.irr === 'object' ? f.irr.value : f.irr
    rows.push([
      f.name,
      f.npv,
      irr != null && irr >= 0 ? irr : 'N/A',
      f.bcr != null ? f.bcr : 'N/A',
      f.simple_payback != null && f.simple_payback > 0 ? f.simple_payback : 'N/A',
      f.discounted_payback != null && f.discounted_payback > 0 ? f.discounted_payback : 'N/A',
      f.lcca,
    ])
  }
  rows.push([])

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

  rows.push(['PARETO-АНАЛІЗ'])
  rows.push(['Захід', 'NPV (грн)', 'CO₂ (т/рік)', 'Pareto-оптимальний'])
  for (const p of results.comparison.pareto_front) {
    rows.push([p.name, p.npv, p.co2_reduction, p.is_pareto_optimal ? 'Так' : 'Ні'])
  }

  const csv = '\uFEFF' + rows.map(r =>
    r.map(cell => {
      const s = String(cell ?? '')
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
