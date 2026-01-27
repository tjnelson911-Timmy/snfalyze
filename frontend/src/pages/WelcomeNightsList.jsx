import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, Play, Edit2, Trash2, Download, FileText } from 'lucide-react'
import {
  getWNPresentations,
  getWNBrands,
  getWNFacilities,
  deleteWNPresentation,
  formatDate,
  getWNExportPptxUrl,
  getWNExportPdfUrl
} from '../services/api'

function WelcomeNightsList() {
  const navigate = useNavigate()
  const [presentations, setPresentations] = useState([])
  const [brands, setBrands] = useState([])
  const [facilities, setFacilities] = useState([])
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState({
    brand_id: '',
    facility_id: '',
    search: ''
  })

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    loadPresentations()
  }, [filters])

  const loadData = async () => {
    try {
      const [brandsData, facilitiesData] = await Promise.all([
        getWNBrands(),
        getWNFacilities()
      ])
      setBrands(brandsData)
      setFacilities(facilitiesData)
      await loadPresentations()
    } catch (err) {
      console.error('Error loading data:', err)
    }
  }

  const loadPresentations = async () => {
    setLoading(true)
    try {
      const params = {}
      if (filters.brand_id) params.brand_id = filters.brand_id
      if (filters.facility_id) params.facility_id = filters.facility_id
      if (filters.search) params.search = filters.search
      const data = await getWNPresentations(params)
      setPresentations(data)
    } catch (err) {
      console.error('Error loading presentations:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id, e) => {
    e.stopPropagation()
    if (!window.confirm('Are you sure you want to delete this presentation?')) return
    try {
      await deleteWNPresentation(id)
      loadPresentations()
    } catch (err) {
      console.error('Error deleting presentation:', err)
    }
  }

  const getBrandName = (brandId) => {
    const brand = brands.find(b => b.id === brandId)
    return brand ? brand.name : ''
  }

  const getBrandSlug = (brandId) => {
    const brand = brands.find(b => b.id === brandId)
    return brand ? brand.slug : ''
  }

  const getFacilityName = (facilityId) => {
    const facility = facilities.find(f => f.id === facilityId)
    return facility ? facility.name : ''
  }

  const getStatusBadge = (status) => {
    const styles = {
      draft: { background: '#f3f4f6', color: '#6b7280' },
      ready: { background: '#dbeafe', color: '#1d4ed8' },
      presented: { background: '#dcfce7', color: '#15803d' },
      archived: { background: '#fef3c7', color: '#b45309' }
    }
    return styles[status] || styles.draft
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Welcome Nights</h1>
          <p className="page-subtitle">Culture Night & Welcome Night presentations</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/welcome-nights/new')}>
          <Plus size={18} />
          <span>New Presentation</span>
        </button>
      </div>

      <div className="card mb-4">
        <div className="wn-filters">
          <div className="form-group" style={{ marginBottom: 0 }}>
            <select
              className="form-select"
              value={filters.brand_id}
              onChange={(e) => setFilters({ ...filters, brand_id: e.target.value, facility_id: '' })}
            >
              <option value="">All Brands</option>
              {brands.map(brand => (
                <option key={brand.id} value={brand.id}>{brand.name}</option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <select
              className="form-select"
              value={filters.facility_id}
              onChange={(e) => setFilters({ ...filters, facility_id: e.target.value })}
            >
              <option value="">All Facilities</option>
              {facilities
                .filter(f => !filters.brand_id || f.brand_id === parseInt(filters.brand_id))
                .map(facility => (
                  <option key={facility.id} value={facility.id}>{facility.name}</option>
                ))}
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 0, position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#9ca3af' }} />
            <input
              type="text"
              className="form-input"
              placeholder="Search presentations..."
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              style={{ paddingLeft: 36 }}
            />
          </div>
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <div className="animate-spin" style={{ width: 40, height: 40, border: '3px solid #e5e7eb', borderTopColor: '#0b7280', borderRadius: '50%', margin: '0 auto 16px' }} />
          <p>Loading presentations...</p>
        </div>
      ) : presentations.length === 0 ? (
        <div className="empty-state">
          <FileText size={48} className="empty-state-icon" />
          <h3 className="empty-state-title">No presentations yet</h3>
          <p className="empty-state-text">Create your first Welcome Night presentation</p>
          <button className="btn btn-primary mt-4" onClick={() => navigate('/welcome-nights/new')}>
            <Plus size={18} />
            <span>New Presentation</span>
          </button>
        </div>
      ) : (
        <div className="wn-presentations-grid">
          {presentations.map(presentation => (
            <div
              key={presentation.id}
              className="wn-presentation-card"
              onClick={() => navigate(`/welcome-nights/${presentation.id}/edit`)}
            >
              <div className="wn-presentation-card-header">
                <div>
                  <div className="wn-presentation-title">{presentation.title}</div>
                  <div className="wn-presentation-facility">{getFacilityName(presentation.facility_id)}</div>
                </div>
                <span className={`wn-brand-badge ${getBrandSlug(presentation.brand_id)}`}>
                  {getBrandName(presentation.brand_id)}
                </span>
              </div>

              <div className="wn-presentation-meta">
                <span
                  className="status-badge"
                  style={getStatusBadge(presentation.status)}
                >
                  {presentation.status}
                </span>
                <span>{formatDate(presentation.created_at)}</span>
              </div>

              <div style={{ display: 'flex', gap: 8, marginTop: 16, borderTop: '1px solid #e5e7eb', paddingTop: 12 }}>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={(e) => { e.stopPropagation(); navigate(`/welcome-nights/${presentation.id}/present`) }}
                  title="Present"
                >
                  <Play size={14} />
                </button>
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={(e) => { e.stopPropagation(); navigate(`/welcome-nights/${presentation.id}/edit`) }}
                  title="Edit"
                >
                  <Edit2 size={14} />
                </button>
                <a
                  className="btn btn-sm btn-secondary"
                  href={getWNExportPptxUrl(presentation.id)}
                  onClick={(e) => e.stopPropagation()}
                  title="Download PPTX"
                >
                  <Download size={14} />
                </a>
                <button
                  className="btn btn-sm btn-danger"
                  onClick={(e) => handleDelete(presentation.id, e)}
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default WelcomeNightsList
