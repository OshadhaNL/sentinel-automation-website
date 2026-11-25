import { useEffect, useState } from 'react';
import { getAudit } from '../../services/api.js';
import { formatDate } from '../../data/dashboard.js';

export default function AuditHistory() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0 });
  const [error, setError] = useState('');
  useEffect(() => {
    let alive = true;
    getAudit(page).then((result) => { if (alive) { setData(result); setError(''); } }).catch((failure) => { if (alive) setError(failure.message); });
    return () => { alive = false; };
  }, [page]);
  return <section className="panel"><div className="panel-heading"><h2>Security audit history</h2></div>
    {error && <p className="form-error">{error}</p>}
    <div className="table-scroll"><table><thead><tr><th>Time</th><th>Action</th><th>By</th><th>Account</th></tr></thead><tbody>{data.items.map((event) => <tr key={event.id}><td>{formatDate(event.createdAt)}</td><td>{event.action.replaceAll('_', ' ')}</td><td>{event.actor}</td><td>{event.target}</td></tr>)}</tbody></table></div>
    <div className="pagination"><button className="secondary-button" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button><span>Page {page}</span><button className="secondary-button" disabled={page * 30 >= data.total} onClick={() => setPage(page + 1)}>Next</button></div>
  </section>;
}
