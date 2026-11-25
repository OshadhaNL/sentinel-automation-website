import StatusBadge from './StatusBadge.jsx';
import ReportLinks from './ReportLinks.jsx';
import { formatDate } from '../../data/dashboard.js';
import { browserLabel } from '../../data/browsers.js';

export default function TestCaseDetails({ test }) {
  return <div className="test-detail-content">
    <h3>{test.code} · {test.name}</h3>
    <p className="muted">{test.module} · {test.category} · {test.executionCount} recorded executions</p>
    {test.isMock && <p className="execution-demo-note">Mock test case — results are simulated.</p>}
    <details><summary>Pytest identity</summary><code className="node-id">{test.pytestNodeId}</code></details>
    <h3 className="history-heading">Latest four results</h3>
    {!test.recentResults.length ? <p>Not Run</p> : <div className="table-scroll" tabIndex={0} role="region" aria-label="Latest four test results"><table><thead><tr><th>Result</th><th>Executed by</th><th>Executed on</th><th>Browser</th><th>Mode</th><th>Duration</th><th>Reports</th></tr></thead><tbody>{test.recentResults.map((result) => <tr key={result.runId}><td><StatusBadge status={result.status} /></td><td>{result.tester}</td><td>{formatDate(result.executedAt)}</td><td>{result.browserLabel || browserLabel(result.browser)}</td><td>{result.mode}</td><td>{result.duration.toFixed(2)}s</td><td><ReportLinks run={result} /></td></tr>)}</tbody></table></div>}
  </div>;
}
