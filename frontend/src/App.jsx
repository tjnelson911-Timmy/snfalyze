import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import DealDetail from './pages/DealDetail'
import AllDeals from './pages/AllDeals'
import NewDeal from './pages/NewDeal'
function App() {
  return <Router><Layout><Routes><Route path="/" element={<Dashboard />} /><Route path="/deals" element={<AllDeals />} /><Route path="/deals/new" element={<NewDeal />} /><Route path="/deals/:id" element={<DealDetail />} /></Routes></Layout></Router>
}
export default App
