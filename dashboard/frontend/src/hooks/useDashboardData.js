import { useCallback, useEffect, useState } from 'react';
import * as api from '../services/api.js';
import usePolling from './usePolling.js';

export const emptyCases = { items: [], total: 0, pageSize: 20 };

export default function useDashboardData({ user, view, filters, historyPage, paused, setUser }) {
  const [data, setData] = useState(null);
  const [cases, setCases] = useState(emptyCases);
  const [history, setHistory] = useState({ items: [], total: 0 });
  const [revision, setRevision] = useState(0);
  const [search, setSearch] = useState(filters.search);
  const enabled = Boolean(user && !user.mustChangePassword && !paused);
  const running = Boolean(data?.busy || data?.activeRun);
  const interval = running ? 2000 : 15000;

  useEffect(() => {
    setData(null);
    setCases(emptyCases);
    setHistory({ items: [], total: 0 });
  }, [user]);

  useEffect(() => {
    const timer = setTimeout(() => setSearch(filters.search), 350);
    return () => clearTimeout(timer);
  }, [filters.search]);

  const loadDashboard = useCallback(async (signal) => {
    const result = await api.getDashboard(signal);
    if (!signal.aborted) setData(result);
  }, [user, revision]);

  // Search only reloads the test list. It does not reload the dashboard.
  const inventoryView = view === 'all' || Boolean(data?.modules.some((module) => module.name === view));
  const module = view === 'all' ? filters.module : view;
  const loadCases = useCallback(async (signal) => {
    const params = {
      search,
      module,
      category: filters.category,
      status: filters.status,
      page: filters.page,
      page_size: 20,
    };
    const result = await api.getTests(params, signal);
    if (!signal.aborted) setCases(result);
  }, [user, search, module, filters.category, filters.status, filters.page, revision]);

  const loadHistory = useCallback(async (signal) => {
    const result = await api.getRuns(historyPage, signal);
    if (!signal.aborted) setHistory(result);
  }, [user, historyPage, revision]);

  const searchReady = search === filters.search;
  const historyView = view === 'history' || view === 'reports';
  const dashboardError = usePolling(loadDashboard, { enabled, interval });
  const casesError = usePolling(loadCases, { enabled: enabled && inventoryView && searchReady, interval });
  const historyError = usePolling(loadHistory, { enabled: enabled && historyView, interval });
  const failure = dashboardError || casesError || historyError;

  useEffect(() => {
    if ([dashboardError, casesError, historyError].some((error) => error?.status === 401)) setUser(null);
  }, [dashboardError, casesError, historyError, setUser]);

  // A sync or new run reloads all visible data immediately.
  const refreshData = useCallback(() => setRevision((value) => value + 1), []);
  return { data, cases, setCases, history, connectionError: failure?.message || '', refreshData };
}
