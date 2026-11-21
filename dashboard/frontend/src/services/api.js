async function request(path, options = {}) {
  let response;
  try {
    response = await fetch('/api' + path, {
      credentials: 'include',
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
  } catch {
    throw new Error('Backend unavailable. Start FastAPI and check the database configuration.');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.map((error) => error.msg).join(' ') : body.detail;
    const error = new Error(detail || 'The request failed. Check that the backend is running.');
    error.status = response.status;
    throw error;
  }
  return response.status === 204 ? null : response.json();
}

export const login = (email, password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
export const logout = () => request('/auth/logout', { method: 'POST' });
export const getMe = () => request('/auth/me');
export const getDashboard = () => request('/dashboard');
export const getTesters = () => request('/testers');
export const createTester = (details) => request('/testers', { method: 'POST', body: JSON.stringify(details) });
export const discoverTests = () => request('/discovery', { method: 'POST' });
export const getTests = (filters) => request('/tests?' + new URLSearchParams(filters));
export const getTest = (id) => request('/tests/' + id);
export const getRun = (id) => request('/runs/' + id);
export const getRuns = (page = 1) => request('/runs?page=' + page);
export const startRun = (settings) => request('/runs', { method: 'POST', body: JSON.stringify(settings) });
export const previewRun = (settings) => request('/runs/preview', { method: 'POST', body: JSON.stringify(settings) });
