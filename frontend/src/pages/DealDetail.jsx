import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Building2, Upload, FileText, Trash2, DollarSign, BarChart3, Edit2, Save, X, Plus, CheckCircle, Clock, RefreshCw, Eye, Loader2, Zap, AlertCircle } from 'lucide-react'
import { getDeal, updateDeal, deleteDeal, updateDealStatus, uploadDocument, deleteDocument, getValuation, createProperty, deleteProperty, createTask, updateTask, formatCurrency, formatNumber, formatDate, formatDateTime } from '../services/api'
import api from '../services/api'

const STS = [{key:'vetting',label:'Vetting'},{key:'pipeline',label:'Pipeline'},{key:'due_diligence',label:'Due Diligence'},{key:'current_operations',label:'Current Ops'},{key:'on_hold',label:'On Hold'},{key:'closed',label:'Closed'},{key:'passed',label:'Passed'}]
const CATS = [{value:'offering_memorandum',label:'Offering Memo'},{value:'financials',label:'Financials'},{value:'rent_roll',label:'Rent Roll'},{value:'survey',label:'Survey'},{value:'payor_mix',label:'Payor Mix'},{value:'other',label:'Other'}]

function DealDetail() {
  const {id} = useParams(), navigate = useNavigate()
  const [deal, setDeal] = useState(null), [loading, setLoading] = useState(true), [tab, setTab] = useState('overview')
  const [editing, setEditing] = useState(false), [ed, setEd] = useState({})
  const [val, setVal] = useState(null)

  const load = useCallback(async () => {
    try { setLoading(true); const d = await getDeal(id); setDeal(d); setEd(d) }
    catch(e){console.error(e)}
    finally{setLoading(false)}
  }, [id])

  useEffect(() => { load() }, [load])

  const chgStatus = async (s) => { try { await updateDealStatus(id, s); load() } catch(e){console.error(e)} }
  const save = async () => { try { await updateDeal(id, ed); setEditing(false); load() } catch(e){console.error(e)} }
  const del = async () => { if(window.confirm('Delete?')) { try { await deleteDeal(id); navigate('/') } catch(e){console.error(e)} } }
  const loadVal = async () => { try { setVal(await getValuation(id)) } catch(e){console.error(e)} }

  if(loading) return <div className="empty-state"><RefreshCw className="empty-state-icon" style={{animation:'spin 1s linear infinite'}}/><p>Loading...</p></div>
  if(!deal) return <div className="empty-state"><p>Not found</p><button className="btn btn-primary" onClick={()=>navigate('/')}>Back</button></div>

  return (
    <div>
      <button onClick={()=>navigate('/')} className="btn btn-secondary btn-sm" style={{marginBottom:16}}><ArrowLeft size={16}/> Back</button>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:24}}>
        <div><h1 className="page-title">{deal.name}</h1>
          <div style={{display:'flex',gap:16,marginTop:8,alignItems:'center'}}>
            <span className={'deal-type-badge '+(deal.deal_type||'snf').toLowerCase()}>{deal.deal_type||'SNF'}</span>
            {deal.total_beds>0&&<span style={{display:'flex',alignItems:'center',gap:4,color:'#64748b',fontSize:14}}><Building2 size={16}/> {deal.total_beds} beds</span>}
            {deal.asking_price>0&&<span style={{display:'flex',alignItems:'center',gap:4,color:'#10b981',fontSize:14,fontWeight:600}}><DollarSign size={16}/> {formatCurrency(deal.asking_price)}</span>}
          </div>
        </div>
        <div style={{display:'flex',gap:8}}>
          <select value={deal.status} onChange={e=>chgStatus(e.target.value)} className="form-select" style={{width:180}}>
            {STS.map(s=><option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
          <button className="btn btn-danger btn-sm" onClick={del}><Trash2 size={16}/></button>
        </div>
      </div>
      <div className="tabs">
        <button className={'tab '+(tab==='overview'?'active':'')} onClick={()=>setTab('overview')}>Overview</button>
        <button className={'tab '+(tab==='properties'?'active':'')} onClick={()=>setTab('properties')}>Properties ({deal.properties?.length||0})</button>
        <button className={'tab '+(tab==='documents'?'active':'')} onClick={()=>setTab('documents')}>Documents ({deal.documents?.length||0})</button>
        <button className={'tab '+(tab==='valuation'?'active':'')} onClick={()=>{setTab('valuation');loadVal()}}>Valuation</button>
        <button className={'tab '+(tab==='tasks'?'active':'')} onClick={()=>setTab('tasks')}>Tasks</button>
        <button className={'tab '+(tab==='activity'?'active':'')} onClick={()=>setTab('activity')}>Activity</button>
      </div>
      {tab==='overview'&&<Overview deal={deal} editing={editing} ed={ed} setEd={setEd} setEditing={setEditing} save={save}/>}
      {tab==='documents'&&<Docs deal={deal} onRefresh={load}/>}
      {tab==='valuation'&&<Val val={val}/>}
      {tab==='properties'&&<Props deal={deal} onRefresh={load}/>}
      {tab==='tasks'&&<Tasks deal={deal} onRefresh={load}/>}
      {tab==='activity'&&<Activity deal={deal}/>}
    </div>
  )
}

