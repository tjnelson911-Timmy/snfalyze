import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Save, Search, Building2, Star, MapPin, Loader2, X, Check } from 'lucide-react'
import { createDeal, createProperty } from '../services/api'
import api from '../services/api'

function NewDeal() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('search') // 'search' or 'manual'
  const [searchQuery, setSearchQuery] = useState('')
  const [searchState, setSearchState] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [selectedFacilities, setSelectedFacilities] = useState([])
  const [saving, setSaving] = useState(false)

  // Manual form
  const [f, setF] = useState({
    name: '', deal_type: 'SNF', priority: 'medium', asking_price: '', ebitdar: '',
    total_beds: '', broker_name: '', broker_company: '', broker_email: '',
    seller_name: '', source: '', notes: '', investment_thesis: ''
  })

  const searchFacilities = useCallback(async () => {
    if (!searchQuery || searchQuery.length < 2) return
    setSearching(true)
    try {
      const params = new URLSearchParams({ q: searchQuery, limit: '25' })
      if (searchState) params.append('state', searchState)
      const response = await api.get(`/facilities/search?${params}`)
      setSearchResults(response.data.facilities || [])
    } catch (e) {
      console.error('Search failed:', e)
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }, [searchQuery, searchState])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      searchFacilities()
    }
  }

  const selectFacility = (facility) => {
    if (selectedFacilities.find(f => f.provider_id === facility.provider_id)) {
      setSelectedFacilities(selectedFacilities.filter(f => f.provider_id !== facility.provider_id))
    } else {
      setSelectedFacilities([...selectedFacilities, facility])
    }
  }

  const createDealFromFacilities = async () => {
    if (selectedFacilities.length === 0) return
    setSaving(true)
    try {
      // Calculate totals
      const totalBeds = selectedFacilities.reduce((sum, f) => sum + (f.licensed_beds || 0), 0)
      const avgOccupancy = selectedFacilities.reduce((sum, f) => sum + (f.current_occupancy || 0), 0) / selectedFacilities.length

      // Create the deal
      const dealName = selectedFacilities.length === 1
        ? selectedFacilities[0].name
        : `${selectedFacilities[0].name} Portfolio (${selectedFacilities.length} facilities)`

      const deal = await createDeal({
        name: dealName,
        deal_type: 'SNF',
        priority: 'medium',
        total_beds: totalBeds || null,
        source: 'CMS Medicare Data',
        notes: selectedFacilities.length > 1
          ? `Portfolio of ${selectedFacilities.length} facilities\nAvg Occupancy: ${avgOccupancy.toFixed(1)}%`
          : `Star Rating: ${selectedFacilities[0].star_rating || 'N/A'}/5\nOccupancy: ${selectedFacilities[0].current_occupancy || 'N/A'}%`
      })

      // Add each facility as a property
      for (const facility of selectedFacilities) {
        await createProperty(deal.id, {
          name: facility.name,
          property_type: 'SNF',
          address: facility.address,
          city: facility.city,
          state: facility.state,
          licensed_beds: facility.licensed_beds,
          star_rating: facility.star_rating,
          current_occupancy: facility.current_occupancy
        })
      }

      navigate('/deals/' + deal.id)
    } catch (e) {
      console.error('Error creating deal:', e)
      alert('Error creating deal')
    } finally {
      setSaving(false)
    }
  }

  const submitManual = async (e) => {
    e.preventDefault()
    if (!f.name.trim()) { alert('Name required'); return }
    setSaving(true)
    try {
      const deal = await createDeal({
        ...f,
        asking_price: f.asking_price ? parseFloat(f.asking_price) : null,
        ebitdar: f.ebitdar ? parseFloat(f.ebitdar) : null,
        total_beds: f.total_beds ? parseInt(f.total_beds) : null
      })
      navigate('/deals/' + deal.id)
    } catch (e) {
      alert('Error')
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  const STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']

  return (
    <div>
      <button onClick={() => navigate('/')} className="btn btn-secondary btn-sm" style={{ marginBottom: 16 }}>
        <ArrowLeft size={16} /> Back
      </button>

      <h1 className="page-title" style={{ marginBottom: 24 }}>Add New Deal</h1>

      {/* Mode Toggle */}
      <div className="tabs" style={{ marginBottom: 24 }}>
        <button className={'tab ' + (mode === 'search' ? 'active' : '')} onClick={() => setMode('search')}>
          <Search size={16} style={{ marginRight: 8 }} /> Search Facilities
        </button>
        <button className={'tab ' + (mode === 'manual' ? 'active' : '')} onClick={() => setMode('manual')}>
          <Building2 size={16} style={{ marginRight: 8 }} /> Enter Manually
        </button>
      </div>

      {mode === 'search' ? (
        <div>
          {/* Search Box */}
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 className="card-title" style={{ marginBottom: 16 }}>Search CMS Medicare Database</h3>
            <p style={{ color: '#64748b', fontSize: 14, marginBottom: 16 }}>
              Search for skilled nursing facilities by name. Data includes beds, star ratings, and occupancy from CMS.
            </p>
            <div style={{ display: 'flex', gap: 12 }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <Search size={18} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#94a3b8' }} />
                <input
                  className="form-input"
                  placeholder="Search facility name..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  style={{ paddingLeft: 40 }}
                />
              </div>
              <select
                className="form-select"
                value={searchState}
                onChange={(e) => setSearchState(e.target.value)}
                style={{ width: 100 }}
              >
                <option value="">All States</option>
                {STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <button className="btn btn-primary" onClick={searchFacilities} disabled={searching || searchQuery.length < 2}>
                {searching ? <Loader2 size={16} className="spinning" /> : <Search size={16} />}
                Search
              </button>
            </div>
          </div>

          {/* Selected Facilities */}
          {selectedFacilities.length > 0 && (
            <div className="card" style={{ marginBottom: 24, background: '#f0fdf4', border: '1px solid #10b981' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <h3 className="card-title" style={{ color: '#166534' }}>
                  Selected ({selectedFacilities.length}) - {selectedFacilities.reduce((sum, f) => sum + (f.licensed_beds || 0), 0)} total beds
                </h3>
                <button
                  className="btn btn-primary"
                  onClick={createDealFromFacilities}
                  disabled={saving}
                >
                  {saving ? <Loader2 size={16} className="spinning" /> : <Check size={16} />}
                  Create Deal
                </button>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {selectedFacilities.map(f => (
                  <div
                    key={f.provider_id}
                    style={{
                      background: 'white',
                      padding: '8px 12px',
                      borderRadius: 8,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      fontSize: 14
                    }}
                  >
                    <span>{f.name}</span>
                    <span style={{ color: '#64748b' }}>({f.licensed_beds || '?'} beds)</span>
                    <button
                      onClick={() => selectFacility(f)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                    >
                      <X size={16} color="#dc2626" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="card">
              <h3 className="card-title" style={{ marginBottom: 16 }}>Results ({searchResults.length})</h3>
              <div style={{ display: 'grid', gap: 12 }}>
                {searchResults.map(facility => {
                  const isSelected = selectedFacilities.find(f => f.provider_id === facility.provider_id)
                  return (
                    <div
                      key={facility.provider_id}
                      onClick={() => selectFacility(facility)}
                      style={{
                        padding: 16,
                        borderRadius: 10,
                        border: isSelected ? '2px solid #10b981' : '1px solid #e2e8f0',
                        background: isSelected ? '#f0fdf4' : 'white',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>
                            {isSelected && <Check size={16} color="#10b981" style={{ marginRight: 6 }} />}
                            {facility.name}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#64748b', fontSize: 13 }}>
                            <MapPin size={14} />
                            {facility.city}, {facility.state} {facility.zip}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          {facility.star_rating && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                              {[1, 2, 3, 4, 5].map(i => (
                                <Star
                                  key={i}
                                  size={14}
                                  fill={i <= facility.star_rating ? '#f59e0b' : 'none'}
                                  color={i <= facility.star_rating ? '#f59e0b' : '#e2e8f0'}
                                />
                              ))}
                            </div>
                          )}
                          <span className="deal-type-badge snf">SNF</span>
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: 24, marginTop: 12, fontSize: 13 }}>
                        <div>
                          <span style={{ color: '#64748b' }}>Beds:</span>{' '}
                          <strong>{facility.licensed_beds || 'N/A'}</strong>
                        </div>
                        <div>
                          <span style={{ color: '#64748b' }}>Occupancy:</span>{' '}
                          <strong>{facility.current_occupancy ? `${facility.current_occupancy}%` : 'N/A'}</strong>
                        </div>
                        <div>
                          <span style={{ color: '#64748b' }}>Ownership:</span>{' '}
                          <strong>{facility.ownership_type || 'N/A'}</strong>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {searchResults.length === 0 && searchQuery && !searching && (
            <div className="empty-state">
              <Building2 className="empty-state-icon" />
              <p>No facilities found. Try a different search term.</p>
            </div>
          )}
        </div>
      ) : (
        /* Manual Form */
        <form onSubmit={submitManual}>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 className="card-title" style={{ marginBottom: 16 }}>Deal Info</h3>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Name *</label>
                <input className="form-input" value={f.name} onChange={e => setF({ ...f, name: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Type</label>
                <select className="form-select" value={f.deal_type} onChange={e => setF({ ...f, deal_type: e.target.value })}>
                  <option value="SNF">SNF</option>
                  <option value="ALF">ALF</option>
                  <option value="ILF">ILF</option>
                  <option value="MC">Memory Care</option>
                </select>
              </div>
            </div>
            <div className="form-row-3">
              <div className="form-group">
                <label className="form-label">Asking ($)</label>
                <input type="number" className="form-input" value={f.asking_price} onChange={e => setF({ ...f, asking_price: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">EBITDAR ($)</label>
                <input type="number" className="form-input" value={f.ebitdar} onChange={e => setF({ ...f, ebitdar: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Beds</label>
                <input type="number" className="form-input" value={f.total_beds} onChange={e => setF({ ...f, total_beds: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Priority</label>
                <select className="form-select" value={f.priority} onChange={e => setF({ ...f, priority: e.target.value })}>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Source</label>
                <input className="form-input" value={f.source} onChange={e => setF({ ...f, source: e.target.value })} />
              </div>
            </div>
          </div>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 className="card-title" style={{ marginBottom: 16 }}>Broker</h3>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Broker Name</label>
                <input className="form-input" value={f.broker_name} onChange={e => setF({ ...f, broker_name: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Company</label>
                <input className="form-input" value={f.broker_company} onChange={e => setF({ ...f, broker_company: e.target.value })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" value={f.broker_email} onChange={e => setF({ ...f, broker_email: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Seller</label>
                <input className="form-input" value={f.seller_name} onChange={e => setF({ ...f, seller_name: e.target.value })} />
              </div>
            </div>
          </div>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 className="card-title" style={{ marginBottom: 16 }}>Notes</h3>
            <div className="form-group">
              <label className="form-label">Thesis</label>
              <textarea className="form-textarea" rows={3} value={f.investment_thesis} onChange={e => setF({ ...f, investment_thesis: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Notes</label>
              <textarea className="form-textarea" rows={3} value={f.notes} onChange={e => setF({ ...f, notes: e.target.value })} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/')}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              <Save size={16} /> {saving ? 'Creating...' : 'Create Deal'}
            </button>
          </div>
        </form>
      )}

      <style>{`
        .spinning { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  )
}

export default NewDeal
