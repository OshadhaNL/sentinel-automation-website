# Sentinel backend

FastAPI + SQLAlchemy + PostgreSQL. Run commands below from this backend folder.

## First-time setup

1. Install PostgreSQL and create a database and login. In PostgreSQL's SQL Shell, connected as a database administrator:

   ```sql
   CREATE USER sentinel WITH PASSWORD 'choose_a_database_password';
   CREATE DATABASE sentinel_dashboard OWNER sentinel;
   ```

2. Copy [../.env.example](../.env.example) to `../.env`. Set `DATABASE_URL` with the actual database password. Set `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `TESTER_EMAIL`, and `TESTER_PASSWORD` for the initial accounts. The previously requested local account emails are `admin@northlark.com` and `tester@northlark.com`; use `password123` for their environment passwords if retaining those local MVP credentials. Passwords are hashed before entering the database. The environment file is ignored by Git.

3. Create a dedicated backend environment; do not install backend dependencies into the automation environment:

   ```powershell
   py -3.13 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
   .\.venv\Scripts\python.exe -m app.setup
   ```

   The setup command creates tables and provisions accounts. It does not reset existing passwords or delete data. `requirements.txt` lists direct dependencies; the lockfile records the verified environment, including versions compatible with this Windows machine's Application Control policy.

4. Start exactly one API process:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
   ```

5. In another terminal, start the frontend from `../frontend` with `npm run dev`. Vite proxies `/api` to port 8000. If Vite was already running before the proxy was added, restart it. Sign in using an account provisioned above, then select **Sync Tests**. Runs also synchronize the inventory automatically before selecting tests.

Health: `http://127.0.0.1:8000/health`. API documentation: `http://127.0.0.1:8000/docs`.

## Execution providers

`EXECUTION_PROVIDER=mock` is the safe initial setting. It creates a small, explicitly mock inventory and stores simulated outcomes. Mock inventory and real inventory are separate; changing providers cannot apply simulated outcomes to real tests. Login and account management still use the real database in either mode.

To connect the real framework, set in `../.env`:

```env
EXECUTION_PROVIDER=pytest
AUTOMATION_ROOT=C:/absolute/path/to/sentinel-automation-full/testing
AUTOMATION_PYTHON=C:/absolute/path/to/sentinel-automation-full/testing/.venv/Scripts/python.exe
```

The runner uses that Python executable, the automation folder as working directory, and `tests/` as collection scope. It never collects backup test copies. Its plugin is loaded externally; no automation source files are edited. It clears inherited pytest addopts. Discovery always uses `-n 0`. The run dialog accepts 1–32 workers: 1 runs sequentially (`-n 0`), and higher values use pytest-xdist (`-n N`). Parallel runs require pytest-xdist in the automation environment; missing support is rejected before creating a run. The backend remains a single API process even when pytest uses multiple workers. There is no job queue. Another execution or synchronization is rejected with HTTP 409.

