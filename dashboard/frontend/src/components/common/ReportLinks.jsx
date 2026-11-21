export default function ReportLinks({ run }) {
  return <span className="report-links">
    {run.htmlReport && <a href={'/api/runs/' + (run.runId || run.id) + '/reports/html?download=false'} target="_blank" rel="noopener noreferrer">HTML</a>}
    {run.pdfReport && <a href={'/api/runs/' + (run.runId || run.id) + '/reports/pdf'}>PDF</a>}
    {!run.htmlReport && !run.pdfReport && <span className="muted">Pending</span>}
  </span>;
}
