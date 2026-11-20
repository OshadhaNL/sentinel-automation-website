import { useState } from 'react';
import { modules } from '../../data/dashboard.js';
import Icon from './Icon.jsx';

export default function RunTestsForm({ moduleName, onClose }) {
  const allSystems = !moduleName;
  const module = moduleName || 'All Systems';
  const showCameraOptions = allSystems || module === 'Onboarding';
  const [scope, setScope] = useState('All Tests');
  const [browserMode, setBrowserMode] = useState('Headless');
  const [cameraMode, setCameraMode] = useState('Exclude real camera');
  const [preview, setPreview] = useState(false);

  if (preview) {
    return (
      <div className="execution-preview">
        <div className="execution-preview-heading" role="status"><Icon name="check" size={22} /><h3>Execution settings ready</h3></div>
        <dl className="run-details">
          <div><dt>Execution scope</dt><dd>{allSystems ? 'All Systems (' + modules.length + ' modules)' : module}</dd></div>
          <div><dt>Test selection</dt><dd>{scope}</dd></div>
          <div><dt>Browser mode</dt><dd>{browserMode}</dd></div>
          {showCameraOptions && <div><dt>Camera tests</dt><dd>{cameraMode}</dd></div>}
        </dl>
        <p className="execution-demo-note"><Icon name="sample" size={18} /><span>UI preview only. No tests have been started. Execution will be connected with the backend.</span></p>
        <div className="form-actions"><button className="secondary-button" onClick={() => setPreview(false)}>Back</button><button className="primary-button" onClick={onClose}>Done</button></div>
      </div>
    );
  }

  return (
    <form className="run-tests-form" onSubmit={(event) => { event.preventDefault(); setPreview(true); }}>
      <div className="form-field">
        <label htmlFor="execution-module">Execution scope</label>
        <input id="execution-module" className="execution-module-name" value={allSystems ? 'All Systems (' + modules.length + ' modules)' : module} readOnly />
        {allSystems && <p className="field-help">One run across {modules.map((item) => item.name).join(', ')}.</p>}
      </div>
      <fieldset className="execution-options">
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
      {showCameraOptions && <fieldset className="execution-options">
        <legend>Camera tests</legend>
        <div className="execution-options-column">
          <label><input type="radio" name="cameraMode" value="Exclude real camera" checked={cameraMode === 'Exclude real camera'} onChange={(event) => setCameraMode(event.target.value)} />Exclude real camera <span className="recommended-label">Recommended</span></label>
          <label><input type="radio" name="cameraMode" value="Include real camera" checked={cameraMode === 'Include real camera'} onChange={(event) => setCameraMode(event.target.value)} />Include real camera</label>
          <label><input type="radio" name="cameraMode" value="Real camera tests only" checked={cameraMode === 'Real camera tests only'} onChange={(event) => setCameraMode(event.target.value)} />Real camera tests only</label>
        </div>
        <p className="field-help">Applies within the selected test scope. Real camera tests only excludes tests without a real camera tag. Camera tests require a camera-enabled execution environment.</p>
      </fieldset>}
      <p className="execution-demo-note"><Icon name="sample" size={18} /><span>Frontend preview. Test execution is not connected yet.</span></p>
      <div className="form-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button type="submit" className="primary-button"><Icon name="play" size={17} />{allSystems ? 'Run All Systems' : 'Run Tests'}</button></div>
    </form>
  );
}
