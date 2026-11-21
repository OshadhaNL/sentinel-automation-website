# Sentinel Automation Website

The dashboard frontend is in [dashboard/frontend](dashboard/frontend) using React, Vite, JavaScript, and plain CSS. Its FastAPI + SQLAlchemy + PostgreSQL backend is in [dashboard/backend](dashboard/backend).

Follow the [backend setup guide](dashboard/backend/README.md) first to configure PostgreSQL and start the API on port 8000.

## Start the frontend

From this repository's root:

```powershell
cd dashboard/frontend
npm install
npm run dev
```

Open the local URL printed by Vite.

## Frontend source

- [App.jsx](dashboard/frontend/src/App.jsx): application shell and navigation.
- [Dashboard.jsx](dashboard/frontend/src/pages/tester/Dashboard.jsx): dashboard page.
- [global.css](dashboard/frontend/src/styles/global.css): supplied colour palette and responsive layout.
- [api.js](dashboard/frontend/src/services/api.js): requests to the backend.
- [Components](dashboard/frontend/src/components): header, sidebar, summary cards, chart, tables, and dialogs.

To verify the production build, run `npm run build` from `dashboard/frontend`.

See the [dashboard README](dashboard/README.md) for features and verification. The [testing](testing) framework is discovered through pytest; real execution is enabled through backend environment configuration after classifying test categories and camera dependencies.
