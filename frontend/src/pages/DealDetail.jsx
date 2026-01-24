import React, { useState, useEffect, useCallback, useRef, createContext, useContext } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Building2, Upload, FileText, Trash2, DollarSign, BarChart3, Edit2, Save, X, Plus, CheckCircle, Clock, RefreshCw, Eye, Loader2, Zap, MapPin, Star, Folder, FolderOpen, ChevronRight, ChevronDown, MoveRight, AlertTriangle, TrendingUp, Shield, Play, FileSearch } from 'lucide-react'
import { getDeal, updateDeal, deleteDeal, updateDealStatus, uploadDocument, deleteDocument, getValuation, createProperty, deleteProperty, createTask, updateTask, formatCurrency, formatNumber, formatPercent, formatDate, formatDateTime, getDealScorecard, calculateScorecard, getDealRiskFlags, detectRisks, getFinancialSummary, getDealClaims, runFullAnalysis } from '../services/api'
import api from '../services/api'

const STS = [
  { key: 'vetting', label: 'Vetting' },
  { key: 'pipeline', label: 'Pipeline' },
  { key: 'due_diligence', label: 'Due Diligence' },
  { key: 'current_operations', label: 'Current Ops' },
  { key: 'on_hold', label: 'On Hold' },
  { key: 'closed', label: 'Closed' },
  { key: 'passed', label: 'Passed' }
]

// Confirmation Modal Component
function ConfirmModal({ isOpen, title, message, onConfirm, onCancel, confirmText = 'Delete', confirmDanger = true }) {
  if (!isOpen) return null

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999
    }} onClick={onCancel}>
      <div style={{
        background: 'white',
        borderRadius: 8,
        padding: 24,
        maxWidth: 400,
        width: '90%',
        boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)'
      }} onClick={e => e.stopPropagation()}>
        <h3 style={{ fontSize: 18, fontWeight: 600, marginBottom: 8, color: '#171717' }}>{title}</h3>
        <p style={{ color: '#525252', marginBottom: 24, lineHeight: 1.5 }}>{message}</p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button className={confirmDanger ? 'btn btn-danger' : 'btn btn-primary'} onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}

// Hook to manage confirmation dialogs
function useConfirm() {
  const [state, setState] = useState({ isOpen: false, title: '', message: '', resolve: null })

  const confirm = useCallback((title, message) => {
    return new Promise((resolve) => {
      setState({ isOpen: true, title, message, resolve })
    })
  }, [])

  const handleConfirm = useCallback(() => {
    state.resolve?.(true)
    setState({ isOpen: false, title: '', message: '', resolve: null })
  }, [state.resolve])

  const handleCancel = useCallback(() => {
    state.resolve?.(false)
    setState({ isOpen: false, title: '', message: '', resolve: null })
  }, [state.resolve])

  const ConfirmDialog = useCallback(() => (
    <ConfirmModal
      isOpen={state.isOpen}
      title={state.title}
      message={state.message}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
    />
  ), [state.isOpen, state.title, state.message, handleConfirm, handleCancel])

  return { confirm, ConfirmDialog }
}

