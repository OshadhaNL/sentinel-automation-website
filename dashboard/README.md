# Sentinel Automation Dashboard

React + Vite + JavaScript frontend, FastAPI backend, SQLAlchemy, and PostgreSQL.

Start with the [backend setup guide](backend/README.md) to create the database, configure [.env.example](.env.example), provision initial accounts, install dependencies, and start the API.

Then, from [frontend](frontend):

```powershell
npm install
npm run dev
```

Vite proxies API requests to FastAPI on port 8000. Restart Vite if it was running before the backend proxy was configured.

## Features

- Database-backed admin and tester accounts, sign in/out, and persisted sessions.
- Admins create/view testers and review test statistics/history/reports; execution endpoints reject admin requests.
- Automatic pytest discovery before each run, stable test codes, parametrized identity, metadata updates, inactive removed tests, and preserved complete history.
- Test inventory with search/filter/pagination, execution counts, latest three outcomes, and latest four on test details.
- All Systems, module, and individual-test execution scopes; All Tests/Happy Path, Headed/Headless, and camera filters.
- Exactly one active execution; overlapping requests are rejected, not queued.
- Polling about every two seconds for progress and results.
- All selected tests receive one result per run, including Not Executed for unfinished selections. Statistics and execution counts are calculated from saved results.
- Protected HTML/PDF reports, including clearly labeled simulated reports in mock mode.
- Separate mock and pytest providers. Browser-only credential checks and sample dashboard counters have been removed.

## Verification

From [backend](backend):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

From [frontend](frontend):

```powershell
npm run build
```

Automated backend tests use isolated temporary SQLite databases. The application's normal runtime requires PostgreSQL; there is no automatic SQLite fallback.

The real automation framework is in [../testing](../testing). The backend loads its pytest integration externally without changing those source files. Discovery is verified independently of execution; camera and positive/negative classifications must be reviewed before enabling filtered real runs. See [the classification guide](backend/README.md#classifications).
