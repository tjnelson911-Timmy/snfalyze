import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Plus, Building2, DollarSign, TrendingUp, FileText, RefreshCw } from 'lucide-react'
import { getDeals, getDealStats, formatCurrency, formatNumber } from '../services/api'
const STATUSES = [{key:'vetting',label:'Vetting'},{key:'pipeline',label:'Pipeline'},{key:'due_diligence',label:'Due Diligence'},{key:'current_operations',label:'Current Ops'},{key:'on_hold',label:'On Hold'}]
function Dashboard() {
  const [deals, setDeals] = useState([])
  const [stats, setStats] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()
  useEffect(() => { loadData() }, [])
  const loadData = async () => {
    try { setLoading(true); setError(null); const [d, s] = await Promise.all([getDeals(), getDealStats()]); setDeals(d); setStats(s) }
    catch (e) { setError('Failed to load. Is backend running?') }
    finally { setLoading(false) }
  }
  if (loading) return <div className="empty-state"><RefreshCw className="empty-state-icon" style={{animation:'spin 1s linear infinite'}}/><p>Loading...</p></div>
  if (error) return <div className="empty-state"><p>{error}</p><button className="btn btn-primary" onClick={loadData}><RefreshCw size={16}/> Retry</button></div>
  return (
    <div>
      <div className="page-header"><h1 className="page-title">Deal Pipeline</h1><Link to="/deals/new" className="btn btn-primary"><Plus size={18}/> New Deal</Link></div>
      <div className="stats-grid">
        {STATUSES.map(s => <div key={s.key} className={'stat-card '+s.key.replace('_','-')}><div className="stat-label">{s.label}</div><div className="stat-value">{stats[s.key]||0}</div></div>)}
      </div>
      <div className="stats-grid" style={{marginBottom:24}}>
        <div className="stat-card"><div style={{display:'flex',alignItems:'center',gap:12}}><div style={{width:48,height:48,borderRadius:12,background:'#dbeafe',display:'flex',alignItems:'center',justifyContent:'center'}}><Building2 size={24} color="#3b82f6"/></div><div><div className="stat-label">Total Beds</div><div className="stat-value">{formatNumber(stats.total_beds)}</div></div></div></div>
        <div className="stat-card"><div style={{display:'flex',alignItems:'center',gap:12}}><div style={{width:48,height:48,borderRadius:12,background:'#dcfce7',display:'flex',alignItems:'center',justifyContent:'center'}}><DollarSign size={24} color="#10b981"/></div><div><div className="stat-label">Pipeline Value</div><div className="stat-value">{formatCurrency(stats.total_value)}</div></div></div></div>
        <div className="stat-card"><div style={{display:'flex',alignItems:'center',gap:12}}><div style={{width:48,height:48,borderRadius:12,background:'#f3e8ff',display:'flex',alignItems:'center',justifyContent:'center'}}><TrendingUp size={24} color="#8b5cf6"/></div><div><div className="stat-label">Total Deals</div><div className="stat-value">{stats.total||0}</div></div></div></div>
      </div>
      <div className="pipeline-board">
        {STATUSES.map(st => (
          <div key={st.key} className="pipeline-column">
            <div className="column-header"><span className="column-title">{st.label}</span><span className="column-count">{deals.filter(d=>d.status===st.key).length}</span></div>
            {deals.filter(d=>d.status===st.key).map(deal => (
              <div key={deal.id} className="deal-card" onClick={()=>navigate('/deals/'+deal.id)}>
                <div className="deal-card-header"><span className="deal-name">{deal.name}</span><span className={'deal-type-badge '+(deal.deal_type||'snf').toLowerCase()}>{deal.deal_type||'SNF'}</span></div>
                <div className="deal-meta">{deal.total_beds>0&&<span><Building2 size={14}/> {deal.total_beds} beds</span>}{deal.document_count>0&&<span><FileText size={14}/> {deal.document_count}</span>}</div>
                {deal.asking_price>0&&<div className="deal-price">{formatCurrency(deal.asking_price)}</div>}
                <div className="deal-footer"><span className={'priority-badge '+(deal.priority||'medium')}>{deal.priority||'Medium'}</span></div>
              </div>
            ))}
            {deals.filter(d=>d.status===st.key).length===0&&<div className="empty-state" style={{padding:24}}><p style={{fontSize:13,color:'#94a3b8'}}>No deals</p></div>}
          </div>
        ))}
      </div>
    </div>
  )
}
export default Dashboard
