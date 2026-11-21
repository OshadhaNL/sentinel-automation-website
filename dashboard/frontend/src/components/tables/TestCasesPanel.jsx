import StatusBadge from '../common/StatusBadge.jsx';
import Icon from '../common/Icon.jsx';

export default function TestCasesPanel({ data, filters, onFilter, modules, moduleName, user, onDetails, onRun, busy }) {
  return <section className="panel test-cases-panel">
    <div className="panel-heading"><h2>Test cases</h2><span className="muted">{data.total} tests</span></div>
    <div className="test-filters">
      <input aria-label="Search test cases" type="search" placeholder="Search by test ID or name" value={filters.search} onChange={(event) => onFilter('search', event.target.value)} />
      {!moduleName && <select aria-label="Filter module" value={filters.module} onChange={(event) => onFilter('module', event.target.value)}><option value="">All Modules</option>{modules.map((module) => <option key={module.name}>{module.name}</option>)}</select>}
      <select aria-label="Filter type" value={filters.category} onChange={(event) => onFilter('category', event.target.value)}><option value="">All Types</option><option>Positive</option><option>Negative</option><option>Unclassified</option></select>
      <select aria-label="Filter result" value={filters.status} onChange={(event) => onFilter('status', event.target.value)}><option value="">All Results</option>{['Passed', 'Failed', 'Skipped', 'Error', 'Not Executed', 'Not Run'].map((status) => <option key={status}>{status}</option>)}</select>
    </div>
    {!data.items.length ? <div className="empty-state"><h3>No matching tests</h3><p>Try changing the filters or synchronize the inventory.</p></div> : <div className="table-scroll" tabIndex={0} role="region" aria-label="Test cases and recent results"><table><thead><tr><th>Test case</th><th>Type</th><th>Executions</th><th>Latest</th><th>Previous 1</th><th>Previous 2</th><th>Action</th></tr></thead><tbody>{data.items.map((test) => <tr key={test.id}>
      <td className="test-name-cell"><button className="run-link" onClick={() => onDetails(test.id)}>{test.code}</button><small>{test.name}</small><span className="muted">{test.module}</span></td><td>{test.category}</td><td>{test.executionCount}</td>
      {[0, 1, 2].map((position) => <td key={position}>{test.recentResults[position] ? <StatusBadge status={test.recentResults[position].status} /> : position === 0 ? <StatusBadge status="Not Run" /> : '—'}</td>)}
      <td><div className="test-actions"><button className="icon-button" aria-label={'View ' + test.code} onClick={() => onDetails(test.id)}><Icon name="eye" size={18} /></button>{user.role === 'tester' && <button className="table-run-button" disabled={busy} onClick={() => onRun(test)}><Icon name="play" size={15} />Run</button>}</div></td>
    </tr>)}</tbody></table></div>}
    <div className="pagination"><button className="secondary-button" disabled={filters.page <= 1} onClick={() => onFilter('page', filters.page - 1)}>Previous</button><span>Page {filters.page} of {Math.max(1, Math.ceil(data.total / data.pageSize))}</span><button className="secondary-button" disabled={filters.page * data.pageSize >= data.total} onClick={() => onFilter('page', filters.page + 1)}>Next</button></div>
  </section>;
}