function Overview({deal,editing,ed,setEd,setEditing,save}) {
  return <div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:24}}>
    <div className="card">
      <div className="card-header"><h3 className="card-title">Deal Info</h3>{editing?<div style={{display:'flex',gap:8}}><button className="btn btn-secondary btn-sm" onClick={()=>setEditing(false)}><X size={14}/></button><button className="btn btn-primary btn-sm" onClick={save}><Save size={14}/></button></div>:<button className="btn btn-secondary btn-sm" onClick={()=>setEditing(true)}><Edit2 size={14}/></button>}</div>
      {editing?<div>
        <div className="form-row"><div className="form-group"><label className="form-label">Name</label><input className="form-input" value={ed.name||''} onChange={e=>setEd({...ed,name:e.target.value})}/></div><div className="form-group"><label className="form-label">Type</label><select className="form-select" value={ed.deal_type||'SNF'} onChange={e=>setEd({...ed,deal_type:e.target.value})}><option value="SNF">SNF</option><option value="ALF">ALF</option><option value="ILF">ILF</option></select></div></div>
        <div className="form-row"><div className="form-group"><label className="form-label">Beds</label><input type="number" className="form-input" value={ed.total_beds||''} onChange={e=>setEd({...ed,total_beds:parseInt(e.target.value)||null})}/></div><div className="form-group"><label className="form-label">Asking ($)</label><input type="number" className="form-input" value={ed.asking_price||''} onChange={e=>setEd({...ed,asking_price:parseFloat(e.target.value)||null})}/></div></div>
        <div className="form-row"><div className="form-group"><label className="form-label">EBITDAR ($)</label><input type="number" className="form-input" value={ed.ebitdar||''} onChange={e=>setEd({...ed,ebitdar:parseFloat(e.target.value)||null})}/></div><div className="form-group"><label className="form-label">Cap Rate (%)</label><input type="number" className="form-input" value={ed.cap_rate||''} onChange={e=>setEd({...ed,cap_rate:parseFloat(e.target.value)||null})}/></div></div>
        <div className="form-group"><label className="form-label">Thesis</label><textarea className="form-textarea" rows={2} value={ed.investment_thesis||''} onChange={e=>setEd({...ed,investment_thesis:e.target.value})}/></div>
        <div className="form-group"><label className="form-label">Notes</label><textarea className="form-textarea" rows={2} value={ed.notes||''} onChange={e=>setEd({...ed,notes:e.target.value})}/></div>
      </div>:<div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:16,fontSize:14}}>
        <div><strong>Type:</strong> {deal.deal_type||'SNF'}</div><div><strong>Priority:</strong> <span className={'priority-badge '+deal.priority}>{deal.priority}</span></div>
        <div><strong>Beds:</strong> {formatNumber(deal.total_beds)}</div><div><strong>Units:</strong> {formatNumber(deal.total_units)}</div>
        <div><strong>Asking:</strong> {formatCurrency(deal.asking_price)}</div><div><strong>EBITDAR:</strong> {formatCurrency(deal.ebitdar)}</div>
        <div><strong>Cap Rate:</strong> {deal.cap_rate?deal.cap_rate+'%':'-'}</div><div><strong>$/Bed:</strong> {formatCurrency(deal.price_per_bed)}</div>
        <div style={{gridColumn:'1/-1'}}><strong>Thesis:</strong> {deal.investment_thesis||'None'}</div>
        <div style={{gridColumn:'1/-1'}}><strong>Notes:</strong> {deal.notes||'None'}</div>
      </div>}
    </div>
    <div>
      <div className="card" style={{marginBottom:16}}><h3 className="card-title" style={{marginBottom:16}}>Broker</h3><div style={{fontSize:14,color:'#64748b'}}><p><strong>Source:</strong> {deal.source||'-'}</p><p><strong>Broker:</strong> {deal.broker_name||'-'}</p><p><strong>Company:</strong> {deal.broker_company||'-'}</p><p><strong>Email:</strong> {deal.broker_email||'-'}</p><p><strong>Seller:</strong> {deal.seller_name||'-'}</p></div></div>
      <div className="card"><h3 className="card-title" style={{marginBottom:16}}>Timeline</h3><div style={{fontSize:14,color:'#64748b'}}><p><strong>Created:</strong> {formatDate(deal.created_at)}</p><p><strong>Updated:</strong> {formatDate(deal.updated_at)}</p></div></div>
    </div>
  </div>
}

