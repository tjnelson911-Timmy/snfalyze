import React, { useState, useEffect, useRef } from 'react'
import { Upload, Building2, ChevronDown, ChevronRight, Users, Trash2, RefreshCw } from 'lucide-react'
import api from '../services/api'

function CurrentOps() {
  const [data, setData] = useState({ companies: [], total: 0 })
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [expandedCompanies, setExpandedCompanies] = useState(new Set())
  const [expandedTeams, setExpandedTeams] = useState(new Set())
  const fileInputRef = useRef(null)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const response = await api.get('/current-operations')
      setData(response.data)
      // Expand all companies by default
      setExpandedCompanies(new Set(response.data.companies.map(c => c.company)))
    } catch (e) {
      console.error('Failed to load current operations:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      await api.post('/current-operations/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      loadData()
    } catch (e) {
      console.error('Upload failed:', e)
      alert('Upload failed. Please check your CSV format.')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleClear = async () => {
    if (!window.confirm('Clear all current operations data?')) return
    try {
      await api.delete('/current-operations')
      loadData()
    } catch (e) {
      console.error('Clear failed:', e)
    }
  }

  const toggleCompany = (company) => {
    const newSet = new Set(expandedCompanies)
    if (newSet.has(company)) newSet.delete(company)
    else newSet.add(company)
    setExpandedCompanies(newSet)
  }

  const toggleTeam = (key) => {
    const newSet = new Set(expandedTeams)
    if (newSet.has(key)) newSet.delete(key)
    else newSet.add(key)
    setExpandedTeams(newSet)
  }

  if (loading) {
    return (
      <div className="empty-state">
        <RefreshCw size={32} className="animate-spin" style={{ color: '#a3a3a3' }} />
        <p style={{ marginTop: 12, color: '#737373' }}>Loading current operations...</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Current Operations</h1>
          <p className="page-subtitle">{data.total} properties across {data.companies.length} companies</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {data.total > 0 && (
            <button className="btn btn-secondary" onClick={handleClear}>
              <Trash2 size={16} /> Clear All
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Upload size={16} /> {uploading ? 'Uploading...' : 'Upload File'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls,.doc,.docx,.pdf"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
        </div>
      </div>

      {/* Upload Instructions */}
      {data.total === 0 && (
        <div className="card" style={{ marginBottom: 20, padding: 24, textAlign: 'center' }}>
          <Upload size={48} color="#a3a3a3" style={{ marginBottom: 16 }} />
          <h3 style={{ marginBottom: 8, color: '#171717' }}>Upload Current Operations</h3>
          <p style={{ color: '#737373', marginBottom: 16 }}>
            Upload a file with your current operations data.
          </p>
          <p style={{ color: '#737373', fontSize: 12, marginBottom: 8 }}>
            <strong>Supported formats:</strong> CSV, Excel (.xlsx), Word (.docx), PDF
          </p>
          <p style={{ color: '#737373', fontSize: 12, marginBottom: 16 }}>
            Expected columns: <strong>Company, Team, Property Name, Property Type, Address, City, State, Beds, Notes</strong>
          </p>
          <button
            className="btn btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <Upload size={16} /> Select File
          </button>
        </div>
      )}

      {/* Companies List */}
      {data.companies.map(company => {
        const isExpanded = expandedCompanies.has(company.company)
        const teamNames = Object.keys(company.teams)
        const totalProps = teamNames.reduce((sum, t) => sum + company.teams[t].length, 0)
        const totalBeds = teamNames.reduce((sum, t) =>
          sum + company.teams[t].reduce((s, p) => s + (p.beds || 0), 0), 0)

        return (
          <div key={company.company} className="card" style={{ marginBottom: 12, padding: 0, overflow: 'hidden' }}>
            {/* Company Header */}
            <div
              onClick={() => toggleCompany(company.company)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px 20px',
                cursor: 'pointer',
                background: isExpanded ? 'white' : '#fafafa',
                borderBottom: isExpanded ? '1px solid #e5e5e5' : 'none'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {isExpanded ? <ChevronDown size={20} color="#737373" /> : <ChevronRight size={20} color="#737373" />}
                <Building2 size={24} color="#0b7280" />
                <div>
                  <div style={{ fontWeight: 700, fontSize: 16, color: '#171717' }}>{company.company}</div>
                  <div style={{ fontSize: 12, color: '#737373' }}>
                    {teamNames.length} team{teamNames.length !== 1 ? 's' : ''} · {totalProps} properties · {totalBeds} beds
                  </div>
                </div>
              </div>
            </div>

            {/* Teams */}
            {isExpanded && (
              <div style={{ padding: '12px 20px' }}>
                {teamNames.map(teamName => {
                  const teamKey = `${company.company}-${teamName}`
                  const isTeamExpanded = expandedTeams.has(teamKey)
                  const properties = company.teams[teamName]
                  const teamBeds = properties.reduce((s, p) => s + (p.beds || 0), 0)

                  return (
                    <div key={teamKey} style={{ marginBottom: 8 }}>
                      {/* Team Header */}
                      <div
                        onClick={() => toggleTeam(teamKey)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10,
                          padding: '10px 12px',
                          background: '#f5f5f5',
                          borderRadius: 6,
                          cursor: 'pointer'
                        }}
                      >
                        {isTeamExpanded ? <ChevronDown size={16} color="#737373" /> : <ChevronRight size={16} color="#737373" />}
                        <Users size={16} color="#7c3aed" />
                        <span style={{ fontWeight: 600, fontSize: 14 }}>{teamName || 'No Team'}</span>
                        <span style={{
                          background: '#0b7280',
                          color: 'white',
                          padding: '2px 8px',
                          borderRadius: 10,
                          fontSize: 11,
                          fontWeight: 600
                        }}>
                          {properties.length}
                        </span>
                        <span style={{ color: '#737373', fontSize: 12 }}>{teamBeds} beds</span>
                      </div>

                      {/* Properties */}
                      {isTeamExpanded && (
                        <div style={{ marginTop: 8, marginLeft: 28 }}>
                          {properties.map(prop => (
                            <div
                              key={prop.id}
                              style={{
                                padding: '10px 12px',
                                background: 'white',
                                border: '1px solid #e5e5e5',
                                borderRadius: 4,
                                marginBottom: 6
                              }}
                            >
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <div>
                                  <div style={{ fontWeight: 600, fontSize: 13 }}>{prop.property_name || 'Unnamed Property'}</div>
                                  {prop.address && (
                                    <div style={{ fontSize: 12, color: '#737373' }}>
                                      {prop.address}{prop.city && `, ${prop.city}`}{prop.state && `, ${prop.state}`}
                                    </div>
                                  )}
                                </div>
                                <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                                  {prop.property_type && (
                                    <span className={'deal-type-badge ' + (prop.property_type || 'snf').toLowerCase()}>
                                      {prop.property_type}
                                    </span>
                                  )}
                                  {prop.beds && (
                                    <span style={{ fontSize: 12, color: '#737373' }}>{prop.beds} beds</span>
                                  )}
                                </div>
                              </div>
                              {prop.notes && (
                                <div style={{ marginTop: 6, fontSize: 12, color: '#525252', fontStyle: 'italic' }}>
                                  {prop.notes}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default CurrentOps
