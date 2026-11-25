import Icon from './Icon.jsx';

const cards = [
  { key: 'total', label: 'Total Tests', icon: 'layers', tone: 'total' },
  { key: 'passed', label: 'Passed', icon: 'check', tone: 'passed' },
  { key: 'failed', label: 'Failed', icon: 'close', tone: 'failed' },
  { key: 'error', label: 'Error', icon: 'alert', tone: 'failed' },
  { key: 'skipped', label: 'Skipped', icon: 'skip', tone: 'skipped' },
  { key: 'notExecuted', label: 'Not Executed', icon: 'clock', tone: 'not-executed' },
];

export default function StatCards({ stats }) {
  return (
    <section className="stats-grid" aria-label="Test result summary">
      {cards.map((card) => (
        <article key={card.key} className={'stat-card stat-' + card.tone}>
          <span className="stat-icon"><Icon name={card.icon} size={34} strokeWidth={card.key === 'passed' || card.key === 'failed' ? 3 : 1.9} /></span>
          <div className="stat-content"><h2>{card.label}</h2><p>{stats[card.key] || 0}</p></div>
        </article>
      ))}
    </section>
  );
}
