import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Search, Building2, Star, MapPin, Loader2, X, Check, Plus, Edit3 } from 'lucide-react'
import { createDeal, createProperty } from '../services/api'
import api from '../services/api'

const PROPERTY_TYPES = [
  { value: 'SNF', label: 'Skilled Nursing (SNF)' },
  { value: 'ALF', label: 'Assisted Living (ALF)' },
  { value: 'ILF', label: 'Independent Living (ILF)' },
  { value: 'MC', label: 'Memory Care' },
  { value: 'CCRC', label: 'CCRC / Life Plan' },
  { value: 'SH', label: 'Senior Housing' },
]

const STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']

function NewDeal() {
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchState, setSearchState] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searching, setSearching] = useState(false)
  const [selectedProperties, setSelectedProperties] = useState([])
  const [saving, setSaving] = useState(false)
  const [dealName, setDealName] = useState('')

  // Manual property form
  const [showManualForm, setShowManualForm] = useState(false)
  const [manualProperty, setManualProperty] = useState({
    name: '',
    property_type: 'ALF',
    address: '',
    city: '',
    state: '',
    licensed_beds: ''
  })

  const searchFacilities = useCallback(async () => {
    if (!searchQuery || searchQuery.length < 2) return
    setSearching(true)
    try {
      const params = new URLSearchParams({ q: searchQuery, limit: '20' })
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

  const toggleFacility = (facility) => {
    const id = facility.provider_id || facility._tempId
    if (selectedProperties.find(p => (p.provider_id || p._tempId) === id)) {
      setSelectedProperties(selectedProperties.filter(p => (p.provider_id || p._tempId) !== id))
    } else {
      setSelectedProperties([...selectedProperties, { ...facility, property_type: facility.property_type || 'SNF' }])
    }
  }

  const updatePropertyType = (id, newType) => {
    setSelectedProperties(selectedProperties.map(p =>
      (p.provider_id || p._tempId) === id ? { ...p, property_type: newType } : p
    ))
  }

  const addManualProperty = () => {
    if (!manualProperty.name.trim()) return

    const newProperty = {
      ...manualProperty,
      _tempId: `manual_${Date.now()}`,
      licensed_beds: manualProperty.licensed_beds ? parseInt(manualProperty.licensed_beds) : null,
      source: 'manual'
    }

    setSelectedProperties([...selectedProperties, newProperty])
    setManualProperty({
      name: '',
      property_type: 'ALF',
      address: '',
      city: '',
      state: '',
      licensed_beds: ''
    })
    setShowManualForm(false)
  }

  const createDealFromProperties = async () => {
    if (selectedProperties.length === 0) return
    setSaving(true)
    try {
      const totalBeds = selectedProperties.reduce((sum, p) => sum + (p.licensed_beds || 0), 0)

      // Determine primary property type
      const typeCounts = {}
      selectedProperties.forEach(p => {
        typeCounts[p.property_type] = (typeCounts[p.property_type] || 0) + 1
      })
      const primaryType = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0][0]

      const name = dealName.trim() || (selectedProperties.length === 1
        ? selectedProperties[0].name
        : `${selectedProperties[0].name} Portfolio (${selectedProperties.length} properties)`)

      const deal = await createDeal({
        name,
        deal_type: primaryType,
        priority: 'medium',
        total_beds: totalBeds || null,
        property_count: selectedProperties.length,
        source: selectedProperties.some(p => p.source === 'cms') ? 'CMS Medicare Data' : 'Manual Entry',
        notes: selectedProperties.length > 1
          ? `Portfolio of ${selectedProperties.length} properties:\n${selectedProperties.map(p => `- ${p.name} (${p.property_type})`).join('\n')}`
          : null
      })

      for (const property of selectedProperties) {
        await createProperty(deal.id, {
          name: property.name,
          property_type: property.property_type,
          address: property.address,
          city: property.city,
          state: property.state,
          licensed_beds: property.licensed_beds,
          star_rating: property.star_rating,
          current_occupancy: property.current_occupancy
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

  const totalBeds = selectedProperties.reduce((sum, p) => sum + (p.licensed_beds || 0), 0)

  return (
    <div>
      <button onClick={() => navigate('/')} className="btn btn-ghost btn-sm" style={{ marginBottom: 16 }}>
        <ArrowLeft size={16} /> Back to Pipeline
      </button>

      <div className="page-header">
        <div>
          <h1 className="page-title">Add New Deal</h1>
          <p className="page-subtitle">Search for facilities or add properties manually</p>
        </div>
      </div>

      {/* Search Section */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <label className="form-label" style={{ margin: 0 }}>Search CMS Database (SNF Facilities)</label>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowManualForm(!showManualForm)}
          >
            <Plus size={14} /> Add Property Manually
          </button>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <div style={{ position: 'relative' }}>
              <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#a3a3a3' }} />
              <input
                className="form-input"
                placeholder="Search by facility name or city..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                style={{ paddingLeft: 36 }}
              />
            </div>
          </div>
          <div style={{ width: 100 }}>
            <select
              className="form-select"
              value={searchState}
              onChange={(e) => setSearchState(e.target.value)}
            >
              <option value="">All States</option>
              {STATES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <button
            className="btn btn-primary"
            onClick={searchFacilities}
            disabled={searching || searchQuery.length < 2}
          >
            {searching ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            Search
          </button>
        </div>
      </div>

      {/* Manual Property Form */}
      {showManualForm && (
        <div className="card" style={{ marginBottom: 16, background: '#fafafa' }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Add Property Manually</h3>
          <p style={{ fontSize: 12, color: '#737373', marginBottom: 16 }}>
            For ALF, ILF, Memory Care, Senior Housing, or any property not in CMS database
          </p>
          <div className="form-row-3">
            <div className="form-group">
              <label className="form-label">Property Name *</label>
              <input
                className="form-input"
                placeholder="e.g. Sunrise Senior Living"
                value={manualProperty.name}
                onChange={e => setManualProperty({ ...manualProperty, name: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Type</label>
              <select
                className="form-select"
                value={manualProperty.property_type}
                onChange={e => setManualProperty({ ...manualProperty, property_type: e.target.value })}
              >
                {PROPERTY_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Beds / Units</label>
              <input
                type="number"
                className="form-input"
                placeholder="e.g. 120"
                value={manualProperty.licensed_beds}
                onChange={e => setManualProperty({ ...manualProperty, licensed_beds: e.target.value })}
              />
            </div>
          </div>
          <div className="form-row-3">
            <div className="form-group">
              <label className="form-label">Address</label>
              <input
                className="form-input"
                value={manualProperty.address}
                onChange={e => setManualProperty({ ...manualProperty, address: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">City</label>
              <input
                className="form-input"
                value={manualProperty.city}
                onChange={e => setManualProperty({ ...manualProperty, city: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label className="form-label">State</label>
              <select
                className="form-select"
                value={manualProperty.state}
                onChange={e => setManualProperty({ ...manualProperty, state: e.target.value })}
              >
                <option value="">Select...</option>
                {STATES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-secondary btn-sm" onClick={() => setShowManualForm(false)}>
              Cancel
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={addManualProperty}
              disabled={!manualProperty.name.trim()}
            >
              <Plus size={14} /> Add to Deal
            </button>
          </div>
        </div>
      )}

      {/* Selected Properties Action Bar */}
      {selectedProperties.length > 0 && (
        <div style={{
          background: '#0b7280',
          borderRadius: 6,
          padding: '12px 16px',
          marginBottom: 16,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, color: 'white' }}>
            <div>
              <span style={{ fontWeight: 600 }}>{selectedProperties.length}</span> {selectedProperties.length === 1 ? 'property' : 'properties'} selected
            </div>
            {totalBeds > 0 && (
              <div style={{ opacity: 0.8 }}>
                {totalBeds} total beds
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Deal name (optional)"
              value={dealName}
              onChange={(e) => setDealName(e.target.value)}
              style={{
                background: 'rgba(255,255,255,0.15)',
                border: '1px solid rgba(255,255,255,0.3)',
                borderRadius: 4,
                padding: '6px 12px',
                color: 'white',
                fontSize: 13,
                width: 200
              }}
            />
            <button
              className="btn"
              onClick={createDealFromProperties}
              disabled={saving}
              style={{ background: 'white', color: '#0b7280' }}
            >
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
              Create Deal
            </button>
          </div>
        </div>
      )}

      {/* Selected Properties List */}
      {selectedProperties.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-title" style={{ marginBottom: 12 }}>Properties in this Deal</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {selectedProperties.map(p => {
              const id = p.provider_id || p._tempId
              return (
                <div
                  key={id}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 6,
                    background: '#f5f5f5',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{p.name}</div>
                      {(p.city || p.state) && (
                        <div style={{ fontSize: 12, color: '#737373' }}>
                          {p.city}{p.city && p.state ? ', ' : ''}{p.state}
                          {p.licensed_beds && ` • ${p.licensed_beds} beds`}
                        </div>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <select
                      value={p.property_type}
                      onChange={(e) => updatePropertyType(id, e.target.value)}
                      style={{
                        padding: '4px 8px',
                        borderRadius: 4,
                        border: '1px solid #d4d4d4',
                        fontSize: 12,
                        background: 'white'
                      }}
                    >
                      {PROPERTY_TYPES.map(t => <option key={t.value} value={t.value}>{t.value}</option>)}
                    </select>
                    <button
                      onClick={() => toggleFacility(p)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
                    >
                      <X size={16} color="#737373" />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <span style={{ fontSize: 13, color: '#737373' }}>{searchResults.length} SNF facilities found</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {searchResults.map(facility => {
              const isSelected = selectedProperties.find(p => p.provider_id === facility.provider_id)
              return (
                <div
                  key={facility.provider_id}
                  onClick={() => toggleFacility({ ...facility, property_type: 'SNF', source: 'cms' })}
                  style={{
                    padding: '12px 16px',
                    borderRadius: 6,
                    border: isSelected ? '2px solid #0b7280' : '1px solid #e5e5e5',
                    background: isSelected ? '#f0fdfa' : 'white',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                      width: 20,
                      height: 20,
                      borderRadius: 4,
                      border: isSelected ? 'none' : '2px solid #d4d4d4',
                      background: isSelected ? '#0b7280' : 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0
                    }}>
                      {isSelected && <Check size={14} color="white" />}
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13, color: '#171717' }}>
                        {facility.name}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#737373', fontSize: 12, marginTop: 2 }}>
                        <MapPin size={12} />
                        {facility.city}, {facility.state}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: '#171717' }}>
                        {facility.licensed_beds || '—'} beds
                      </div>
                      <div style={{ fontSize: 12, color: '#737373' }}>
                        {facility.current_occupancy ? `${facility.current_occupancy}% occ` : '—'}
                      </div>
                    </div>
                    {facility.star_rating && (
                      <div style={{ display: 'flex', gap: 2 }}>
                        {[1, 2, 3, 4, 5].map(i => (
                          <Star
                            key={i}
                            size={14}
                            fill={i <= facility.star_rating ? '#f59e0b' : 'none'}
                            color={i <= facility.star_rating ? '#f59e0b' : '#e5e5e5'}
                          />
                        ))}
                      </div>
                    )}
                    <span className="deal-type-badge snf">SNF</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Empty state */}
      {searchResults.length === 0 && selectedProperties.length === 0 && !searching && !showManualForm && (
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <Building2 size={40} color="#d4d4d4" style={{ marginBottom: 16 }} />
          <div style={{ fontSize: 14, color: '#525252', marginBottom: 8 }}>
            Search for SNF facilities or add properties manually
          </div>
          <div style={{ fontSize: 13, color: '#737373', marginBottom: 24 }}>
            CMS database includes 15,000+ skilled nursing facilities.<br/>
            Use "Add Property Manually" for ALF, ILF, Memory Care, and other senior living.
          </div>
          <button
            className="btn btn-primary"
            onClick={() => setShowManualForm(true)}
          >
            <Plus size={14} /> Add Property Manually
          </button>
        </div>
      )}
    </div>
  )
}

export default NewDeal
