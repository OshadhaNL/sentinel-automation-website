# Sentinel Automation

This project uses **Python + Playwright + pytest** to automate testing of the Sentinel web application.

The framework includes:
- **UI Tests** — Check page elements, buttons, inputs, tables, and forms.
- **Functional Tests** — Check application workflows and functionality.
- **Page Objects** — Store locators and reusable actions separately from tests.

## 1. Project Setup (One-Time Only)

Follow these steps when setting up the project on a new laptop.

### Step 1 — Install Required Tools

Install:
- Python
- Git
- PyCharm or VS Code

Check the installations in PowerShell:

```powershell
python --version
git --version
```

### Step 2 — Clone the Project from GitHub

```powershell
git clone https://github.com/OshadhaNL/sentinel-automation.git
cd sentinel-automation
```

If the project is already on your laptop, simply open the `sentinel-automation` folder.

### Step 3 — Create a Virtual Environment

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

You should now see `(.venv)` in your terminal.

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Step 4 — Install Python Packages

```powershell
python -m pip install -r requirements.txt
```

If `requirements.txt` is not available yet:

```powershell
python -m pip install playwright pytest pytest-playwright python-dotenv requests pytest-html pytest-xdist
```

Install the Playwright Chromium browser:

```powershell
python -m playwright install chromium
```

### Step 5 — Configure Login Credentials

Create a `.env` file in the project root.

Add your QA login credentials:

```env
TEST_EMAIL=your-test-email
TEST_PASSWORD=your-test-password
```

Make sure `.env` is included in `.gitignore`. Never push credentials to GitHub.

### Step 6 — Check Everything

```powershell
python -m pytest --version
python -m playwright --version
python -m pip check
```

Your project is now ready.

---

## 2. Daily Commands (Use Every Day)

Open PowerShell in the `sentinel-automation` project folder.

### Activate the Virtual Environment

```powershell
.\.venv\Scripts\Activate.ps1
```

### Check Your Git Branch

```powershell
git branch
git status
```

### Get the Latest Changes

```powershell
git pull
```

### Run Your Tests

```powershell
python -m pytest tests/ui -v
```

### Deactivate the Virtual Environment

```powershell
deactivate
```

---

## 3. Run Automation Tests

### Run All Tests (Headless)

```powershell
python -m pytest -v
```

Headless means the browser runs without opening a visible window.

### Run All Tests (Visible Browser)

```powershell
python -m pytest -v --headed
```

### Run Only UI Tests

```powershell
python -m pytest tests/ui -v
```

### Run Only Functional Tests

```powershell
python -m pytest tests/functions -v
```

### Run Only Authentication Tests

```powershell
python -m pytest tests/auth -v
```

### Run a Specific Test File

Example — Transaction page:

```powershell
python -m pytest tests/ui/test_transaction_page.py -v
```

Example — Onboarding page:

```powershell
python -m pytest tests/ui/test_onboarding_page.py -v
```

### Run a Specific Test

```powershell
python -m pytest tests/ui/test_transaction_page.py -k "test_dates_sorted_ascending" -v
```

### Run Multiple Selected Tests

```powershell
python -m pytest tests/ui/test_transaction_page.py -k "search or sorting" -v
```

Replace `search` and `sorting` with keywords from your test names.

### Run Smoke Tests

```powershell
python -m pytest -m smoke -v
```

### Run Tests Slowly (For Debugging)

```powershell
python -m pytest tests/ui -v --headed --slowmo 500
```

### Run Tests in Parallel (Faster Execution)

```powershell
python -m pytest tests/ui -n 4 -v
```

This uses four parallel workers. Make sure `pytest-xdist` is installed.

### Run Tests and Show Print Statements

```powershell
python -m pytest tests/ui -v -s
```

### Stop After the First Failure

```powershell
python -m pytest tests/ui -x -v
```

### Show Only a Short Error Report

```powershell
python -m pytest tests/ui -v --tb=short
```

---

## 4. Generate HTML Test Reports

Create the reports folder once:

```powershell
New-Item -ItemType Directory -Force reports
```

### Run All Tests and Generate a Report

```powershell
python -m pytest -v --html=reports/report.html --self-contained-html
```

### Run UI Tests and Generate a Report

```powershell
python -m pytest tests/ui -v --html=reports/ui-report.html --self-contained-html
```

### Run Tests in Parallel and Generate a Report

```powershell
python -m pytest tests/ui -n 4 -v --html=reports/ui-report.html --self-contained-html
```

Open the generated HTML file from the `reports` folder to view the results.

---

## 5. GitHub Commands

