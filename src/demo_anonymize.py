"""Turns an export of your real budget sheet into a demo with the same tabs,
rows, formulas, formatting and charts but made-up numbers, names and
accounts, so the dashboards can be shown without any real data.

It opens the .xlsx (Google's File > Download > Microsoft Excel export) and
changes only what's personal:

- Expense Log: every row replaced by a fictional household's year.
- Budget: pay, taxes and 401(k) inputs, and each category's yearly budget.
- Net Worth: institutions renamed, balances simulated month by month (past
  months frozen as values, the current month looked up from the Savings Log
  as in the real sheet), and the Monthly Savings Contributions.
- Savings Log: its imported account block, and its dividend, interest and
  gain figures, replaced by fixed fake values (no IMPORTRANGE).
- Anywhere else, Google's cached results inside `__xludf.DUMMYFUNCTION`
  formulas are emptied, so no real value hides behind a formula Google
  will recompute anyway.

Real institution names are only ever read from the file you pass in and
mapped to invented ones at run time; none of them is in this code. It also
adds the tabs FinanceToSheets writes (`holdings_dump`, `dividends_ledger`,
`Stocks`), built to match the fake Net Worth rows.

    python -m src.demo_anonymize "Budget - 2026.xlsx" --out "Demo Budget - 2026.xlsx"
"""

import argparse
import datetime
import random
import re

import openpyxl
from openpyxl.cell.cell import MergedCell
from openpyxl.utils import get_column_letter

from src import demo_data as dd

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]  # fmt: skip
SECTIONS = ["cash accounts", "investments", "retirement", "real estate", "liabilities"]

# Pay and 401(k): per paycheck, 24 a year, plus a bonus
SALARY, BONUS = 165_000.0, 15_000.0
PAYCHECKS = 24
RATES = {"Federal Tax": 0.21, "State Tax": 0.056, "Medicare": 0.0145}
FICA_CAP, FICA_RATE = 176_100.0, 0.062
COMMUTER_YEARLY = 1_200.0
RETIREMENT_YEARLY, MATCH_YEARLY = 16_500.0, 4_950.0

# Yearly budget per sub-category, for the person's own share of shared bills
BUDGET_SHARE = 0.6
OWN_BUDGETS = {"Mortgage": 18_900.0}

# Made-up names handed out in the order the real ones are first met
BANKS = ["Atlas Bank", "Harbor Credit Union", "Summit Savings", "Cedar Trust",
         "Orchard Online Bank", "Overseas Trust Bank", "Lakeview Bank"]  # fmt: skip
FINANCIAL = [
    "Meridian Financial",
    "Northwind Financial",
    "Atlas Financial",
    "Kestrel Financial",
]  # banks that also have a brokerage
BROKERS = ["Meridian Brokerage", "Northwind Invest", "Coinvault", "Federal Savings Bonds",
           "Tidewater Securities"]  # fmt: skip
RETIREMENT = ["Summit Retirement", "Pinecrest Retirement", "Ridgeline Retirement"]
CARDS = ["Voyager Card", "Skyline Card", "Orchard Cash Card", "Everyday Rewards",
         "Harbor Visa", "Kestrel Card", "Atlas Rewards Card"]  # fmt: skip

# What's put aside varies by month, except for what's automatic
JITTER = [0.6, 0.8, 1.0, 1.0, 1.2, 1.4]
STEADY = {("retirement", "roth ira"), ("real estate", "extra payments")}

ROBO_WEIGHTS = {"VTI": 0.5, "VXUS": 0.3, "BND": 0.2}


# ── Names ───────────────────────────────────────────────────────────────────


def _norm(text) -> str:
    return " ".join(str(text or "").split()).lower()


