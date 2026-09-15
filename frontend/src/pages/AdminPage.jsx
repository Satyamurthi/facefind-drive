import { useState, useEffect, useCallback } from 'react'
import { toast } from 'react-hot-toast'
import { api } from '../api'

/* ─── Sub-panels ─────────────────────────────────────────────────────────── */

function ConfigPanel() {
  const [cfg, setCfg] = useState(null)
  const [saving, setSaving] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [cacheStatus, setCacheStatus] = useState(null)

  useEffect(() => {
    api.getConfig().then(setCfg).catch(() => toast.error('Could not load config'))
    api.getCacheStatus().then(setCacheStatus).catch(() => {})
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      await api.updateConfig({
        drive_folder_id: cfg.drive_folder_id,
        face_similarity_threshold: parseFloat(cfg.face_similarity_threshold),
        stated_purpose: cfg.stated_purpose,
        index_interval_hours: parseInt(cfg.index_interval_hours),
      })
      toast.success('Config saved')
    } catch (err) {
      toast.error(err.message)
    } finally {
      setSaving(false)
    }
  }

  const triggerRefresh = async (full) => {
    setRefreshing(true)
    try {
      const r = await api.refreshCache(full)
      toast.success(r.message)
      setTimeout(() => api.getCacheStatus().then(setCacheStatus), 2000)
    } catch (err) {
      toast.error(err.message)
    } finally {
      setRefreshing(false)
    }
  }

  if (!cfg) return <div className="spinner spinner-lg" style={{ margin: '40px auto' }} />

  return (
    <div style={{ display: 'grid', gap: 'var(--space-xl)', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))' }}>
      {/* App Settings */}
      <div className="card" style={{ padding: 'var(--space-xl)' }}>
        <h3 style={{ marginBottom: 'var(--space-lg)' }}>⚙️ App Settings</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <div className="form-group">
            <label className="form-label">Drive Folder ID</label>
            <input className="form-input" id="cfg-folder-id"
              value={cfg.drive_folder_id || ''} onChange={e => setCfg(c => ({...c, drive_folder_id: e.target.value}))}
              placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2..."
              style={{ fontFamily: 'monospace', fontSize: '0.8rem' }} />
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
              Extract from the Drive folder URL: /folders/<strong style={{color:'var(--color-accent)'}}>FOLDER_ID</strong>
            </span>
          </div>
          <div className="form-group">
            <label className="form-label">Stated Purpose</label>
            <input className="form-input" id="cfg-purpose"
              value={cfg.stated_purpose || ''} onChange={e => setCfg(c => ({...c, stated_purpose: e.target.value}))}
              placeholder="Event Photo Retrieval — MIT 2024" />
          </div>
          <div className="form-group">
            <label className="form-label">Similarity Threshold ({Math.round((cfg.face_similarity_threshold||0.68)*100)}%)</label>
            <input type="range" min="0.5" max="0.95" step="0.01" id="cfg-threshold"
              value={cfg.face_similarity_threshold || 0.68}
              onChange={e => setCfg(c => ({...c, face_similarity_threshold: e.target.value}))}
              style={{ width: '100%', accentColor: 'var(--color-primary)' }} />
            <div style={{ display:'flex', justifyContent:'space-between', fontSize:'0.75rem', color:'var(--color-text-muted)' }}>
              <span>50% (loose)</span><span>95% (strict)</span>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Re-index Interval (hours)</label>
            <input className="form-input" id="cfg-interval" type="number" min="1" max="168"
              value={cfg.index_interval_hours || 6} onChange={e => setCfg(c => ({...c, index_interval_hours: e.target.value}))} />
          </div>
          <button className="btn btn-primary" onClick={save} disabled={saving} id="btn-save-config">
            {saving ? <><span className="spinner"/>Saving…</> : '💾 Save Config'}
          </button>
        </div>
      </div>

      {/* Cache / Index */}
      <div className="card" style={{ padding: 'var(--space-xl)' }}>
        <h3 style={{ marginBottom: 'var(--space-lg)' }}>🗄️ Drive Index</h3>
        {cacheStatus && (
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'var(--space-md)', marginBottom:'var(--space-xl)' }}>
            {[
              { label:'Total Files', value: cacheStatus.total_files ?? '—' },
              { label:'Indexed', value: cacheStatus.indexed_files ?? '—' },
              { label:'Errors', value: cacheStatus.errors ?? '—' },
              { label:'Status', value: cacheStatus.running ? '🔄 Running' : '✅ Idle' },
            ].map(s => (
              <div className="stat-card" key={s.label}>
                <div className="stat-value" style={{ fontSize:'1.75rem' }}>{s.value}</div>
                <div className="stat-label">{s.label}</div>
              </div>
            ))}
          </div>
        )}
        <div style={{ display:'flex', gap:10, flexWrap:'wrap' }}>
          <button className="btn btn-primary" onClick={() => triggerRefresh(false)} disabled={refreshing} id="btn-incremental-index">
            {refreshing ? <><span className="spinner"/>Running…</> : '⚡ Incremental Update'}
          </button>
          <button className="btn btn-ghost" onClick={() => triggerRefresh(true)} disabled={refreshing} id="btn-full-index">
            🔄 Full Re-index
          </button>
        </div>
        <p style={{ fontSize:'0.8rem', marginTop:12, color:'var(--color-text-muted)' }}>
          Engine: <strong style={{color:'var(--color-text-secondary)'}}>Google Gemini Vision</strong>
          &nbsp;·&nbsp;
          Model: <strong style={{color:'var(--color-text-secondary)'}}>{cfg.gemini_model || 'gemini-1.5-flash'}</strong>
          &nbsp;·&nbsp;
          API Key: <span className={cfg.gemini_key_configured ? 'badge badge-success' : 'badge badge-danger'} style={{fontSize:'0.7rem'}}>
            {cfg.gemini_key_configured ? '✓ Configured' : '✗ Not set'}
          </span>
        </p>
      </div>
    </div>
  )
}