Use these commands to save your automation changes to GitHub.

### Check Your Current Branch

```powershell
git branch
```

### Create a New Branch (One-Time Per Branch)

```powershell
git switch -c your-branch-name
```

### Switch to Your Branch

Example:

```powershell
git switch oshadha
```

### Check Changed Files

```powershell
git status
```

### Add Changed Files

```powershell
git add .
```

### Commit Changes

```powershell
git commit -m "Added transaction automation tests"
```

### Push Changes to GitHub

First push of a new branch:

```powershell
git push -u origin your-branch-name
```

For later pushes:

```powershell
git push
```

### Get Latest Changes

```powershell
git pull
```

### Merge Your Branch into Main

The recommended method is to create a **Pull Request on GitHub** and merge it after review.

Alternatively, to merge locally:

```powershell
git switch main
git pull origin main
git merge oshadha
git push origin main
```

Replace `oshadha` with your branch name if different. Resolve any merge conflicts before pushing.

---

## 6. Useful Troubleshooting Commands

### Check Python Version

```powershell
python --version
```

### Check Installed Packages

```powershell
python -m pip list
```

### Check for Broken Dependencies

```powershell
python -m pip check
```

### Reinstall Playwright Chromium

```powershell
python -m playwright install chromium
```

### Check Python Syntax Without Running Tests

```powershell
python -m py_compile tests/ui/test_transaction_page.py pages/transactionPage.py
```

### Check Test Collection

```powershell
python -m pytest --collect-only -q
```

### Show Detailed Errors

```powershell
python -m pytest -vv --tb=long
```

### Update Dependencies

After intentionally changing the project's installed packages:

```powershell
python -m pip freeze > requirements.txt
```

Review the changes before committing `requirements.txt`.

---

## 7. Project Folder Structure

```text
sentinel-automation/
│
├── config/             # Application settings
├── pages/              # Page locators and reusable actions
├── components/         # Reusable UI components
├── workflows/          # Reusable business workflows
├── utils/              # Helper functions
├── test_data/          # Test data
│
├── tests/
│   ├── ui/             # UI tests
│   ├── functions/      # Functional tests
│   └── auth/           # Authentication tests
│
├── reports/            # Test reports
├── .env                # Login credentials (do not commit)
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 8. Quick Command Cheat Sheet

| What you want to do | Command |
|---|---|
| Activate environment | `.\.venv\Scripts\Activate.ps1` |
| Run all tests | `python -m pytest -v` |
| Run tests with browser visible | `python -m pytest -v --headed` |
| Run UI tests | `python -m pytest tests/ui -v` |
| Run functional tests | `python -m pytest tests/functions -v` |
| Run tests in parallel | `python -m pytest -n 4 -v` |
| Run smoke tests | `python -m pytest -m smoke -v` |
| Generate HTML report | `python -m pytest -v --html=reports/report.html --self-contained-html` |
| Check branch | `git branch` |
| Check changes | `git status` |
| Get latest changes | `git pull` |
| Stage changes | `git add .` |
| Commit changes | `git commit -m "Your message"` |
| Push changes | `git push` |

---

## 9. Important Notes

- Always activate `.venv` before running tests.
- Run commands from the project root folder.
- Keep your `.env` file and passwords out of GitHub.
- Do not commit `.venv`, generated reports, or temporary test files.
- Use the QA/staging environment for automation testing.
- Keep locators and reusable actions in `pages/`.
- Keep test scenarios and assertions in `tests/`.
- Use a separate Git branch for your changes and merge into `main` through a Pull Request when ready.

## 10. Live QA coverage review (26 November 2026)

Additional scenarios are in [tests/ui/review](tests/ui/review). They cover
Settings, Access Control, invitations without sending, Profile Settings password
rules, Activity Logs, nine additional protected routes, and locally simulated
login HTTP/network failures. [pages/settingsPage.py](pages/settingsPage.py)
contains the shared Settings locators and navigation.

Use the existing `TEST_EMAIL` and `TEST_PASSWORD` environment variables for an
approved QA account with access to the Settings pages. Credentials are not
embedded in the tests. Run from this testing folder:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/review -q -n 0
```

Authenticated **read-only** review fixtures block all API methods other than GET, HEAD and
OPTIONS, and fail if a test attempts a write. Successful login is performed
once per browser/worker before that guard is installed. Login-failure tests
answer the login request locally, so they do not send failed attempts to the
real account. Each test receives an isolated browser context; authentication
state is held in memory, not a file. Read-only save/error checks use locally
intercepted responses; persisted accounts, passwords, signatures and tenant
settings are preserved. Real-data workflows require the separate opt-ins below.