// Analysis Section Component with expandable view
function AnalysisSection({ doc, analysis }) {
  const [expanded, setExpanded] = useState(false)
  const summary = analysis?.summary || doc.analysis_summary || 'Document analyzed'

  // Simple markdown-like formatting for the summary
  const formatSummary = (text) => {
    if (!text) return 'Document analyzed'
    // Convert **bold** to styled spans and handle line breaks
    return text.split('\n').map((line, i) => {
      const formatted = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      return <div key={i} dangerouslySetInnerHTML={{ __html: formatted }} style={{ marginBottom: line.startsWith('**') ? 6 : 2 }} />
    })
  }

  return (
    <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #e5e5e5' }}>
      <div
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <CheckCircle size={14} color="#059669" />
          <span style={{ fontWeight: 600, fontSize: 12, color: '#059669' }}>Analysis Complete</span>
          {analysis?.document_type && (
            <span style={{ background: '#dbeafe', color: '#1d4ed8', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
              {analysis.document_type.replace('_', ' ').toUpperCase()}
            </span>
          )}
        </div>
        <button
          className="btn btn-ghost btn-sm"
          style={{ padding: '4px 8px', fontSize: 11 }}
        >
          {expanded ? 'Hide' : 'View'} Analysis
          {expanded ? <ChevronDown size={12} style={{ marginLeft: 4 }} /> : <ChevronRight size={12} style={{ marginLeft: 4 }} />}
        </button>
      </div>

      {/* Metrics row - always visible if present */}
      {analysis?.metrics && Object.keys(analysis.metrics).length > 0 && (
        <div style={{ display: 'flex', gap: 16, marginTop: 8, padding: '8px 12px', background: '#f0fdfa', borderRadius: 4 }}>
          {analysis.metrics.beds && (
            <div>
              <span style={{ fontSize: 10, color: '#737373', fontWeight: 500 }}>BEDS</span>
              <div style={{ fontWeight: 700, fontSize: 14, color: '#0b7280' }}>{analysis.metrics.beds}</div>
            </div>
          )}
          {analysis.metrics.occupancy && (
            <div>
              <span style={{ fontSize: 10, color: '#737373', fontWeight: 500 }}>OCCUPANCY</span>
              <div style={{ fontWeight: 700, fontSize: 14, color: '#0b7280' }}>{analysis.metrics.occupancy}%</div>
            </div>
          )}
          {analysis.metrics.ebitdar && (
            <div>
              <span style={{ fontSize: 10, color: '#737373', fontWeight: 500 }}>EBITDAR</span>
              <div style={{ fontWeight: 700, fontSize: 14, color: '#059669' }}>{formatCurrency(analysis.metrics.ebitdar)}</div>
            </div>
          )}
          {analysis.metrics.asking_price && (
            <div>
              <span style={{ fontSize: 10, color: '#737373', fontWeight: 500 }}>PRICE</span>
              <div style={{ fontWeight: 700, fontSize: 14, color: '#0b7280' }}>{formatCurrency(analysis.metrics.asking_price)}</div>
            </div>
          )}
        </div>
      )}

      {/* Expanded analysis content */}
      {expanded && (
        <div style={{
          marginTop: 10,
          padding: 12,
          background: 'white',
          borderRadius: 6,
          border: '1px solid #e5e5e5',
          fontSize: 13,
          lineHeight: 1.6,
          color: '#374151',
          maxHeight: 300,
          overflowY: 'auto'
        }}>
          {formatSummary(summary)}
        </div>
      )}
    </div>
  )
}

const DEFAULT_CATS = [
  { value: 'offering_memorandum', label: 'Offering Memo' },
  { value: 'financials', label: 'Financials' },
  { value: 'rent_roll', label: 'Rent Roll' },
  { value: 'survey', label: 'Survey' },
  { value: 'payor_mix', label: 'Payor Mix' },
  { value: 'other', label: 'Other' }
]

function DealDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [deal, setDeal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('overview')
  const [editing, setEditing] = useState(false)
  const [ed, setEd] = useState({})
  const [val, setVal] = useState(null)
  const { confirm, ConfirmDialog } = useConfirm()

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const d = await getDeal(id)
      setDeal(d)
      setEd(d)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  const chgStatus = async (s) => {
    try {
      await updateDealStatus(id, s)
      load()
    } catch (e) { console.error(e) }
  }

  const save = async () => {
    try {
      await updateDeal(id, ed)
      setEditing(false)
      load()
    } catch (e) { console.error(e) }
  }

  const del = async () => {
    const confirmed = await confirm('Delete Deal', 'Are you sure you want to delete this deal? This action cannot be undone.')
    if (confirmed) {
      try {
        await deleteDeal(id)
        navigate('/')
      } catch (e) { console.error(e) }
    }
  }

  const loadVal = async () => {
    try {
      setVal(await getValuation(id))
    } catch (e) { console.error(e) }
  }

  if (loading) {
    return (
      <div className="empty-state">
        <RefreshCw size={32} className="animate-spin" style={{ color: '#a3a3a3' }} />
        <p style={{ marginTop: 12, color: '#737373' }}>Loading deal...</p>
      </div>
    )
  }

  if (!deal) {
    return (
      <div className="empty-state">
        <p style={{ color: '#737373', marginBottom: 16 }}>Deal not found</p>
        <button className="btn btn-primary" onClick={() => navigate('/')}>Back to Pipeline</button>
      </div>
    )
  }

  return (
    <div>
      {/* Back button */}
      <button onClick={() => navigate('/')} className="btn btn-ghost btn-sm" style={{ marginBottom: 16 }}>
        <ArrowLeft size={16} /> Back to Pipeline
      </button>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h1 className="page-title">{deal.name}</h1>
          <div style={{ display: 'flex', gap: 12, marginTop: 8, alignItems: 'center' }}>
            <span className={'deal-type-badge ' + (deal.deal_type || 'snf').toLowerCase()}>
              {deal.deal_type || 'SNF'}
            </span>
            {deal.total_beds > 0 && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#737373', fontSize: 13 }}>
                <Building2 size={14} /> {deal.total_beds} beds
              </span>
            )}
            {deal.properties?.length > 1 && (
              <span style={{ color: '#737373', fontSize: 13 }}>
                {deal.properties.length} properties
              </span>
            )}
            {deal.asking_price > 0 && (
              <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#0b7280', fontSize: 13, fontWeight: 600 }}>
                <DollarSign size={14} /> {formatCurrency(deal.asking_price)}
              </span>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <select
            value={deal.status}
            onChange={e => chgStatus(e.target.value)}
            className="form-select"
            style={{ width: 160 }}
          >
            {STS.map(s => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
          <button className="btn btn-danger btn-sm" onClick={del}>
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button className={'tab ' + (tab === 'overview' ? 'active' : '')} onClick={() => setTab('overview')}>
          Overview
        </button>
        <button className={'tab ' + (tab === 'properties' ? 'active' : '')} onClick={() => setTab('properties')}>
          Properties ({deal.properties?.length || 0})
        </button>
        <button className={'tab ' + (tab === 'documents' ? 'active' : '')} onClick={() => setTab('documents')}>
          Documents ({deal.documents?.length || 0})
        </button>
        <button className={'tab ' + (tab === 'valuation' ? 'active' : '')} onClick={() => { setTab('valuation'); loadVal() }}>
          Valuation
        </button>
        <button className={'tab ' + (tab === 'tasks' ? 'active' : '')} onClick={() => setTab('tasks')}>
          Tasks
        </button>
        <button className={'tab ' + (tab === 'activity' ? 'active' : '')} onClick={() => setTab('activity')}>
          Activity
        </button>
        <button className={'tab ' + (tab === 'analysis' ? 'active' : '')} onClick={() => setTab('analysis')} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <FileSearch size={14} />
          Analysis
        </button>
      </div>

      {/* Tab Content */}
      {tab === 'overview' && <Overview deal={deal} editing={editing} ed={ed} setEd={setEd} setEditing={setEditing} save={save} />}
      {tab === 'documents' && <Docs deal={deal} onRefresh={load} confirm={confirm} />}
      {tab === 'valuation' && <Val val={val} />}
      {tab === 'properties' && <Props deal={deal} onRefresh={load} confirm={confirm} />}
      {tab === 'tasks' && <Tasks deal={deal} onRefresh={load} />}
      {tab === 'activity' && <Activity deal={deal} />}
      {tab === 'analysis' && <Analysis deal={deal} />}

      {/* Confirmation Dialog */}
      <ConfirmDialog />
    </div>
  )
}

function Overview({ deal, editing, ed, setEd, setEditing, save }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20 }}>
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Deal Information</h3>
          {editing ? (
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-secondary btn-sm" onClick={() => setEditing(false)}>
                <X size={14} /> Cancel
              </button>
              <button className="btn btn-primary btn-sm" onClick={save}>
                <Save size={14} /> Save
              </button>
            </div>
          ) : (
            <button className="btn btn-secondary btn-sm" onClick={() => setEditing(true)}>
              <Edit2 size={14} /> Edit
            </button>
          )}
        </div>

        {editing ? (
          <div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Name</label>
                <input className="form-input" value={ed.name || ''} onChange={e => setEd({ ...ed, name: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Type</label>
                <select className="form-select" value={ed.deal_type || 'SNF'} onChange={e => setEd({ ...ed, deal_type: e.target.value })}>
                  <option value="SNF">SNF</option>
                  <option value="ALF">ALF</option>
                  <option value="ILF">ILF</option>
                  <option value="MC">Memory Care</option>
                </select>
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Total Beds</label>
                <input type="number" className="form-input" value={ed.total_beds || ''} onChange={e => setEd({ ...ed, total_beds: parseInt(e.target.value) || null })} />
              </div>
              <div className="form-group">
                <label className="form-label">Asking Price ($)</label>
                <input type="number" className="form-input" value={ed.asking_price || ''} onChange={e => setEd({ ...ed, asking_price: parseFloat(e.target.value) || null })} />
              </div>
            </div>
            <div className="form-row">
              <div className="form-group">
                <label className="form-label">EBITDAR ($)</label>
                <input type="number" className="form-input" value={ed.ebitdar || ''} onChange={e => setEd({ ...ed, ebitdar: parseFloat(e.target.value) || null })} />
              </div>
              <div className="form-group">
                <label className="form-label">Cap Rate (%)</label>
                <input type="number" className="form-input" value={ed.cap_rate || ''} onChange={e => setEd({ ...ed, cap_rate: parseFloat(e.target.value) || null })} />
              </div>
            </div>
            <div className="form-group">
              <label className="form-label">Investment Thesis</label>
              <textarea className="form-textarea" rows={2} value={ed.investment_thesis || ''} onChange={e => setEd({ ...ed, investment_thesis: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Notes</label>
              <textarea className="form-textarea" rows={2} value={ed.notes || ''} onChange={e => setEd({ ...ed, notes: e.target.value })} />
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, fontSize: 13 }}>
            <div><span style={{ color: '#737373' }}>Type:</span> <strong>{deal.deal_type || 'SNF'}</strong></div>
            <div><span style={{ color: '#737373' }}>Priority:</span> <span className={'priority-badge ' + deal.priority}>{deal.priority}</span></div>
            <div><span style={{ color: '#737373' }}>Beds:</span> <strong>{formatNumber(deal.total_beds)}</strong></div>
            <div><span style={{ color: '#737373' }}>Units:</span> <strong>{formatNumber(deal.total_units)}</strong></div>
            <div><span style={{ color: '#737373' }}>Asking:</span> <strong>{formatCurrency(deal.asking_price)}</strong></div>
            <div><span style={{ color: '#737373' }}>EBITDAR:</span> <strong>{formatCurrency(deal.ebitdar)}</strong></div>
            <div><span style={{ color: '#737373' }}>Cap Rate:</span> <strong>{deal.cap_rate ? deal.cap_rate + '%' : '—'}</strong></div>
            <div><span style={{ color: '#737373' }}>$/Bed:</span> <strong>{formatCurrency(deal.price_per_bed)}</strong></div>
            <div style={{ gridColumn: '1/-1', paddingTop: 8, borderTop: '1px solid #e5e5e5' }}>
              <span style={{ color: '#737373' }}>Thesis:</span>
              <p style={{ marginTop: 4 }}>{deal.investment_thesis || '—'}</p>
            </div>
            <div style={{ gridColumn: '1/-1' }}>
              <span style={{ color: '#737373' }}>Notes:</span>
              <p style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{deal.notes || '—'}</p>
            </div>
          </div>
        )}
      </div>

      <div>
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 className="card-title" style={{ marginBottom: 12 }}>Broker / Source</h3>
          <div style={{ fontSize: 13, color: '#525252' }}>
            <p style={{ marginBottom: 8 }}><span style={{ color: '#737373' }}>Source:</span> <strong>{deal.source || '—'}</strong></p>
            <p style={{ marginBottom: 8 }}><span style={{ color: '#737373' }}>Broker:</span> <strong>{deal.broker_name || '—'}</strong></p>
            <p style={{ marginBottom: 8 }}><span style={{ color: '#737373' }}>Company:</span> {deal.broker_company || '—'}</p>
            <p style={{ marginBottom: 8 }}><span style={{ color: '#737373' }}>Email:</span> {deal.broker_email || '—'}</p>
            <p><span style={{ color: '#737373' }}>Seller:</span> {deal.seller_name || '—'}</p>
          </div>
        </div>
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 12 }}>Timeline</h3>
          <div style={{ fontSize: 13, color: '#525252' }}>
            <p style={{ marginBottom: 8 }}><span style={{ color: '#737373' }}>Created:</span> {formatDate(deal.created_at)}</p>
            <p><span style={{ color: '#737373' }}>Updated:</span> {formatDate(deal.updated_at)}</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function Docs({ deal, onRefresh, confirm }) {
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState({})
  const [analysisResults, setAnalysisResults] = useState({})
  const [dragActive, setDragActive] = useState(false)
  const [uploadCat, setUploadCat] = useState('other')
  const [movingDoc, setMovingDoc] = useState(null)
  const [draggedDoc, setDraggedDoc] = useState(null)
  const [dragOverFolder, setDragOverFolder] = useState(null)
  const [renamingDocId, setRenamingDocId] = useState(null)
  const [renameValue, setRenameValue] = useState('')
  const [addingFolder, setAddingFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [renamingFolderId, setRenamingFolderId] = useState(null)
  const [folderRenameValue, setFolderRenameValue] = useState('')
  const fileInputRef = useRef(null)

  // Merge default categories with custom categories from deal
  const customCats = deal.custom_categories || []
  const CATS = React.useMemo(() => {
    const cats = [...DEFAULT_CATS]
    customCats.forEach(custom => {
      const existing = cats.find(c => c.value === custom.key)
      if (existing) {
        existing.label = custom.label
      } else {
        // Add new custom category before 'other'
        const otherIndex = cats.findIndex(c => c.value === 'other')
        cats.splice(otherIndex, 0, { value: custom.key, label: custom.label, isCustom: true })
      }
    })
    return cats
  }, [customCats])

  const [expandedFolders, setExpandedFolders] = useState(() => new Set(DEFAULT_CATS.map(c => c.value)))

  // Expand new custom folders when they're added
  useEffect(() => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev)
      CATS.forEach(c => newSet.add(c.value))
      return newSet
    })
  }, [CATS])

  // Group documents by category
  const docsByCategory = {}
  CATS.forEach(c => { docsByCategory[c.value] = [] })
  deal.documents?.forEach(doc => {
    const cat = doc.category || 'other'
    if (!docsByCategory[cat]) docsByCategory[cat] = []
    docsByCategory[cat].push(doc)
  })

  const toggleFolder = (cat) => {
    const newSet = new Set(expandedFolders)
    if (newSet.has(cat)) newSet.delete(cat)
    else newSet.add(cat)
    setExpandedFolders(newSet)
  }

  // File upload drag handlers
  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true)
    else if (e.type === 'dragleave') setDragActive(false)
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files?.length > 0) await uploadFiles(e.dataTransfer.files)
  }

  // Document drag between folders
  const handleDocDragStart = (e, doc) => {
    setDraggedDoc(doc)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', doc.id)
    setTimeout(() => { e.target.style.opacity = '0.5' }, 0)
  }

  const handleDocDragEnd = (e) => {
    e.target.style.opacity = '1'
    setDraggedDoc(null)
    setDragOverFolder(null)
  }

  const handleFolderDragOver = (e, folderKey) => {
    e.preventDefault()
    e.stopPropagation()
    // Only show drop indicator if dragging a doc (not a file from desktop)
    if (draggedDoc && draggedDoc.category !== folderKey) {
      e.dataTransfer.dropEffect = 'move'
      setDragOverFolder(folderKey)
    }
  }

  const handleFolderDragLeave = (e) => {
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setDragOverFolder(null)
    }
  }

  const handleFolderDrop = async (e, folderKey) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOverFolder(null)

    if (draggedDoc && draggedDoc.category !== folderKey) {
      await moveDoc(draggedDoc.id, folderKey)
    }
    setDraggedDoc(null)
  }

  const handleFileInput = async (e) => {
    if (e.target.files?.length > 0) await uploadFiles(e.target.files)
  }

  const uploadFiles = async (files) => {
    setUploading(true)
    try {
      for (const file of files) {
        const result = await uploadDocument(deal.id, file, uploadCat)
        const docId = result.document?.id
        if (docId) {
          setAnalyzing(prev => ({ ...prev, [docId]: true }))
          try {
            const analysis = await api.post(`/documents/${docId}/analyze?auto_apply=true`)
            setAnalysisResults(prev => ({ ...prev, [docId]: analysis.data }))
          } catch (e) { console.error('Analysis failed:', e) }
          setAnalyzing(prev => ({ ...prev, [docId]: false }))
        }
      }
      // Expand the folder we just uploaded to
      setExpandedFolders(prev => new Set([...prev, uploadCat]))
      onRefresh()
    } catch (e) {
      console.error('Upload failed:', e)
      alert('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const analyzeDoc = async (docId, e) => {
    e?.stopPropagation()
    setAnalyzing(prev => ({ ...prev, [docId]: true }))
    try {
      const response = await api.post(`/documents/${docId}/analyze?auto_apply=true`)
      setAnalysisResults(prev => ({ ...prev, [docId]: response.data }))
      onRefresh()
    } catch (e) {
      console.error('Analysis failed:', e)
    } finally {
      setAnalyzing(prev => ({ ...prev, [docId]: false }))
    }
  }

  const moveDoc = async (docId, newCategory) => {
    try {
      await api.patch(`/documents/${docId}/category?category=${newCategory}`)
      setMovingDoc(null)
      setExpandedFolders(prev => new Set([...prev, newCategory]))
      onRefresh()
    } catch (e) {
      console.error('Move failed:', e)
    }
  }

  const startRename = (doc, e) => {
    e?.stopPropagation()
    setRenamingDocId(doc.id)
    setRenameValue(doc.original_filename)
  }

  const cancelRename = () => {
    setRenamingDocId(null)
    setRenameValue('')
  }

  const saveRename = async (docId) => {
    if (!renameValue.trim()) {
      cancelRename()
      return
    }
    try {
      await api.patch(`/documents/${docId}/rename?name=${encodeURIComponent(renameValue.trim())}`)
      setRenamingDocId(null)
      setRenameValue('')
      onRefresh()
    } catch (e) {
      console.error('Rename failed:', e)
    }
  }

  const handleRenameKeyDown = (e, docId) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      saveRename(docId)
    } else if (e.key === 'Escape') {
      cancelRename()
    }
  }

  // Folder management
  const addFolder = async () => {
    if (!newFolderName.trim()) return
    try {
      await api.post(`/deals/${deal.id}/categories?label=${encodeURIComponent(newFolderName.trim())}`)
      setAddingFolder(false)
      setNewFolderName('')
      onRefresh()
    } catch (e) {
      console.error('Add folder failed:', e)
      alert(e.response?.data?.detail || 'Failed to add folder')
    }
  }

  const startFolderRename = (cat, e) => {
    e?.stopPropagation()
    setRenamingFolderId(cat.value)
    setFolderRenameValue(cat.label)
  }

  const cancelFolderRename = () => {
    setRenamingFolderId(null)
    setFolderRenameValue('')
  }

  const saveFolderRename = async (catKey) => {
    if (!folderRenameValue.trim()) {
      cancelFolderRename()
      return
    }
    try {
      await api.patch(`/deals/${deal.id}/categories/${catKey}?label=${encodeURIComponent(folderRenameValue.trim())}`)
      setRenamingFolderId(null)
      setFolderRenameValue('')
      onRefresh()
    } catch (e) {
      console.error('Rename folder failed:', e)
    }
  }

  const handleFolderRenameKeyDown = (e, catKey) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      saveFolderRename(catKey)
    } else if (e.key === 'Escape') {
      cancelFolderRename()
    }
  }

  const deleteFolder = async (catKey) => {
    const confirmed = await confirm('Delete Folder', 'Are you sure you want to delete this folder? Documents will be moved to "Other".')
    if (!confirmed) return
    try {
      await api.delete(`/deals/${deal.id}/categories/${catKey}?move_to=other`)
      onRefresh()
    } catch (e) {
      console.error('Delete folder failed:', e)
    }
  }

  const delDoc = async (docId, e) => {
    e?.stopPropagation()
    const confirmed = await confirm('Delete Document', 'Are you sure you want to delete this document? This action cannot be undone.')
    if (confirmed) {
      try {
        await deleteDocument(docId)
        onRefresh()
      } catch (e) { console.error(e) }
    }
  }

  const totalDocs = deal.documents?.length || 0

  return (
    <div>
      {/* Upload Zone */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
          <div className="form-group" style={{ margin: 0, flex: 1, maxWidth: 200 }}>
            <label className="form-label">Upload to Folder</label>
            <select className="form-select" value={uploadCat} onChange={e => setUploadCat(e.target.value)}>
              {CATS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          <button
            className="btn btn-secondary"
            onClick={() => setAddingFolder(true)}
            style={{ whiteSpace: 'nowrap' }}
          >
            <Plus size={14} /> New Folder
          </button>
        </div>

        {/* Add folder form */}
        {addingFolder && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 6 }}>
            <input
              type="text"
              className="form-input"
              placeholder="Folder name..."
              value={newFolderName}
              onChange={(e) => setNewFolderName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') addFolder()
                else if (e.key === 'Escape') { setAddingFolder(false); setNewFolderName('') }
              }}
              autoFocus
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary btn-sm" onClick={addFolder} disabled={!newFolderName.trim()}>
              Create
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => { setAddingFolder(false); setNewFolderName('') }}>
              <X size={14} />
            </button>
          </div>
        )}

        <div
          className={`file-upload-zone ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input ref={fileInputRef} type="file" multiple onChange={handleFileInput} style={{ display: 'none' }} disabled={uploading} />
          {uploading ? (
            <>
              <Loader2 className="file-upload-icon animate-spin" />
              <p className="file-upload-text">Uploading...</p>
            </>
          ) : (
            <>
              <Upload className="file-upload-icon" />
              <p className="file-upload-text">{dragActive ? 'Drop files here' : 'Drag & drop or click to upload'}</p>
              <p className="file-upload-subtext">PDF, Word, Excel, CSV, Images</p>
            </>
          )}
        </div>
      </div>

      {/* Document Folders */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {CATS.map(cat => {
          const docs = docsByCategory[cat.value] || []
          const isExpanded = expandedFolders.has(cat.value)
          const hasAnalyzed = docs.some(d => d.analyzed || analysisResults[d.id])
          const isDragOver = dragOverFolder === cat.value && draggedDoc?.category !== cat.value

          return (
            <div
              key={cat.value}
              className="card"
              style={{
                padding: 0,
                overflow: 'hidden',
                borderColor: isDragOver ? '#0b7280' : undefined,
                background: isDragOver ? '#f0fdfa' : undefined,
                transition: 'all 0.15s'
              }}
              onDragOver={(e) => handleFolderDragOver(e, cat.value)}
              onDragLeave={handleFolderDragLeave}
              onDrop={(e) => handleFolderDrop(e, cat.value)}
            >
              {/* Folder Header */}
              <div
                onClick={() => renamingFolderId !== cat.value && toggleFolder(cat.value)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '12px 16px',
                  cursor: renamingFolderId === cat.value ? 'default' : 'pointer',
                  background: isDragOver ? '#e6fffa' : (isExpanded ? 'white' : '#fafafa'),
                  borderBottom: isExpanded && docs.length > 0 ? '1px solid #e5e5e5' : 'none',
                  transition: 'background 0.15s'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
                  {isExpanded ? <ChevronDown size={16} color="#737373" /> : <ChevronRight size={16} color="#737373" />}
                  {isDragOver ? (
                    <FolderOpen size={18} color="#0b7280" />
                  ) : isExpanded && docs.length > 0 ? (
                    <FolderOpen size={18} color="#0b7280" />
                  ) : (
                    <Folder size={18} color={docs.length > 0 ? '#0b7280' : '#a3a3a3'} />
                  )}
                  {renamingFolderId === cat.value ? (
                    <input
                      type="text"
                      className="form-input"
                      value={folderRenameValue}
                      onChange={(e) => setFolderRenameValue(e.target.value)}
                      onKeyDown={(e) => handleFolderRenameKeyDown(e, cat.value)}
                      onBlur={() => saveFolderRename(cat.value)}
                      onClick={(e) => e.stopPropagation()}
                      autoFocus
                      style={{ padding: '4px 8px', fontSize: 13, fontWeight: 600, width: 150 }}
                    />
                  ) : (
                    <span style={{ fontWeight: 600, fontSize: 13, color: isDragOver ? '#0b7280' : (docs.length > 0 ? '#171717' : '#737373') }}>
                      {isDragOver ? `Drop in ${cat.label}` : cat.label}
                    </span>
                  )}
                  <span style={{
                    background: docs.length > 0 ? '#0b7280' : '#e5e5e5',
                    color: docs.length > 0 ? 'white' : '#737373',
                    padding: '2px 8px',
                    borderRadius: 10,
                    fontSize: 11,
                    fontWeight: 600
                  }}>
                    {docs.length}
                  </span>
                  {hasAnalyzed && (
                    <CheckCircle size={14} color="#059669" style={{ marginLeft: 4 }} />
                  )}
                </div>
                {/* Folder actions */}
                <div style={{ display: 'flex', gap: 2 }} onClick={(e) => e.stopPropagation()}>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={(e) => startFolderRename(cat, e)}
                    data-tooltip="Rename this folder"
                    style={{ padding: '4px 6px' }}
                  >
                    <Edit2 size={12} />
                  </button>
                  {cat.isCustom && (
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => deleteFolder(cat.value)}
                      data-tooltip="Delete this folder"
                      style={{ padding: '4px 6px' }}
                    >
                      <Trash2 size={12} color="#dc2626" />
                    </button>
                  )}
                </div>
              </div>

              {/* Folder Contents */}
              {isExpanded && docs.length > 0 && (
                <div style={{ padding: '8px' }}>
                  {docs.map(doc => {
                    const analysis = analysisResults[doc.id]
                    const isAnalyzing = analyzing[doc.id]
                    const isMoving = movingDoc === doc.id
                    const isDragging = draggedDoc?.id === doc.id

                    return (
                      <div
                        key={doc.id}
                        draggable
                        onDragStart={(e) => handleDocDragStart(e, { ...doc, category: cat.value })}
                        onDragEnd={handleDocDragEnd}
                        style={{
                          padding: '10px 12px',
                          borderRadius: 6,
                          background: isDragging ? '#e5e5e5' : '#f5f5f5',
                          marginBottom: 8,
                          cursor: 'grab',
                          opacity: isDragging ? 0.5 : 1,
                          transition: 'all 0.15s'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
                            <FileText size={18} color="#737373" style={{ cursor: 'grab', flexShrink: 0 }} />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              {renamingDocId === doc.id ? (
                                <input
                                  type="text"
                                  className="form-input"
                                  value={renameValue}
                                  onChange={(e) => setRenameValue(e.target.value)}
                                  onKeyDown={(e) => handleRenameKeyDown(e, doc.id)}
                                  onBlur={() => saveRename(doc.id)}
                                  autoFocus
                                  onClick={(e) => e.stopPropagation()}
                                  style={{ padding: '4px 8px', fontSize: 13, fontWeight: 600 }}
                                />
                              ) : (
                                <div style={{ fontWeight: 600, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{doc.original_filename}</div>
                              )}
                              <div style={{ display: 'flex', gap: 8, fontSize: 11, color: '#737373', marginTop: 2 }}>
                                <span style={{ background: 'white', padding: '1px 6px', borderRadius: 3 }}>{doc.file_type.toUpperCase()}</span>
                                <span>{formatDate(doc.uploaded_at)}</span>
                              </div>
                            </div>
                          </div>
                          <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={(e) => startRename(doc, e)}
                              data-tooltip="Edit title of document"
                            >
                              <Edit2 size={14} />
                            </button>
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={(e) => { e.stopPropagation(); setMovingDoc(isMoving ? null : doc.id) }}
                              data-tooltip="Move to another folder"
                            >
                              <MoveRight size={14} />
                            </button>
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={(e) => analyzeDoc(doc.id, e)}
                              disabled={isAnalyzing}
                              data-tooltip="Analyze document with AI"
                            >
                              {isAnalyzing ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
                            </button>
                            <a
                              href={'/uploads/' + doc.filename}
                              target="_blank"
                              className="btn btn-ghost btn-sm"
                              onClick={e => e.stopPropagation()}
                              data-tooltip="View document"
                            >
                              <Eye size={14} />
                            </a>
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={(e) => delDoc(doc.id, e)}
                              data-tooltip="Delete document"
                            >
                              <Trash2 size={14} color="#dc2626" />
                            </button>
                          </div>
                        </div>

                        {/* Move dropdown */}
                        {isMoving && (
                          <div style={{
                            marginTop: 8,
                            padding: '8px 12px',
                            background: 'white',
                            borderRadius: 6,
                            border: '1px solid #e5e5e5'
                          }}>
                            <div style={{ fontSize: 11, color: '#737373', marginBottom: 6, fontWeight: 600 }}>MOVE TO:</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                              {CATS.filter(c => c.value !== cat.value).map(c => (
                                <button
                                  key={c.value}
                                  onClick={(e) => { e.stopPropagation(); moveDoc(doc.id, c.value) }}
                                  style={{
                                    padding: '4px 10px',
                                    borderRadius: 4,
                                    border: '1px solid #d4d4d4',
                                    background: 'white',
                                    fontSize: 12,
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 4
                                  }}
                                >
                                  <Folder size={12} /> {c.label}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Analysis Results */}
                        {(doc.analyzed || analysis) && (
                          <AnalysisSection doc={doc} analysis={analysis} />
                        )}
                      </div>
                    )
                  })}
                </div>
              )}

              {/* Empty folder message */}
              {isExpanded && docs.length === 0 && (
                <div style={{
                  padding: '16px',
                  textAlign: 'center',
                  color: isDragOver ? '#0b7280' : '#a3a3a3',
                  fontSize: 12,
                  border: isDragOver ? '2px dashed #0b7280' : '2px dashed transparent',
                  borderRadius: 6,
                  margin: 8,
                  background: isDragOver ? '#f0fdfa' : 'transparent',
                  transition: 'all 0.15s'
                }}>
                  {isDragOver ? 'Drop here' : 'No documents in this folder'}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Empty state when no documents at all */}
      {totalDocs === 0 && (
        <div className="card empty-state" style={{ marginTop: 16 }}>
          <FileText size={32} color="#d4d4d4" />
          <p style={{ marginTop: 12 }}>No documents uploaded yet</p>
        </div>
      )}
    </div>
  )
}

function Val({ val }) {
  if (!val) return <div className="card empty-state"><BarChart3 size={32} color="#d4d4d4" /><p style={{ marginTop: 12 }}>Loading valuation...</p></div>

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20 }}>
      {val.income_approach && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 16 }}>Income Approach</h3>
          <p style={{ marginBottom: 12, color: '#737373', fontSize: 13 }}>EBITDAR: <strong>{formatCurrency(val.income_approach.ebitdar)}</strong></p>
          <table className="data-table">
            <thead><tr><th>Scenario</th><th>Cap Rate</th><th>Value</th></tr></thead>
            <tbody>
              <tr><td>Conservative</td><td>{(val.income_approach.low_cap.cap_rate * 100).toFixed(1)}%</td><td>{formatCurrency(val.income_approach.low_cap.value)}</td></tr>
              <tr style={{ background: '#f0fdfa' }}><td><strong>Base</strong></td><td><strong>{(val.income_approach.mid_cap.cap_rate * 100).toFixed(1)}%</strong></td><td><strong>{formatCurrency(val.income_approach.mid_cap.value)}</strong></td></tr>
              <tr><td>Aggressive</td><td>{(val.income_approach.high_cap.cap_rate * 100).toFixed(1)}%</td><td>{formatCurrency(val.income_approach.high_cap.value)}</td></tr>
            </tbody>
          </table>
        </div>
      )}

      {val.market_approach && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 16 }}>Market Approach ($/Bed)</h3>
          <p style={{ marginBottom: 12, color: '#737373', fontSize: 13 }}>Total Beds: <strong>{formatNumber(val.market_approach.total_beds)}</strong></p>
          <table className="data-table">
            <thead><tr><th>Scenario</th><th>$/Bed</th><th>Value</th></tr></thead>
            <tbody>
              <tr><td>Low</td><td>{formatCurrency(val.market_approach.low.price_per_bed)}</td><td>{formatCurrency(val.market_approach.low.value)}</td></tr>
              <tr style={{ background: '#f0fdfa' }}><td><strong>Mid</strong></td><td><strong>{formatCurrency(val.market_approach.mid.price_per_bed)}</strong></td><td><strong>{formatCurrency(val.market_approach.mid.value)}</strong></td></tr>
              <tr><td>High</td><td>{formatCurrency(val.market_approach.high.price_per_bed)}</td><td>{formatCurrency(val.market_approach.high.value)}</td></tr>
            </tbody>
          </table>
        </div>
      )}

      {val.summary?.estimated_value && (
        <div className="card" style={{ gridColumn: '1/-1' }}>
          <h3 className="card-title" style={{ marginBottom: 16 }}>Summary</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 20, textAlign: 'center' }}>
            <div>
              <div className="stat-label">Estimated Value</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#059669' }}>{formatCurrency(val.summary.estimated_value)}</div>
            </div>
            <div>
              <div className="stat-label">Asking Price</div>
              <div style={{ fontSize: 24, fontWeight: 700 }}>{formatCurrency(val.summary.asking_price)}</div>
            </div>
            <div>
              <div className="stat-label">Spread</div>
              <div style={{ fontSize: 24, fontWeight: 700, color: val.summary.spread_pct > 0 ? '#059669' : '#dc2626' }}>
                {val.summary.spread_pct > 0 ? '+' : ''}{val.summary.spread_pct}%
              </div>
            </div>
            <div>
              <div className="stat-label">Recommendation</div>
              <div style={{ fontSize: 16, fontWeight: 600, marginTop: 4, color: val.summary.recommendation?.includes('Under') ? '#059669' : (val.summary.recommendation?.includes('Over') ? '#dc2626' : '#737373') }}>
                {val.summary.recommendation}
              </div>
            </div>
          </div>
        </div>
      )}

      {!val.income_approach && !val.market_approach && (
        <div className="card empty-state" style={{ gridColumn: '1/-1' }}>
          <BarChart3 size={32} color="#d4d4d4" />
          <p style={{ marginTop: 12 }}>Enter EBITDAR and/or beds in Overview to see valuation</p>
        </div>
      )}
    </div>
  )
}

function Props({ deal, onRefresh, confirm }) {
  const [show, setShow] = useState(false)
  const [np, setNp] = useState({ name: '', property_type: 'SNF', address: '', city: '', state: '', licensed_beds: '' })

  const add = async () => {
    try {
      await createProperty(deal.id, { ...np, licensed_beds: np.licensed_beds ? parseInt(np.licensed_beds) : null })
      setShow(false)
      setNp({ name: '', property_type: 'SNF', address: '', city: '', state: '', licensed_beds: '' })
      onRefresh()
    } catch (e) { console.error(e) }
  }

  const del = async (id) => {
    const confirmed = await confirm('Remove Property', 'Are you sure you want to remove this property from the deal?')
    if (confirmed) {
      try {
        await deleteProperty(id)
        onRefresh()
      } catch (e) { console.error(e) }
    }
  }

  return (
    <div>
      <button className="btn btn-primary" onClick={() => setShow(true)} style={{ marginBottom: 16 }}>
        <Plus size={14} /> Add Property
      </button>

      {show && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 className="card-title" style={{ marginBottom: 16 }}>Add Property</h3>
          <div className="form-row-3">
            <div className="form-group">
              <label className="form-label">Name *</label>
              <input className="form-input" value={np.name} onChange={e => setNp({ ...np, name: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Type</label>
              <select className="form-select" value={np.property_type} onChange={e => setNp({ ...np, property_type: e.target.value })}>
                <option value="SNF">SNF</option>
                <option value="ALF">ALF</option>
                <option value="ILF">ILF</option>
                <option value="MC">Memory Care</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Beds</label>
              <input type="number" className="form-input" value={np.licensed_beds} onChange={e => setNp({ ...np, licensed_beds: e.target.value })} />
            </div>
          </div>
          <div className="form-row-3">
            <div className="form-group">
              <label className="form-label">Address</label>
              <input className="form-input" value={np.address} onChange={e => setNp({ ...np, address: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">City</label>
              <input className="form-input" value={np.city} onChange={e => setNp({ ...np, city: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">State</label>
              <input className="form-input" value={np.state} onChange={e => setNp({ ...np, state: e.target.value })} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-secondary" onClick={() => setShow(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={add} disabled={!np.name}>Add Property</button>
          </div>
        </div>
      )}

      {deal.properties?.length > 0 ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
          {deal.properties.map(p => (
            <div key={p.id} className="card" style={{ padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{p.name}</div>
                  <span className={'deal-type-badge ' + (p.property_type || 'snf').toLowerCase()} style={{ marginTop: 4 }}>
                    {p.property_type}
                  </span>
                </div>
                <button className="btn btn-danger btn-sm" onClick={() => del(p.id)}><Trash2 size={14} /></button>
              </div>
              {p.address && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: '#737373', fontSize: 12, marginBottom: 8 }}>
                  <MapPin size={12} /> {p.address}, {p.city}, {p.state}
                </div>
              )}
              <div style={{ display: 'flex', gap: 16, fontSize: 13 }}>
                <div><span style={{ color: '#737373' }}>Beds:</span> <strong>{p.licensed_beds || '—'}</strong></div>
                <div><span style={{ color: '#737373' }}>Occupancy:</span> <strong>{p.current_occupancy ? p.current_occupancy + '%' : '—'}</strong></div>
                {p.star_rating && (
                  <div style={{ display: 'flex', gap: 1 }}>
                    {[1, 2, 3, 4, 5].map(i => (
                      <Star key={i} size={12} fill={i <= p.star_rating ? '#f59e0b' : 'none'} color={i <= p.star_rating ? '#f59e0b' : '#e5e5e5'} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="card empty-state">
          <Building2 size={32} color="#d4d4d4" />
          <p style={{ marginTop: 12 }}>No properties added</p>
        </div>
      )}
    </div>
  )
}

function Tasks({ deal, onRefresh }) {
  const [show, setShow] = useState(false)
  const [nt, setNt] = useState({ title: '', priority: 'medium' })

  const add = async () => {
    try {
      await createTask(deal.id, nt)
      setShow(false)
      setNt({ title: '', priority: 'medium' })
      onRefresh()
    } catch (e) { console.error(e) }
  }

  const toggle = async (t) => {
    try {
      await updateTask(t.id, { status: t.status === 'completed' ? 'pending' : 'completed' })
      onRefresh()
    } catch (e) { console.error(e) }
  }

  const pending = deal.tasks?.filter(t => t.status !== 'completed') || []
  const done = deal.tasks?.filter(t => t.status === 'completed') || []

  return (
    <div>
      <button className="btn btn-primary" onClick={() => setShow(true)} style={{ marginBottom: 16 }}>
        <Plus size={14} /> Add Task
      </button>

      {show && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 className="card-title" style={{ marginBottom: 16 }}>Add Task</h3>
          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Title *</label>
              <input className="form-input" value={nt.title} onChange={e => setNt({ ...nt, title: e.target.value })} />
            </div>
            <div className="form-group">
              <label className="form-label">Priority</label>
              <select className="form-select" value={nt.priority} onChange={e => setNt({ ...nt, priority: e.target.value })}>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-secondary" onClick={() => setShow(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={add} disabled={!nt.title}>Add Task</button>
          </div>
        </div>
      )}

      <div className="card">
        <h3 className="card-title" style={{ marginBottom: 16 }}>Pending ({pending.length})</h3>
        {pending.length > 0 ? pending.map(t => (
          <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid #f5f5f5' }}>
            <button
              onClick={() => toggle(t)}
              style={{ width: 20, height: 20, borderRadius: 4, border: '2px solid #d4d4d4', background: 'none', cursor: 'pointer', flexShrink: 0 }}
            />
            <div style={{ flex: 1, fontSize: 13 }}>{t.title}</div>
            <span className={'priority-badge ' + t.priority}>{t.priority}</span>
            {t.due_date && <span style={{ fontSize: 11, color: '#737373' }}><Clock size={12} /> {formatDate(t.due_date)}</span>}
          </div>
        )) : <p style={{ color: '#737373', fontSize: 13 }}>No pending tasks</p>}
      </div>

      {done.length > 0 && (
        <div className="card" style={{ marginTop: 16, opacity: 0.7 }}>
          <h3 className="card-title" style={{ marginBottom: 16 }}>Completed ({done.length})</h3>
          {done.map(t => (
            <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid #f5f5f5' }}>
              <button
                onClick={() => toggle(t)}
                style={{ width: 20, height: 20, borderRadius: 4, border: 'none', background: '#059669', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
              >
                <CheckCircle size={12} color="white" />
              </button>
              <div style={{ flex: 1, fontSize: 13, textDecoration: 'line-through', color: '#737373' }}>{t.title}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Activity({ deal }) {
  return (
    <div className="card">
      <h3 className="card-title" style={{ marginBottom: 16 }}>Activity Log</h3>
      {deal.activities?.length > 0 ? (
        <ul className="activity-list">
          {deal.activities.map((a, i) => (
            <li key={i} className="activity-item">
              <div className="activity-icon">
                {a.action === 'created' && <Plus size={14} />}
                {a.action === 'status_changed' && <RefreshCw size={14} />}
                {a.action === 'document_uploaded' && <Upload size={14} />}
                {a.action === 'property_added' && <Building2 size={14} />}
                {a.action === 'task_completed' && <CheckCircle size={14} color="#059669" />}
                {a.action === 'document_analyzed' && <Zap size={14} color="#7c3aed" />}
                {a.action === 'updated' && <Edit2 size={14} />}
              </div>
              <div className="activity-content">
                <div className="activity-description">{a.description}</div>
                <div className="activity-time">{formatDateTime(a.created_at)}</div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p style={{ color: '#737373', fontSize: 13 }}>No activity yet</p>
      )}
    </div>
  )
}

// Analysis Tab Component
function Analysis({ deal }) {
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [scorecard, setScorecard] = useState(null)
  const [riskFlags, setRiskFlags] = useState([])
  const [financials, setFinancials] = useState(null)
  const [claims, setClaims] = useState([])
  const [error, setError] = useState(null)

  const loadAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      const [sc, rf, fin, cl] = await Promise.all([
        getDealScorecard(deal.id).catch(() => null),
        getDealRiskFlags(deal.id).catch(() => []),
        getFinancialSummary(deal.id).catch(() => null),
        getDealClaims(deal.id).catch(() => [])
      ])
      setScorecard(sc)
      setRiskFlags(rf || [])
      setFinancials(fin)
      setClaims(cl || [])
    } catch (err) {
      setError('Failed to load analysis data')
    }
    setLoading(false)
  }

  useEffect(() => { loadAnalysis() }, [deal.id])

  const runAnalysis = async () => {
    setRunning(true)
    setError(null)
    try {
      await runFullAnalysis(deal.id)
      // Reload after analysis
      await loadAnalysis()
    } catch (err) {
      setError('Analysis failed: ' + (err.response?.data?.detail || err.message))
    }
    setRunning(false)
  }

  const getScoreColor = (score) => {
    if (score >= 70) return '#059669'
    if (score >= 50) return '#d97706'
    return '#dc2626'
  }

  const getRecommendationStyle = (rec) => {
    const styles = {
      strong_proceed: { bg: '#dcfce7', color: '#166534', label: 'Strong Proceed' },
      proceed_with_caution: { bg: '#fef9c3', color: '#854d0e', label: 'Proceed with Caution' },
      needs_further_review: { bg: '#fed7aa', color: '#9a3412', label: 'Needs Further Review' },
      not_recommended: { bg: '#fee2e2', color: '#991b1b', label: 'Not Recommended' },
      pass: { bg: '#fee2e2', color: '#991b1b', label: 'Pass' }
    }
    return styles[rec] || { bg: '#f3f4f6', color: '#374151', label: rec || 'Pending' }
  }

  const getSeverityStyle = (severity) => {
    const styles = {
      high: { bg: '#fee2e2', color: '#991b1b', border: '#fecaca' },
      medium: { bg: '#fef3c7', color: '#92400e', border: '#fde68a' },
      low: { bg: '#d1fae5', color: '#065f46', border: '#a7f3d0' }
    }
    return styles[severity] || styles.medium
  }

  if (loading) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 60 }}>
        <Loader2 size={32} className="spin" style={{ margin: '0 auto 16px', color: '#6366f1' }} />
        <p style={{ color: '#737373' }}>Loading analysis data...</p>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header with Run Analysis button */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ fontSize: 18, fontWeight: 600, color: '#171717', marginBottom: 4 }}>Deal Analysis</h3>
            <p style={{ fontSize: 13, color: '#737373' }}>
              Comprehensive analysis of documents, financials, and risk factors
            </p>
          </div>
          <button
            className="btn btn-primary"
            onClick={runAnalysis}
            disabled={running}
            style={{ display: 'flex', alignItems: 'center', gap: 8 }}
          >
            {running ? (
              <>
                <Loader2 size={16} className="spin" />
                Running Analysis...
              </>
            ) : (
              <>
                <Play size={16} />
                Run Full Analysis
              </>
            )}
          </button>
        </div>
        {error && (
          <div style={{ marginTop: 12, padding: 12, background: '#fee2e2', borderRadius: 6, color: '#991b1b', fontSize: 13 }}>
            {error}
          </div>
        )}
      </div>

      {/* Scorecard */}
      <div className="card">
        <h3 className="card-title" style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <TrendingUp size={18} />
          Deal Scorecard
        </h3>

        {scorecard ? (
          <div>
            {/* Recommendation Banner */}
            {scorecard.recommendation && (
              <div style={{
                padding: 16,
                borderRadius: 8,
                marginBottom: 20,
                background: getRecommendationStyle(scorecard.recommendation).bg,
                color: getRecommendationStyle(scorecard.recommendation).color
              }}>
                <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>
                  Recommendation: {getRecommendationStyle(scorecard.recommendation).label}
                </div>
                {scorecard.recommendation_summary && (
                  <div style={{ fontSize: 13, opacity: 0.9 }}>{scorecard.recommendation_summary}</div>
                )}
              </div>
            )}

            {/* Overall Score */}
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 100,
                height: 100,
                borderRadius: '50%',
                background: `conic-gradient(${getScoreColor(scorecard.overall_score || 0)} ${(scorecard.overall_score || 0) * 3.6}deg, #e5e7eb 0deg)`,
                position: 'relative'
              }}>
                <div style={{
                  width: 80,
                  height: 80,
                  borderRadius: '50%',
                  background: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexDirection: 'column'
                }}>
                  <span style={{ fontSize: 28, fontWeight: 700, color: getScoreColor(scorecard.overall_score || 0) }}>
                    {Math.round(scorecard.overall_score || 0)}
                  </span>
                </div>
              </div>
              <div style={{ marginTop: 8, fontWeight: 600, color: '#374151' }}>Overall Score</div>
            </div>

            {/* Score Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
              {[
                { label: 'Financial', score: scorecard.financial_score },
                { label: 'Operational', score: scorecard.operational_score },
                { label: 'Quality', score: scorecard.quality_score },
                { label: 'Compliance', score: scorecard.compliance_score }
              ].map(item => (
                <div key={item.label} style={{ padding: 12, background: '#f9fafb', borderRadius: 8 }}>
                  <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>{item.label}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ flex: 1, height: 8, background: '#e5e7eb', borderRadius: 4, overflow: 'hidden' }}>
                      <div style={{
                        width: `${item.score || 0}%`,
                        height: '100%',
                        background: getScoreColor(item.score || 0),
                        borderRadius: 4
                      }} />
                    </div>
                    <span style={{ fontWeight: 600, fontSize: 14, color: getScoreColor(item.score || 0) }}>
                      {Math.round(item.score || 0)}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Key Strengths */}
            {scorecard.key_strengths?.length > 0 && (
              <div style={{ marginTop: 20 }}>
                <div style={{ fontWeight: 600, marginBottom: 8, color: '#059669' }}>Key Strengths</div>
                {scorecard.key_strengths.map((s, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, fontSize: 13 }}>
                    <CheckCircle size={14} color="#059669" />
                    <span>{s.description || s.area}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#737373' }}>
            <Shield size={40} style={{ marginBottom: 12, opacity: 0.5 }} />
            <p>No scorecard calculated yet. Run full analysis to generate.</p>
          </div>
        )}
      </div>

      {/* Risk Flags */}
      <div className="card">
        <h3 className="card-title" style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertTriangle size={18} />
          Risk Flags ({riskFlags.length})
        </h3>

        {riskFlags.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {riskFlags.map(flag => {
              const style = getSeverityStyle(flag.severity)
              return (
                <div key={flag.id} style={{
                  padding: 14,
                  background: style.bg,
                  border: `1px solid ${style.border}`,
                  borderRadius: 8
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                    <div>
                      <div style={{ fontWeight: 600, color: style.color, marginBottom: 4 }}>{flag.title}</div>
                      <div style={{ fontSize: 13, color: '#525252', marginBottom: 8 }}>{flag.description}</div>
                      {flag.recommendation && (
                        <div style={{ fontSize: 12, color: '#737373', fontStyle: 'italic' }}>
                          💡 {flag.recommendation}
                        </div>
                      )}
                    </div>
                    <span style={{
                      padding: '4px 10px',
                      borderRadius: 12,
                      fontSize: 11,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      background: style.color,
                      color: 'white'
                    }}>
                      {flag.severity}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#737373' }}>
            <CheckCircle size={40} style={{ marginBottom: 12, opacity: 0.5, color: '#059669' }} />
            <p>No risk flags identified</p>
          </div>
        )}
      </div>

      {/* Financial Summary */}
      {financials?.metrics && Object.keys(financials.metrics).length > 0 && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <DollarSign size={18} />
            Financial Summary
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
            {financials.metrics.total_revenue > 0 && (
              <div style={{ padding: 16, background: '#f0fdf4', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>Total Revenue</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#059669' }}>
                  {formatCurrency(financials.metrics.total_revenue)}
                </div>
              </div>
            )}
            {financials.metrics.ebitdar > 0 && (
              <div style={{ padding: 16, background: '#eff6ff', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>EBITDAR</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#2563eb' }}>
                  {formatCurrency(financials.metrics.ebitdar)}
                </div>
              </div>
            )}
            {financials.metrics.ebitdar_margin > 0 && (
              <div style={{ padding: 16, background: '#faf5ff', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>EBITDAR Margin</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#7c3aed' }}>
                  {formatPercent(financials.metrics.ebitdar_margin)}
                </div>
              </div>
            )}
            {financials.metrics.labor_ratio > 0 && (
              <div style={{ padding: 16, background: '#fff7ed', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>Labor Ratio</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#ea580c' }}>
                  {formatPercent(financials.metrics.labor_ratio)}
                </div>
              </div>
            )}
            {financials.metrics.total_opex > 0 && (
              <div style={{ padding: 16, background: '#fef2f2', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 11, color: '#6b7280', marginBottom: 4 }}>Total OpEx</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: '#dc2626' }}>
                  {formatCurrency(financials.metrics.total_opex)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Claims Summary */}
      {claims.length > 0 && (
        <div className="card">
          <h3 className="card-title" style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileSearch size={18} />
            OM Claims ({claims.length})
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600 }}>Type</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600 }}>Claimed</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600 }}>Verified</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600 }}>Variance</th>
                  <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {claims.slice(0, 10).map(claim => (
                  <tr key={claim.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{ fontWeight: 500 }}>{claim.claim_type}</span>
                      <div style={{ fontSize: 11, color: '#6b7280' }}>{claim.claim_category}</div>
                    </td>
                    <td style={{ padding: '10px 12px' }}>{claim.claimed_value || '-'}</td>
                    <td style={{ padding: '10px 12px' }}>{claim.verified_value || '-'}</td>
                    <td style={{ padding: '10px 12px' }}>
                      {claim.variance_pct != null ? (
                        <span style={{ color: Math.abs(claim.variance_pct) > 10 ? '#dc2626' : '#059669' }}>
                          {claim.variance_pct > 0 ? '+' : ''}{claim.variance_pct.toFixed(1)}%
                        </span>
                      ) : '-'}
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 500,
                        background: claim.verification_status === 'verified' ? '#dcfce7' :
                                   claim.verification_status === 'flagged' ? '#fee2e2' :
                                   claim.verification_status === 'disputed' ? '#fef3c7' : '#f3f4f6',
                        color: claim.verification_status === 'verified' ? '#166534' :
                               claim.verification_status === 'flagged' ? '#991b1b' :
                               claim.verification_status === 'disputed' ? '#92400e' : '#374151'
                      }}>
                        {claim.verification_status}
                      </span>
                      {claim.is_red_flag && (
                        <AlertTriangle size={14} color="#dc2626" style={{ marginLeft: 6 }} />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {claims.length > 10 && (
              <div style={{ padding: 12, textAlign: 'center', color: '#6b7280', fontSize: 12 }}>
                Showing 10 of {claims.length} claims
              </div>
            )}
          </div>
        </div>
      )}

      {/* Export Links */}
      <div className="card">
        <h3 className="card-title" style={{ marginBottom: 16 }}>Export Reports</h3>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <a
            href={`/api/deals/${deal.id}/export/ic-memo.html`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <FileText size={14} />
            IC Memo (HTML)
          </a>
          <a
            href={`/api/deals/${deal.id}/export/data.json`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <FileText size={14} />
            Full Data (JSON)
          </a>
          <a
            href={`/api/deals/${deal.id}/export/financials.csv`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <FileText size={14} />
            Financials (CSV)
          </a>
        </div>
      </div>
    </div>
  )
}

export default DealDetail
