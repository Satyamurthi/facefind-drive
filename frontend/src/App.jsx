import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect, createContext, useContext } from 'react'
import { api, clearTokens } from './api'
import Navbar from './components/Navbar'
import LoginPage from './pages/LoginPage'
import SearchPage from './pages/SearchPage'
import AdminPage from './pages/AdminPage'

// ─── Auth Context ─────────────────────────────────────────────────────────
export const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <div className="spinner spinner-lg" />
    </div>
  )
  if (!user) return <Navigate to="/login" replace />
  return children
}

function RequireAdmin({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  if (!user || user.role !== 'admin') return <Navigate to="/" replace />
  return children
}

// ─── App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { setLoading(false); return }
    api.me()
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false))
  }, [])

  const logout = () => {
    clearTokens()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, setUser, logout, loading }}>
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        {user && <Navbar />}
        <main style={{ flex: 1 }}>
          <Routes>
            <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
            <Route path="/" element={
              <RequireAuth><SearchPage /></RequireAuth>
            } />
            <Route path="/admin" element={
              <RequireAdmin><AdminPage /></RequireAdmin>
            } />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </AuthContext.Provider>
  )
}