Coverage outputs:

- [Existing/new test inventory](coverage/test_inventory.csv)
- [New scenarios and validation results](coverage/new_scenarios.csv)
- [Coverage gaps and prerequisites](coverage/coverage_gaps.csv)
- [Findings](coverage/findings.csv)
- [Shadowed existing definitions](coverage/shadowed_definitions.csv)

The profile-password mixed-case guidance currently accepts a dummy value with
no lowercase letters. Its regression assertion intentionally remains failing
while that UI discrepancy exists; it is not skipped or weakened. The review
does not establish whether the backend accepts such a password, because no
password change was submitted.

The original write-heavy suites were compared by source and collected, not run
against shared QA data. Complete write workflows, exact business boundaries,
and other-role permissions need the prerequisites listed in the gap report.
Use Sync Tests in the automation dashboard to discover the new cases.

## 11. Connected workflows

The suite includes read-only workflows, locally simulated server failures,
and opt-in persistent workflows. Current totals and validation are recorded in
[remaining coverage](coverage/all_remaining_coverage.csv) and
[remaining results](coverage/all_remaining_results.csv). Unexecuted cases are
identified separately from passing cases.

The added workflow tests reuse existing page objects and keep each scenario in
plain sequential steps. [Workflow coverage](coverage/workflow_coverage.csv)
lists new cases, existing coverage we retained, and requirements still needed.

