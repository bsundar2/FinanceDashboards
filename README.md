# FinanceDashboards

Dashboards over a yearly budget Google Sheet, built with [marimo](https://marimo.io), plus the template that sheet is built from.

- **Yearly Overview**: spending by category and month against budget, savings by month, net worth, and income and investment tiles.
- **Net Worth**: your allocation by category, then its types, accounts by month and the securities each account holds.
- **Budget template**: a household budget spreadsheet (one person or a couple) whose labels the dashboards read.

The dashboards read the sheet live, so any sheet built from the template (or the older layout `budget_migration` understands) works. The data in it comes from [SplitwiseToSheets](https://github.com/bsundar2/SplitwiseToSheets) (the Expense Logs) and [FinanceToSheets](https://github.com/bsundar2/FinanceToSheets) (account balances and holdings); both are optional, since you can fill the sheet by hand.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

1. Create a Google service account and download its key to `data/gsheets_authentication.json` (gitignored).
2. Share your budget spreadsheet with the service account's `client_email` as a Viewer. To drill into securities on the Net Worth page, share the spreadsheet with FinanceToSheets's `holdings_dump` tab with it too.
3. Point the dashboards at them:

| Variable | Description |
|---|---|
| `BUDGET_SPREADSHEET_NAME` | The budget sheet (default `Budget - 2026`) |
| `HOLDINGS_SPREADSHEET_NAME` | The sheet with `holdings_dump` (default `RH_Sheets`; optional) |
| `GSHEETS_AUTH_FILE` | The key file (default `data/gsheets_authentication.json`) |

```bash
marimo run src/finance_dashboard.py     # Yearly Overview
marimo run src/net_worth_dashboard.py   # Net Worth
```

## One site behind a password

`src/dashboard_server.py` serves the Yearly Overview at `/` and Net Worth at `/net-worth` from one process, behind one password (`FINANCE_TOKEN`; you log in once for both):

```bash
FINANCE_TOKEN=<any password> uvicorn --factory src.dashboard_server:create_app --port 2718
```

A menu bar at the top of each page links them, plus FinanceToSheets's Swing Trading page and SplitwiseToSheets's Spending dashboard when `PNL_DASHBOARD_URL` and `SPENDING_DASHBOARD_URL` are set.

### Hosting on Render (one-time)

`render.yaml` defines the `finance-dashboard` service:
1. Share the budget sheet with the service account (see Setup).
2. In Render, sync the Blueprint, then on the `finance-dashboard` service:
   - **Environment → Secret Files**: add `gsheets_authentication.json` with the key file's contents. `GSHEETS_AUTH_FILE` already points at `/etc/secrets/gsheets_authentication.json`.
   - **Environment**: set `FINANCE_TOKEN` to a long random password (e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`) and keep it in your password manager. Set `PNL_DASHBOARD_URL` and `SPENDING_DASHBOARD_URL` to the other apps' URLs.
3. Next year, change `BUDGET_SPREADSHEET_NAME` to the new spreadsheet's name, and share that one too.

These pages load your finances on the server, so the password is all that stands between the public URL and your data.

## Budget template

`src/budget_template.py` builds the yearly budget spreadsheet as an `.xlsx` to import into Google Sheets: a generic household template, one sheet that both partners share (or just you, leaving the partner's parts empty). It has:
- **Settings**: both names, the year and how often each of you is paid. Every formula reads these instead of hard-coding them.
- **Income**: each person's pay, taxes and 401k side by side. The Budget tab's income rows add the two up, so take-home pay is the household's.
- **Expense Log** and **Partner Expense Log**: one per person, each filled by that person's SplitwiseToSheets. `My Owed` is that person's share of each expense, so a bill you split appears in both logs with each share, and the two add up to its full cost without counting it twice. Budget and Monthly Expenses total both.
- **Accounts**: balances entered by hand, plus an optional IMPORTRANGE of each person's SimpleFIN `bank_accounts_dump` (yours at G5, your partner's at L5).
- **Net Worth**: every account once, at its full balance, with each person's %: 100% / 0% for yours, 0% / 100% for your partner's, 50% / 50% (or 60% / 40%) for a joint account or the house. A balance is looked up by account name (or a fragment like `(1234)`), not a fixed cell, so new SimpleFIN accounts don't shift anything. The subtotals and NET WORTH are the household's, and two rows under NET WORTH give each person's own net worth.

```bash
# Blank template
python -m src.budget_template --out "Budget Template.xlsx" --year 2027

# An existing sheet in the original layout (File → Download → .xlsx), moved onto the template
python -m src.budget_migration "Budget - 2026.xlsx" --out "Budget - 2026 (v2).xlsx" --name Alex --partner Sam --year 2026
```

The migration puts the old sheet in your columns and tabs: your pay in Income, your Expense Log, and your Net Worth rows at full balance with your % (a `0.6 *` factor becomes 60% yours, 40% your partner's). Your partner's Income columns, Partner Expense Log and accounts start empty. A joint account the old sheet tracked as your part only stays that way, 100% yours, until you switch it to the full balance and each person's %.

To use either file, upload it to Google Drive and open it with Google Sheets (or File → Import → Create new spreadsheet). Then click **Allow access** on the first IMPORTRANGE cell (Accounts G5) so it can read the pipeline's spreadsheet. To keep the Expense Logs updating, point each person's SplitwiseToSheets `SPREADSHEET_KEY` at the new sheet, with your partner's `EXPENSES_WORKSHEET_NAME` (or `--worksheet`) set to `Partner Expense Log`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests mock Google Sheets. The formula tests recalculate the template in LibreOffice and are skipped without `libreoffice-calc`.
