from html import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle

from app.services.history import run_profile


def generate_reports(db, run, settings):
    data = run_profile(db, run, details=True)
    folder = settings.reports_root / run.id
    folder.mkdir(parents=True, exist_ok=True)
    label = 'MOCK EXECUTION - SIMULATED RESULTS' if run.is_mock else 'Pytest execution'
    metadata = f"{data['module']} / {data['scope']} | {data['mode']} | Workers: {data['workers']} | Camera: {data['cameraMode']} | {data['tester']} | {data['executedAt']}"
    rows = ''.join('<tr>' + ''.join(f'<td>{escape(str(value or ""))}</td>' for value in
                                  [result['code'], result['name'], result['status'], result['duration'], result['error']]) + '</tr>' for result in data['results'])
    html = f'''<!doctype html><html><head><meta charset="utf-8"><title>Sentinel {escape(run.id)}</title>
<style>body{{font:15px Arial,sans-serif;color:#111827;margin:32px}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:9px;text-align:left;overflow-wrap:anywhere}}th{{background:#fce7f3}}.label{{color:#ad1f68}}p{{overflow-wrap:anywhere}}</style></head><body>
<h1>Sentinel Execution Report</h1><h2 class="label">{escape(label)}</h2><p>Run: {run.id}</p><p>{escape(metadata)}</p>
<p>Run status: {escape(run.status)}</p><p>{escape(str(data['summary']))}</p><p>{escape(run.error_message or '')}</p>
<table><thead><tr><th>Test ID</th><th>Test name</th><th>Outcome</th><th>Seconds</th><th>Failure details</th></tr></thead><tbody>{rows}</tbody></table></body></html>'''
    html_path = folder / 'report.html'
    pdf_path = folder / 'report.pdf'
    html_path.write_text(html, encoding='utf-8')
    run.html_report_path = str(html_path)
    db.commit()
    styles = getSampleStyleSheet()
    story = [Paragraph('Sentinel Execution Report', styles['Title']), Paragraph(escape(label), styles['Heading2']),
             Paragraph(escape(run.id), styles['BodyText']), Paragraph(escape(metadata), styles['BodyText']),
             Paragraph(escape(f'Run status: {run.status}'), styles['BodyText']),
             Paragraph(escape(str(data['summary'])), styles['BodyText']), Spacer(1, 16)]
    if run.error_message:
        story += [Paragraph(escape(run.error_message), styles['BodyText']), Spacer(1, 10)]
    table_rows = [['Test ID / Name', 'Result', 'Seconds']]
    for result in data['results']:
        text = escape(result['code'] + ' / ' + result['name'][:250])
        if result['error']:
            text += '<br/>' + escape(result['error'][:1200])
            if len(result['error']) > 1200:
                text += '<br/>Full failure details are available in the HTML report.'
        table_rows.append([Paragraph(text, styles['BodyText']), result['status'], str(round(result['duration'], 2))])
    table = LongTable(table_rows, colWidths=[330, 95, 65], repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#FCE7F3')),
                               ('GRID', (0, 0), (-1, -1), .4, colors.lightgrey), ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(table)
    SimpleDocTemplate(str(pdf_path)).build(story)
    run.html_report_path = str(html_path)
    run.pdf_report_path = str(pdf_path)
    db.commit()
