import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Plus, Building2, TrendingUp, RefreshCw, ChevronDown, ChevronRight, Users, Upload, MapPin, Eye, EyeOff } from 'lucide-react'
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet'
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd'
import { getDeals, getDealStats, updateDealStatus, formatCurrency, formatNumber } from '../services/api'
import api from '../services/api'

// Company colors for map markers
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
  const [mapDeals, setMapDeals] = useState([])
  const [stats, setStats] = useState({})
  const [currentOps, setCurrentOps] = useState({ companies: [], total: 0 })
  const [expandedCompanies, setExpandedCompanies] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [mapFilters, setMapFilters] = useState({ showAll: true, companies: {}, deals: {} })
  const navigate = useNavigate()

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      const [d, s, ops, md] = await Promise.all([
        getDeals(),
        getDealStats(),
        api.get('/current-operations').then(r => r.data).catch(() => ({ companies: [], total: 0 })),
        api.get('/deals/map').then(r => r.data).catch(() => [])
      ])
      setDeals(d)
      setStats(s)
      setCurrentOps(ops)
      setMapDeals(md)
      // Initialize map filters for companies and deals
      const companyFilters = {}
      ops.companies?.forEach(c => { companyFilters[c.company] = true })
      const dealFilters = {}
      md.forEach(deal => { dealFilters[deal.id] = true })
      setMapFilters(prev => ({ ...prev, companies: companyFilters, deals: dealFilters }))
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
      const newDeals = {}
      Object.keys(mapFilters.deals).forEach(d => { newDeals[d] = newShowAll })
      setMapFilters({ showAll: newShowAll, companies: newCompanies, deals: newDeals })
    } else if (type === 'company') {
      const newCompanies = { ...mapFilters.companies, [key]: !mapFilters.companies[key] }
      const allCompaniesOn = Object.values(newCompanies).every(v => v)
      const allDealsOn = Object.values(mapFilters.deals).every(v => v)
      setMapFilters({ ...mapFilters, companies: newCompanies, showAll: allCompaniesOn && allDealsOn })
    } else if (type === 'deal') {
      const newDeals = { ...mapFilters.deals, [key]: !mapFilters.deals[key] }
      const allCompaniesOn = Object.values(mapFilters.companies).every(v => v)
      const allDealsOn = Object.values(newDeals).every(v => v)
      setMapFilters({ ...mapFilters, deals: newDeals, showAll: allCompaniesOn && allDealsOn })
    }
  }

  // Compute map markers from current operations and deals
  const mapMarkers = useMemo(() => {
    const markers = []

    // Add current operations markers
    currentOps.companies?.forEach(company => {
      if (!mapFilters.companies[company.company]) return
      const color = COMPANY_COLORS[company.company] || '#6b7280'

      Object.values(company.teams).forEach(properties => {
        properties.forEach(prop => {
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

    // Add deal property markers
    mapDeals.forEach(deal => {
      if (!mapFilters.deals[deal.id]) return
      deal.properties?.forEach(prop => {
        if (prop.latitude && prop.longitude) {
          markers.push({
              id: `deal-${deal.id}-${prop.id}`,
              position: [prop.latitude, prop.longitude],
              name: prop.name || deal.name,
              company: deal.name,
              type: 'deal',
              status: deal.status,
              color: DEAL_COLOR,
              beds: prop.licensed_beds,
              address: prop.address,
              city: prop.city,
              state: prop.state
            })
          }
        })
      })

    return markers
  }, [currentOps, mapDeals, mapFilters])

  // Drag-and-drop handler
  const onDragEnd = async (result) => {
    const { draggableId, destination, source } = result
    if (!destination || destination.droppableId === source.droppableId) return

    const dealId = parseInt(draggableId)
    const newStatus = destination.droppableId

    // Optimistically update UI
    setDeals(prev => prev.map(d =>
      d.id === dealId ? { ...d, status: newStatus } : d
    ))

    try {
      await updateDealStatus(dealId, newStatus)
    } catch (err) {
      console.error('Failed to update status:', err)
      loadData()
    }
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
      <DragDropContext onDragEnd={onDragEnd}>
        <div className="pipeline-board">
          {STATUSES.map(st => {
            const columnDeals = deals.filter(d => d.status === st.key)
            const isCurrentOpsColumn = st.key === 'current_operations'

            return (
              <div key={st.key} className="pipeline-column">
                <div className="column-header">
                  <span className="column-title">{st.label}</span>
                  <span className="column-count">
                    {isCurrentOpsColumn ? currentOps.total : columnDeals.length}
                  </span>
                </div>

                {isCurrentOpsColumn ? (
                  <div className="column-cards">
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
                  </div>
                ) : (
                  <Droppable droppableId={st.key}>
                    {(provided, snapshot) => (
                      <div
                        ref={provided.innerRef}
                        {...provided.droppableProps}
                        className="column-cards"
                        style={{
                          background: snapshot.isDraggingOver ? '#f0fdfa' : undefined,
                          transition: 'background 0.15s ease',
                          minHeight: 100
                        }}
                      >
                        {columnDeals.map((deal, index) => (
                          <Draggable key={deal.id} draggableId={String(deal.id)} index={index}>
                            {(provided, snapshot) => (
                              <div
                                ref={provided.innerRef}
                                {...provided.draggableProps}
                                {...provided.dragHandleProps}
                                className="deal-card"
                                onClick={() => navigate('/deals/' + deal.id)}
                                style={{
                                  ...provided.draggableProps.style,
                                  cursor: 'grab',
                                  opacity: snapshot.isDragging ? 0.8 : 1,
                                  boxShadow: snapshot.isDragging ? '0 8px 16px rgba(0,0,0,0.15)' : undefined
                                }}
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
                            )}
                          </Draggable>
                        ))}
                        {provided.placeholder}
                        {columnDeals.length === 0 && !snapshot.isDraggingOver && (
                          <div style={{
                            padding: 16,
                            textAlign: 'center',
                            color: '#a3a3a3',
                            fontSize: 12,
                            border: '2px dashed transparent',
                            borderRadius: 6,
                            margin: 4
                          }}>
                            No deals
                          </div>
                        )}
                        {snapshot.isDraggingOver && columnDeals.length === 0 && (
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
                    )}
                  </Droppable>
                )}
              </div>
            )
          })}
        </div>
      </DragDropContext>

      {/* Map Section */}
      <div style={{ marginTop: 24, display: 'flex', gap: 16 }}>
        {/* Map */}
        <div className="card" style={{ flex: 1, padding: 0, overflow: 'hidden', height: 450 }}>
          <MapContainer
            center={[39.8283, -98.5795]}
            zoom={4}
            style={{ height: '100%', width: '100%' }}
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
                fillColor={marker.color}
                color="#fff"
                weight={2}
                opacity={1}
                fillOpacity={0.8}
              >
                <Popup>
                  <div style={{ minWidth: 150 }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>{marker.name}</div>
                    <div style={{ fontSize: 12, color: '#64748b' }}>{marker.company}</div>
                    {marker.beds && <div style={{ fontSize: 12, marginTop: 4 }}>{marker.beds} beds</div>}
                    {marker.address && (
                      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                        {marker.address}<br />
                        {marker.city}, {marker.state}
                      </div>
                    )}
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        {/* Legend */}
        <div className="card" style={{ width: 200, padding: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 14 }}>
            <MapPin size={14} style={{ marginRight: 6 }} />
            Map Legend
          </div>

          {/* Show All Toggle */}
          <div
            onClick={() => toggleMapFilter('showAll')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 0',
              cursor: 'pointer',
              borderBottom: '1px solid #e5e5e5',
              marginBottom: 8
            }}
          >
            {mapFilters.showAll ? <Eye size={14} color="#0b7280" /> : <EyeOff size={14} color="#a3a3a3" />}
            <span style={{ fontSize: 12, fontWeight: 500 }}>Show All</span>
          </div>

          {/* Company filters */}
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6, fontWeight: 600 }}>CURRENT OPERATIONS</div>
          {Object.keys(mapFilters.companies).map(company => (
            <div
              key={company}
              onClick={() => toggleMapFilter('company', company)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 0',
                cursor: 'pointer',
                opacity: mapFilters.companies[company] ? 1 : 0.5
              }}
            >
              <div style={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                background: COMPANY_COLORS[company] || '#6b7280',
                border: '2px solid white',
                boxShadow: '0 0 0 1px ' + (COMPANY_COLORS[company] || '#6b7280')
              }} />
              <span style={{ fontSize: 12 }}>{company}</span>
              {mapFilters.companies[company] ? <Eye size={12} color="#0b7280" /> : <EyeOff size={12} color="#a3a3a3" />}
            </div>
          ))}

          {/* Deals filter */}
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 12, marginBottom: 6, fontWeight: 600 }}>PIPELINE DEALS</div>
          {mapDeals.map(deal => (
            <div
              key={deal.id}
              onClick={() => toggleMapFilter('deal', deal.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '6px 0',
                cursor: 'pointer',
                opacity: mapFilters.deals[deal.id] ? 1 : 0.5
              }}
            >
              <div style={{
                width: 12,
                height: 12,
                borderRadius: '50%',
                background: DEAL_COLOR,
                border: '2px solid white',
                boxShadow: '0 0 0 1px ' + DEAL_COLOR
              }} />
              <span style={{ fontSize: 12 }}>{deal.name}</span>
              <span style={{ fontSize: 9, color: '#94a3b8', textTransform: 'capitalize' }}>({deal.status.replace('_', ' ')})</span>
              {mapFilters.deals[deal.id] ? <Eye size={12} color="#0b7280" /> : <EyeOff size={12} color="#a3a3a3" />}
            </div>
          ))}
          {mapDeals.length === 0 && (
            <div style={{ fontSize: 11, color: '#a3a3a3', padding: '6px 0' }}>No geocoded deals</div>
          )}

          <div style={{ marginTop: 12, fontSize: 11, color: '#94a3b8' }}>
            {mapMarkers.length} locations shown
          </div>
        </div>
      </div>

    </div>
  )
}

export default Dashboard
