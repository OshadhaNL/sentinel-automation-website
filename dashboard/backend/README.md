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