function Docs({ deal, onRefresh }) {
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState({})
  const [analysisResults, setAnalysisResults] = useState({})
  const [dragActive, setDragActive] = useState(false)
  const [cat, setCat] = useState('other')
  const [autoAnalyze, setAutoAnalyze] = useState(true)
  const fileInputRef = useRef(null)

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await uploadFiles(e.dataTransfer.files)
    }
  }

  const handleFileInput = async (e) => {
    if (e.target.files && e.target.files.length > 0) {
      await uploadFiles(e.target.files)
    }
  }

  const uploadFiles = async (files) => {
    setUploading(true)
    try {
      for (const file of files) {
        // Upload document
        const result = await uploadDocument(deal.id, file, cat)
        const docId = result.document?.id

        // Auto-analyze if enabled
        if (autoAnalyze && docId) {
          setAnalyzing(prev => ({ ...prev, [docId]: true }))
          try {
            const analysis = await api.post(`/documents/${docId}/analyze?auto_apply=true`)
            setAnalysisResults(prev => ({ ...prev, [docId]: analysis.data }))
          } catch (e) {
            console.error('Analysis failed:', e)
          }
          setAnalyzing(prev => ({ ...prev, [docId]: false }))
        }
      }
      onRefresh()
    } catch (e) {
      console.error('Upload failed:', e)
      alert('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const analyzeDoc = async (docId) => {
    setAnalyzing(prev => ({ ...prev, [docId]: true }))
    try {
      const response = await api.post(`/documents/${docId}/analyze?auto_apply=true`)
      setAnalysisResults(prev => ({ ...prev, [docId]: response.data }))
      onRefresh()
    } catch (e) {
      console.error('Analysis failed:', e)
      alert('Analysis failed')
    } finally {
      setAnalyzing(prev => ({ ...prev, [docId]: false }))
    }
  }

  const delDoc = async (docId) => {
    if (window.confirm('Delete this document?')) {
      try {
        await deleteDocument(docId)
        onRefresh()
      } catch (e) {
        console.error(e)
      }
    }
  }

  return (
    <div>
      {/* Upload Zone */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16 }}>
          <div className="form-group" style={{ margin: 0, flex: 1 }}>
            <label className="form-label">Category for uploads</label>
            <select className="form-select" value={cat} onChange={e => setCat(e.target.value)}>
              {CATS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </div>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginTop: 20 }}>
            <input
              type="checkbox"
              checked={autoAnalyze}
              onChange={e => setAutoAnalyze(e.target.checked)}
              style={{ width: 18, height: 18 }}
            />
            <span style={{ fontSize: 14, color: '#64748b' }}>Auto-analyze on upload</span>
          </label>
        </div>

        <div
          className={`file-upload-zone ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            borderColor: dragActive ? '#10b981' : undefined,
            background: dragActive ? '#f0fdf4' : undefined
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileInput}
            style={{ display: 'none' }}
            disabled={uploading}
          />
          {uploading ? (
            <>
              <Loader2 className="file-upload-icon" style={{ animation: 'spin 1s linear infinite' }} />
              <p className="file-upload-text">Uploading & analyzing...</p>
            </>
          ) : (
            <>
              <Upload className="file-upload-icon" />
              <p className="file-upload-text">
                {dragActive ? 'Drop files here' : 'Drag & drop files or click to upload'}
              </p>
              <p className="file-upload-subtext">PDF, Word, Excel, CSV, Images</p>
            </>
          )}
        </div>
      </div>

      {/* Documents List */}
      {deal.documents?.length > 0 ? (
        <div style={{ display: 'grid', gap: 16 }}>
          {deal.documents.map(doc => {
            const analysis = analysisResults[doc.id]
            const isAnalyzing = analyzing[doc.id]

            return (
              <div key={doc.id} className="card" style={{ padding: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                      width: 48, height: 48, borderRadius: 10,
                      background: '#f1f5f9', display: 'flex',
                      alignItems: 'center', justifyContent: 'center'
                    }}>
                      <FileText size={24} color="#64748b" />
                    </div>
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>{doc.original_filename}</div>
                      <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#64748b' }}>
                        <span style={{ background: '#f1f5f9', padding: '2px 8px', borderRadius: 4 }}>
                          {doc.file_type.toUpperCase()}
                        </span>
                        <span>{CATS.find(c => c.value === doc.category)?.label || doc.category}</span>
                        <span>{formatDate(doc.uploaded_at)}</span>
                      </div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => analyzeDoc(doc.id)}
                      disabled={isAnalyzing}
                    >
                      {isAnalyzing ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Zap size={14} />}
                      Analyze
                    </button>
                    <a href={'/uploads/' + doc.filename} target="_blank" className="btn btn-secondary btn-sm">
                      <Eye size={14} />
                    </a>
                    <button className="btn btn-danger btn-sm" onClick={() => delDoc(doc.id)}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Analysis Results */}
                {(doc.analyzed || analysis) && (
                  <div style={{
                    marginTop: 16, paddingTop: 16, borderTop: '1px solid #e2e8f0',
                    background: '#f8fafc', margin: '16px -16px -16px', padding: 16, borderRadius: '0 0 12px 12px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                      <CheckCircle size={16} color="#10b981" />
                      <span style={{ fontWeight: 600, fontSize: 14 }}>Analysis Results</span>
                      {analysis?.document_type && (
                        <span style={{
                          background: '#dbeafe', color: '#1d4ed8',
                          padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 600
                        }}>
                          {analysis.document_type.replace('_', ' ').toUpperCase()}
                        </span>
                      )}
                      {analysis?.confidence && (
                        <span style={{ fontSize: 12, color: '#64748b' }}>
                          ({Math.round(analysis.confidence * 100)}% confidence)
                        </span>
                      )}
                    </div>

                    {/* Extracted Metrics */}
                    {analysis?.metrics && Object.keys(analysis.metrics).length > 0 && (
                      <div style={{
                        display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))',
                        gap: 12, marginBottom: 12
                      }}>
                        {analysis.metrics.beds && (
                          <div style={{ background: 'white', padding: '8px 12px', borderRadius: 8 }}>
                            <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Beds</div>
                            <div style={{ fontWeight: 700, fontSize: 18 }}>{analysis.metrics.beds}</div>
                          </div>
                        )}
                        {analysis.metrics.occupancy && (
                          <div style={{ background: 'white', padding: '8px 12px', borderRadius: 8 }}>
                            <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Occupancy</div>
                            <div style={{ fontWeight: 700, fontSize: 18 }}>{analysis.metrics.occupancy}%</div>
                          </div>
                        )}
                        {analysis.metrics.revenue && (
                          <div style={{ background: 'white', padding: '8px 12px', borderRadius: 8 }}>
                            <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Revenue</div>
                            <div style={{ fontWeight: 700, fontSize: 18 }}>{formatCurrency(analysis.metrics.revenue)}</div>
                          </div>
                        )}
                        {analysis.metrics.ebitdar && (
                          <div style={{ background: 'white', padding: '8px 12px', borderRadius: 8 }}>
                            <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>EBITDAR</div>
                            <div style={{ fontWeight: 700, fontSize: 18, color: '#10b981' }}>{formatCurrency(analysis.metrics.ebitdar)}</div>
                          </div>
                        )}
                        {analysis.metrics.asking_price && (
                          <div style={{ background: 'white', padding: '8px 12px', borderRadius: 8 }}>
                            <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Asking Price</div>
                            <div style={{ fontWeight: 700, fontSize: 18 }}>{formatCurrency(analysis.metrics.asking_price)}</div>
                          </div>
                        )}
                        {analysis.metrics.cap_rate && (
                          <div style={{ background: 'white', padding: '8px 12px', borderRadius: 8 }}>
                            <div style={{ fontSize: 11, color: '#64748b', textTransform: 'uppercase' }}>Cap Rate</div>
                            <div style={{ fontWeight: 700, fontSize: 18 }}>{analysis.metrics.cap_rate}%</div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Summary */}
                    <div style={{ fontSize: 13, color: '#475569', whiteSpace: 'pre-wrap' }}>
                      {analysis?.summary || doc.analysis_summary || 'Document analyzed'}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ) : (
        <div className="empty-state">
          <FileText className="empty-state-icon" />
          <p>No documents uploaded yet</p>
          <p style={{ fontSize: 14, color: '#94a3b8' }}>Drag and drop files to get started</p>
        </div>
      )}

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .file-upload-zone.drag-active { border-color: #10b981 !important; background: #f0fdf4 !important; }
      `}</style>
    </div>
  )
}

