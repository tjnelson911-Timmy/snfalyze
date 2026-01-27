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

// Enhanced analysis endpoints
export const getMarketAnalysis = async (dealId) => (await api.get('/deals/' + dealId + '/market-analysis')).data
export const runMarketAnalysis = async (dealId) => (await api.post('/deals/' + dealId + '/market-analysis')).data
export const getPropertyResearch = async (dealId) => (await api.get('/deals/' + dealId + '/property-research')).data
export const runPropertyResearch = async (dealId) => (await api.post('/deals/' + dealId + '/property-research')).data
export const getDeepFinancialAnalysis = async (dealId) => (await api.get('/deals/' + dealId + '/deep-financial-analysis')).data
export const runDeepFinancialAnalysis = async (dealId) => (await api.post('/deals/' + dealId + '/deep-financial-analysis')).data
export const runComprehensiveAnalysis = async (dealId) => (await api.post('/deals/' + dealId + '/comprehensive-analysis')).data

export const formatCurrency = (v) => v ? new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(v) : '-'
export const formatNumber = (v) => v ? new Intl.NumberFormat('en-US').format(v) : '-'
export const formatPercent = (v) => v != null ? v.toFixed(1) + '%' : '-'
export const formatDate = (d) => d ? new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) : '-'
export const formatDateTime = (d) => d ? new Date(d).toLocaleString('en-US') : '-'

// ============================================================================
// WELCOME NIGHTS PRESENTATION BUILDER API
// ============================================================================

// Brands
export const getWNBrands = async () => (await api.get('/wn/brands')).data
export const getWNBrand = async (id) => (await api.get('/wn/brands/' + id)).data
export const createWNBrand = async (data) => (await api.post('/wn/brands', data)).data
export const updateWNBrand = async (id, data) => (await api.put('/wn/brands/' + id, data)).data

// Facilities
export const getWNFacilities = async (params = {}) => (await api.get('/wn/facilities', { params })).data
export const getWNFacility = async (id) => (await api.get('/wn/facilities/' + id)).data
export const createWNFacility = async (data) => (await api.post('/wn/facilities', data)).data
export const updateWNFacility = async (id, data) => (await api.put('/wn/facilities/' + id, data)).data
export const deleteWNFacility = async (id) => (await api.delete('/wn/facilities/' + id)).data
export const importWNFacilities = async (brandId, file) => {
  const fd = new FormData()
  fd.append('brand_id', brandId)
  fd.append('file', file)
  return (await api.post('/wn/facilities/import', fd, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}
export const uploadFacilityLogo = async (facilityId, file) => {
  const fd = new FormData()
  fd.append('file', file)
  return (await api.post(`/wn/facilities/${facilityId}/logo`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}
export const deleteFacilityLogo = async (facilityId) => (await api.delete(`/wn/facilities/${facilityId}/logo`)).data

// Templates
export const getWNTemplates = async () => (await api.get('/wn/templates')).data
export const uploadWNTemplate = async (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return (await api.post('/wn/templates', fd, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}
export const deleteWNTemplate = async (filename) => (await api.delete(`/wn/templates/${encodeURIComponent(filename)}`)).data

// Assets
export const getWNAssets = async (params = {}) => (await api.get('/wn/assets', { params })).data
export const uploadWNAsset = async (brandId, assetType, file) => {
  const fd = new FormData()
  fd.append('brand_id', brandId)
  fd.append('asset_type', assetType)
  fd.append('file', file)
  return (await api.post('/wn/assets', fd, { headers: { 'Content-Type': 'multipart/form-data' } })).data
}
export const deleteWNAsset = async (id) => (await api.delete('/wn/assets/' + id)).data

// Agenda Templates
export const getWNAgendaTemplates = async (params = {}) => (await api.get('/wn/agenda-templates', { params })).data
export const getWNAgendaTemplate = async (id) => (await api.get('/wn/agenda-templates/' + id)).data
export const createWNAgendaTemplate = async (data) => (await api.post('/wn/agenda-templates', data)).data
export const updateWNAgendaTemplate = async (id, data) => (await api.put('/wn/agenda-templates/' + id, data)).data
export const deleteWNAgendaTemplate = async (id) => (await api.delete('/wn/agenda-templates/' + id)).data

// Reusable Content
export const getWNContent = async (brandId, contentKey = null) => {
  const params = { brand_id: brandId }
  if (contentKey) params.content_key = contentKey
  return (await api.get('/wn/content', { params })).data
}
export const getWNContentItem = async (id) => (await api.get('/wn/content/' + id)).data
export const createWNContent = async (data) => (await api.post('/wn/content', data)).data
export const updateWNContent = async (id, data) => (await api.put('/wn/content/' + id, data)).data

// Games
export const getWNGames = async (params = {}) => (await api.get('/wn/games', { params })).data
export const getWNGame = async (id) => (await api.get('/wn/games/' + id)).data
export const createWNGame = async (data) => (await api.post('/wn/games', data)).data
export const updateWNGame = async (id, data) => (await api.put('/wn/games/' + id, data)).data
export const deleteWNGame = async (id) => (await api.delete('/wn/games/' + id)).data

// Presentations
export const getWNPresentations = async (params = {}) => (await api.get('/wn/presentations', { params })).data
export const getWNPresentation = async (id) => (await api.get('/wn/presentations/' + id)).data
export const createWNPresentation = async (data) => (await api.post('/wn/presentations', data)).data
export const updateWNPresentation = async (id, data) => (await api.put('/wn/presentations/' + id, data)).data
export const deleteWNPresentation = async (id) => (await api.delete('/wn/presentations/' + id)).data

// Slide building
export const buildWNSlides = async (presentationId, config) => (await api.post('/wn/presentations/' + presentationId + '/build-slides', config)).data
export const getWNSlides = async (presentationId) => (await api.get('/wn/presentations/' + presentationId + '/slides')).data

// Present mode
export const getWNPresentData = async (presentationId) => (await api.get('/wn/presentations/' + presentationId + '/present')).data
export const markWNPresented = async (presentationId) => (await api.post('/wn/presentations/' + presentationId + '/mark-presented')).data

// Export
export const getWNExportPptxUrl = (presentationId) => '/api/wn/presentations/' + presentationId + '/export/pptx'
export const getWNExportPdfUrl = (presentationId) => '/api/wn/presentations/' + presentationId + '/export/pdf'

export default api
