/**
 * Centralized API client with JWT token injection and refresh logic.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

function getTokens() {
  return {
    access: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),
  };
}

function setTokens(access, refresh) {
  if (access) localStorage.setItem('access_token', access);
  if (refresh) localStorage.setItem('refresh_token', refresh);
}

export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

async function refreshAccessToken() {
  const { refresh } = getTokens();
  if (!refresh) return null;
  const res = await fetch(`${BASE_URL}/api/auth/refresh`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${refresh}` },
  });
  if (!res.ok) return null;
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

async function request(path, options = {}, retry = true) {
  const { access } = getTokens();
  const headers = { ...options.headers };
  if (access) headers['Authorization'] = `Bearer ${access}`;
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401 && retry) {
    const newToken = await refreshAccessToken();
    if (newToken) return request(path, options, false);
    clearTokens();
    window.location.href = '/login';
    return;
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      msg = err.detail || JSON.stringify(err);
    } catch (_) {}
    throw new Error(msg);
  }

  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return res;
}

export const api = {
  // Auth
  login: (email, password) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  register: (email, password, full_name, invite_code) =>
    request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, full_name, invite_code }),
    }),

  me: () => request('/api/auth/me'),

  purpose: () => fetch(`${BASE_URL}/api/purpose`).then(r => r.json()),

  // Search — returns raw Response for SSE
  searchStream: async (file) => {
    const { access } = getTokens();
    const form = new FormData();
    form.append('file', file);
    return fetch(`${BASE_URL}/api/search`, {
      method: 'POST',
      headers: access ? { Authorization: `Bearer ${access}` } : {},
      body: form,
    });
  },

  // Download
  downloadFile: (fileId) => `${BASE_URL}/api/download/file/${fileId}`,
  thumbnailUrl: (fileId) => `${BASE_URL}/api/download/thumbnail/${fileId}`,

  downloadZip: (fileIds) =>
    request('/api/download/zip', {
      method: 'POST',
      body: JSON.stringify({ file_ids: fileIds }),
    }),

  // Admin
  getConfig: () => request('/api/admin/config'),
  updateConfig: (data) => request('/api/admin/config', { method: 'PUT', body: JSON.stringify(data) }),
  getUsers: () => request('/api/admin/users'),
  createUser: (data) => request('/api/admin/users', { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id, data) => request(`/api/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteUser: (id) => request(`/api/admin/users/${id}`, { method: 'DELETE' }),
  getInviteCodes: () => request('/api/admin/invite-codes'),
  createInviteCode: (data) => request('/api/admin/invite-codes', { method: 'POST', body: JSON.stringify(data) }),
  getAuditLogs: (limit = 100) => request(`/api/admin/audit-logs?limit=${limit}`),
  getIndexStats: () => request('/api/admin/index-stats'),
  getCacheStatus: () => request('/api/cache/status'),
  refreshCache: (full = false) => request(`/api/cache/refresh?full=${full}`, { method: 'POST' }),

  setTokens,
};