function Val({val}) {
  if(!val) return <div className="empty-state"><BarChart3 className="empty-state-icon"/><p>Loading...</p></div>
  return <div style={{display:'grid',gridTemplateColumns:'repeat(2,1fr)',gap:24}}>
    {val.income_approach&&<div className="card"><h3 className="card-title" style={{marginBottom:16}}>Income Approach</h3><p style={{marginBottom:12,color:'#64748b'}}><strong>EBITDAR:</strong> {formatCurrency(val.income_approach.ebitdar)}</p><table className="data-table"><thead><tr><th>Scenario</th><th>Cap</th><th>Value</th></tr></thead><tbody><tr><td>Conservative</td><td>{(val.income_approach.low_cap.cap_rate*100).toFixed(1)}%</td><td>{formatCurrency(val.income_approach.low_cap.value)}</td></tr><tr style={{background:'#f0fdf4'}}><td><strong>Base</strong></td><td><strong>{(val.income_approach.mid_cap.cap_rate*100).toFixed(1)}%</strong></td><td><strong>{formatCurrency(val.income_approach.mid_cap.value)}</strong></td></tr><tr><td>Aggressive</td><td>{(val.income_approach.high_cap.cap_rate*100).toFixed(1)}%</td><td>{formatCurrency(val.income_approach.high_cap.value)}</td></tr></tbody></table></div>}
    {val.market_approach&&<div className="card"><h3 className="card-title" style={{marginBottom:16}}>Market ($/Bed)</h3><p style={{marginBottom:12,color:'#64748b'}}><strong>Beds:</strong> {formatNumber(val.market_approach.total_beds)}</p><table className="data-table"><thead><tr><th>Scenario</th><th>$/Bed</th><th>Value</th></tr></thead><tbody><tr><td>Low</td><td>{formatCurrency(val.market_approach.low.price_per_bed)}</td><td>{formatCurrency(val.market_approach.low.value)}</td></tr><tr style={{background:'#f0fdf4'}}><td><strong>Mid</strong></td><td><strong>{formatCurrency(val.market_approach.mid.price_per_bed)}</strong></td><td><strong>{formatCurrency(val.market_approach.mid.value)}</strong></td></tr><tr><td>High</td><td>{formatCurrency(val.market_approach.high.price_per_bed)}</td><td>{formatCurrency(val.market_approach.high.value)}</td></tr></tbody></table></div>}
    {val.summary?.estimated_value&&<div className="card" style={{gridColumn:'1/-1'}}><h3 className="card-title" style={{marginBottom:16}}>Summary</h3><div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:24,textAlign:'center'}}><div><div className="stat-label">Est. Value</div><div className="stat-value" style={{color:'#10b981',fontSize:28}}>{formatCurrency(val.summary.estimated_value)}</div></div><div><div className="stat-label">Asking</div><div className="stat-value" style={{fontSize:28}}>{formatCurrency(val.summary.asking_price)}</div></div><div><div className="stat-label">Spread</div><div className="stat-value" style={{fontSize:28,color:val.summary.spread_pct>0?'#10b981':'#ef4444'}}>{val.summary.spread_pct>0?'+':''}{val.summary.spread_pct}%</div></div><div><div className="stat-label">Rec</div><div style={{fontSize:18,fontWeight:600,marginTop:8,color:val.summary.recommendation?.includes('Under')?'#10b981':(val.summary.recommendation?.includes('Over')?'#ef4444':'#64748b')}}>{val.summary.recommendation}</div></div></div></div>}
    {!val.income_approach&&!val.market_approach&&<div className="empty-state" style={{gridColumn:'1/-1'}}><BarChart3 className="empty-state-icon"/><p>Enter EBITDAR and/or beds in Overview</p></div>}
  </div>
}