class _Names:
    """Maps each real institution to an invented one, the same way each
    time it comes up (so two rows at one bank stay at one fake bank). The
    pool depends on what the real one does across the sheet: a bank, a
    broker, a retirement provider, or a bank that also has a brokerage."""

    def __init__(self, roles: dict):
        self.roles = roles  # normalized real name -> the sections it's in
        self.seen: dict[tuple, str] = {}
        self.used: dict[int, int] = {}

    def _pool(self, real, card):
        sections = self.roles.get(_norm(real), set())
        if card:
            return CARDS
        if "retirement" in sections:
            return RETIREMENT
        banking = sections & {"cash accounts", "real estate", "liabilities"}
        if banking and "investments" in sections:
            return FINANCIAL
        return BROKERS if "investments" in sections else BANKS

    def institution(self, real, section: str, card: bool = False) -> str | None:
        if not _norm(real):
            return None
        key = (_norm(real), card)
        if key not in self.seen:
            pool = self._pool(real, card)
            count = self.used.get(id(pool), 0)
            self.used[id(pool)] = count + 1
            round_ = count // len(pool)
            self.seen[key] = pool[count % len(pool)] + (
                f" {round_ + 1}" if round_ else ""
            )
        return self.seen[key]


# ── Workbook helpers ────────────────────────────────────────────────────────


def _set(ws, ref, value):
    cell = ws[ref] if isinstance(ref, str) else ws.cell(row=ref[0], column=ref[1])
    if not isinstance(cell, MergedCell):
        cell.value = value


def _row_where(ws, column, test, start=1, stop=None):
    for row in range(start, (stop or ws.max_row) + 1):
        value = ws.cell(row=row, column=column).value
        if value is not None and test(_norm(value)):
            return row
    return None


def _scrub_cached(value):
    """A Google export wraps a function Excel lacks as
    =IFERROR(__xludf.DUMMYFUNCTION("<formula>"), <cached result>). Google
    recomputes the formula on import, so the cached result (which holds real
    values) is replaced by an empty string."""
    prefix = "=IFERROR(__xludf.DUMMYFUNCTION("
    if not (isinstance(value, str) and value.startswith(prefix)):
        return value
    depth, in_text, i = 1, False, len(prefix)
    while i < len(value) and depth:
        ch = value[i]
        if ch == '"':
            in_text = not in_text
        elif not in_text:
            depth += (ch == "(") - (ch == ")")
        i += 1
    return f'{value[:i]},"")' if depth == 0 else value


# ── Expense Log ─────────────────────────────────────────────────────────────


def _expense_log(ws, rng, year, today):
    expenses = dd.generate_expenses(rng, year, today)
    rows = [row[:10] + row[11:] for row in dd.expense_logs(expenses)[0]]
    # Bills Splitwise already holds for next month (the dashboard skips them)
    for month_day, amount, category, description in (
        ((today.month % 12 + 1, 1), 3150, "Mortgage", "Mortgage payment"),
        ((today.month % 12 + 1, 3), 79.99, "TV/Phone/Internet", "Home internet"),
    ):
        when = datetime.datetime(year + (today.month == 12), *month_day)
        if when.date() > today:
            half = round(amount / 2, 2)
            rows.append([when, amount, category, description, None, "partner",
                         f"{dd.NAME}, {dd.PARTNER}", amount, half, round(amount - half, 2),
                         9000 + len(rows), f"demo-upcoming-{len(rows)}"])  # fmt: skip
    for row in range(2, ws.max_row + 1):
        for col in range(1, 13):
            _set(ws, (row, col), None)
    for r, values in enumerate(rows, start=2):
        for c, value in enumerate(values, start=1):
            _set(ws, (r, c), value)
    ws._hyperlinks = []
    for row in ws.iter_rows():
        for cell in row:
            if cell.hyperlink:
                cell.hyperlink = None


# ── Budget ──────────────────────────────────────────────────────────────────


