import { useState } from 'react';

export default function ModuleDistribution({ modules, total, onSelect }) {
  const [hovered, setHovered] = useState(null);
  let offset = 0;
  const circumference = 2 * Math.PI * 80;

  return (
    <section className="panel distribution-panel">
      <h2>Module Distribution ({total} Tests)</h2>
      <div className="distribution-body">
        <div className="donut-wrap">
          <svg viewBox="0 0 220 220" role="img" aria-label={'Distribution of ' + total + ' sample tests across seven modules'}>
            <title>Module distribution</title>
            <g transform="rotate(-90 110 110)">
              {modules.map((module) => {
                const length = module.total / total * circumference;
                const currentOffset = offset;
                offset += length;
                return <circle key={module.name} cx="110" cy="110" r="80" fill="none" stroke={module.color} strokeWidth="40"
                  strokeDasharray={length + ' ' + circumference} strokeDashoffset={-currentOffset}
                  className={hovered && hovered !== module.name ? 'segment-muted' : 'donut-segment'}
                  onMouseEnter={() => setHovered(module.name)} onMouseLeave={() => setHovered(null)}>
                  <title>{module.name + ': ' + module.total + ' tests'}</title>
                </circle>;
              })}
            </g>
          </svg>
          <div className="donut-label" aria-hidden="true">
            <strong>{hovered ? modules.find((module) => module.name === hovered).total : total}</strong>
            <span>{hovered || 'Tests'}</span>
          </div>
        </div>
        <ul className="chart-legend">
          {modules.map((module) => (
            <li key={module.name}>
              <button onClick={() => onSelect(module.name)}
                onMouseEnter={() => setHovered(module.name)} onMouseLeave={() => setHovered(null)}
                onFocus={() => setHovered(module.name)} onBlur={() => setHovered(null)}>
                <span className="legend-swatch" style={{ background: module.color }} />
                <span>{module.name} ({module.total})</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