function UsersPanel() {
  const [users, setUsers] = useState([])
  const [invites, setInvites] = useState([])
  const [newUser, setNewUser] = useState({ email:'', password:'', full_name:'', role:'user' })
  const [creating, setCreating] = useState(false)
  const [creatingInvite, setCreatingInvite] = useState(false)

  const load = useCallback(() => {
    api.getUsers().then(setUsers).catch(() => {})
    api.getInviteCodes().then(setInvites).catch(() => {})
  }, [])
  useEffect(load, [load])

  const createUser = async (e) => {
    e.preventDefault()
    setCreating(true)
    try {
      await api.createUser(newUser)
      toast.success('User created')
      setNewUser({ email:'', password:'', full_name:'', role:'user' })
      load()
    } catch (err) { toast.error(err.message) }
    finally { setCreating(false) }
  }

  const toggleUser = async (user) => {
    try {
      await api.updateUser(user.id, { is_active: !user.is_active })
      toast.success(user.is_active ? 'User disabled' : 'User enabled')
      load()
    } catch (err) { toast.error(err.message) }
  }

  const generateInvite = async () => {
    setCreatingInvite(true)
    try {
      const inv = await api.createInviteCode({ role:'user', expires_in_hours: 48 })
      toast.success(`Invite code: ${inv.code}`)
      load()
    } catch (err) { toast.error(err.message) }
    finally { setCreatingInvite(false) }
  }

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'var(--space-xl)' }}>
      {/* Create User */}
      <div className="card" style={{ padding:'var(--space-xl)' }}>
        <h3 style={{ marginBottom:'var(--space-lg)' }}>➕ Create User</h3>
        <form onSubmit={createUser} style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(200px, 1fr))', gap:'var(--space-md)', alignItems:'end' }}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input className="form-input" placeholder="Jane Doe" value={newUser.full_name}
              onChange={e => setNewUser(u=>({...u, full_name:e.target.value}))} />
          </div>
          <div className="form-group">
            <label className="form-label">Email *</label>
            <input className="form-input" type="email" required placeholder="jane@mit.edu" value={newUser.email}
              onChange={e => setNewUser(u=>({...u, email:e.target.value}))} />
          </div>
          <div className="form-group">
            <label className="form-label">Password *</label>
            <input className="form-input" type="password" required placeholder="••••••••" value={newUser.password}
              onChange={e => setNewUser(u=>({...u, password:e.target.value}))} />
          </div>
          <div className="form-group">
            <label className="form-label">Role</label>
            <select className="form-input" value={newUser.role} onChange={e => setNewUser(u=>({...u, role:e.target.value}))}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button type="submit" className="btn btn-primary" disabled={creating} id="btn-create-user">
            {creating ? <><span className="spinner"/>Creating…</> : 'Create'}
          </button>
        </form>
      </div>

      {/* Invite Codes */}
      <div className="card" style={{ padding:'var(--space-xl)' }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:'var(--space-lg)' }}>
          <h3>🎟️ Invite Codes</h3>
          <button className="btn btn-accent btn-sm" onClick={generateInvite} disabled={creatingInvite} id="btn-gen-invite">
            {creatingInvite ? <><span className="spinner"/>…</> : '+ Generate'}
          </button>
        </div>
        <div style={{ overflowX:'auto' }}>
          <table className="data-table">
            <thead><tr>
              <th>Code</th><th>Role</th><th>Used By</th><th>Expires</th>
            </tr></thead>
            <tbody>
              {invites.map(inv => (
                <tr key={inv.id}>
                  <td><span className="monospace">{inv.code}</span></td>
                  <td><span className={`badge ${inv.role === 'admin' ? 'badge-warning' : 'badge-primary'}`}>{inv.role}</span></td>
                  <td>{inv.used_by ? <span className="badge badge-muted">Used</span> : <span className="badge badge-success">Available</span>}</td>
                  <td style={{ fontSize:'0.8rem', color:'var(--color-text-muted)' }}>
                    {inv.expires_at ? new Date(inv.expires_at).toLocaleDateString() : '—'}
                  </td>
                </tr>
              ))}
              {invites.length === 0 && <tr><td colSpan={4} style={{textAlign:'center', color:'var(--color-text-muted)'}}>No invite codes yet</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      {/* User list */}
      <div className="card" style={{ padding:'var(--space-xl)' }}>
        <h3 style={{ marginBottom:'var(--space-lg)' }}>👥 Users ({users.length})</h3>
        <div style={{ overflowX:'auto' }}>
          <table className="data-table">
            <thead><tr><th>Name / Email</th><th>Role</th><th>Status</th><th>Last Login</th><th>Actions</th></tr></thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id}>
                  <td>
                    <div style={{ fontWeight:600, color:'var(--color-text-primary)' }}>{u.full_name || '—'}</div>
                    <div style={{ fontSize:'0.8rem', color:'var(--color-text-muted)' }}>{u.email}</div>
                  </td>
                  <td><span className={`badge ${u.role==='admin'?'badge-warning':'badge-primary'}`}>{u.role}</span></td>
                  <td><span className={`badge ${u.is_active?'badge-success':'badge-danger'}`}>{u.is_active?'Active':'Disabled'}</span></td>
                  <td style={{ fontSize:'0.8rem', color:'var(--color-text-muted)' }}>
                    {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                  </td>
                  <td>
                    <button
                      className={`btn btn-sm ${u.is_active?'btn-danger':'btn-ghost'}`}
                      onClick={() => toggleUser(u)}
                    >
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function AuditPanel() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getAuditLogs(200)
      .then(setLogs)
      .catch(() => toast.error('Could not load audit logs'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="spinner spinner-lg" style={{ margin:'40px auto' }} />

  return (
    <div className="card" style={{ padding:'var(--space-xl)' }}>
      <h3 style={{ marginBottom:'var(--space-lg)' }}>📋 Audit Log ({logs.length} entries)</h3>
      <div style={{ overflowX:'auto' }}>
        <table className="data-table">
          <thead><tr>
            <th>Time</th><th>Action</th><th>User</th><th>Matches</th><th>IP</th><th>Threshold</th>
          </tr></thead>
          <tbody>
            {logs.map((log, i) => (
              <tr key={i}>
                <td style={{ fontSize:'0.78rem', whiteSpace:'nowrap' }}>
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td><span className="badge badge-primary">{log.action}</span></td>
                <td style={{ fontSize:'0.8rem' }}>{log.user_email || '—'}</td>
                <td>{log.matches_returned ?? '—'}</td>
                <td style={{ fontSize:'0.78rem', color:'var(--color-text-muted)' }}>{log.ip_address || '—'}</td>
                <td style={{ fontSize:'0.78rem' }}>{log.threshold_used ? `${Math.round(log.threshold_used*100)}%` : '—'}</td>
              </tr>
            ))}
            {logs.length === 0 && (
              <tr><td colSpan={6} style={{textAlign:'center', color:'var(--color-text-muted)', padding:32}}>No audit records yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ─── Main Admin Page ─────────────────────────────────────────────────────── */

const TABS = [
  { id: 'config', label: '⚙️ Configuration', Panel: ConfigPanel },
  { id: 'users', label: '👥 Users & Invites', Panel: UsersPanel },
  { id: 'audit', label: '📋 Audit Log', Panel: AuditPanel },
]

export default function AdminPage() {
  const [active, setActive] = useState('config')
  const { Panel } = TABS.find(t => t.id === active)

  return (
    <div className="container" style={{ paddingTop:'var(--space-xl)', paddingBottom:'var(--space-2xl)' }}>
      <h1 style={{ marginBottom:'var(--space-lg)' }}>
        Admin <span className="gradient-text">Dashboard</span>
      </h1>

      <div className="admin-tabs">
        {TABS.map(t => (
          <div
            key={t.id}
            className={`admin-tab ${active === t.id ? 'active' : ''}`}
            onClick={() => setActive(t.id)}
            role="tab"
            id={`admin-tab-${t.id}`}
          >
            {t.label}
          </div>
        ))}
      </div>

      <Panel />
    </div>
  )
}
