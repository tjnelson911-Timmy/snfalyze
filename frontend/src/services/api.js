import axios from 'axios'
const api = axios.create({ baseURL: '/api' })
export const getDeals = async (params = {}) => (await api.get('/deals', { params })).data
export const getDealStats = async () => (await api.get('/deals/stats')).data
export const getDeal = async (id) => (await api.get('/deals/' + id)).data
export const createDeal = async (data) => (await api.post('/deals', data)).data
export const updateDeal = async (id, data) => (await api.put('/deals/' + id, data)).data
export const deleteDeal = async (id) => (await api.delete('/deals/' + id)).data
export const updateDealStatus = async (id, status) => (await api.put('/deals/' + id + '/status', { status })).data
export const createProperty = async (dealId, data) => (await api.post('/deals/' + dealId + '/properties', data)).data
export const deleteProperty = async (id) => (await api.delete('/properties/' + id)).data
export const uploadDocument = async (dealId, file, category = 'other') => {
  const fd = new FormData(); fd.append('file', file); fd.append('category', category)
  return (await api.post('/deals/' + dealId + '/documents', fd, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}
export const analyzeDocument = async (id) => (await api.post('/documents/' + id + '/analyze')).data
export const deleteDocument = async (id) => (await api.delete('/documents/' + id)).data
export const getValuation = async (dealId) => (await api.get('/deals/' + dealId + '/valuation')).data
export const createTask = async (dealId, data) => (await api.post('/deals/' + dealId + '/tasks', data)).data
export const updateTask = async (id, data) => (await api.put('/tasks/' + id, data)).data
// Analysis endpoints
export const getDealScorecard = async (dealId) => (await api.get('/deals/' + dealId + '/scorecard')).data
export const calculateScorecard = async (dealId) => (await api.post('/deals/' + dealId + '/calculate-scorecard')).data
export const getDealRiskFlags = async (dealId) => (await api.get('/deals/' + dealId + '/risk-flags')).data
export const detectRisks = async (dealId) => (await api.post('/deals/' + dealId + '/detect-risks')).data
export const getFinancialSummary = async (dealId) => (await api.get('/deals/' + dealId + '/financial-summary')).data
export const getDealClaims = async (dealId) => (await api.get('/deals/' + dealId + '/claims')).data
export const runFullAnalysis = async (dealId) => (await api.post('/deals/' + dealId + '/full-analysis')).data
export const getAnalysisJobs = async (dealId) => (await api.get('/deals/' + dealId + '/analysis-jobs')).data
export const verifyClaims = async (dealId) => (await api.post('/deals/' + dealId + '/verify-claims')).data
export const analyzeDocumentFull = async (docId) => (await api.post('/documents/' + docId + '/analyze-full')).data

export const formatCurrency = (v) => v ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v) : '-'
export const formatNumber = (v) => v ? new Intl.NumberFormat('en-US').format(v) : '-'
export const formatPercent = (v) => v != null ? v.toFixed(1) + '%' : '-'
export const formatDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : '-'
export const formatDateTime = (d) => d ? new Date(d).toLocaleString('en-US') : '-'
export default api
