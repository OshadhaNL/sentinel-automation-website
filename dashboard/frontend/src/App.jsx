import { useEffect, useState } from 'react';
import Header from './components/layout/Header.jsx';
import Sidebar from './components/layout/Sidebar.jsx';
import Dashboard from './pages/tester/Dashboard.jsx';
import AdminDashboard from './pages/admin/AdminDashboard.jsx';
import Login from './pages/auth/Login.jsx';
import TesterManagement from './pages/admin/TesterManagement.jsx';
import CreateTesterForm from './components/common/CreateTesterForm.jsx';
import RunTestsForm from './components/common/RunTestsForm.jsx';
import Modal from './components/common/Modal.jsx';
import Icon from './components/common/Icon.jsx';
import ExecutionsTable from './components/tables/ExecutionsTable.jsx';
import TestCasesPanel from './components/tables/TestCasesPanel.jsx';
import TestCaseDetails from './components/common/TestCaseDetails.jsx';
import RunStatus from './components/common/RunStatus.jsx';
import * as api from './services/api.js';
import AcceptInvitation from './pages/auth/AcceptInvitation.jsx';
import SecuritySetup from './pages/auth/SecuritySetup.jsx';
import AuditHistory from './pages/admin/AuditHistory.jsx';
import useDashboardData, { emptyCases } from './hooks/useDashboardData.js';

const initialInviteToken = new URLSearchParams(window.location.hash.slice(1)).get('invite') || '';

const emptyFilters = { search: '', module: '', category: '', status: '', page: 1 };

