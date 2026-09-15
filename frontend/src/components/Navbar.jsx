import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../App'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className="navbar">
      <div className="container navbar-inner">
        <NavLink to="/" className="navbar-logo">
          <div className="navbar-logo-icon">🔍</div>
          <span>FaceFind <span className="gradient-text">Drive</span></span>
        </NavLink>

        <div className="navbar-nav">
          <NavLink
            to="/"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            🔎 Search
          </NavLink>
          {user?.role === 'admin' && (
            <NavLink
              to="/admin"
              className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            >
              ⚙️ Admin
            </NavLink>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ textAlign: 'right' }} className="hide-mobile">
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              {user?.full_name || user?.email}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {user?.role}
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={handleLogout} id="btn-logout">
            Sign out
          </button>
        </div>
      </div>
    </nav>
  )
}