Worker counts are saved in `test_runs.workers` and returned in execution/history details and reports. Backend startup and `app.setup` add this column to an existing database automatically, assigning 1 to older runs. Mock runs save the setting but still produce simulated outcomes. Parallel tests must have independent accounts/data and resources; shared session fixtures can execute once per worker. Choose 1 for tests that share a physical camera or cannot run independently. See the [pytest-xdist worker documentation](https://pytest-xdist.readthedocs.io/en/stable/distribution.html).

The run dialog previews the selected count from the synced inventory using the same module/category/camera selection as the runner. `POST /api/runs/preview` is read-only and does not collect or execute tests. Its worker tip is a starting estimate (one worker per 20 tests, rounded up, capped at 8 and the server CPU count), not a performance measurement. A selection with real or unclassified camera dependencies recommends one worker. The user can apply the suggestion or keep a custom count.

Both discovery and real execution import the automation test modules. Test collection does not run test bodies, but ordinary Python import side effects can still occur. Collection has a 120-second timeout; execution has a one-hour timeout. Pytest exit code 1 can represent completed tests with failures, so it does not imply a failed-to-start run.

## Browser selection

The Execute Tests dialog accepts one or more browsers: Chromium (the existing
default), Google Chrome, Microsoft Edge, and WebKit. It applies Headed/Headless,
test selection, camera filtering, and the selected worker count to each browser.

Browsers in one request run sequentially under the same execution lock. Each
browser has its own run, outcomes, and HTML/PDF reports. The execution-details
dialog lets you switch between these runs. Other run/discovery requests remain
blocked until all selected browsers finish. A failed browser does not prevent
the remaining selected browsers from running.

Every browser run adds one recorded execution per selected test, including
Failed, Skipped, Error, and Not Executed. For example, 10 tests on three browsers
produce 30 result records. Test identities remain stable across browsers;
pytest's original Chromium parameter IDs remain inventory keys while the
runtime browser fixture uses the selected engine. Browser names are stored on
the run and shown next to results. Pending results still do not count.

Chrome and Edge must be installed on the execution PC. For the bundled
Chromium and WebKit engines, use the automation environment:

```powershell
.\testing\.venv\Scripts\python.exe -m playwright install chromium webkit
```

Run that command from the repository root. WebKit is Playwright's WebKit build,
not the Safari application. Camera permissions and other features differ by
engine; verify real-camera tests on each chosen browser. Tests must use the
standard pytest-playwright fixtures; browser choices cannot override a test
that manually launches a hard-coded browser.

The API accepts `browsers: ["chrome", "edge", "webkit"]` on `POST /api/runs`.
An omitted list preserves Chromium as the default. Empty, duplicate, and
unsupported browser lists are rejected. Startup adds browser/batch columns
without deleting existing runs; older runs are labelled Chromium. Restart the
backend after updating. Mock mode simulates each browser run without launching
real browsers.

## Classifications

Collection preserves each complete pytest node ID, including parameter identity. Modules are mapped from the existing test file organization. New tests are added automatically with a stable `TC-...` dashboard code; existing node IDs retain their code and complete history. Renaming/moving a test changes its node ID and currently creates a new inventory entry.

Happy Path means explicitly Positive tests. Recognized pytest markers: `positive`, `happy_path`, `negative`, and `real_camera`. A `test_negative_...` name also identifies a negative test. Other tests remain **Unclassified**; they are not silently declared positive.

For classifications without changing the framework, edit [test_metadata.json](test_metadata.json), using exact node IDs returned by discovery:

```json
{
  "tests/ui/test_login_page.py::TestLoginPage::test_login_heading": {
    "category": "Positive",
    "requires_real_camera": false
  },
  "tests/ui/test_individual_onboarding_page.py::TestIndividualOnboarding::test_capture_live_photo": {
    "category": "Positive",
    "requires_real_camera": true
  }
}
```

Supported override fields: `module`, `category`, `requires_real_camera`. Review helpers and fixtures as well as test bodies: document/review tests can require camera capture indirectly. Onboarding camera dependencies are deliberately unclassified until explicitly marked or overridden. A filtered run is rejected if its scope contains unclassified relevant tests. This prevents an unsafe or misleading partial selection.

Real camera execution additionally requires `REAL_CAMERA_AVAILABLE=1`, set only after verifying hardware, browser permissions, and the execution session. Headed mode alone does not prove camera availability. The runner does not change camera flags in the existing framework.

## Result and counting rules

- Successful full discovery updates metadata, inserts new tests, and marks missing tests inactive. Failed/incomplete collection leaves the previous inventory intact. No tests or history are deleted.
- Each accepted run persists its selected tests before starting. Each selected test gets exactly one final result: Passed, Failed, Skipped, Error, or Not Executed. An internal Pending placeholder is excluded from counts until a result is recorded.
- Test execution count is derived from these saved result rows. All outcomes count, including Not Executed. Tests outside the selected scope do not change. Busy or invalid requests create no run or result rows.
- The overview table queries the newest three outcomes. Details query the newest four. Complete history remains in the database.
- Unfinished selections become Not Executed after interruption, startup failure, or backend restart. Completed individual outcomes survive a restart.
- PostgreSQL grants an advisory lock for the backend lifetime, refusing a second backend process before recovery. Database and in-process execution locks reject overlapping jobs. Run one process; distributed execution is out of scope.
- Statistics use each active test's latest recorded outcome; counts are not manually incremented. Error is displayed separately. Never-run and Not Executed tests are included in the Not Executed summary card.

## Authentication and reports

Accounts use salted PBKDF2 password hashes. Authentication uses opaque, hashed, revocable database sessions and an HTTP-only SameSite cookie. Admin-only and tester-only endpoints enforce roles server-side. No public registration exists. Cookie sessions survive page reloads and backend restarts until expiration or logout.

### Invitations and account security

The admin UI now uses **manual Outlook welcome emails**. Enter the tester's name, company email, and designation, then select **Create account & preview email**. The backend creates an active tester with a random temporary password and returns an editable subject/body preview. **Send via Outlook** opens Outlook Web with the recipient, subject, and body; the admin must click Send in Outlook. A default-email-app link is also available. This flow needs no SMTP, Graph credentials, or extra service. It uses the Outlook account the admin is signed into and cannot confirm delivery. Email content is plain text with a sign-in URL, not an HTML login button.

The temporary password is hashed in the database and shown only in that preview. The tester must change it before accessing the dashboard. Closing the preview does not undo account creation. **Prepare welcome email** generates a replacement password for an account awaiting its first password change; it revokes old sessions and invalidates the previous password and invitation links. No plaintext password or email body is saved in audit history. The account's designation is saved and shown in the tester list. The application does not treat a manual email draft as proof of email ownership or delivery.

Set `PUBLIC_APP_URL` to the dashboard URL recipients can reach. Loopback URLs only work on the same computer. The manual UI uses `POST /api/testers/outlook-draft` and `POST /api/testers/{id}/outlook-draft`; direct automated invitation APIs below remain available separately.

- Admins invite testers using their name and company email. The account stays inactive until the tester accepts a single-use, 24-hour link and sets their own password. Tokens are stored only as SHA-256 hashes in the database. Resending or revoking an invitation invalidates the previous link.
- New passwords must have 6–128 characters. A small local blocklist rejects common/repeated passwords; this is not an exhaustive breached-password database. Existing accounts require a password update after the security migration. Starter credentials in the environment only provision accounts; changing them does not reset existing passwords.
- Only admin@northlark.com can be provisioned or authenticated as an administrator. Admin sign-in uses email and password; authenticator and recovery codes are not required. The tester invitation API cannot create admin accounts.
- Disabling a tester revokes all their sessions and outstanding invitations while retaining execution history. Admins can enable previously activated testers and resend pending invitations. Sessions also rotate on password change, revoking other sessions.
- The admin Security Audit page records account invitations, acceptance, status changes, password changes, and sign-in success/failure. Events identify users by database IDs, not credentials; passwords and invitation tokens are never stored in audit events. Audit events have no update/delete API. A database administrator can still modify the database; the log is not tamper-proof.

### Email configuration

No connector or ChatGPT plugin is required. The backend supports Microsoft Graph for company Microsoft 365 mailboxes, SMTP with verified TLS, and a local outbox. Configure these values in `dashboard/.env`:

```env
MAIL_MODE=outbox
PUBLIC_APP_URL=http://127.0.0.1:5173
MAIL_FROM=sentinel@northlark.com
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_SSL=0
```

`outbox` is an explicit local development mode: invitation messages are saved as `.eml` files under `storage/email_outbox`, and the UI states that no email was sent. Open the newest file locally and use its invitation link for development. Anyone able to read that file can use its link until it expires or is revoked. Keep the outbox private and remove expired messages as part of local housekeeping.

For real delivery set `MAIL_MODE=smtp` and fill in your provider's host, sender, and SMTP credentials. Port 587 uses STARTTLS; set `SMTP_SSL=1` for implicit TLS (usually port 465). The sender must be authorised by the provider. Use an HTTPS `PUBLIC_APP_URL` and `SECURE_COOKIES=1` for a hosted system. SMTP delivery failure rolls back the invitation and reports an error; it is not shown as sent.

The SMTP transport supports credentials or an authorised relay. SPF/DKIM/DMARC and sender-domain verification are configured with the email provider, not in this application.

### Microsoft 365 / Outlook company mailbox

The Graph transport uses application credentials and obtains its own access token for each invitation. It does not use a mailbox password or require an interactive Outlook login. No additional Python dependency is required. See Microsoft's [application authentication flow](https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow).

1. In the Microsoft Entra admin center, open **App registrations → New registration**. Create a single-tenant application named `Sentinel Dashboard Mail`.
2. Copy its **Directory (tenant) ID** and **Application (client) ID** from Overview.
3. Open **Certificates & secrets → Client secrets → New client secret**. Put the secret **Value** directly into the local environment file, not the secret ID. Track its expiry and replace it before expiration.
4. Ask the Microsoft 365/Exchange administrator to authorise the app for the chosen sender mailbox. Prefer the scoped `Application Mail.Send` role using [Exchange Application RBAC](https://learn.microsoft.com/en-us/exchange/permissions-exo/application-rbac). The administrator must register the enterprise service principal in Exchange, scope the role to the sender, and test its access. Avoid adding an unscoped Entra `Mail.Send` grant alongside scoped RBAC: those grants are additive and can allow other mailboxes.
5. Fill in the environment values below, set `MAIL_MODE=graph` only when ready, and restart the backend:

```env
MAIL_MODE=graph
MAIL_FROM=YOUR_ACTUAL_SENDER@northlark.com
MICROSOFT_TENANT_ID=YOUR_DIRECTORY_TENANT_ID
MICROSOFT_CLIENT_ID=YOUR_APPLICATION_CLIENT_ID
MICROSOFT_CLIENT_SECRET=YOUR_SECRET_VALUE
PUBLIC_APP_URL=http://127.0.0.1:5173
```

The sender must be an existing, authorised Microsoft 365 mailbox. The tenant and client IDs must be UUIDs. For testers on other computers, replace the loopback public URL with the dashboard address they can reach; use HTTPS when hosted. Keep secrets in the backend environment only.

The app submits mail through [Graph sendMail](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0). A successful response means Microsoft accepted the message for delivery, not that it reached the inbox. The UI reflects that distinction. Missing configuration, authentication failures, and rejected sends roll back the invitation without falling back to the outbox or SMTP. Real Microsoft delivery still needs a configured tenant and an invitation sent through the UI; automated tests use a mocked Microsoft service.

The new routes are `POST /api/auth/invitations/accept`, `POST /api/auth/password`, `POST /api/testers/{id}/invite`, `POST /api/testers/{id}/status`, and `GET /api/audit`. `POST /api/testers` now accepts only name/email and sends an invitation; it no longer accepts a password.

Account creation accepts only the exact `northlark.com` email domain, including initial accounts provisioned by `app.setup`. Addresses are trimmed and lowercased before validation and duplicate detection. External domains, subdomains, and suffix lookalikes are rejected by the backend as well as the account creation form. This validates the address domain; it does not verify mailbox ownership or change existing accounts.

Report URLs accept a run ID and a fixed HTML/PDF format, never an arbitrary path. Downloads require authentication. HTML reports escape test content and are served with a restrictive content security policy. Both reports include run settings, initiating tester, outcomes, and failure details. Mock reports are prominently labeled simulated.

For HTTPS deployment set `SECURE_COOKIES=1` and configure exact `FRONTEND_ORIGINS`. In production, route `/api` to FastAPI on the same site as the frontend. Vite's development proxy is not a deployment configuration.

## API

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `POST /api/auth/login` | Public | Sign in |
| `POST /api/auth/logout` | Cookie session | Revoke session |
| `GET /api/auth/me` | Signed in | Current account |
| `GET /api/testers` | Admin | Tester profiles |
| `POST /api/testers` | Admin | Create tester |
| `POST /api/discovery` | Signed in | Full inventory synchronization |
| `GET /api/dashboard` | Signed in | Modules, statistics, recent and current runs |
| `GET /api/tests` | Signed in | Search, filters, pagination, execution counts, newest three results |
| `GET /api/tests/{id}` | Signed in | Test metadata and newest four results |
| `POST /api/runs` | Tester | Start all/module/individual scope |
| `GET /api/runs` | Signed in | Paginated run history |
| `GET /api/runs/{id}` | Signed in | Progress, metadata, per-test outcomes |
| `GET /api/runs/{id}/reports/{html or pdf}` | Signed in | Protected report |

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests use a temporary SQLite database only for isolation, not as a runtime fallback. They exercise authentication, role enforcement, uniqueness, discovery, counts/latest results, all outcome states, busy rejection, restart recovery, persistence, protected reports, and a real subprocess running a disposable pytest suite. They do not execute the user's live Sentinel tests. PostgreSQL connectivity must also be verified after local database configuration.
