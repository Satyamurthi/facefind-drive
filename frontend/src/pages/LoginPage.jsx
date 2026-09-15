import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import { api } from '../api'
import { useAuth } from '../App'

export default function LoginPage() {
  const [tab, setTab] = useState('login')
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({ email: '', password: '', full_name: '', invite_code: '' })
  const { setUser } = useAuth()
  const navigate = useNavigate()

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      let tokens
      if (tab === 'login') {
        tokens = await api.login(form.email, form.password)
      } else {
        tokens = await api.register(form.email, form.password, form.full_name, form.invite_code)
      }
      api.setTokens(tokens.access_token, tokens.refresh_token)
      const me = await api.me()
      setUser(me)
      toast.success(`Welcome${me.full_name ? `, ${me.full_name}` : ''}!`)
      navigate('/')
    } catch (err) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      {/* Background orbs */}
      <div className="auth-bg-orb auth-bg-orb-1" />
      <div className="auth-bg-orb auth-bg-orb-2" />

      <div className="auth-card">
        {/* Logo */}
        <div className="auth-logo">
          <div className="auth-logo-icon">🔍</div>
          <h1 style={{ fontSize: '1.75rem', marginBottom: 6 }}>
            FaceFind <span className="gradient-text">Drive</span>
          </h1>
          <p style={{ fontSize: '0.875rem' }}>
            Facial recognition photo search — restricted access
          </p>
        </div>

        {/* Tabs */}
        <div className="auth-tabs">
          <div
            className={`auth-tab ${tab === 'login' ? 'active' : ''}`}
            onClick={() => setTab('login')}
            role="tab"
            id="tab-login"
          >
            Sign In
          </div>
          <div
            className={`auth-tab ${tab === 'register' ? 'active' : ''}`}
            onClick={() => setTab('register')}
            role="tab"
            id="tab-register"
          >
            Register
          </div>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} id="auth-form">
          {tab === 'register' && (
            <div className="form-group">
              <label className="form-label" htmlFor="full-name">Full Name</label>
              <input
                id="full-name"
                className="form-input"
                type="text"
                placeholder="Your name"
                value={form.full_name}
                onChange={e => set('full_name', e.target.value)}
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="email">Email</label>
            <input
              id="email"
              className="form-input"
              type="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={e => set('email', e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              className="form-input"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={e => set('password', e.target.value)}
              required
              autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
            />
          </div>

          {tab === 'register' && (
            <div className="form-group">
              <label className="form-label" htmlFor="invite-code">Invite Code</label>
              <input
                id="invite-code"
                className="form-input"
                type="text"
                placeholder="XXXX-XXXX-XXXX"
                value={form.invite_code}
                onChange={e => set('invite_code', e.target.value.toUpperCase())}
                required
                style={{ fontFamily: 'monospace', letterSpacing: '0.1em' }}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                Obtain an invite code from your administrator.
              </span>
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={loading}
            id="btn-auth-submit"
            style={{ width: '100%', marginTop: 8 }}
          >
            {loading
              ? <><span className="spinner" /> {tab === 'login' ? 'Signing in…' : 'Creating account…'}</>
              : tab === 'login' ? '→ Sign In' : '→ Create Account'
            }
          </button>
        </form>

        <p style={{ textAlign: 'center', fontSize: '0.75rem', marginTop: 24, color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
          This system is restricted to authorized users only.<br />
          All activity is logged for security and compliance.
        </p>
      </div>
    </div>
  )
}
