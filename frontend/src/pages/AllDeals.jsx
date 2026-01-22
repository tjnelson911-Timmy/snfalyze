import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { getDeals, formatCurrency, formatDate } from '../services/api'
function AllDeals() {
  const [deals, setDeals] = useState([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const navigate = useNavigate()
  useEffect(() => { getDeals({search:search||undefined,status:statusFilter||undefined}).then(setDeals).catch(console.error) }, [search, statusFilter])
  return (
    <div>
      <div className="page-header"><h1 className="page-title">All Deals</h1><Link to="/deals/new" className="btn btn-primary"><Plus size={18}/> New Deal</Link></div>
      <div className="card" style={{marginBottom:24}}>
        <div style={{display:'flex',gap:16}}>
          <div style={{flex:1,position:'relative'}}><Search size={18} style={{position:'absolute',left:12,top:'50%',transform:'translateY(-50%)',color:'#94a3b8'}}/><input className="form-input" placeholder="Search..." value={search} onChange={e=>setSearch(e.target.value)} style={{paddingLeft:40}}/></div>
          <select className="form-select" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)} style={{width:200}}><option value="">All</option><option value="vetting">Vetting</option><option value="pipeline">Pipeline</option><option value="due_diligence">Due Diligence</option><option value="current_operations">Current Ops</option><option value="on_hold">On Hold</option></select>
        </div>
      </div>
      <table className="data-table"><thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Beds</th><th>Price</th><th>Created</th></tr></thead>
        <tbody>{deals.map(d=><tr key={d.id} onClick={()=>navigate('/deals/'+d.id)} style={{cursor:'pointer'}}><td><strong>{d.name}</strong></td><td><span className={'deal-type-badge '+(d.deal_type||'snf').toLowerCase()}>{d.deal_type||'SNF'}</span></td><td><span className={'status-badge '+d.status}>{d.status.replace('_',' ')}</span></td><td>{d.total_beds||'-'}</td><td>{formatCurrency(d.asking_price)}</td><td>{formatDate(d.created_at)}</td></tr>)}</tbody>
      </table>
    </div>
  )
}
export default AllDeals