def _budget(ws):
    """Pay, tax and 401(k) inputs (found by their labels) and category
    budgets."""
    rows = {}
    for row in range(1, ws.max_row + 1):
        label = _norm(ws.cell(row=row, column=2).value)
        if label:
            rows.setdefault(label, row)
    per_check = round(SALARY / PAYCHECKS, 2)
    wages = SALARY + BONUS
    fica = round(FICA_CAP * FICA_RATE, 2)
    spec = {
        "gross salary": {"C": SALARY, "F": per_check},
        "bonus": {"C": BONUS, "D": BONUS},
        "federal tax": {"C": round(wages * RATES["Federal Tax"], 2),
                        "D": f"=(E{{r}}*12)+(D{rows['bonus']}*{RATES['Federal Tax']})",
                        "F": round(per_check * RATES["Federal Tax"], 2)},
        "state tax": {"C": round(wages * RATES["State Tax"], 2),
                      "D": f"=(E{{r}}*12)+(D{rows['bonus']}*{RATES['State Tax']})",
                      "F": round(per_check * RATES["State Tax"], 2)},
        "fica / social security": {"C": fica, "D": f"=MIN({fica}, E{{r}}*12)",
                                   "F": round(per_check * FICA_RATE, 2)},
        "medicare": {"C": round(wages * RATES["Medicare"], 2),
                     "D": f"=(E{{r}}*12)+(D{rows['bonus']}*{RATES['Medicare']})",
                     "F": round(per_check * RATES["Medicare"], 2)},
        "401k contribution": {"C": RETIREMENT_YEARLY,
                              "D": f"=MIN(E{{r}}*12, {RETIREMENT_YEARLY})",
                              "F": round(RETIREMENT_YEARLY / PAYCHECKS, 2)},
        "401k company match": {"C": MATCH_YEARLY, "D": f"=MIN(E{{r}}*12, {MATCH_YEARLY})",
                               "F": round(MATCH_YEARLY / PAYCHECKS, 2)},
    }  # fmt: skip
    for label, cells in spec.items():
        row = rows.get(label)
        if row:
            for col, value in cells.items():
                _set(
                    ws,
                    f"{col}{row}",
                    value.format(r=row) if isinstance(value, str) else value,
                )
    pre_tax = _row_where(ws, 1, lambda t: t == "pre-tax")
    if pre_tax:  # the commuter-card row below the PRE-TAX title
        _set(ws, f"C{pre_tax + 1}", COMMUTER_YEARLY)
        _set(ws, f"E{pre_tax + 1}", COMMUTER_YEARLY / 12)

    budgets = {name: float(round(budget * BUDGET_SHARE, -1))
               for _, name, budget, _ in dd.CATEGORIES}  # fmt: skip
    budgets.update(OWN_BUDGETS)
    start = _row_where(ws, 1, lambda t: t == "expenses")
    stop = _row_where(ws, 2, lambda t: t == "total expenses", start or 1)
    for row in range((start or 0) + 1, (stop or 0)):
        label = ws.cell(row=row, column=2).value
        if label:
            _set(ws, f"D{row}", budgets.get(str(label).strip(), 0.0))


# ── Net Worth ───────────────────────────────────────────────────────────────


