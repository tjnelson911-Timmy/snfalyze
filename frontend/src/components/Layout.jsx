import React from 'react'
import { NavLink } from 'react-router-dom'
import { LayoutDashboard, FolderKanban, Plus, Building2, Briefcase } from 'lucide-react'

function Layout({ children }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            SNF<span>alyze</span>
          </div>
          <div className="sidebar-tagline">Deal Management</div>
        </div>
        <nav>
          <ul className="sidebar-nav">
            <li>
              <NavLink to="/" className={({isActive}) => isActive ? 'active' : ''} end>
                <LayoutDashboard size={18}/>
                <span>Dashboard</span>
              </NavLink>
            </li>
            <li>
              <NavLink to="/deals" className={({isActive}) => isActive ? 'active' : ''}>
                <FolderKanban size={18}/>
                <span>All Deals</span>
              </NavLink>
            </li>
            <li>
              <NavLink to="/deals/new" className={({isActive}) => isActive ? 'active' : ''}>
                <Plus size={18}/>
                <span>New Deal</span>
              </NavLink>
            </li>
            <li>
              <NavLink to="/current-ops" className={({isActive}) => isActive ? 'active' : ''}>
                <Briefcase size={18}/>
                <span>Current Ops</span>
              </NavLink>
            </li>
          </ul>
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-user">
            <div className="sidebar-avatar">TN</div>
            <div className="sidebar-user-info">
              <div className="sidebar-user-name">Tim Nelson</div>
              <div className="sidebar-user-role">Acquisitions</div>
            </div>
          </div>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  )
}

export default Layout