Run the read-only review from this `testing` folder:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/review -m readonly -q -n 2 --dist loadfile
```

This includes draft discard, saved transaction comparisons after cancelling,
closing, reloading or leaving; unsent individual/entity onboarding drafts;
screening draft navigation; HTTP 500/503 and network recovery; and simulated
expired or locally removed sessions across ten application routes. Expiry is
simulated locally: these tests do not establish the server's actual session TTL
or revocation rules. The known password-hint regression can still fail.

Persistent workflows live in [tests/ui/review/workflows](tests/ui/review/workflows).
They are **disabled by default** and skip before opening a browser. Use only
after authorizing changes to disposable QA data, from this folder, with `-n 0`:

```powershell
$env:WORKFLOW_ALLOW_WRITES = '1'
$env:WORKFLOW_DISPOSABLE_DATA_CONFIRMED = '1'
# Enable only the feature you intend to validate, then provide its data below.
$env:WORKFLOW_TRANSACTIONS = '1'
$env:WORKFLOW_TRANSACTION_SELLER = '<exact disposable seller name>'
$env:WORKFLOW_TRANSACTION_BUYER = '<exact disposable buyer name>'
.\.venv\Scripts\python.exe -m pytest tests/ui/review/workflows/test_transaction_lifecycle.py -q -n 0
```

The current QA Property Address control is a searchable selector with an
`Add "address"` option. New transaction workflows use the additive
`choose_or_create_property` helper in [transactionPage.py](pages/transactionPage.py).
Existing test bodies and their field-entry helpers were preserved; older
field-level tests that assume a plain address input may need separate migration.

| Feature flag (set to `1`) | Additional inputs | Workflow |
|---|---|---|
| `WORKFLOW_TRANSACTIONS` | Distinct seller/buyer variables above | Create, edit several fields, reload and check same ID/parties; failed save and retry; rapid double submission |
| `WORKFLOW_ONBOARDING` | None | Create a fresh individual/entity, leave, find exact ID in Pending, reopen and reload |
| `WORKFLOW_ONBOARDING_COMPLETION` | `WORKFLOW_VERIFIED_PENDING_CLIENT_ID` | Save/reload KYC, calculate risk, complete onboarding, reload risk and reopen exact profile |
| `WORKFLOW_DOCUMENTS` | `WORKFLOW_DOCUMENT_CLIENT_ID`, optional `WORKFLOW_DOCUMENT_SLOT` (default `Others`), `WORKFLOW_ALLOW_DELETES=1` | Upload own generated PNG, reload, preview, cancel deletion, reload, delete and verify absence |
| `WORKFLOW_DOCUMENTS` (size tests) | Same document inputs | Valid PNG at 10,485,759 / 10,485,760 / 10,485,761 bytes |
| `WORKFLOW_SCREENING` | `WORKFLOW_ALLOW_DELETES=1` | New unique individual/organization analysis, daily persistence, reopen, remove and check absence |
| `WORKFLOW_SCREENING_RESOLUTIONS` | `WORKFLOW_SCREENING_MATCH_NAME` | Fresh non-ongoing provider analysis with unresolved matches, resolve one hit, reload and check same IDs/counts |

Screening consumes provider requests. Onboarding completion changes a pending
client into a completed profile: supply a separate disposable client for each
execution. Transaction/property/client records remain for audit; no automatic deletion
is attempted. Document slots must be empty. Document cleanup only targets the
generated filename; screening cleanup only targets the unique generated record.
These workflows never send invitation emails or change tenant configuration.
Existing real-camera/OCR verification coverage remains in
[test_client_reuse_poc.py](tests/ui/test_client_reuse_poc.py); the new completion
workflow starts from an explicitly supplied verified client and uses no camera.

The deployed frontend's uploader compares file sizes with `10485760`, so the
exact client limit is now verified as 10 MiB, inclusive. Generated PNGs use valid
image chunks/checksums, including their padding. Backend file/content checks
remain distinct from the locally mocked upload tests.

Role-permission coverage is in
[test_role_permissions.py](tests/ui/review/test_role_permissions.py).
Copy [permission_matrix.example.json](coverage/permission_matrix.example.json)
to a local policy file, fill in the approved rules for every role, then set
`WORKFLOW_PERMISSION_MATRIX` to its absolute path. The example only records
observed Admin access; empty role entries intentionally require a real policy.
For each role, supply `WORKFLOW_<ROLE>_EMAIL` and `WORKFLOW_<ROLE>_PASSWORD` via
environment variables (`ADMIN`, `ANALYST`, `MLRO`, `COMPLIANCE_OFFICER`, `CLIENT`).
No credentials belong in the JSON. Each role uses a separate browser context.

Allowed page checks require `path`, `heading` and `allowed: true`. A denied
page also requires `denial_text` for its actual access-denied screen; asserting
that a button is absent is insufficient. API checks specify an exact approved
QA backend `url` and expected `status` (`200` or `403`). Use only authorized test
records in those URLs; tests do not enumerate client IDs or other tenants.

After testing, remove the `WORKFLOW_*` opt-in variables from the shell. Do not
add them to the dashboard service environment unless you intend UI executions
to run these write scenarios. Sync Tests will discover them with normal stable
pytest IDs; skipped opt-in workflows are not evidence that business behaviour
passed. See [workflow_results.csv](coverage/workflow_results.csv) for validation.

## 12. Remaining coverage added in one pass

The additional cases cover direct API authentication, server-error recovery,
invitation name boundaries, calendar limits, file validation, reminder/expiry
rules, camera errors and stream cleanup, cross-client access, real session
refresh/logout/expiry, financial boundaries/concurrent edits, personal-data
boundaries, document content/duplicate/replacement handling, account/invitation
lifecycles, inbox delivery, CSV accounting, and isolated-tenant config persistence.
Existing tests and their stable IDs are preserved.

This addition contains 203 cases: 137 passed in Chromium, and 66 have not been
executed (56 persistent workflows and 10 cases needing camera-client, ownership
or unusable-invitation fixtures). Full collection contains 1,933 tests, including
321 review cases. This is collection coverage, not a claim that the full suite
passed. The earlier confirmed password-guidance regression remains failing.

The dashboard metadata maps the new stable IDs to their modules and camera
requirements. Thirty-seven cases keep the `Unclassified` category because
their positive/negative outcome depends on the approved business rules; they
are not silently included in Happy Path runs. Use All Tests or select those
cases explicitly after configuring their prerequisites. Config and Access
Control retain their own module names in the inventory.

Known limits come from the deployed application, not guessed values:

| Control | Verified client rule |
|---|---|
| Supporting-file upload | Size <= 10,485,760 bytes; PDF/PNG/JPG/JPEG extensions |
| Invitation first and last names | At least two characters after trimming |
| Invite validity | Positive integer; Minutes <= 59, Hours <= 23, Days <= 29, Weeks <= 4, Months <= 12 |
| Reminders | Positive integers within the selected unit's maximum; strictly ascending and before expiry |
| Transaction date / Profiles date filter | Future days disabled relative to browser-local today |

Read-only failure tests intercept account/invitation POSTs, profile/password PUTs,
screening analyses, config changes and uploads locally. Successful upload replies
are simulated: no file reaches QA object storage. The actual controls and their
validation execute in the deployed UI. These checks do not certify backend file
sniffing or email/provider behaviour; persistent tests cover those separately.

Run the review's read-only tests from this folder:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ui/review -m readonly -q -n 2 --dist loadfile
```

