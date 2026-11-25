import { useState } from 'react';

export default function OutlookDraft({ draft, onClose }) {
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const query = 'to=' + encodeURIComponent(draft.to) + '&subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
  const outlookUrl = 'https://outlook.office.com/mail/deeplink/compose?' + query;
  const mailtoUrl = 'mailto:' + encodeURIComponent(draft.to) + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);

  return <div className="outlook-draft">
    <p className="tester-form-note">The account has been created. Review the email, open Outlook, then click Send there to deliver it.</p>
    <div className="form-field"><label htmlFor="draft-to">To</label><input id="draft-to" value={draft.to} readOnly /></div>
    <div className="form-field"><label htmlFor="draft-subject">Subject</label><input id="draft-subject" value={subject} onChange={(event) => setSubject(event.target.value)} maxLength={200} /></div>
    <div className="form-field"><label htmlFor="draft-body">Email content</label><textarea id="draft-body" value={body} onChange={(event) => setBody(event.target.value)} maxLength={4000} rows={16} /></div>
    <p className="field-help">The temporary password is shown only in this preview. If you close it, use Prepare welcome email in the tester list to generate a new one.</p>
    <p className="field-help">Outlook opens a draft; this dashboard cannot confirm whether you sent it. The email uses a plain-text sign-in link.</p>
    <div className="form-actions"><button type="button" className="secondary-button" onClick={onClose}>Close</button><a className="primary-button outlook-send-link" href={outlookUrl} target="_blank" rel="noreferrer">Send via Outlook</a></div>
    <a className="text-button" href={mailtoUrl}>Open in default email app instead</a>
  </div>;
}