def _template(section, b, c, rng, seen):
    """The simulated account behind a Net Worth row, from its generic Account
    and Type labels. `seen` counts rows already given a flow."""
    b, c = _norm(b), _norm(c)
    base = dict(section=SECTIONS.index(section), account=b, type=c, institution="",
                key="", share=1)  # fmt: skip

    def first(tag):
        seen[tag] = seen.get(tag, 0) + 1
        return seen[tag] == 1

    if section == "cash accounts":
        if "uninvested" in c:
            return dd.Account(kind="cash", start=rng.uniform(300, 1200), sigma=0.5,
                              feed_name="Brokerage Cash", **base)  # fmt: skip
        if "checking" in b:
            return dd.Account(kind="cash", start=rng.uniform(4500, 9500), sigma=0.22,
                              feed_name="Everyday Checking", **base)  # fmt: skip
        if "foreign" in c:
            return dd.Account(kind="saving", start=9000, mu=0.003,
                              feed_name="Overseas Savings", **base)  # fmt: skip
        if "joint" in c:
            return dd.Account(kind="saving", start=rng.uniform(18000, 36000), flow=500, mu=0.0033,
                              feed_name="Joint Savings 3.95% APY",
                              contribution=("savings", "joint"), **base)  # fmt: skip
        flow = 800 if first("savings") else 0
        return dd.Account(kind="saving", start=rng.uniform(15000, 30000), flow=flow,
                          mu=0.0034, feed_name="High-Yield Savings 4.10% APY",
                          contribution=("savings", "individual") if flow else (), **base)  # fmt: skip
    if section == "investments":
        if "crypto" in c:
            return dd.Account(kind="invest", start=6500, flow=100, mu=0.01, sigma=0.12,
                              feed_name="Crypto Wallet", contribution=("crypto", "crypto"),
                              weights=tuple(dd.CRYPTO_WEIGHTS.items()), **base)  # fmt: skip
        if "stock" in c:
            return dd.Account(kind="invest", start=61000, flow=700, mu=0.006, sigma=0.032,
                              feed_name="Individual Brokerage - Stocks",
                              contribution=("brokerage", "stocks"),
                              weights=tuple(dd.STOCK_WEIGHTS.items()), **base)  # fmt: skip
        if "etf" in c:
            if first("etf"):
                return dd.Account(kind="invest", start=49000, flow=600, mu=0.006,
                                  sigma=0.024, feed_name="Individual Brokerage - ETF",
                                  contribution=("brokerage", "etf"),
                                  weights=tuple(dd.ETF_WEIGHTS.items()), **base)  # fmt: skip
            return dd.Account(kind="invest", start=18000, mu=0.006, sigma=0.022,
                              feed_name="Robo Portfolio ETF",
                              weights=tuple(ROBO_WEIGHTS.items()), **base)  # fmt: skip
        if "bond" in c:
            return dd.Account(kind="saving", start=9000, flow=100, mu=0.0035,
                              feed_name="Savings Bonds", contribution=("bonds", "i-bonds"),
                              **base)  # fmt: skip
        return dd.Account(kind="saving", start=7200, mu=0.005, feed_name="Term Deposit",
                          **base)  # fmt: skip
    if section == "retirement":
        if "401" in c:
            return dd.Account(kind="retire", start=128000,
                              payroll=(RETIREMENT_YEARLY + MATCH_YEARLY) / 12, mu=0.006,
                              sigma=0.026, feed_name="401(k)",
                              weights=tuple(dd.K401_WEIGHTS.items()),
                              sources=(("Pre-Tax", 0.75), ("Match", 0.25)), **base)  # fmt: skip
        if "roth" in c:
            return dd.Account(kind="retire", start=41000, flow=6500 / 12, mu=0.006,
                              sigma=0.028, feed_name="Roth IRA",
                              contribution=("retirement", "roth ira"),
                              weights=tuple(dd.ROTH_WEIGHTS.items()), **base)  # fmt: skip
        return dd.Account(kind="retire", start=18500, mu=0.006, sigma=0.02,
                          feed_name="Traditional IRA",
                          weights=tuple(dd.TRAD_WEIGHTS.items()), **base)  # fmt: skip
    if section == "real estate":
        if "home" in c:
            return dd.Account(kind="home", start=598000, mu=0.0018, sigma=0.002, **base)
        if "extra" in c:
            return dd.Account(kind="extra", start=0, flow=500,
                              contribution=("real estate", "extra payments"), **base)  # fmt: skip
        return dd.Account(
            kind="mortgage", start=-392000, feed_name="Home Mortgage", **base
        )
    if "loan" in c:
        return dd.Account(kind="loan", start=-15600, feed_name="Auto Loan", **base)
    return dd.Account(kind="card", start=-1900, feed_name="Rewards Card", **base)