function Props({deal,onRefresh}) {
  const [show, setShow] = useState(false)
  const [np, setNp] = useState({name:'',property_type:'SNF',address:'',city:'',state:'',licensed_beds:''})
  const add = async () => { try { await createProperty(deal.id,{...np,licensed_beds:np.licensed_beds?parseInt(np.licensed_beds):null}); setShow(false); setNp({name:'',property_type:'SNF',address:'',city:'',state:'',licensed_beds:''}); onRefresh() } catch(e){console.error(e)} }
  const del = async (id) => { if(window.confirm('Delete?')) { try { await deleteProperty(id); onRefresh() } catch(e){console.error(e)} } }
  return <div>
    <button className="btn btn-primary" onClick={()=>setShow(true)} style={{marginBottom:16}}><Plus size={16}/> Add Property</button>
    {show&&<div className="card" style={{marginBottom:24}}><h3 className="card-title" style={{marginBottom:16}}>Add Property</h3>
      <div className="form-row-3"><div className="form-group"><label className="form-label">Name *</label><input className="form-input" value={np.name} onChange={e=>setNp({...np,name:e.target.value})}/></div><div className="form-group"><label className="form-label">Type</label><select className="form-select" value={np.property_type} onChange={e=>setNp({...np,property_type:e.target.value})}><option value="SNF">SNF</option><option value="ALF">ALF</option><option value="ILF">ILF</option></select></div><div className="form-group"><label className="form-label">Beds</label><input type="number" className="form-input" value={np.licensed_beds} onChange={e=>setNp({...np,licensed_beds:e.target.value})}/></div></div>
      <div className="form-row"><div className="form-group"><label className="form-label">Address</label><input className="form-input" value={np.address} onChange={e=>setNp({...np,address:e.target.value})}/></div><div className="form-group"><label className="form-label">City</label><input className="form-input" value={np.city} onChange={e=>setNp({...np,city:e.target.value})}/></div></div>
      <div style={{display:'flex',gap:8,marginTop:16}}><button className="btn btn-secondary" onClick={()=>setShow(false)}>Cancel</button><button className="btn btn-primary" onClick={add} disabled={!np.name}>Add</button></div>
    </div>}
    {deal.properties?.length>0?<div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(350px,1fr))',gap:16}}>{deal.properties.map(p=><div key={p.id} className="card"><div style={{display:'flex',justifyContent:'space-between',marginBottom:12}}><div><h4 style={{marginBottom:4}}>{p.name}</h4><span className={'deal-type-badge '+p.property_type?.toLowerCase()}>{p.property_type}</span></div><button className="btn btn-danger btn-sm" onClick={()=>del(p.id)}><Trash2 size={14}/></button></div>{p.address&&<p style={{color:'#64748b',fontSize:14,marginBottom:12}}>{p.address}, {p.city}, {p.state}</p>}<div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8,fontSize:14}}><div><strong>Beds:</strong> {p.licensed_beds||'-'}</div><div><strong>Occupancy:</strong> {p.current_occupancy?p.current_occupancy+'%':'-'}</div></div></div>)}</div>:<div className="empty-state"><Building2 className="empty-state-icon"/><p>No properties</p></div>}
  </div>
}

