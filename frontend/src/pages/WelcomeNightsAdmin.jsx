import React, { useState, useEffect, useRef } from 'react'
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import { FileText, Gamepad2, Building2, Image, Plus, Edit2, Trash2, Save, X, Upload, Download, FileBox } from 'lucide-react'
import {
  getWNBrands,
  getWNContent,
  updateWNContent,
  getWNGames,
  createWNGame,
  updateWNGame,
  deleteWNGame,
  getWNFacilities,
  createWNFacility,
  updateWNFacility,
  deleteWNFacility,
  importWNFacilities,
  uploadFacilityLogo,
  deleteFacilityLogo,
  getWNAssets,
  uploadWNAsset,
  deleteWNAsset,
  getWNTemplates,
  uploadWNTemplate,
  deleteWNTemplate
} from '../services/api'

function WelcomeNightsAdmin() {
  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Welcome Nights Admin</h1>
          <p className="page-subtitle">Manage content, games, facilities, and assets</p>
        </div>
      </div>

      <div className="tabs mb-4">
        <NavLink to="/admin/welcome-nights/content" className={({ isActive }) => `tab ${isActive ? 'active' : ''}`}>
          <FileText size={16} style={{ marginRight: 6 }} />
          Content
        </NavLink>
        <NavLink to="/admin/welcome-nights/games" className={({ isActive }) => `tab ${isActive ? 'active' : ''}`}>
          <Gamepad2 size={16} style={{ marginRight: 6 }} />
          Games
        </NavLink>
        <NavLink to="/admin/welcome-nights/facilities" className={({ isActive }) => `tab ${isActive ? 'active' : ''}`}>
          <Building2 size={16} style={{ marginRight: 6 }} />
          Facilities
        </NavLink>
        <NavLink to="/admin/welcome-nights/assets" className={({ isActive }) => `tab ${isActive ? 'active' : ''}`}>
          <Image size={16} style={{ marginRight: 6 }} />
          Logos
        </NavLink>
        <NavLink to="/admin/welcome-nights/templates" className={({ isActive }) => `tab ${isActive ? 'active' : ''}`}>
          <FileBox size={16} style={{ marginRight: 6 }} />
          Templates
        </NavLink>
      </div>

      <Routes>
        <Route path="/" element={<ContentAdmin />} />
        <Route path="/content" element={<ContentAdmin />} />
        <Route path="/games" element={<GamesAdmin />} />
        <Route path="/facilities" element={<FacilitiesAdmin />} />
        <Route path="/assets" element={<AssetsAdmin />} />
        <Route path="/templates" element={<TemplatesAdmin />} />
      </Routes>
    </div>
  )
}