def _simulate(account, rng, months, part):
    if account.kind == "extra":  # a running total of the extra payments
        return [round(account.flow * (m - 1 + (part if m == months else 1)), 2)
                for m in range(1, months + 1)]  # fmt: skip
    series = dd._simulate(account, rng, months, part)
    return (
        [-v for v in series] if account.kind == "mortgage" else series
    )  # held positive


def _net_worth(wb, rng, today, year, months, part):
    """Rewrites every account row's balances and the contributions block.
    Returns the feeds that go in the Savings Log and the holdings."""
    ws = wb["Net Worth"]
    month_col = {}
    for col in range(1, ws.max_column + 1):
        label = _norm(ws.cell(row=4, column=col).value)
        for number, name in enumerate(MONTHS, start=1):
            if label == name.lower():
                month_col[number] = col
    section, contributing, rows, flows, seen = None, False, [], {}, {}
    for row in range(5, ws.max_row + 1):
        a = _norm(ws.cell(row=row, column=1).value)
        b = ws.cell(row=row, column=2).value
        c = ws.cell(row=row, column=3).value
        if a in SECTIONS:
            section, contributing = a, False
        elif a.startswith("subtotal"):
            section = None
        elif a.startswith("monthly savings contributions"):
            section, contributing = None, True
        elif a.startswith("total contributed"):
            contributing = False
        elif b is not None and section:
            rows.append((row, section, b, c, ws.cell(row=row, column=4).value))
        elif b is not None and contributing:
            rows.append((row, "contributions", b, c, None))

    roles: dict[str, set] = {}
    for _, sect, _, _, d in rows:
        if sect != "contributions" and _norm(d):
            roles.setdefault(_norm(d), set()).add(sect)
    names = _Names(roles)
    feeds, contribution_rows = [], []
    for row, sect, b, c, d in rows:
        if sect == "contributions":
            contribution_rows.append((row, (_norm(b), _norm(c))))
            continue
        real = [ws.cell(row=row, column=month_col[m]).value for m in sorted(month_col)]
        if all(v is None for v in real):
            continue  # an empty row (Other Debt) stays empty
        account = _template(sect, b, c, rng, seen)
        series = _simulate(account, rng, months, part)
        institution = names.institution(d, sect, card=account.kind == "card")
        if institution and account.kind == "card":
            institution = f"{institution} ({rng.randint(1000, 9999)})"
        if account.contribution:
            steady = account.contribution in STEADY
            flows[account.contribution] = {
                m: round(
                    account.flow
                    * (1 if steady else rng.choice(JITTER))
                    * (part if m == months else 1),
                    2,
                )
                for m in range(1, months + 1)
            }
        _set(ws, (row, 4), institution)
        feed_row = None
        if account.feed_name:
            feeds.append({"row": row, "account": account, "institution": institution or "",
                          "balance": series[-1], "label": account.feed_name})  # fmt: skip
        for m in range(1, 13):
            col = month_col[m]
            if m < months:
                _set(ws, (row, col), series[m - 1])
            elif account.feed_name:
                _set(ws, (row, col), None)  # filled in once the Savings Log rows exist
            elif m == months:
                _set(ws, (row, col), series[-1])
            else:
                _set(ws, (row, col), f"={get_column_letter(col - 1)}{row}")
    for row, key in contribution_rows:
        for m in range(1, 13):
            _set(ws, (row, month_col[m]), flows.get(key, {}).get(m))
    return feeds, month_col


# ── Savings Log ─────────────────────────────────────────────────────────────


