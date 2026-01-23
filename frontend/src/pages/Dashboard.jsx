import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Plus, Building2, TrendingUp, RefreshCw, ChevronDown, ChevronRight, Users, Upload, MapPin, Eye, EyeOff } from 'lucide-react'
import { getDeals, getDealStats, updateDealStatus, formatCurrency, formatNumber } from '../services/api'
import api from '../services/api'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

// Company colors
const COMPANY_COLORS = {
  'Columbia': '#e11d48',
  'Envision': '#7c3aed',
  'Northern': '#0891b2',
  'Olympus': '#059669',
  'Three Rivers': '#d97706',
  'Vincero': '#dc2626',
}

const DEAL_COLOR = '#2563eb'

const STATUSES = [
  { key: 'vetting', label: 'Vetting' },
  { key: 'pipeline', label: 'Pipeline' },
  { key: 'due_diligence', label: 'Due Diligence' },
  { key: 'current_operations', label: 'Current Ops' },
  { key: 'on_hold', label: 'On Hold' }
]

function Dashboard() {
  const [deals, setDeals] = useState([])
  const [stats, setStats] = useState({})
  const [currentOps, setCurrentOps] = useState({ companies: [], total: 0 })
  const [expandedCompanies, setExpandedCompanies] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [mapFilters, setMapFilters] = useState({ showAll: true, companies: {}, deals: true })
  const [error, setError] = useState(null)
  const [draggedDeal, setDraggedDeal] = useState(null)
  const [dragOverColumn, setDragOverColumn] = useState(null)
  const navigate = useNavigate()

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [d, s, ops] = await Promise.all([
        getDeals(),
        getDealStats(),
        api.get('/current-operations').then(r => r.data).catch(() => ({ companies: [], total: 0 }))
      ])
      setDeals(d)
      setStats(s)
      setCurrentOps(ops)
      // Initialize map filters with all companies visible
      const companyFilters = {}
      ops.companies?.forEach(c => { companyFilters[c.company] = true })
      setMapFilters(prev => ({ ...prev, companies: companyFilters }))
    } catch (e) {
      setError('Failed to load data. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const toggleCompany = (company) => {
    const newSet = new Set(expandedCompanies)
    if (newSet.has(company)) newSet.delete(company)
    else newSet.add(company)
    setExpandedCompanies(newSet)
  }

  // Map filter toggles
  const toggleMapFilter = (type, key) => {
    if (type === 'showAll') {
      const newShowAll = !mapFilters.showAll
      const newCompanies = {}
      Object.keys(mapFilters.companies).forEach(c => { newCompanies[c] = newShowAll })
      setMapFilters({ showAll: newShowAll, companies: newCompanies, deals: newShowAll })
    } else if (type === 'company') {
      const newCompanies = { ...mapFilters.companies, [key]: !mapFilters.companies[key] }
      const allOn = Object.values(newCompanies).every(v => v) && mapFilters.deals
      setMapFilters({ ...mapFilters, companies: newCompanies, showAll: allOn })
    } else if (type === 'deals') {
      const newDeals = !mapFilters.deals
      const allOn = Object.values(mapFilters.companies).every(v => v) && newDeals
      setMapFilters({ ...mapFilters, deals: newDeals, showAll: allOn })
    }
  }

  // Compute map markers
  const mapMarkers = useMemo(() => {
    const markers = []

    // Add current operations markers
    currentOps.companies?.forEach(company => {
      if (!mapFilters.companies[company.company]) return
      const color = COMPANY_COLORS[company.company] || '#6b7280'

      Object.values(company.teams).forEach(properties => {
        properties.forEach(prop => {
          // Use actual coordinates if available
          if (prop.latitude && prop.longitude) {
            markers.push({
              id: `op-${prop.id}`,
              position: [prop.latitude, prop.longitude],
              name: prop.property_name || 'Unknown',
              company: company.company,
              type: 'operation',
              color,
              beds: prop.beds,
              address: prop.address,
              city: prop.city,
              state: prop.state
            })
          }
        })
      })
    })

    // Add deal markers
    if (mapFilters.deals) {
      deals.forEach(deal => {
        deal.properties?.forEach(prop => {
          if (prop.latitude && prop.longitude) {
            markers.push({
              id: `deal-${deal.id}-${prop.id}`,
              position: [prop.latitude, prop.longitude],
              name: prop.name || deal.name,
              company: 'Deal: ' + deal.name,
              type: 'deal',
              color: DEAL_COLOR,
              beds: prop.licensed_beds,
              address: prop.address,
              city: prop.city,
              state: prop.state
            })
          }
        })
      })
    }

    return markers
  }, [currentOps, deals, mapFilters])

  // Drag handlers for deals
  const handleDragStart = (e, deal) => {
    setDraggedDeal(deal)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', deal.id)
    // Add dragging class after a brief delay for visual feedback
    setTimeout(() => {
      e.target.style.opacity = '0.5'
    }, 0)
  }

  const handleDragEnd = (e) => {
    e.target.style.opacity = '1'
    setDraggedDeal(null)
    setDragOverColumn(null)
  }

  const handleDragOver = (e, statusKey) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    if (dragOverColumn !== statusKey) {
      setDragOverColumn(statusKey)
    }
  }

  const handleDragLeave = (e) => {
    // Only clear if leaving the column entirely
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setDragOverColumn(null)
    }
  }

  const handleDrop = async (e, newStatus) => {
    e.preventDefault()
    setDragOverColumn(null)

    if (!draggedDeal || draggedDeal.status === newStatus) return

    // Optimistically update UI
    setDeals(prev => prev.map(d =>
      d.id === draggedDeal.id ? { ...d, status: newStatus } : d
    ))

    try {
      await updateDealStatus(draggedDeal.id, newStatus)
    } catch (err) {
      console.error('Failed to update status:', err)
      // Revert on error
      loadData()
    }

    setDraggedDeal(null)
  }

  if (loading) {
    return (
      <div className="empty-state">
        <RefreshCw size={32} className="animate-spin" style={{ color: '#a3a3a3' }} />
        <p style={{ marginTop: 12, color: '#737373' }}>Loading pipeline...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="empty-state">
        <p style={{ color: '#737373', marginBottom: 16 }}>{error}</p>
        <button className="btn btn-primary" onClick={loadData}>
          <RefreshCw size={14} /> Retry
        </button>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">{stats.total || 0} active deals</p>
        </div>
        <Link to="/deals/new" className="btn btn-primary">
          <Plus size={16} /> New Deal
        </Link>
      </div>

      {/* Summary Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 24 }}>
        <div className="card" style={{ padding: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 6, background: '#ecfdf5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <TrendingUp size={20} color="#059669" />
          </div>
          <div>
            <div className="stat-label">Total Deals</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#171717' }}>{stats.total || 0}</div>
          </div>
        </div>
        <div className="card" style={{ padding: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 6, background: '#f5f3ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Building2 size={20} color="#7c3aed" />
          </div>
          <div>
            <div className="stat-label">Total Properties</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#171717' }}>{stats.total_properties || 0}</div>
          </div>
        </div>
        <div className="card" style={{ padding: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: 6, background: '#f0f9ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Building2 size={20} color="#0284c7" />
          </div>
          <div>
            <div className="stat-label">Total Beds</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: '#171717' }}>{formatNumber(stats.total_beds)}</div>
          </div>
        </div>
      </div>

      {/* Pipeline Board */}
      <div className="pipeline-board">
        {STATUSES.map(st => {
          const columnDeals = deals.filter(d => d.status === st.key)
          const isOver = dragOverColumn === st.key && draggedDeal?.status !== st.key
          const isCurrentOpsColumn = st.key === 'current_operations'

          return (
            <div
              key={st.key}
              className="pipeline-column"
              onDragOver={(e) => handleDragOver(e, st.key)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, st.key)}
              style={{
                background: isOver ? '#f0fdfa' : 'white',
                borderColor: isOver ? '#0b7280' : undefined,
                transition: 'all 0.15s ease'
              }}
            >
              <div className="column-header" style={{ background: isOver ? '#e6fffa' : undefined }}>
                <span className="column-title">{st.label}</span>
                <span className="column-count">
                  {isCurrentOpsColumn ? currentOps.total : columnDeals.length}
                </span>
              </div>
              <div className="column-cards">
                {/* Regular deals for non-current-ops columns */}
                {!isCurrentOpsColumn && columnDeals.map(deal => (
                  <div
                    key={deal.id}
                    className="deal-card"
                    draggable
                    onDragStart={(e) => handleDragStart(e, deal)}
                    onDragEnd={handleDragEnd}
                    onClick={() => navigate('/deals/' + deal.id)}
                    style={{ cursor: 'grab' }}
                  >
                    <div className="deal-card-header">
                      <span className="deal-name">{deal.name}</span>
                      <span className={'deal-type-badge ' + (deal.deal_type || 'snf').toLowerCase()}>
                        {deal.deal_type || 'SNF'}
                      </span>
                    </div>
                    {(deal.total_beds > 0 || deal.property_count > 1) && (
                      <div className="deal-meta">
                        {deal.total_beds > 0 && (
                          <span><Building2 size={12} /> {deal.total_beds} beds</span>
                        )}
                        {deal.property_count > 1 && (
                          <span>{deal.property_count} properties</span>
                        )}
                      </div>
                    )}
                    {deal.asking_price > 0 && (
                      <div className="deal-price">{formatCurrency(deal.asking_price)}</div>
                    )}
                    <div className="deal-footer">
                      <span className={'priority-badge ' + (deal.priority || 'medium')}>
                        {deal.priority || 'Medium'}
                      </span>
                    </div>
                  </div>
                ))}

                {/* Current Operations content */}
                {isCurrentOpsColumn && (
                  <>
                    {currentOps.companies.map(company => {
                      const isExpanded = expandedCompanies.has(company.company)
                      const teamNames = Object.keys(company.teams)
                      const totalProps = teamNames.reduce((sum, t) => sum + company.teams[t].length, 0)
                      const totalBeds = teamNames.reduce((sum, t) =>
                        sum + company.teams[t].reduce((s, p) => s + (p.beds || 0), 0), 0)

                      return (
                        <div key={company.company} style={{
                          background: '#f8fafc',
                          borderRadius: 6,
                          marginBottom: 8,
                          border: '1px solid #e2e8f0',
                          overflow: 'hidden'
                        }}>
                          <div
                            onClick={() => toggleCompany(company.company)}
                            style={{
                              padding: '10px 12px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              gap: 8,
                              background: isExpanded ? '#f1f5f9' : 'transparent'
                            }}
                          >
                            {isExpanded ? <ChevronDown size={14} color="#64748b" /> : <ChevronRight size={14} color="#64748b" />}
                            <Building2 size={14} color="#0b7280" />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div style={{ fontWeight: 600, fontSize: 12, color: '#1e293b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {company.company}
                              </div>
                              <div style={{ fontSize: 10, color: '#64748b' }}>
                                {totalProps} properties · {totalBeds} beds
                              </div>
                            </div>
                          </div>

                          {isExpanded && (
                            <div style={{ padding: '0 8px 8px' }}>
                              {teamNames.map(teamName => (
                                <div key={teamName} style={{ marginTop: 6 }}>
                                  <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 6,
                                    padding: '4px 6px',
                                    background: '#e2e8f0',
                                    borderRadius: 4,
                                    marginBottom: 4
                                  }}>
                                    <Users size={10} color="#7c3aed" />
                                    <span style={{ fontSize: 10, fontWeight: 600, color: '#475569' }}>
                                      {teamName || 'No Team'}
                                    </span>
                                    <span style={{
                                      background: '#0b7280',
                                      color: 'white',
                                      padding: '1px 5px',
                                      borderRadius: 8,
                                      fontSize: 9,
                                      fontWeight: 600
                                    }}>
                                      {company.teams[teamName].length}
                                    </span>
                                  </div>
                                  {company.teams[teamName].map(prop => (
                                    <div key={prop.id} style={{
                                      padding: '6px 8px',
                                      background: 'white',
                                      borderRadius: 4,
                                      marginBottom: 3,
                                      border: '1px solid #e5e5e5'
                                    }}>
                                      <div style={{ fontSize: 11, fontWeight: 500, color: '#1e293b' }}>
                                        {prop.property_name || 'Unnamed'}
                                      </div>
                                      <div style={{ fontSize: 9, color: '#64748b', display: 'flex', gap: 8, marginTop: 2 }}>
                                        {prop.property_type && (
                                          <span className={'deal-type-badge ' + prop.property_type.toLowerCase()} style={{ padding: '1px 4px', fontSize: 8 }}>
                                            {prop.property_type}
                                          </span>
                                        )}
                                        {prop.beds && <span>{prop.beds} beds</span>}
                                        {prop.city && prop.state && <span>{prop.city}, {prop.state}</span>}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )
                    })}

                    {currentOps.total === 0 && (
                      <div style={{
                        padding: 16,
                        textAlign: 'center',
                        color: '#a3a3a3',
                        fontSize: 12
                      }}>
                        <Upload size={20} color="#d4d4d4" style={{ marginBottom: 8 }} />
                        <div>No current operations</div>
                        <Link to="/current-ops" style={{ fontSize: 11, color: '#0b7280', marginTop: 4, display: 'inline-block' }}>
                          Upload data
                        </Link>
                      </div>
                    )}
                  </>
                )}

                {/* Empty state for non-current-ops columns */}
                {!isCurrentOpsColumn && columnDeals.length === 0 && (
                  <div style={{
                    padding: 16,
                    textAlign: 'center',
                    color: isOver ? '#0b7280' : '#a3a3a3',
                    fontSize: 12,
                    border: isOver ? '2px dashed #0b7280' : '2px dashed transparent',
                    borderRadius: 6,
                    margin: 4,
                    transition: 'all 0.15s'
                  }}>
                    {isOver ? 'Drop here' : 'No deals'}
                  </div>
                )}
                {/* Drop zone indicator when column has deals */}
                {!isCurrentOpsColumn && columnDeals.length > 0 && isOver && (
                  <div style={{
                    padding: 12,
                    textAlign: 'center',
                    color: '#0b7280',
                    fontSize: 12,
                    border: '2px dashed #0b7280',
                    borderRadius: 6,
                    margin: 4,
                    background: '#f0fdfa'
                  }}>
                    Drop here
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Map Section */}
      <div style={{ marginTop: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, color: '#171717' }}>
          <MapPin size={20} style={{ display: 'inline', marginRight: 8, verticalAlign: 'middle' }} />
          Facility Locations
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 240px', gap: 16 }}>
          {/* Map */}
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <MapContainer
              center={[39.8283, -98.5795]}
              zoom={4}
              style={{ width: '100%', height: 450 }}
              scrollWheelZoom={true}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {mapMarkers.map(marker => (
                <CircleMarker
                  key={marker.id}
                  center={marker.position}
                  radius={8}
                  pathOptions={{
                    fillColor: marker.color,
                    fillOpacity: 0.8,
                    color: '#fff',
                    weight: 2
                  }}
                >
                  <Popup>
                    <div style={{ minWidth: 150 }}>
                      <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{marker.name}</div>
                      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>{marker.company}</div>
                      {marker.address && <div style={{ fontSize: 11, color: '#9ca3af' }}>{marker.address}</div>}
                      <div style={{ fontSize: 11, color: '#9ca3af' }}>{marker.city}, {marker.state}</div>
                      {marker.beds && <div style={{ fontSize: 12, marginTop: 4, fontWeight: 500 }}>{marker.beds} beds</div>}
                    </div>
                  </Popup>
                </CircleMarker>
              ))}
            </MapContainer>
            <div style={{ padding: '8px 16px', background: '#f9fafb', borderTop: '1px solid #e5e5e5', fontSize: 12, color: '#6b7280' }}>
              Showing {mapMarkers.length} facilities • Scroll to zoom, drag to pan
            </div>
          </div>

          {/* Legend */}
          <div className="card" style={{ padding: 16, height: 'fit-content' }}>
            <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12, color: '#171717' }}>Show on Map</h3>

            {/* Show All Toggle */}
            <div
              onClick={() => toggleMapFilter('showAll')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '8px 10px',
                background: mapFilters.showAll ? '#f0fdfa' : '#f5f5f5',
                borderRadius: 6,
                cursor: 'pointer',
                marginBottom: 12,
                border: mapFilters.showAll ? '1px solid #0b7280' : '1px solid transparent'
              }}
            >
              {mapFilters.showAll ? <Eye size={16} color="#0b7280" /> : <EyeOff size={16} color="#9ca3af" />}
              <span style={{ fontWeight: 600, fontSize: 13, color: mapFilters.showAll ? '#0b7280' : '#6b7280' }}>
                Show All
              </span>
            </div>

            {/* Current Operations Section */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af', marginBottom: 8, textTransform: 'uppercase' }}>
                Current Operations
              </div>
              {Object.keys(mapFilters.companies).map(company => (
                <div
                  key={company}
                  onClick={() => toggleMapFilter('company', company)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '6px 8px',
                    borderRadius: 4,
                    cursor: 'pointer',
                    marginBottom: 4,
                    background: mapFilters.companies[company] ? '#fafafa' : 'transparent',
                    opacity: mapFilters.companies[company] ? 1 : 0.5
                  }}
                >
                  <div style={{
                    width: 12,
                    height: 12,
                    borderRadius: '50%',
                    background: COMPANY_COLORS[company] || '#6b7280',
                    border: mapFilters.companies[company] ? 'none' : '2px solid #d1d5db'
                  }} />
                  <span style={{ fontSize: 12, color: '#374151' }}>{company}</span>
                </div>
              ))}
            </div>

            {/* Deals Section */}
            <div>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af', marginBottom: 8, textTransform: 'uppercase' }}>
                Pipeline Deals
              </div>
              <div
                onClick={() => toggleMapFilter('deals')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 8px',
                  borderRadius: 4,
                  cursor: 'pointer',
                  background: mapFilters.deals ? '#fafafa' : 'transparent',
                  opacity: mapFilters.deals ? 1 : 0.5
                }}
              >
                <div style={{
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  background: DEAL_COLOR,
                  border: mapFilters.deals ? 'none' : '2px solid #d1d5db'
                }} />
                <span style={{ fontSize: 12, color: '#374151' }}>All Deals ({deals.length})</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
