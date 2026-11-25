async function request(path, options = {}) {
  let response;
  try {
    response = await fetch('/api' + path, {
      credentials: 'include',
      ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
  } catch (failure) {
    if (failure.name === 'AbortError') throw failure;
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
export const getMe = (signal) => request('/auth/me', { signal });
export const getDashboard = (signal) => request('/dashboard', { signal });
export const getTesters = (signal) => request('/testers', { signal });
export const createTester = (details) => request('/testers/outlook-draft', { method: 'POST', body: JSON.stringify(details) });
export const prepareOutlookDraft = (id) => request('/testers/' + id + '/outlook-draft', { method: 'POST' });
export const discoverTests = () => request('/discovery', { method: 'POST' });
export const getTests = (filters, signal) => request('/tests?' + new URLSearchParams(filters), { signal });
export const getTest = (id) => request('/tests/' + id);
export const getRun = (id, signal) => request('/runs/' + id, { signal });
export const getRuns = (page = 1, signal) => request('/runs?page=' + page, { signal });
export const startRun = (settings) => request('/runs', { method: 'POST', body: JSON.stringify(settings) });
export const previewRun = (settings) => request('/runs/preview', { method: 'POST', body: JSON.stringify(settings) });
export const acceptInvitation = (token, password) => request('/auth/invitations/accept', { method: 'POST', body: JSON.stringify({ token, password }) });
export const changePassword = (current_password, password) => request('/auth/password', { method: 'POST', body: JSON.stringify({ current_password, password }) });
export const setTesterStatus = (id, is_active) => request('/testers/' + id + '/status', { method: 'POST', body: JSON.stringify({ is_active }) });
export const resendInvitation = (id) => request('/testers/' + id + '/invite', { method: 'POST' });
export const getAudit = (page = 1) => request('/audit?page=' + page);
