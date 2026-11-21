import StatusBadge from '../common/StatusBadge.jsx';
import { formatDate } from '../../data/dashboard.js';

export default function ExecutionsTable({ runs, onSelect }) {
  if (!runs.length) return <div className="empty-state"><h3>No executions yet</h3><p>Execution records will appear here after a tester starts a run.</p></div>;
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Execution results">
      <table className="executions-table">
        <thead><tr><th>Run ID</th><th>Execution</th><th>Executed On</th><th>Result</th></tr></thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td><button className="run-link" onClick={() => onSelect(run)} aria-label={'View execution ' + (run.label || run.id)}>{run.label || run.id}{run.isMock && <span className="mock-run-label">Mock</span>}</button></td>
              <td>{run.module} – {run.scope}</td>
              <td><time dateTime={run.executedAt}>{formatDate(run.executedAt)}</time></td>
              <td><StatusBadge status={run.result} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