export default function App() {
  const [user, setUser] = useState(null);
  const [inviteToken, setInviteToken] = useState(initialInviteToken);
  const [changingPassword, setChangingPassword] = useState(false);
  const [checkingSession, setCheckingSession] = useState(true);
  const [testers, setTesters] = useState([]);
  const [filters, setFilters] = useState(emptyFilters);
  const [historyPage, setHistoryPage] = useState(1);
  const [view, setView] = useState('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [modal, setModal] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [syncing, setSyncing] = useState(false);
  const { data, cases, setCases, history, connectionError, refreshData } = useDashboardData({
    user, view, filters, historyPage, paused: changingPassword || Boolean(inviteToken), setUser,
  });

  useEffect(() => {
    const controller = new AbortController();
    api.getMe(controller.signal).then((account) => {
      if (controller.signal.aborted) return;
      setUser(account);
      setView(account.role === 'admin' ? 'testers' : 'overview');
    }).catch(() => {}).finally(() => { if (!controller.signal.aborted) setCheckingSession(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (user?.role !== 'admin' || user.mustChangePassword) return;
    const controller = new AbortController();
    api.getTesters(controller.signal).then((accounts) => {
      if (!controller.signal.aborted) setTesters(accounts);
    }).catch((failure) => { if (!controller.signal.aborted) setError(failure.message); });
    return () => controller.abort();
  }, [user]);

  function navigate(nextView) {
    setView(nextView);
    setFilters(emptyFilters);
    setCases(emptyCases);
    setHistoryPage(1);
    setSidebarOpen(false);
  }

  async function signOut() {
    try {
      await api.logout();
      setUser(null);
      setChangingPassword(false);
      setModal(null);
      setTesters([]);
      setNotice('');
      setError('');
      navigate('overview');
    } catch (failure) { setError(failure.message); }
  }

  async function synchronize() {
    setSyncing(true);
    setError('');
    try {
      const result = await api.discoverTests();
      setNotice(result.count + ' tests synchronized. Existing history was preserved.');
      refreshData();
    } catch (failure) { setError(failure.message); }
    finally { setSyncing(false); }
  }

  async function openTest(id) {
    try { setModal({ type: 'test', test: await api.getTest(id) }); }
    catch (failure) { setError(failure.message); }
  }

  async function runTests(settings) {
    const run = await api.startRun(settings);
    setModal({ type: 'run', id: run.id });
    refreshData();
  }

  if (inviteToken) return <AcceptInvitation token={inviteToken} onDone={() => { setInviteToken(''); window.history.replaceState(null, '', window.location.pathname); setUser(null); }} />;
  if (checkingSession) return <main className="connection-state">Checking your session…</main>;
  if (!user) return <Login onLogin={(account) => { navigate(account.role === 'admin' ? 'testers' : 'overview'); setError(''); setUser(account); }} />;
  if (user.mustChangePassword || changingPassword) return <SecuritySetup user={changingPassword ? { ...user, mustChangePassword: true } : user} onComplete={(account) => { setUser(account); setChangingPassword(false); }} onLogout={signOut} />;

  const modules = data?.modules || [];
  const selectedModule = modules.find((module) => module.name === view);
  const runs = selectedModule ? (data?.runs || []).filter((run) => run.modules.includes(view)) : data?.runs || [];
  const isAdmin = user.role === 'admin';
  const activeRun = data?.activeRun;
  const busy = Boolean(data?.busy || activeRun);
  const pageTitles = {
    overview: isAdmin ? 'Admin Dashboard' : 'Dashboard',
    all: 'All Systems',
    reports: 'Reports',
    history: 'Execution History',
    testers: 'Tester Management',
    audit: 'Security Audit',
  };
  const title = pageTitles[view] || view;
  const DashboardPage = isAdmin && view === 'overview' ? AdminDashboard : Dashboard;
  const isInventoryView = view === 'all' || Boolean(selectedModule);

  return <div className="app">
    <Header user={user} onLogout={signOut} onSecurity={() => setChangingPassword(true)} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
    <Sidebar user={user} modules={modules} view={view} onNavigate={navigate} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
    <main className="main-content">
      <div className="page-heading">
        <div><h1>{title}</h1><p>{isInventoryView ? 'Test inventory and latest results' : view === 'testers' ? 'Manage your tester accounts' : 'Test automation overview'}</p></div>
        <div className="page-heading-actions">
          {data?.provider === 'mock' && <span className="sample-label"><Icon name="sample" size={15} />Mock mode · Simulated executions</span>}
          {view !== 'testers' && <button className="secondary-button" disabled={syncing || busy} onClick={synchronize}>{syncing ? 'Synchronizing…' : 'Sync Tests'}</button>}
          {!isAdmin && isInventoryView && <button className="primary-button run-tests-button" disabled={busy || syncing} onClick={() => setModal({ type: 'execute', module: selectedModule?.name })}><Icon name="play" size={17} />{selectedModule ? 'Run ' + selectedModule.name + ' Tests' : 'Run All Systems'}</button>}
        </div>
      </div>
      {(error || connectionError) && <p className="form-error" role="alert">{error || connectionError}</p>}
      {notice && <div className="account-success" role="status"><Icon name="check" size={20} /><span>{notice}</span><button className="icon-button" aria-label="Dismiss confirmation" onClick={() => setNotice('')}><Icon name="close" size={18} /></button></div>}
      {data?.warnings?.map((warning) => <p className="inventory-warning" key={warning}>{warning}</p>)}
      {activeRun && <div className="execution-busy" role="status"><span>An execution is in progress. New requests will be rejected.</span><button className="text-button" onClick={() => setModal({ type: 'run', id: activeRun.id })}>View progress</button></div>}
      {!data ? <p className="empty-state">Connecting to the backend…</p> : <>
        {(view === 'overview' || selectedModule) && <DashboardPage stats={selectedModule || data.totals} modules={modules} runs={runs} selectedModule={selectedModule}
          testerCount={testers.length} onCreateTester={() => setModal({ type: 'createTester' })} onNavigate={navigate}
          onViewAll={() => navigate('history')} onSelectRun={(run) => setModal({ type: 'run', id: run.id })} />}
        {view === 'all' && <section className="panel inventory-panel">
          <div className="panel-heading"><h2>Modules</h2><span className="muted">{data.totals.total} discovered tests</span></div>
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Module inventory"><table className="inventory-table"><thead><tr><th>Module</th><th>Total Tests</th><th>Passed</th><th>Failed</th><th>Error</th><th>Skipped</th><th>Not Executed</th>{!isAdmin && <th>Action</th>}</tr></thead><tbody>
            {modules.map((module) => <tr key={module.name}><td><button className="module-link" onClick={() => navigate(module.name)}><Icon name={module.icon} size={20} />{module.name}</button></td><td>{module.total}</td><td>{module.passed}</td><td>{module.failed}</td><td>{module.error}</td><td>{module.skipped}</td><td>{module.notExecuted}</td>{!isAdmin && <td><button className="table-run-button" disabled={busy || syncing} aria-label={'Run ' + module.name + ' Tests'} onClick={() => setModal({ type: 'execute', module: module.name })}><Icon name="play" size={15} />Run Tests</button></td>}</tr>)}
          </tbody></table></div>
        </section>}
        {isInventoryView && <TestCasesPanel data={cases} filters={filters} modules={modules} moduleName={selectedModule?.name} user={user} busy={busy || syncing}
          onFilter={(name, value) => setFilters({ ...filters, [name]: value, page: name === 'page' ? value : 1 })}
          onDetails={openTest} onRun={(test) => setModal({ type: 'execute', module: test.module, test })} />}
        {view === 'testers' && isAdmin && <TesterManagement testers={testers} onCreate={() => setModal({ type: 'createTester' })} />}
        {view === 'audit' && isAdmin && <AuditHistory />}
        {(view === 'reports' || view === 'history') && <section className="panel reports-panel"><div className="panel-heading"><h2>{view === 'reports' ? 'Execution Reports' : 'Executions'}</h2></div><p className="panel-note">Select a run for its results and HTML/PDF reports. Run status is separate from individual test outcomes.</p>
          <ExecutionsTable runs={history.items} onSelect={(run) => setModal({ type: 'run', id: run.id })} />
          <div className="pagination"><button className="secondary-button" disabled={historyPage === 1} onClick={() => setHistoryPage(historyPage - 1)}>Previous</button><span>Page {historyPage}</span><button className="secondary-button" disabled={historyPage * 30 >= history.total} onClick={() => setHistoryPage(historyPage + 1)}>Next</button></div>
        </section>}
      </>}
    </main>
    {modal?.type === 'execute' && !isAdmin && <Modal key="execute" title="Execute Tests" onClose={() => setModal(null)}><RunTestsForm modules={modules} moduleName={modal.module} testCase={modal.test} isMock={data?.provider === 'mock'} onRun={runTests} onClose={() => setModal(null)} /></Modal>}
    {modal?.type === 'run' && <Modal key="run" wide title="Execution Details" onClose={() => setModal(null)}><RunStatus runId={modal.id} /></Modal>}
    {modal?.type === 'test' && <Modal key="test" wide title="Test Case Details" onClose={() => setModal(null)}><TestCaseDetails test={modal.test} /></Modal>}
    {modal?.type === 'createTester' && isAdmin && <Modal key="createTester" wide title="Invite Tester" onClose={() => setModal(null)}><CreateTesterForm onCancel={() => setModal(null)} onCreate={async (details) => {
      const tester = await api.createTester(details);
      setTesters(await api.getTesters());
      navigate('testers');
      setNotice(tester.name + ': ' + tester.message);
      return tester;
    }} /></Modal>}
  </div>;
}