For financial, age, normalization, document-content and revocation policies,
copy [qa_rules.example.json](coverage/qa_rules.example.json) to an approved local
rules file and set `WORKFLOW_RULES_FILE` to its absolute path. `null` means the
rule is unconfirmed: that case skips with the missing rule's name. It never
counts as a business pass. Supported policy values:

- `financial.excess_precision`: `reject`, `round-half-up`, `preserve`.
- `financial.concurrent_edit`: `reject-stale`, `last-save-wins`.
- `person.leap_birthday`: `feb28`, `mar1` (only needed for a leap-day age cutoff).
- `documents.duplicate_filename`: `reject`, `allow-independent` (across two empty slots).
- `screening_csv.duplicate_rows`: `reject-batch`, `skip-duplicates`, `process-all`.
- `screening_csv.partial_failure`: `reject-batch`, `process-valid`.

Additional fixtures/opt-ins:

| Coverage | Required configuration |
|---|---|
| Camera failure/retry/track cleanup | `WORKFLOW_CAMERA_CLIENT_ID`: approved unverified individual; simulated media only, no real camera |
| Personal name/DOB/expiry boundaries | `WORKFLOW_PERSONAL_BOUNDARIES=1`, `WORKFLOW_KYC_BOUNDARY_CLIENT_ID`, approved rules; valid saved KYC on a disposable verified client, different from completion client |
| Financial/concurrency cases | Transaction opt-ins/parties from Section 11 plus approved financial rules |
| MIME/extension mismatch and duplicate filename | Document opt-ins from Section 11 plus approved document policy; duplicate case requires two empty slots |
| Failed file replacement | Document opt-ins; only own generated files; API and object-storage failures simulated |
| Real session checks | `WORKFLOW_SESSION_SECURITY=1`, `WORKFLOW_SESSION_EMAIL`, `WORKFLOW_SESSION_PASSWORD`: dedicated account different from `TEST_EMAIL` |
| Actual access-token expiry | Session inputs, agreed `session.access_expiry_leeway_seconds`, and sufficient `WORKFLOW_SESSION_EXPIRY_WAIT_SECONDS`; real issued token and real elapsed server time |
| Cross-client ownership | `WORKFLOW_OWNERSHIP_FILE`: approved copy of [ownership.example.json](coverage/ownership.example.json); two supplied account prefixes, exact owned resources and agreed 403/404 denial status |
| Expired/used invitation links | `WORKFLOW_EXPIRED_INVITE_URL`, `WORKFLOW_USED_INVITE_URL`: approved unusable links; mutating requests blocked |
| Staff create/read/duplicate/disable/reactivate/delete | `WORKFLOW_ACCOUNTS=1`, write/disposable/delete opt-ins, `WORKFLOW_ALLOW_EMAILS=1`, and controlled `WORKFLOW_TEST_EMAIL_DOMAIN` |
| Invitation create/link/delete | `WORKFLOW_INVITATIONS=1` plus the same email/write/delete opt-ins |
| Actual invitation delivery | Invitation inputs plus `WORKFLOW_IMAP_HOST`, `WORKFLOW_IMAP_USER`, and `WORKFLOW_IMAP_OAUTH_TOKEN` or `WORKFLOW_IMAP_PASSWORD`; reads test INBOX without marking messages as read |
| Config save/reload/restore | `WORKFLOW_CONFIG=1`, write/disposable opt-ins, `WORKFLOW_ISOLATED_TENANT_CONFIRMED=1`; never target shared tenant settings |
| Bulk screening CSV | `WORKFLOW_SCREENING_BULK=1`, write/disposable opt-ins, approved `screening_csv` contract, `WORKFLOW_SCREENING_CSV_SAMPLE`, explicit `WORKFLOW_BULK_ROW_BUDGET` |

The CSV contract specifies actual required headers, multipart field names, row
limit, duplicate/partial-failure behaviour and batch-summary field names/URL.
The suite validates every submitted row's accepted/failed/skipped accounting;
it does not treat HTTP 202 admission as completed screening. The approved CSV
sample must use disposable test data. Generated batches remain for audit.

Persistent tests use `-n 0` and the feature-specific opt-ins above. Staff and
invitation cleanup targets only IDs returned for freshly generated test email
addresses. Personal boundary tests restore the original tested KYC field;
config tests restore the isolated tenant's settings. Check cleanup errors rather
than treating them as passes. Shared test records must not be edited by another
run while these workflows execute.

No account is created, invitation sent, real file uploaded, screening analysis
started or shared configuration changed by the default read-only checks. Real
credentials, tokens, invitation URLs and mailbox credentials belong only in
local environment variables, never in the example JSON files or source code.