// Content Admin
function ContentAdmin() {
  const [brands, setBrands] = useState([])
  const [selectedBrand, setSelectedBrand] = useState(null)
  const [content, setContent] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editingContent, setEditingContent] = useState(null)
  const [editValue, setEditValue] = useState('')

  useEffect(() => { loadBrands() }, [])
  useEffect(() => { if (selectedBrand) loadContent() }, [selectedBrand])

  const loadBrands = async () => {
    const data = await getWNBrands()
    setBrands(data)
    if (data.length > 0) setSelectedBrand(data[0].id)
  }

  const loadContent = async () => {
    setLoading(true)
    const data = await getWNContent(selectedBrand)
    setContent(data)
    setLoading(false)
  }

  const handleEdit = (item) => {
    setEditingContent(item.id)
    setEditValue(JSON.stringify(item.content, null, 2))
  }

  const handleSave = async (item) => {
    setSaving(true)
    try {
      const parsed = JSON.parse(editValue)
      await updateWNContent(item.id, { content: parsed, updated_by: 'Admin' })
      setEditingContent(null)
      loadContent()
    } catch (err) {
      alert('Invalid JSON: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  const CONTENT_LABELS = {
    history: 'History Timeline',
    footprint: 'Our Footprint',
    regions: 'Regions Map',
    culture: 'Culture Block'
  }

  return (
    <div>
      <div className="wn-filters mb-4">
        <select
          className="form-select"
          value={selectedBrand || ''}
          onChange={(e) => setSelectedBrand(parseInt(e.target.value))}
        >
          {brands.map(brand => (
            <option key={brand.id} value={brand.id}>{brand.name}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <p>Loading...</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {content.map(item => (
            <div key={item.id} className="card">
              <div className="card-header">
                <div>
                  <h3 className="card-title">{CONTENT_LABELS[item.content_key] || item.content_key}</h3>
                  <p className="card-subtitle">{item.title || 'No title set'}</p>
                </div>
                {editingContent === item.id ? (
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-sm btn-primary" onClick={() => handleSave(item)} disabled={saving}>
                      <Save size={14} /> Save
                    </button>
                    <button className="btn btn-sm btn-secondary" onClick={() => setEditingContent(null)}>
                      <X size={14} /> Cancel
                    </button>
                  </div>
                ) : (
                  <button className="btn btn-sm btn-secondary" onClick={() => handleEdit(item)}>
                    <Edit2 size={14} /> Edit
                  </button>
                )}
              </div>
              {editingContent === item.id ? (
                <textarea
                  className="form-textarea"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  style={{ fontFamily: 'monospace', minHeight: 300 }}
                />
              ) : (
                <pre style={{ fontSize: 12, background: '#f9fafb', padding: 12, borderRadius: 6, overflow: 'auto', maxHeight: 200 }}>
                  {JSON.stringify(item.content, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// Games Admin
function GamesAdmin() {
  const [games, setGames] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingGame, setEditingGame] = useState(null)
  const [form, setForm] = useState({
    title: '', description: '', rules: '', duration_minutes: '',
    game_type: 'challenge', value_label: ''
  })

  useEffect(() => { loadGames() }, [])

  const loadGames = async () => {
    setLoading(true)
    const data = await getWNGames()
    setGames(data)
    setLoading(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const data = {
        ...form,
        duration_minutes: form.duration_minutes ? parseInt(form.duration_minutes) : null
      }
      if (editingGame) {
        await updateWNGame(editingGame, data)
      } else {
        await createWNGame(data)
      }
      setShowForm(false)
      setEditingGame(null)
      setForm({ title: '', description: '', rules: '', duration_minutes: '', game_type: 'challenge', value_label: '' })
      loadGames()
    } catch (err) {
      alert('Error saving game')
    }
  }

  const handleEdit = (game) => {
    setEditingGame(game.id)
    setForm({
      title: game.title || '',
      description: game.description || '',
      rules: game.rules || '',
      duration_minutes: game.duration_minutes || '',
      game_type: game.game_type || 'challenge',
      value_label: game.value_label || ''
    })
    setShowForm(true)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this game?')) return
    await deleteWNGame(id)
    loadGames()
  }

  const handleToggleActive = async (game) => {
    await updateWNGame(game.id, { is_active: !game.is_active })
    loadGames()
  }

  return (
    <div>
      <div className="wn-admin-section-header">
        <h3 className="wn-admin-section-title">Games Library</h3>
        <button className="btn btn-primary btn-sm" onClick={() => { setShowForm(true); setEditingGame(null); setForm({ title: '', description: '', rules: '', duration_minutes: '', game_type: 'challenge', value_label: '' }) }}>
          <Plus size={16} /> Add Game
        </button>
      </div>

      {showForm && (
        <div className="card mb-4">
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Title</label>
                <input className="form-input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
              </div>
              <div className="form-group">
                <label className="form-label">Type</label>
                <select className="form-select" value={form.game_type} onChange={(e) => setForm({ ...form, game_type: e.target.value })}>
                  <option value="icebreaker">Ice Breaker</option>
                  <option value="challenge">Challenge (Minute-to-Win-It)</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <input className="form-input" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Rules</label>
              <textarea className="form-textarea" rows={4} value={form.rules} onChange={(e) => setForm({ ...form, rules: e.target.value })} />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Duration (minutes)</label>
                <input type="number" className="form-input" value={form.duration_minutes} onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Value Label (e.g., FAMILY, TEAMWORK)</label>
                <input className="form-input" value={form.value_label} onChange={(e) => setForm({ ...form, value_label: e.target.value })} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className="btn btn-primary">{editingGame ? 'Update' : 'Create'} Game</button>
              <button type="button" className="btn btn-secondary" onClick={() => { setShowForm(false); setEditingGame(null) }}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {loading ? <p>Loading...</p> : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Duration</th>
              <th>Value</th>
              <th>Active</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {games.map(game => (
              <tr key={game.id}>
                <td><strong>{game.title}</strong></td>
                <td><span className={`wn-game-type-badge ${game.game_type}`}>{game.game_type}</span></td>
                <td>{game.duration_minutes ? `${game.duration_minutes} min` : '-'}</td>
                <td>{game.value_label || '-'}</td>
                <td>
                  <button className={`btn btn-sm ${game.is_active ? 'btn-primary' : 'btn-secondary'}`} onClick={() => handleToggleActive(game)}>
                    {game.is_active ? 'Active' : 'Inactive'}
                  </button>
                </td>
                <td>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-sm btn-ghost" onClick={() => handleEdit(game)}><Edit2 size={14} /></button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(game.id)}><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// Facilities Admin
function FacilitiesAdmin() {
  const [brands, setBrands] = useState([])
  const [facilities, setFacilities] = useState([])
  const [assets, setAssets] = useState({})
  const [selectedBrand, setSelectedBrand] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingFacility, setEditingFacility] = useState(null)
  const [form, setForm] = useState({ name: '', city: '', state: '', address: '' })
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [uploadingLogo, setUploadingLogo] = useState(null)
  const importFileRef = useRef(null)
  const logoFileRefs = useRef({})

  useEffect(() => { loadBrands() }, [])
  useEffect(() => { if (selectedBrand) loadFacilities() }, [selectedBrand])

  const loadBrands = async () => {
    const data = await getWNBrands()
    setBrands(data)
    if (data.length > 0) setSelectedBrand(data[0].id)
  }

  const loadFacilities = async () => {
    setLoading(true)
    const data = await getWNFacilities({ brand_id: selectedBrand })
    setFacilities(data)
    // Load assets to get logo URLs
    const assetData = await getWNAssets({ brand_id: selectedBrand, asset_type: 'facility_logo' })
    const assetMap = {}
    assetData.forEach(a => { assetMap[a.id] = a })
    setAssets(assetMap)
    setLoading(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingFacility) {
        await updateWNFacility(editingFacility, form)
      } else {
        await createWNFacility({ ...form, brand_id: selectedBrand })
      }
      setShowForm(false)
      setEditingFacility(null)
      setForm({ name: '', city: '', state: '', address: '' })
      loadFacilities()
    } catch (err) {
      alert('Error saving facility')
    }
  }

  const handleEdit = (facility) => {
    setEditingFacility(facility.id)
    setForm({
      name: facility.name,
      city: facility.city || '',
      state: facility.state || '',
      address: facility.address || ''
    })
    setShowForm(true)
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this facility?')) return
    await deleteWNFacility(id)
    loadFacilities()
  }

  const handleImport = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setImporting(true)
    setImportResult(null)
    try {
      const result = await importWNFacilities(selectedBrand, file)
      setImportResult(result)
      loadFacilities()
    } catch (err) {
      setImportResult({ message: 'Import failed: ' + (err.response?.data?.detail || err.message), errors: [] })
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  const handleLogoUpload = async (facilityId, e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploadingLogo(facilityId)
    try {
      await uploadFacilityLogo(facilityId, file)
      loadFacilities()
    } catch (err) {
      alert('Error uploading logo: ' + (err.response?.data?.detail || err.message))
    } finally {
      setUploadingLogo(null)
      e.target.value = ''
    }
  }

  const handleLogoDelete = async (facilityId) => {
    if (!window.confirm('Remove this logo?')) return
    try {
      await deleteFacilityLogo(facilityId)
      loadFacilities()
    } catch (err) {
      alert('Error removing logo')
    }
  }

  const downloadTemplate = () => {
    const csv = 'name,city,state,address\nExample Facility,Portland,OR,123 Main St'
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'facilities_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      <div className="wn-filters mb-4">
        <select className="form-select" value={selectedBrand || ''} onChange={(e) => setSelectedBrand(parseInt(e.target.value))}>
          {brands.map(brand => <option key={brand.id} value={brand.id}>{brand.name}</option>)}
        </select>
        <button className="btn btn-primary btn-sm" onClick={() => { setShowForm(true); setEditingFacility(null); setForm({ name: '', city: '', state: '', address: '' }) }}>
          <Plus size={16} /> Add Facility
        </button>
        <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
          <Upload size={16} /> {importing ? 'Importing...' : 'Import CSV/Excel'}
          <input
            ref={importFileRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleImport}
            style={{ display: 'none' }}
            disabled={importing}
          />
        </label>
        <button className="btn btn-ghost btn-sm" onClick={downloadTemplate} title="Download CSV template">
          <Download size={16} /> Template
        </button>
      </div>

      {importResult && (
        <div className={`alert ${importResult.errors?.length ? 'alert-warning' : 'alert-success'} mb-4`}>
          <strong>{importResult.message}</strong>
          {importResult.errors?.length > 0 && (
            <ul style={{ marginTop: 8, paddingLeft: 20, fontSize: 13 }}>
              {importResult.errors.map((err, i) => <li key={i}>{err}</li>)}
            </ul>
          )}
          <button className="btn btn-sm btn-ghost" onClick={() => setImportResult(null)} style={{ marginLeft: 'auto' }}>
            <X size={14} />
          </button>
        </div>
      )}

      {showForm && (
        <div className="card mb-4">
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Facility Name</label>
              <input className="form-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">City</label>
                <input className="form-input" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">State</label>
                <input className="form-input" value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Address</label>
              <input className="form-input" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" className="btn btn-primary">{editingFacility ? 'Update' : 'Create'} Facility</button>
              <button type="button" className="btn btn-secondary" onClick={() => { setShowForm(false); setEditingFacility(null) }}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {loading ? <p>Loading...</p> : (
        <table className="data-table">
          <thead>
            <tr><th style={{ width: 80 }}>Logo</th><th>Name</th><th>City</th><th>State</th><th>Actions</th></tr>
          </thead>
          <tbody>
            {facilities.map(f => (
              <tr key={f.id}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {f.logo_asset_id && assets[f.logo_asset_id] ? (
                      <div style={{ position: 'relative', width: 50, height: 50 }}>
                        <img
                          src={`http://localhost:8000${assets[f.logo_asset_id].url}`}
                          alt={f.name}
                          style={{ width: 50, height: 50, objectFit: 'contain', borderRadius: 4, background: '#f3f4f6' }}
                        />
                        <button
                          className="btn btn-sm btn-danger"
                          onClick={() => handleLogoDelete(f.id)}
                          style={{ position: 'absolute', top: -8, right: -8, padding: 2, minWidth: 20, height: 20 }}
                          title="Remove logo"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ) : (
                      <label style={{ cursor: 'pointer' }}>
                        <div
                          style={{
                            width: 50,
                            height: 50,
                            borderRadius: 4,
                            background: '#f3f4f6',
                            border: '2px dashed #d1d5db',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#9ca3af'
                          }}
                          title="Click to upload logo (PNG)"
                        >
                          {uploadingLogo === f.id ? (
                            <div className="animate-spin" style={{ width: 16, height: 16, border: '2px solid #9ca3af', borderTopColor: 'transparent', borderRadius: '50%' }} />
                          ) : (
                            <Image size={20} />
                          )}
                        </div>
                        <input
                          type="file"
                          accept="image/png,image/jpeg,image/gif,image/webp"
                          onChange={(e) => handleLogoUpload(f.id, e)}
                          style={{ display: 'none' }}
                          disabled={uploadingLogo === f.id}
                        />
                      </label>
                    )}
                  </div>
                </td>
                <td><strong>{f.name}</strong></td>
                <td>{f.city || '-'}</td>
                <td>{f.state || '-'}</td>
                <td>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-sm btn-ghost" onClick={() => handleEdit(f)}><Edit2 size={14} /></button>
                    <button className="btn btn-sm btn-danger" onClick={() => handleDelete(f.id)}><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
            {facilities.length === 0 && (
              <tr><td colSpan={5} style={{ textAlign: 'center', color: '#6b7280' }}>No facilities yet. Add one or import from CSV/Excel.</td></tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}

// Assets Admin
function AssetsAdmin() {
  const [brands, setBrands] = useState([])
  const [assets, setAssets] = useState([])
  const [selectedBrand, setSelectedBrand] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [assetType, setAssetType] = useState('logo')

  useEffect(() => { loadBrands() }, [])
  useEffect(() => { if (selectedBrand) loadAssets() }, [selectedBrand])

  const loadBrands = async () => {
    const data = await getWNBrands()
    setBrands(data)
    if (data.length > 0) setSelectedBrand(data[0].id)
  }

  const loadAssets = async () => {
    setLoading(true)
    const data = await getWNAssets({ brand_id: selectedBrand })
    // Sort alphabetically by original filename
    data.sort((a, b) => (a.original_filename || '').localeCompare(b.original_filename || ''))
    setAssets(data)
    setLoading(false)
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      await uploadWNAsset(selectedBrand, assetType, file)
      loadAssets()
    } catch (err) {
      alert('Error uploading asset')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this asset?')) return
    await deleteWNAsset(id)
    loadAssets()
  }

  return (
    <div>
      <div className="wn-filters mb-4">
        <select className="form-select" value={selectedBrand || ''} onChange={(e) => setSelectedBrand(parseInt(e.target.value))}>
          {brands.map(brand => <option key={brand.id} value={brand.id}>{brand.name}</option>)}
        </select>
        <select className="form-select" value={assetType} onChange={(e) => setAssetType(e.target.value)}>
          <option value="logo">Logo</option>
          <option value="background">Background</option>
          <option value="icon">Icon</option>
          <option value="image">Image</option>
        </select>
        <label className="btn btn-primary btn-sm" style={{ cursor: 'pointer' }}>
          <Plus size={16} /> {uploading ? 'Uploading...' : 'Upload Asset'}
          <input type="file" accept="image/*" onChange={handleUpload} style={{ display: 'none' }} disabled={uploading} />
        </label>
      </div>

      {loading ? <p>Loading...</p> : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
          {assets.map(asset => (
            <div key={asset.id} className="card" style={{ padding: 12 }}>
              <div style={{ aspectRatio: '1', background: '#f3f4f6', borderRadius: 8, marginBottom: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                <img src={`http://localhost:8000${asset.url}`} alt={asset.original_filename} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
              </div>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {asset.original_filename}
              </div>
              <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 8 }}>{asset.asset_type}</div>
              <button className="btn btn-sm btn-danger" onClick={() => handleDelete(asset.id)} style={{ width: '100%' }}>
                <Trash2 size={14} /> Delete
              </button>
            </div>
          ))}
          {assets.length === 0 && <p className="text-muted">No assets uploaded yet</p>}
        </div>
      )}
    </div>
  )
}

// Templates Admin - Upload reference PPTX templates
function TemplatesAdmin() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)

  useEffect(() => { loadTemplates() }, [])

  const loadTemplates = async () => {
    setLoading(true)
    try {
      const data = await getWNTemplates()
      setTemplates(data)
    } catch (err) {
      console.error('Error loading templates:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    try {
      await uploadWNTemplate(file)
      loadTemplates()
    } catch (err) {
      alert('Error uploading template: ' + (err.response?.data?.detail || err.message))
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const handleDelete = async (filename) => {
    if (!window.confirm('Delete this template?')) return
    try {
      await deleteWNTemplate(filename)
      loadTemplates()
    } catch (err) {
      alert('Error deleting template')
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDate = (isoString) => {
    return new Date(isoString).toLocaleString()
  }

  return (
    <div>
      <div className="wn-admin-section-header">
        <div>
          <h3 className="wn-admin-section-title">PowerPoint Templates</h3>
          <p style={{ color: '#6b7280', fontSize: 14, marginTop: 4 }}>
            Upload your existing Culture Night PowerPoint templates as reference for improving the generated presentations.
          </p>
        </div>
        <label className="btn btn-primary" style={{ cursor: 'pointer' }}>
          <Upload size={16} /> {uploading ? 'Uploading...' : 'Upload Template'}
          <input
            type="file"
            accept=".pptx,.ppt"
            onChange={handleUpload}
            style={{ display: 'none' }}
            disabled={uploading}
          />
        </label>
      </div>

      {loading ? <p>Loading...</p> : (
        <div style={{ marginTop: 24 }}>
          {templates.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: 40 }}>
              <FileBox size={48} style={{ color: '#d1d5db', marginBottom: 16 }} />
              <p style={{ color: '#6b7280', marginBottom: 16 }}>No templates uploaded yet</p>
              <p style={{ color: '#9ca3af', fontSize: 14 }}>
                Upload your current Culture Night PowerPoint template (.pptx) so we can use it as a reference.
              </p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Size</th>
                  <th>Uploaded</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {templates.map(t => (
                  <tr key={t.filename}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <FileBox size={20} style={{ color: '#f97316' }} />
                        <strong>{t.filename}</strong>
                      </div>
                    </td>
                    <td>{formatFileSize(t.size)}</td>
                    <td>{formatDate(t.uploaded_at)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <a
                          href={`http://localhost:8000${t.url}`}
                          download
                          className="btn btn-sm btn-secondary"
                        >
                          <Download size={14} /> Download
                        </a>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(t.filename)}>
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

export default WelcomeNightsAdmin