def _savings_log(wb, feeds, month_col, months, today, rng):
    ws = wb["Savings Log"]
    ledger = {}
    for row in range(1, ws.max_row + 1):
        label = _norm(ws.cell(row=row, column=1).value)
        for prefix in ("dividends received", "interest", "stock gain/loss"):
            if label.startswith(prefix):
                ledger[row] = (ws.cell(row=row, column=1).value, prefix)
    last = max(ws.max_row, len(feeds) + 1)
    for row in range(1, last + 1):
        for col in range(1, 8):
            _set(ws, (row, col), None)
    fake = {
        "dividends received": 2923.0,
        "interest": 1412.55,
        "stock gain/loss": -640.25,
    }
    for row, (label, prefix) in ledger.items():
        _set(ws, f"A{row}", label)
        _set(ws, f"B{row}", fake[prefix])
    for col, label in zip(
        "DEFG", ["Institution", "Account Name", "Balance", "Balance As Of"]
    ):
        _set(ws, f"{col}1", label)
    as_of = datetime.datetime.combine(today, datetime.time())
    ordered = sorted(feeds, key=lambda f: (f["institution"], f["label"]))
    nw = wb["Net Worth"]
    for number, feed in enumerate(ordered, start=2):
        last4 = rng.randint(1000, 9999)
        feed["name"] = f"{feed['label']} ({last4})"
        feed["last4"] = last4
        sign = -1 if feed["account"].kind == "mortgage" else 1
        _set(ws, f"D{number}", feed["institution"])
        _set(ws, f"E{number}", feed["name"])
        _set(ws, f"F{number}", round(sign * feed["balance"], 2))
        _set(ws, f"G{number}", as_of)
        ref = f"'Savings Log'!$F${number}"
        for m in range(months, 13):
            _set(nw, (feed["row"], month_col[m]), f"={'-' if sign < 0 else ''}{ref}")
    return ordered


# ── Holdings tabs ───────────────────────────────────────────────────────────


def _holdings(feeds, today):
    rows, institutions = [], []
    as_of = datetime.datetime.combine(today, datetime.time())
    for feed in feeds:
        account = feed["account"]
        if not account.weights:
            continue
        if account.sources:
            parts = [(f"{feed['label']} {suffix} ({feed['last4']})", feed["balance"] * share)
                     for suffix, share in account.sources]  # fmt: skip
        else:
            parts = [(feed["name"], feed["balance"])]
        if "401" not in feed["label"] and feed["institution"] not in institutions:
            institutions.append(feed["institution"])
        for name, balance in parts:
            for symbol, shares, value in dd._positions(account.weights, balance):
                description, price = dd.SECURITIES[symbol][:2]
                rows.append([feed["institution"], name, symbol, description, shares, value,
                             round(value * 0.78, 2), round(price * 0.78, 2), "USD", as_of])  # fmt: skip
    return rows, tuple(institutions)


# ── Putting it together ─────────────────────────────────────────────────────


def anonymize(
    path: str,
    today: datetime.date | None = None,
    seed: int = 7,
    year: int | None = None,
) -> openpyxl.Workbook:
    """The demo workbook made from the export at `path`."""
    today = today or datetime.date.today()
    rng = random.Random(seed)
    wb = openpyxl.load_workbook(path)
    if year is None:
        first = wb["Expense Log"]["A2"].value
        year = first.year if isinstance(first, datetime.datetime) else today.year
    months = today.month if today.year == year else 12
    last_day = dd._last_day(year, today.month)
    part = today.day / last_day if today.year == year and today.day < last_day else 1.0
    _expense_log(wb["Expense Log"], rng, year, today)
    _budget(wb["Budget"])
    feeds, month_col = _net_worth(wb, rng, today, year, months, part)
    feeds = _savings_log(wb, feeds, month_col, months, today, rng)
    holdings, institutions = _holdings(feeds, today)
    dd.add_holdings_tabs(wb, holdings, today, year, rng, institutions)

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and not isinstance(cell, MergedCell):
                    cell.value = _scrub_cached(cell.value)
    wb.properties.creator = "Demo"
    wb.properties.lastModifiedBy = None
    return wb


# ── Checks ──────────────────────────────────────────────────────────────────

_SUSPECT = re.compile(r"IMPORTRANGE|https?://|@|[A-Za-z0-9_-]{40,}")


