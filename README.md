# Sentinel Automation Website

The dashboard frontend is implemented in [dashboard/frontend](dashboard/frontend) using React, Vite, JavaScript, and plain CSS.

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
- [dashboard.js](dashboard/frontend/src/data/dashboard.js): clearly labeled sample data.
- [Components](dashboard/frontend/src/components): header, sidebar, summary cards, chart, tables, and dialogs.

To verify the production build, run `npm run build` from `dashboard/frontend`.

Backend development and automation integration follow later. See the [dashboard README](dashboard/README.md) for the current frontend scope.
