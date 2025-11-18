import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { motion, AnimatePresence } from 'framer-motion'

// Providers
import { AuthProvider } from './contexts/AuthContext'
import { WebSocketProvider } from './components/providers/WebSocketProvider'

// Auth Components
import ProtectedRoute from './components/auth/ProtectedRoute'
import Login from './pages/Login'

// Layout
import Layout from './components/layout/Layout'

// Pages
import Dashboard from './pages/Dashboard'
import Vulnerabilities from './pages/Vulnerabilities'
import Patches from './pages/Patches'
import Deployments from './pages/Deployments'
import Monitoring from './pages/Monitoring'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

function App() {
  return (
    <Router>
      <AuthProvider>
        <WebSocketProvider>
          <div className="min-h-screen bg-cyber-darker">
            {/* Animated background gradient */}
            <div className="fixed inset-0 bg-gradient-to-br from-cyber-dark via-cyber-darker to-cyber-dark opacity-50 pointer-events-none" />

            {/* Grid overlay */}
            <div className="fixed inset-0 cyber-grid opacity-30 pointer-events-none" />

            {/* Main content */}
            <div className="relative z-10">
              <AnimatePresence mode="wait">
                <Routes>
                  {/* Public routes */}
                  <Route path="/login" element={<Login />} />

                  {/* Protected routes */}
                  <Route
                    path="/"
                    element={
                      <ProtectedRoute>
                        <Layout />
                      </ProtectedRoute>
                    }
                  >
                    <Route index element={<Dashboard />} />
                    <Route path="vulnerabilities" element={<Vulnerabilities />} />
                    <Route path="patches" element={<Patches />} />
                    <Route path="deployments" element={<Deployments />} />
                    <Route path="monitoring" element={<Monitoring />} />
                    <Route path="analytics" element={<Analytics />} />
                    <Route path="settings" element={<Settings />} />
                  </Route>
                </Routes>
              </AnimatePresence>
            </div>

            {/* Toast notifications */}
            <Toaster
              position="top-right"
              toastOptions={{
                className: 'glass-card',
                style: {
                  background: 'rgba(15, 23, 42, 0.9)',
                  backdropFilter: 'blur(12px)',
                  border: '1px solid rgba(0, 217, 255, 0.2)',
                  color: '#f1f5f9',
                },
                success: {
                  iconTheme: {
                    primary: '#00ff88',
                    secondary: '#0a0e27',
                  },
                },
                error: {
                  iconTheme: {
                    primary: '#ff0055',
                    secondary: '#0a0e27',
                  },
                },
              }}
            />
          </div>
        </WebSocketProvider>
      </AuthProvider>
    </Router>
  )
}

export default App
