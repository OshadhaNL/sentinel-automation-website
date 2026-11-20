# Sentinel Automation Dashboard

Frontend dashboard built with React, Vite, JavaScript, and CSS. The backend is reserved for a later implementation.

## Run the frontend

Install a current Node.js LTS release, then run from this project directory:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite.

## Production build

```powershell
cd frontend
npm run build
npm run preview
```

## Current scope

- Responsive dashboard matching the supplied pink and neutral visual reference.
- Result summary cards, module distribution chart, and recent executions.
- Sidebar module summaries and All Systems inventory.
- Tester-only Run Tests controls on every module. Run All Systems selects all seven modules in one execution. Settings include Headed/Headless and All Tests/Happy Path (positive tests). Onboarding and All Systems also show camera options: exclude, include, or real-camera tests only. Camera-only selection filters the chosen scope to tests tagged for a real camera.
- Submitting execution settings displays a UI-only confirmation; it does not start tests, change statistics, or record execution results.
- Execution history and sample execution detail dialogs.
- Notification and tester profile popovers.
- All displayed inventory and execution records are explicitly labeled sample data.
- Login page with a frontend-only admin demo account and a tester preview.
- Admin dashboard with read-only test statistics, module coverage, and execution review.
- Admin-only tester management: create tester accounts, search and view profiles, and sign in as a created tester.
- Account menu with role, identity, and sign out. Reloading ends the demo session.
- No live authentication, actual test execution, or report generation is connected yet.

## Demo login

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@northlark.com` | `password123` |
| Tester | `tester@northlark.com` | `password123` |

The built-in tester is listed in admin tester management and remains available after reload. Accounts created through the form are cleared on reload.

These are public frontend demo credentials, checked in [demoAuth.js](frontend/src/services/demoAuth.js). They are not a provisioned database account or secure authentication. No password or session is saved to browser storage. Replace the demo adapter with backend authentication and password hashing before real deployment.

Admins can select **Create Tester** on their dashboard or open **Testers** in the sidebar. The form requires a name, unique email, password of at least eight characters, and password confirmation. Tester roles are fixed. Created testers can sign in after the admin signs out, in the same tab. Accounts survive sign out but are cleared on page reload. Tester passwords are salted and hashed in memory with Web Crypto; profiles never expose passwords or hashes. Only demo credentials should be used until the backend is connected.

Use **Explore tester preview** on the login page to view the existing tester dashboard.

Sample data lives in [frontend/src/data/dashboard.js](frontend/src/data/dashboard.js).
Colour tokens live in [frontend/src/styles/global.css](frontend/src/styles/global.css).
The reference module counts sum to 321; the sample Screening count is 35 so the inventory totals 324.

The existing automation project is unchanged. Future FastAPI integration will replace the frontend fixtures with authenticated API responses.

## Build compatibility

Rollup uses its official WebAssembly package because this Windows machine blocks the native Rollup binary through Application Control. The package alias and override are recorded in the frontend package manifest and lockfile.