def audit(wb) -> list[str]:
    """Cells that still look like they point at, or come from, something
    outside the workbook: an IMPORTRANGE, a link, an email or a sheet id."""
    return [
        f"{ws.title}!{cell.coordinate}"
        for ws in wb.worksheets
        for row in ws.iter_rows()
        for cell in row
        if isinstance(cell.value, str) and _SUSPECT.search(cell.value)
    ]


def _quoted_strings(text: str) -> list[str]:
    return [m.replace('""', '"') for m in re.findall(r'"((?:[^"]|"")*)"', text)]


def _personal_strings(wb) -> set[str]:
    """What a real export holds that mustn't survive: transaction text and
    names, institutions and account names, and the cached strings inside
    Google's wrapped formulas."""
    found = set()
    sources = {"Expense Log": (4, 5, 7, 12), "Net Worth": (4,), "Savings Log": (4, 5)}
    for title, columns in sources.items():
        if title not in wb.sheetnames:
            continue
        for row in wb[title].iter_rows(min_row=2):
            for cell in row:
                if cell.column in columns and isinstance(cell.value, str):
                    found.add(_norm(cell.value))
                    if cell.value.startswith("=IFERROR(__xludf"):
                        found.update(_norm(s) for s in _quoted_strings(cell.value))
    found.discard("")
    return {s for s in found if len(s) >= 4 and "dummyfunction" not in s
            and s != "computed_value" and not s.startswith("=")}  # fmt: skip


# Tabs whose text can hold personal data; the others are the template's own
# labels and instructions
_DATA_TABS = ("Expense Log", "Net Worth", "Savings Log", "holdings_dump",
              "dividends_ledger", "Stocks")  # fmt: skip


def _data_cells(wb):
    for title in _DATA_TABS:
        if title in wb.sheetnames:
            for row in wb[title].iter_rows(min_row=2):
                for cell in row:
                    if cell.value is not None and not isinstance(cell, MergedCell):
                        yield cell


def leaks(real_path: str, demo) -> list[str]:
    """Strings from the real export (see _personal_strings) that appear in
    the demo's data tabs. Public company names in the made-up holdings and
    everyday words can match; look at each before worrying."""
    real = _personal_strings(openpyxl.load_workbook(real_path))
    corpus = " \n ".join(
        _norm(cell.value) for cell in _data_cells(demo) if isinstance(cell.value, str)
    )
    return sorted(s for s in real if s in corpus)


def leaked_numbers(real_path: str, demo) -> list[str]:
    """Where a real figure (1,000 or more, with cents or five digits) has
    survived: the cells of the demo's data tabs holding the same value."""
    real = {
        round(float(c.value), 2)
        for c in _data_cells(openpyxl.load_workbook(real_path))
        if isinstance(c.value, (int, float)) and not isinstance(c.value, bool)
        and abs(c.value) >= 1000 and (abs(c.value) >= 10_000 or c.value % 1)
    }  # fmt: skip
    return [
        f"{cell.parent.title}!{cell.coordinate}"
        for cell in _data_cells(demo)
        if isinstance(cell.value, (int, float)) and round(float(cell.value), 2) in real
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Make a demo copy of your real budget export"
    )
    parser.add_argument("source", help="the real sheet, downloaded as .xlsx")
    parser.add_argument("--out", default="Demo Budget - 2026.xlsx")
    parser.add_argument("--today", help="YYYY-MM-DD; default today")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    today = datetime.date.fromisoformat(args.today) if args.today else None
    wb = anonymize(args.source, today, args.seed)
    wb.save(args.out)
    found, suspects = leaks(args.source, wb), audit(wb)
    numbers = leaked_numbers(args.source, wb)
    print(f"Wrote {args.out}")
    print(f"Strings from the real file still in the demo: {len(found)}")
    for item in found:
        print("  ", item)
    print(f"Figures from the real file still in the demo: {len(numbers)}")
    for item in numbers[:10]:
        print("  ", item)
    print(f"Cells that still look external (IMPORTRANGE, link, id): {len(suspects)}")
    for item in suspects[:10]:
        print("  ", item)


if __name__ == "__main__":
    main()
