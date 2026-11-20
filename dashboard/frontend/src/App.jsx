import { useState } from 'react';
import Header from './components/layout/Header.jsx';
import Sidebar from './components/layout/Sidebar.jsx';
import Dashboard from './pages/tester/Dashboard.jsx';
import AdminDashboard from './pages/admin/AdminDashboard.jsx';
import Login from './pages/auth/Login.jsx';
import TesterManagement from './pages/admin/TesterManagement.jsx';
import CreateTesterForm from './components/common/CreateTesterForm.jsx';
import RunTestsForm from './components/common/RunTestsForm.jsx';
import { getDemoTesters, createDemoTester } from './services/demoAuth.js';
import Modal from './components/common/Modal.jsx';
import Icon from './components/common/Icon.jsx';
import StatusBadge from './components/common/StatusBadge.jsx';
import ExecutionsTable from './components/tables/ExecutionsTable.jsx';
import { modules, totals, executions, formatDate } from './data/dashboard.js';

export default function App() {
  const [user, setUser] = useState(null);
  const [testers, setTesters] = useState(getDemoTesters);
  const [accountNotice, setAccountNotice] = useState('');
  const [view, setView] = useState('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [modal, setModal] = useState(null);
  const selectedModule = modules.find((module) => module.name === view);
  const runs = selectedModule ? executions.filter((run) => run.module === view) : executions;
  const title = view === 'overview' ? (user?.role === 'admin' ? 'Admin Dashboard' : 'Dashboard') : view === 'all' ? 'All Systems' : view === 'reports' ? 'Reports' : view === 'testers' ? 'Tester Management' : view;
  const subtitle = view === 'overview' ? 'Test automation overview'
    : view === 'all' ? 'Test inventory across all modules'
    : view === 'reports' ? 'Execution reports and results'
    : view === 'testers' ? 'Manage your tester accounts'
    : view + ' test automation overview';

  function resetWorkspace() {
    setView('overview');
    setModal(null);
    setSidebarOpen(false);
    setAccountNotice('');
  }

  if (!user) return <Login onLogin={(account) => { resetWorkspace(); setUser(account); }} />;

  const DashboardPage = user.role === 'admin' && view === 'overview' ? AdminDashboard : Dashboard;

  return (
    <div className="app">
      <Header user={user} onLogout={() => { resetWorkspace(); setUser(null); }} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
      <Sidebar user={user} view={view} onNavigate={setView} open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <main id="main-content" className="main-content">
        <div className="page-heading">
          <div><h1>{title}</h1><p>{subtitle}</p></div>
          <div className="page-heading-actions">
            <span className="sample-label"><Icon name="sample" size={15} />Preview · Sample data</span>
            {user.role === 'tester' && (selectedModule || view === 'all') && <button className="primary-button run-tests-button" onClick={() => setModal({ type: 'execute', module: selectedModule?.name })}><Icon name="play" size={17} />{selectedModule ? 'Run ' + selectedModule.name + ' Tests' : 'Run All Systems'}</button>}
          </div>
        </div>
        {accountNotice && user.role === 'admin' && <div className="account-success" role="status"><Icon name="check" size={20} /><span>{accountNotice}</span><button className="icon-button" onClick={() => setAccountNotice('')} aria-label="Dismiss confirmation"><Icon name="close" size={18} /></button></div>}
        {(view === 'overview' || selectedModule) && (
          <DashboardPage stats={selectedModule || totals} modules={modules} runs={runs} selectedModule={selectedModule}
            testerCount={testers.length} onCreateTester={() => setModal({ type: 'createTester' })}
            onNavigate={setView} onViewAll={() => setModal({ type: 'history' })}
            onSelectRun={(run) => setModal({ type: 'run', run })} />
        )}
        {view === 'testers' && user.role === 'admin' && <TesterManagement testers={testers} onCreate={() => setModal({ type: 'createTester' })} />}
        {view === 'all' && (
          <section className="panel inventory-panel">
            <div className="panel-heading"><h2>Modules</h2><span className="muted">{totals.total} sample tests</span></div>
            <div className="table-scroll" tabIndex={0} role="region" aria-label="Module inventory">
              <table className="inventory-table">
                <thead><tr><th>Module</th><th>Total Tests</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Not Executed</th>{user.role === 'tester' && <th>Action</th>}</tr></thead>
                <tbody>{modules.map((module) => <tr key={module.name}>
                  <td><button className="module-link" onClick={() => setView(module.name)}><Icon name={module.icon} size={20} />{module.name}</button></td>
                  <td>{module.total}</td><td>{module.passed}</td><td>{module.failed}</td><td>{module.skipped}</td><td>{module.notExecuted}</td>
                  {user.role === 'tester' && <td><button className="table-run-button" aria-label={'Run ' + module.name + ' Tests'} onClick={() => setModal({ type: 'execute', module: module.name })}><Icon name="play" size={15} />Run Tests</button></td>}
                </tr>)}</tbody>
              </table>
            </div>
          </section>
        )}
        {view === 'reports' && <section className="panel reports-panel">
          <div className="panel-heading"><h2>Sample Executions</h2></div>
          <p className="panel-note">Select a run to review its sample details. HTML and PDF reports will be available after backend integration.</p>
          <ExecutionsTable runs={executions} onSelect={(run) => setModal({ type: 'run', run })} />
        </section>}
      </main>
      {modal?.type === 'execute' && user.role === 'tester' && <Modal title="Execute Tests" onClose={() => setModal(null)}><RunTestsForm moduleName={modal.module} onClose={() => setModal(null)} /></Modal>}
      {modal?.type === 'createTester' && user.role === 'admin' && <Modal title="Create Tester" onClose={() => setModal(null)}><CreateTesterForm onCancel={() => setModal(null)} onCreate={async (details) => {
        const tester = await createDemoTester(user, details);
        setTesters(getDemoTesters());
        setModal(null);
        setView('testers');
        setAccountNotice(tester.name + ' was created. They can now sign in to this demo.');
      }} /></Modal>}
      {modal?.type === 'history' && <Modal wide title={selectedModule ? selectedModule.name + ' Execution History' : 'Execution History'} onClose={() => setModal(null)}>
        <p className="modal-note">Sample data only · Times are shown in your local timezone.</p>
        <ExecutionsTable runs={runs} onSelect={(run) => setModal({ type: 'run', run })} />
      </Modal>}
      {modal?.type === 'run' && <Modal title={modal.run.id} onClose={() => setModal(null)}>
        <p className="modal-note">Sample execution · This test run was not executed.</p>
        <dl className="run-details">
          <div><dt>Execution</dt><dd>{modal.run.module} – {modal.run.scope}</dd></div>
          <div><dt>Run status</dt><dd>Completed</dd></div>
          <div><dt>Test outcome</dt><dd><StatusBadge status={modal.run.result} /></dd></div>
          <div><dt>Executed by</dt><dd>{modal.run.tester}</dd></div>
          <div><dt>Executed on</dt><dd>{formatDate(modal.run.executedAt)}</dd></div>
          <div><dt>Duration</dt><dd>{modal.run.duration}</dd></div>
          <div><dt>Browser mode</dt><dd>{modal.run.mode}</dd></div>
        </dl>
        <p className="report-notice"><Icon name="reports" size={19} />Reports will be available after backend integration.</p>
      </Modal>}
    </div>
  );
}
