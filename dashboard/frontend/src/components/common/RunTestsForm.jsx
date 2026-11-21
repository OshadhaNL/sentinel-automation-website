import { useEffect, useState } from 'react';
import Icon from './Icon.jsx';
import { previewRun } from '../../services/api.js';

export default function RunTestsForm({ moduleName, testCase, modules, isMock, onRun, onClose }) {
  const allSystems = !moduleName;
  const module = moduleName || 'All Systems';
  const showCameraOptions = allSystems || module === 'Onboarding';
  const [scope, setScope] = useState('All Tests');
  const [browserMode, setBrowserMode] = useState('Headless');
  const [workers, setWorkers] = useState(1);
  const [cameraMode, setCameraMode] = useState('Exclude real camera');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [recommendation, setRecommendation] = useState(null);
  const [previewError, setPreviewError] = useState('');

  const scopeType = testCase ? 'test' : allSystems ? 'all' : 'module';
  const scopeValue = testCase ? testCase.code : allSystems ? null : module;
  const selection = !testCase && scope === 'Happy Path' ? 'positive' : 'all';
  const camera = showCameraOptions ? { 'Exclude real camera': 'exclude', 'Include real camera': 'include', 'Real camera tests only': 'only' }[cameraMode] : 'exclude';

  useEffect(() => {
    let alive = true;
    setRecommendation(null);
    setPreviewError('');
    previewRun({ scope_type: scopeType, scope_value: scopeValue, selection, camera_mode: camera })
      .then((result) => { if (alive) setRecommendation(result); })
      .catch((failure) => { if (alive) setPreviewError(failure.message); });
    return () => { alive = false; };
  }, [scopeType, scopeValue, selection, camera]);

  async function submit(event) {
    event.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    setError('');
    try {
      await onRun({
        scope_type: scopeType,
        scope_value: scopeValue,
        selection,
        browser_mode: browserMode.toLowerCase(),
        workers: Number(workers),
        camera_mode: camera,
      });
    } catch (failure) { setError(failure.message); setSubmitting(false); }
  }

  return (
    <form className="run-tests-form" onSubmit={submit} aria-busy={submitting}>
      <div className="form-field">
        <label htmlFor="execution-module">Execution scope</label>
        <input id="execution-module" className="execution-module-name" value={testCase ? testCase.code + ' · ' + testCase.name : allSystems ? 'All Systems (' + modules.length + ' modules)' : module} readOnly />
        {allSystems && <p className="field-help">One run across {modules.map((item) => item.name).join(', ')}.</p>}
      </div>
      <fieldset className="execution-options" disabled={submitting || Boolean(testCase)}>
        <legend>Test selection</legend>
        <div className="execution-options-row">
          <label><input type="radio" name="testScope" value="All Tests" checked={scope === 'All Tests'} onChange={(event) => setScope(event.target.value)} />All Tests</label>
          <label><input type="radio" name="testScope" value="Happy Path" checked={scope === 'Happy Path'} onChange={(event) => setScope(event.target.value)} />Happy Path</label>
        </div>
        <p className="field-help">{allSystems ? 'Happy Path selects positive tests across all modules.' : 'Happy Path selects positive tests in this module.'}</p>
      </fieldset>
      <fieldset className="execution-options">
        <legend>Browser mode</legend>
        <div className="execution-options-row">
          <label><input type="radio" name="browserMode" value="Headed" checked={browserMode === 'Headed'} onChange={(event) => setBrowserMode(event.target.value)} />Headed</label>
          <label><input type="radio" name="browserMode" value="Headless" checked={browserMode === 'Headless'} onChange={(event) => setBrowserMode(event.target.value)} />Headless</label>
        </div>
      </fieldset>
      <div className="form-field">
        <label htmlFor="execution-workers">Workers</label>
        <input id="execution-workers" type="number" min="1" max="32" step="1" required value={workers} onChange={(event) => setWorkers(event.target.value)} disabled={submitting} aria-describedby="worker-tip" />
        <p className="field-help">1 runs tests sequentially. A higher number runs tests in parallel, up to 32 workers.{isMock && ' Mock mode only simulates results.'}</p>
        <div id="worker-tip" className="worker-tip" aria-live="polite">
          {recommendation ? <>
            <strong>{recommendation.selectedCount} selected tests: try {recommendation.recommendedWorkers} {recommendation.recommendedWorkers === 1 ? 'worker' : 'workers'}.</strong>
            <p>{recommendation.reason} Based on the synced inventory.</p>
            <button type="button" className="text-button" disabled={submitting || Number(workers) === recommendation.recommendedWorkers} onClick={() => setWorkers(recommendation.recommendedWorkers)}>Use recommendation</button>
          </> : <p>{previewError || 'Checking selected tests...'}</p>}
        </div>
      </div>
      {showCameraOptions && <fieldset className="execution-options">
        <legend>Camera tests</legend>
        <div className="execution-options-column">
          <label><input type="radio" name="cameraMode" value="Exclude real camera" checked={cameraMode === 'Exclude real camera'} onChange={(event) => setCameraMode(event.target.value)} />Exclude real camera <span className="recommended-label">Recommended</span></label>
          <label><input type="radio" name="cameraMode" value="Include real camera" checked={cameraMode === 'Include real camera'} onChange={(event) => setCameraMode(event.target.value)} />Include real camera</label>
          <label><input type="radio" name="cameraMode" value="Real camera tests only" checked={cameraMode === 'Real camera tests only'} onChange={(event) => setCameraMode(event.target.value)} />Real camera tests only</label>
        </div>
        <p className="field-help">Applies within the selected test scope. Real camera tests only excludes tests without a real camera tag. Camera tests require a camera-enabled execution environment.</p>
      </fieldset>}
      {isMock && <p className="execution-demo-note"><Icon name="sample" size={18} /><span>Mock mode: this run will produce clearly labeled simulated results, not real automation results.</span></p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="form-actions"><button type="button" className="secondary-button" onClick={onClose} disabled={submitting}>Cancel</button><button type="submit" className="primary-button" disabled={submitting}><Icon name="play" size={17} />{submitting ? 'Starting…' : allSystems ? 'Run All Systems' : 'Run Tests'}</button></div>
    </form>
  );
}
