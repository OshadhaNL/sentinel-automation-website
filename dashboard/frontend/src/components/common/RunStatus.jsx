import { useCallback, useState } from 'react';
import usePolling from '../../hooks/usePolling.js';
import { getRun } from '../../services/api.js';
import StatusBadge from './StatusBadge.jsx';
import ReportLinks from './ReportLinks.jsx';
import { formatDate } from '../../data/dashboard.js';
import { browserLabel } from '../../data/browsers.js';

export default function RunStatus({ runId }) {
  const [run, setRun] = useState(null);
  const [selectedRunId, setSelectedRunId] = useState(runId);
  const loadRun = useCallback(async (signal) => {
    const result = await getRun(selectedRunId, signal);
    if (!signal.aborted) setRun(result);
  }, [selectedRunId]);
  const batchRunning = run?.browserRuns?.some((item) => ['Pending', 'Running'].includes(item.status));
  const needsRefresh = !run || batchRunning || ['Pending', 'Running'].includes(run.status) || (!run.pdfReport && !run.error);
  const error = usePolling(loadRun, { interval: needsRefresh ? 2000 : null });
  return <div className="run-status-content">
    {error && <p role="alert" className="form-error">{error.message}</p>}
    {!run ? <p>Loading execution…</p> : <>
      {run.isMock && <p className="execution-demo-note">Mock execution — all outcomes below are simulated.</p>}
      {run.browserRuns?.length > 1 && <div className="form-field">
        <label htmlFor="browser-run">Browser run</label>
        <select id="browser-run" className="browser-run-select" value={selectedRunId} onChange={(event) => {
          setRun(null);
          setSelectedRunId(event.target.value);
        }}>
          {run.browserRuns.map((item) => <option key={item.id} value={item.id}>{browserLabel(item.browser)} — {item.status}</option>)}
        </select>
        <p className="field-help">Browsers run sequentially. Select a browser to view its progress and reports.</p>
      </div>}
      <h3>{run.label} · {run.status}</h3>
      <p className="panel-note">{run.module} · {run.scope} · {run.mode} · {run.tester}</p>
      <progress value={run.completed} max={Math.max(run.total, 1)} aria-label="Execution progress" />
      <p className="muted">Workers: {run.workers}</p>
      <p className="muted">Browser: {run.browserLabel || browserLabel(run.browser)}</p>
      <p className="muted">{run.completed} / {run.total} results recorded · {formatDate(run.executedAt)}</p>
      {run.error && <p className="form-error" role="alert">{run.error}</p>}
      <div className="run-report-row"><span>Execution reports</span><ReportLinks run={run} /></div>
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Individual test outcomes"><table><thead><tr><th>Test case</th><th>Outcome</th><th>Duration</th></tr></thead><tbody>{run.results.map((result) => <tr key={result.testCaseId}><td className="test-name-cell">{result.code}<small>{result.name}</small>{result.error && <details><summary>Details</summary><pre>{result.error}</pre></details>}</td><td><StatusBadge status={result.status} /></td><td>{result.duration.toFixed(2)}s</td></tr>)}</tbody></table></div>
    </>}
  </div>;
}
