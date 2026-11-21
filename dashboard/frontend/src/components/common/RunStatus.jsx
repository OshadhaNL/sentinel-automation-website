import { useEffect, useState } from 'react';
import { getRun } from '../../services/api.js';
import StatusBadge from './StatusBadge.jsx';
import ReportLinks from './ReportLinks.jsx';
import { formatDate } from '../../data/dashboard.js';

export default function RunStatus({ runId }) {
  const [run, setRun] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    let timer;
    async function refresh() {
      try {
        const data = await getRun(runId);
        if (!alive) return;
        setRun(data);
        setError('');
        if (['Pending', 'Running'].includes(data.status) || (!data.pdfReport && !data.error)) timer = setTimeout(refresh, 2000);
      } catch (failure) { if (alive) setError(failure.message); }
    }
    refresh();
    return () => { alive = false; clearTimeout(timer); };
  }, [runId]);
  return <div className="run-status-content">
    {error && <p role="alert" className="form-error">{error}</p>}
    {!run ? <p>Loading execution…</p> : <>
      {run.isMock && <p className="execution-demo-note">Mock execution — all outcomes below are simulated.</p>}
      <h3>{run.label} · {run.status}</h3>
      <p className="panel-note">{run.module} · {run.scope} · {run.mode} · {run.tester}</p>
      <progress value={run.completed} max={Math.max(run.total, 1)} aria-label="Execution progress" />
      <p className="muted">Workers: {run.workers}</p>
      <p className="muted">{run.completed} / {run.total} results recorded · {formatDate(run.executedAt)}</p>
      {run.error && <p className="form-error" role="alert">{run.error}</p>}
      <div className="run-report-row"><span>Execution reports</span><ReportLinks run={run} /></div>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Individual test outcomes"><table><thead><tr><th>Test case</th><th>Outcome</th><th>Duration</th></tr></thead><tbody>{run.results.map((result) => <tr key={result.testCaseId}><td className="test-name-cell">{result.code}<small>{result.name}</small>{result.error && <details><summary>Details</summary><pre>{result.error}</pre></details>}</td><td><StatusBadge status={result.status} /></td><td>{result.duration.toFixed(2)}s</td></tr>)}</tbody></table></div>
    </>}
  </div>;
}