function Tasks({deal,onRefresh}) {
  const [show, setShow] = useState(false)
  const [nt, setNt] = useState({title:'',priority:'medium'})
  const add = async () => { try { await createTask(deal.id,nt); setShow(false); setNt({title:'',priority:'medium'}); onRefresh() } catch(e){console.error(e)} }
  const toggle = async (t) => { try { await updateTask(t.id,{status:t.status==='completed'?'pending':'completed'}); onRefresh() } catch(e){console.error(e)} }
  const pending = deal.tasks?.filter(t=>t.status!=='completed')||[], done = deal.tasks?.filter(t=>t.status==='completed')||[]
  return <div>
    <button className="btn btn-primary" onClick={()=>setShow(true)} style={{marginBottom:16}}><Plus size={16}/> Add Task</button>
    {show&&<div className="card" style={{marginBottom:24}}><h3 className="card-title" style={{marginBottom:16}}>Add Task</h3>
      <div className="form-row"><div className="form-group"><label className="form-label">Title *</label><input className="form-input" value={nt.title} onChange={e=>setNt({...nt,title:e.target.value})}/></div><div className="form-group"><label className="form-label">Priority</label><select className="form-select" value={nt.priority} onChange={e=>setNt({...nt,priority:e.target.value})}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></div></div>
      <div style={{display:'flex',gap:8,marginTop:16}}><button className="btn btn-secondary" onClick={()=>setShow(false)}>Cancel</button><button className="btn btn-primary" onClick={add} disabled={!nt.title}>Add</button></div>
    </div>}
    <div className="card"><h3 className="card-title" style={{marginBottom:16}}>Pending ({pending.length})</h3>
      {pending.length>0?pending.map(t=><div key={t.id} style={{display:'flex',alignItems:'center',gap:12,padding:'12px 0',borderBottom:'1px solid #f1f5f9'}}><button onClick={()=>toggle(t)} style={{width:24,height:24,borderRadius:'50%',border:'2px solid #e2e8f0',background:'none',cursor:'pointer'}}/><div style={{flex:1}}>{t.title}</div><span className={'priority-badge '+t.priority}>{t.priority}</span>{t.due_date&&<span style={{fontSize:12,color:'#64748b'}}><Clock size={12}/> {formatDate(t.due_date)}</span>}</div>):<p style={{color:'#64748b'}}>No pending tasks</p>}
    </div>
    {done.length>0&&<div className="card" style={{marginTop:16,opacity:0.7}}><h3 className="card-title" style={{marginBottom:16}}>Completed ({done.length})</h3>{done.map(t=><div key={t.id} style={{display:'flex',alignItems:'center',gap:12,padding:'12px 0',borderBottom:'1px solid #f1f5f9'}}><button onClick={()=>toggle(t)} style={{width:24,height:24,borderRadius:'50%',border:'none',background:'#10b981',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center'}}><CheckCircle size={14} color="white"/></button><div style={{flex:1,textDecoration:'line-through'}}>{t.title}</div></div>)}</div>}
  </div>
}

function Activity({deal}) {
  return <div className="card"><h3 className="card-title" style={{marginBottom:16}}>Activity</h3>
    {deal.activities?.length>0?<ul className="activity-list">{deal.activities.map((a,i)=><li key={i} className="activity-item"><div className="activity-icon">{a.action==='created'&&<Plus size={16}/>}{a.action==='status_changed'&&<RefreshCw size={16}/>}{a.action==='document_uploaded'&&<Upload size={16}/>}{a.action==='property_added'&&<Building2 size={16}/>}{a.action==='task_completed'&&<CheckCircle size={16} color="#10b981"/>}{a.action==='document_analyzed'&&<Zap size={16} color="#8b5cf6"/>}{a.action==='updated'&&<Edit2 size={16}/>}</div><div className="activity-content"><div className="activity-description">{a.description}</div><div className="activity-time">{formatDateTime(a.created_at)}</div></div></li>)}</ul>:<p style={{color:'#64748b'}}>No activity yet.</p>}
  </div>
}

export default DealDetail
