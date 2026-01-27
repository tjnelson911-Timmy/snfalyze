import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import DealDetail from './pages/DealDetail'
import AllDeals from './pages/AllDeals'
import NewDeal from './pages/NewDeal'
import CurrentOps from './pages/CurrentOps'
import WelcomeNightsList from './pages/WelcomeNightsList'
import WelcomeNightsWizard from './pages/WelcomeNightsWizard'
import WelcomeNightsPresent from './pages/WelcomeNightsPresent'
import WelcomeNightsAdmin from './pages/WelcomeNightsAdmin'

function App() {
  return (
    <Router>
      <Routes>
        {/* Present mode without layout */}
        <Route path="/welcome-nights/:id/present" element={<WelcomeNightsPresent />} />

        {/* All other routes with layout */}
        <Route path="/*" element={
          <Layout>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/deals" element={<AllDeals />} />
              <Route path="/deals/new" element={<NewDeal />} />
              <Route path="/deals/:id" element={<DealDetail />} />
              <Route path="/current-ops" element={<CurrentOps />} />
              <Route path="/welcome-nights" element={<WelcomeNightsList />} />
              <Route path="/welcome-nights/new" element={<WelcomeNightsWizard />} />
              <Route path="/welcome-nights/:id/edit" element={<WelcomeNightsWizard />} />
              <Route path="/admin/welcome-nights/*" element={<WelcomeNightsAdmin />} />
            </Routes>
          </Layout>
        } />
      </Routes>
    </Router>
  )
}

export default App
