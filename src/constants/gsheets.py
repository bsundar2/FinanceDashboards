import os

# Env var pointing at the service account credentials file somewhere other
# than the default local path - e.g. a hosted dashboard whose secret file is
# mounted elsewhere (Render puts them under /etc/secrets/).
SHEETS_AUTHENTICATION_FILE_ENV_VAR = "GSHEETS_AUTH_FILE"
SHEETS_AUTHENTICATION_FILE = os.environ.get(
    SHEETS_AUTHENTICATION_FILE_ENV_VAR, "data/gsheets_authentication.json"
)

# The yearly budget spreadsheet the dashboards read (it must be shared with
# the service account). The env var lets next year's sheet be swapped in
# without a code change.
BUDGET_SPREADSHEET_NAME_ENV_VAR = "BUDGET_SPREADSHEET_NAME"
DEFAULT_BUDGET_SPREADSHEET_NAME = "Budget - 2026"

# The spreadsheet holding the SimpleFIN pipeline's holdings_dump tab (one row
# per security per account), which the Net Worth page drills into. Optional:
# without it the page falls back to account balances.
HOLDINGS_SPREADSHEET_NAME_ENV_VAR = "HOLDINGS_SPREADSHEET_NAME"
DEFAULT_HOLDINGS_SPREADSHEET_NAME = "RH_Sheets"
HOLDINGS_DUMP_SHEET_NAME = "holdings_dump"
