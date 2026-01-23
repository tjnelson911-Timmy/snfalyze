import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Plus, Search, Building2 } from 'lucide-react'
import { getDeals, formatCurrency, formatDate } from '../services/api'

function AllDeals() {
  const [deals, setDeals] = useState([])
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    getDeals({ search: search || undefined, status: statusFilter || undefined })
      .then(setDeals)
      .catch(console.error)
  }, [search, statusFilter])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">All Deals</h1>
          <p className="page-subtitle">{deals.length} deals</p>
        </div>
        <Link to="/deals/new" className="btn btn-primary">
          <Plus size={16} /> New Deal
        </Link>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 20, padding: 16 }}>
        <div style={{ display: 'flex', gap: 12 }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#a3a3a3' }} />
            <input
              className="form-input"
              placeholder="Search deals..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ paddingLeft: 36 }}
            />
          </div>
          <select
            className="form-select"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            style={{ width: 180 }}
          >
            <option value="">All Statuses</option>
            <option value="vetting">Vetting</option>
            <option value="pipeline">Pipeline</option>
            <option value="due_diligence">Due Diligence</option>
            <option value="current_operations">Current Ops</option>
            <option value="on_hold">On Hold</option>
            <option value="closed">Closed</option>
            <option value="passed">Passed</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <table className="data-table">
        <thead>
          <tr>
            <th>Deal Name</th>
            <th>Type</th>
            <th>Status</th>
            <th>Beds</th>
            <th>Properties</th>
            <th>Price</th>
            <th>Created</th>
          </tr>
        </thead>
        <tbody>
          {deals.map(d => (
            <tr
              key={d.id}
              onClick={() => navigate('/deals/' + d.id)}
              style={{ cursor: 'pointer' }}
            >
              <td>
                <div style={{ fontWeight: 600 }}>{d.name}</div>
              </td>
              <td>
                <span className={'deal-type-badge ' + (d.deal_type || 'snf').toLowerCase()}>
                  {d.deal_type || 'SNF'}
                </span>
              </td>
              <td>
                <span className={'status-badge ' + d.status}>
                  {d.status.replace('_', ' ')}
                </span>
              </td>
              <td>{d.total_beds || '—'}</td>
              <td>{d.property_count || 1}</td>
              <td style={{ fontWeight: 500 }}>{formatCurrency(d.asking_price)}</td>
              <td style={{ color: '#737373' }}>{formatDate(d.created_at)}</td>
            </tr>
          ))}
          {deals.length === 0 && (
            <tr>
              <td colSpan="7" style={{ textAlign: 'center', padding: 48, color: '#737373' }}>
                <Building2 size={32} color="#d4d4d4" style={{ marginBottom: 12 }} />
                <div>No deals found</div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

export default AllDeals
