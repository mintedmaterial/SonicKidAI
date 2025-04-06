import { Routes, Route } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import Dashboard from './pages/Dashboard'
import NFTs from './pages/NFTs'
import Trading from './pages/Trading'
import Social from './pages/Social'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

export default function Router() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/nfts" element={<NFTs />} />
        <Route path="/trading" element={<Trading />} />
        <Route path="/social" element={<Social />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </MainLayout>
  )
}
