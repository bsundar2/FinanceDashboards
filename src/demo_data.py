"""A fictional household for demos: the yearly budget spreadsheet filled with
made-up data, so the dashboards can be shown without any real numbers.

It builds on the budget template (src/budget_template.py), so the Budget,
Monthly Expenses, Net Worth and Dashboard tabs are the real formulas over
invented inputs, and adds the tabs the pipelines in FinanceToSheets would
write, in their column layout: `bank_accounts_dump`, `holdings_dump`,
`dividends_ledger` and a `Stocks` tab with the projected yearly dividend.
One spreadsheet holds all of it, so point both BUDGET_SPREADSHEET_NAME and
HOLDINGS_SPREADSHEET_NAME at it.

Everything is generated from a seed, so a run is repeatable. Names, banks,
merchants and amounts are invented; nothing here comes from a real account.
The sheet's name must contain its year (the dashboards read it from there).

    python -m src.demo_data --out "Demo Budget - 2026.xlsx"
"""

import argparse
import calendar
import datetime
import random
from dataclasses import dataclass

from src import budget_template as bt

NAME, PARTNER = "Alex", "Sam"

BANK_ACCOUNTS_TAB = "bank_accounts_dump"
HOLDINGS_TAB = "holdings_dump"
DIVIDENDS_TAB = "dividends_ledger"
STOCKS_TAB = "Stocks"

BANK_COLUMNS = ["Institution", "Account Name", "Balance", "Balance As Of"]
HOLDINGS_COLUMNS = [
    "Institution", "Account Name", "Symbol", "Description", "Shares",
    "Market Value", "Cost Basis (raw)", "Purchase Price (raw)", "Currency", "As Of",
]  # fmt: skip
DIVIDEND_COLUMNS = [
    "Transaction ID", "Posted", "Institution", "Account Name", "Security",
    "Description", "Amount", "Symbol",
]  # fmt: skip
DIVIDENDS_HEADER_ROW = 6

# Pay, per paycheck (24 a year each)
PAY = {NAME: 5200.0, PARTNER: 4100.0}
BONUS = {NAME: 8000.0, PARTNER: 4000.0}
PRE_TAX_PER_PAYCHECK = 160.0
TAX_RATES = {9: 0.155, 10: 0.048, 11: 0.062, 12: 0.0145}  # Income tab rows
RETIREMENT_RATE, MATCH_RATE = 0.06, 0.04

# (group, sub-category, yearly budget, counts toward Total Expenses)
CATEGORIES = [
    ("Utilities", "Electricity", 1500, True),
    ("Utilities", "Heat/gas", 900, True),
    ("Utilities", "Trash", 360, True),
    ("Utilities", "TV/Phone/Internet", 2300, True),
    ("Utilities", "Water", 700, True),
    ("Entertainment", "Games", 400, True),
    ("Entertainment", "Movies", 500, True),
    ("Entertainment", "Music", 300, True),
    ("Entertainment", "Sports", 900, True),
    ("Food and drink", "Dining out", 4800, True),
    ("Food and drink", "Groceries", 9600, True),
    ("Food and drink", "Liquor", 600, True),
    ("Home", "Furniture", 2500, True),
    ("Home", "Household supplies", 1200, True),
    ("Home", "Maintenance", 3000, True),
    ("Home", "Mortgage", 37800, True),
    ("Home", "Pets", 2000, True),
    ("Transportation", "Bus/train", 600, True),
    ("Transportation", "Car", 2400, True),
    ("Transportation", "Gas/fuel", 1800, True),
    ("Transportation", "Hotel", 2500, True),
    ("Transportation", "Parking", 300, True),
    ("Transportation", "Plane", 3000, True),
    ("Life", "Clothing", 2400, True),
    ("Life", "Education", 600, True),
    ("Life", "Gifts", 1500, True),
    ("Life", "Insurance", 5400, True),
    ("Life", "Medical expenses", 1800, True),
    ("Life", "Taxes", 4800, True),
]  # fmt: skip

GROCERS = ["Harvest Market", "Green Basket", "Daily Fresh Foods", "Bluebird Grocer"]
RESTAURANTS = [
    "Corner Bistro", "Noodle House", "Maple Street Pizza", "The Copper Kettle",
    "Saffron Kitchen", "Harbor Fish Shack", "Sunday Brunch Cafe",
]  # fmt: skip
PHARMACIES = ["Lakeside Pharmacy", "Family Care Clinic", "Smile Dental"]
SHOPS = ["Threadwell Clothing", "Outdoor Supply Co", "Shoe Barn", "Linen & Loom"]
FUEL = ["Sunrise Fuel", "QuickFill"]


@dataclass
class Expense:
    date: datetime.datetime
    amount: float
    category: str
    description: str
    payer: str
    shared: bool = True  # split 50/50; otherwise only the payer's own


# ── Spending ────────────────────────────────────────────────────────────────


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def generate_expenses(rng: random.Random, year: int, today: datetime.date) -> list:
    """A year of household spending up to today: bills, groceries and
    dinners, and a few big one-offs (a sofa, a trip, a roof repair)."""
    expenses: list[Expense] = []

    def add(month, day, amount, category, description, payer, shared=True):
        day = min(day, _last_day(year, month))
        when = datetime.datetime(year, month, day)
        if when.date() <= today:
            expenses.append(
                Expense(when, round(amount, 2), category, description, payer, shared)
            )

    def either():
        return rng.choice([NAME, PARTNER])

    last_month = today.month if today.year == year else 12
    for month in range(1, last_month + 1):
        winter = month in (1, 2, 3, 11, 12)
        add(month, 1, 3150, "Mortgage", "Mortgage payment", NAME)
        add(month, 5, 214, "Insurance", "Car insurance", NAME)
        add(month, 8, 79.99, "TV/Phone/Internet", "Home internet", PARTNER)
        add(month, 22, 128, "TV/Phone/Internet", "Mobile plans", PARTNER)
        add(month, 12, rng.uniform(78, 135), "Electricity", "Electric bill", NAME)
        add(month, 14, rng.uniform(120, 190) if winter else rng.uniform(28, 45),
            "Heat/gas", "Gas bill", NAME)  # fmt: skip
        add(month, 18, rng.uniform(52, 66), "Water", "Water & sewer", PARTNER)
        add(month, 25, 30, "Trash", "Trash pickup", NAME)
        add(month, 3, 11.99, "Music", "Music streaming", NAME, shared=False)
        add(month, 9, 15.49, "Movies", "Movie streaming", PARTNER)
        add(month, 4, 45, "Sports", "Gym membership", NAME, shared=False)
        add(month, 6, 62, "Bus/train", "Transit pass", PARTNER, shared=False)
        for _ in range(rng.randint(4, 5)):
            add(month, rng.randint(1, 28), rng.uniform(78, 215), "Groceries",
                rng.choice(GROCERS), either())  # fmt: skip
        for _ in range(rng.randint(6, 9)):
            add(month, rng.randint(1, 28), rng.uniform(26, 98), "Dining out",
                rng.choice(RESTAURANTS), either(), shared=rng.random() < 0.7)  # fmt: skip
        for _ in range(rng.randint(3, 4)):
            add(month, rng.randint(1, 28), rng.uniform(36, 64), "Gas/fuel",
                rng.choice(FUEL), either(), shared=False)  # fmt: skip
        for _ in range(2):
            add(month, rng.randint(1, 28), rng.uniform(22, 118),
                "Household supplies", "Home & garden store", either())  # fmt: skip
        add(
            month,
            rng.randint(1, 28),
            rng.uniform(55, 110),
            "Pets",
            "Pet food",
            either(),
        )
        for _ in range(rng.randint(1, 2)):
            add(month, rng.randint(1, 28), rng.uniform(38, 185), "Clothing",
                rng.choice(SHOPS), either(), shared=False)  # fmt: skip
        if rng.random() < 0.7:
            add(month, rng.randint(1, 28), rng.uniform(35, 180), "Medical expenses",
                rng.choice(PHARMACIES), either(), shared=False)  # fmt: skip
        if rng.random() < 0.35:
            add(month, rng.randint(1, 28), rng.uniform(25, 60), "Liquor",
                "Wine & spirits", either())  # fmt: skip
        if rng.random() < 0.4:
            add(month, rng.randint(1, 28), rng.uniform(14, 30), "Movies",
                "Cinema tickets", either())  # fmt: skip
        if rng.random() < 0.3:
            add(month, rng.randint(1, 28), rng.uniform(8, 24), "Parking",
                "City parking", either(), shared=False)  # fmt: skip

    # Occasional and one-off bills
    add(2, 14, 142, "Gifts", "Anniversary gift", NAME, shared=False)
    add(3, 12, 2480, "Furniture", "Living room sofa", NAME)
    add(4, 10, 2400, "Taxes", "Property tax (first half)", NAME)
    add(5, 6, 285, "Pets", "Vet visit", PARTNER)
    add(5, 19, 175, "Gifts", "Birthday gifts", PARTNER, shared=False)
    add(6, 10, 1780, "Car", "Car repair", NAME)
    add(7, 3, 1640, "Plane", "Flights to the coast", NAME)
    add(7, 8, 1320, "Hotel", "Seaside hotel", PARTNER)
    add(8, 21, 450, "Education", "Evening course", PARTNER, shared=False)
    add(9, 15, 6850, "Maintenance", "Roof repair", PARTNER)
    add(10, 10, 2400, "Taxes", "Property tax (second half)", NAME)
    add(10, 27, 96, "Games", "Board game night", PARTNER)
    add(11, 20, 164, "Gifts", "Holiday gifts", NAME, shared=False)
    add(11, 24, 320, "Dining out", "Anniversary dinner", NAME)
    return sorted(expenses, key=lambda e: e.date)


def expense_logs(expenses: list) -> tuple[list, list]:
    """The two people's Expense Log rows, in SplitwiseToSheets's columns. A
    shared bill is in both, under one Splitwise ID, with each person's own
    paid / owed / net; a personal expense only in its payer's."""
    logs: dict[str, list] = {NAME: [], PARTNER: []}
    for number, e in enumerate(expenses, start=1001):
        parties = [NAME, PARTNER] if e.shared else [e.payer]
        halves = {NAME: round(e.amount / 2, 2)}
        halves[PARTNER] = round(e.amount - halves[NAME], 2)
        for person in parties:
            owed = halves[person] if e.shared else e.amount
            paid = e.amount if person == e.payer else 0
            logs[person].append([
                e.date, e.amount, e.category, e.description, None,
                "partner" if e.shared else "self",
                f"{NAME}, {PARTNER}" if e.shared else person,
                paid, owed, round(paid - owed, 2), None, number, f"demo-{number}",
            ])  # fmt: skip
    return logs[NAME], logs[PARTNER]


# ── Pay ─────────────────────────────────────────────────────────────────────


def paychecks_so_far(today: datetime.date, year: int) -> int:
    """Twice-monthly pay, on the 15th and the last day."""
    if today.year != year:
        return 24 if today.year > year else 0
    count = 2 * (today.month - 1)
    return count + (today.day >= 15) + (today.day >= _last_day(year, today.month))


def income_overrides(today: datetime.date, year: int) -> dict:
    """Both people's Income cells: per-paycheck figures (which the budget
    columns scale up) and what's actually been paid so far."""
    paid = paychecks_so_far(today, year)
    cells: dict = {}
    for person, (actual, yearly, paycheck) in zip(
        (NAME, PARTNER), (("C", "D", "F"), ("H", "I", "K"))
    ):
        gross = PAY[person]
        bonus_paid = BONUS[person] if today >= datetime.date(year, 3, 15) else 0
        cells[f"{paycheck}5"] = gross
        cells[f"{actual}5"] = round(gross * paid, 2)
        cells[f"{actual}6"] = bonus_paid
        cells[f"{yearly}6"] = BONUS[person]
        for row, rate in TAX_RATES.items():
            cells[f"{paycheck}{row}"] = round(gross * rate, 2)
            cells[f"{actual}{row}"] = round((gross * paid + bonus_paid) * rate, 2)
        cells[f"{paycheck}15"] = PRE_TAX_PER_PAYCHECK
        cells[f"{actual}15"] = PRE_TAX_PER_PAYCHECK * paid
        for row, rate in ((17, RETIREMENT_RATE), (18, MATCH_RATE)):
            cells[f"{paycheck}{row}"] = round(gross * rate, 2)
            cells[f"{actual}{row}"] = round(gross * rate * paid, 2)
    return cells


# ── Accounts, holdings and net worth ────────────────────────────────────────

# Fund and stock universe: symbol -> (name, price, yearly dividend yield,
# months it pays in). Prices are round, made-up figures.
SECURITIES = {
    "MSFT": ("Microsoft Corp", 415.0, 0.007, (3, 6, 9, 12)),
    "AAPL": ("Apple Inc", 232.0, 0.005, (2, 5, 8, 11)),
    "NVDA": ("NVIDIA Corp", 138.0, 0.0003, ()),
    "COST": ("Costco Wholesale Corp", 905.0, 0.006, (2, 5, 8, 11)),
    "JNJ": ("Johnson & Johnson", 158.0, 0.031, (3, 6, 9, 12)),
    "KO": ("Coca-Cola Co", 68.0, 0.030, (4, 7, 10, 12)),
    "PG": ("Procter & Gamble Co", 171.0, 0.024, (2, 5, 8, 11)),
    "JPM": ("JPMorgan Chase & Co", 238.0, 0.021, (1, 4, 7, 10)),
    "O": ("Realty Income Corp", 57.0, 0.055, tuple(range(1, 13))),
    "XOM": ("Exxon Mobil Corp", 112.0, 0.034, (3, 6, 9, 12)),
    "VTI": ("Vanguard Total Stock Market ETF", 292.0, 0.012, (3, 6, 9, 12)),
    "VXUS": ("Vanguard Total International Stock ETF", 64.0, 0.032, (6, 12)),
    "SCHD": ("Schwab US Dividend Equity ETF", 28.0, 0.034, (3, 6, 9, 12)),
    "QQQ": ("Invesco QQQ Trust", 510.0, 0.006, (3, 6, 9, 12)),
    "BND": ("Vanguard Total Bond Market ETF", 73.0, 0.036, tuple(range(1, 13))),
    "VYM": ("Vanguard High Dividend Yield ETF", 128.0, 0.029, (3, 6, 9, 12)),
    "BTC": ("Bitcoin", 94000.0, 0, ()),
    "ETH": ("Ethereum", 3300.0, 0, ()),
    "SOL": ("Solana", 190.0, 0, ()),
    "VFIAX": ("Vanguard 500 Index Fund Admiral Shares", 540.0, 0, ()),
    "VTIAX": (
        "Vanguard Total International Stock Index Fund Admiral Shares",
        40.0,
        0,
        (),
    ),
    "VBTLX": ("Vanguard Total Bond Market Index Fund Admiral Shares", 9.7, 0, ()),
    "VFIFX": ("Vanguard Target Retirement 2050 Fund", 62.0, 0, ()),
    "FXAIX": ("Fidelity 500 Index Fund", 215.0, 0, ()),
    "VTTSX": ("Vanguard Target Retirement 2060 Fund", 45.0, 0, ()),
}

# Positions as shares of an account's balance (the rest is cash). 401(k)s list
# each fund once per money source, as the real feeds do.
STOCK_WEIGHTS = {"MSFT": .16, "AAPL": .13, "NVDA": .11, "COST": .09, "JNJ": .09,
                 "KO": .09, "PG": .08, "JPM": .08, "O": .07, "XOM": .06}  # fmt: skip
ETF_WEIGHTS = {"VTI": 0.36, "VXUS": 0.18, "SCHD": 0.22, "QQQ": 0.14, "BND": 0.09}
CRYPTO_WEIGHTS = {"BTC": 0.62, "ETH": 0.28, "SOL": 0.09}
ROTH_WEIGHTS = {"SCHD": 0.34, "VTI": 0.30, "VYM": 0.20, "VXUS": 0.15}
TRAD_WEIGHTS = {"VBTLX": 0.45, "VFIAX": 0.40, "VTIAX": 0.14}
K401_WEIGHTS = {"VFIAX": 0.46, "VTIAX": 0.16, "VBTLX": 0.10, "VFIFX": 0.28}
PARTNER_K401_WEIGHTS = {"FXAIX": 0.62, "VTTSX": 0.38}


@dataclass
class Account:
    """One Net Worth row and the feed behind it."""

    section: int
    account: str
    type: str
    institution: str
    key: str
    share: float
    kind: str  # cash, saving, invest, retire, home, mortgage, card, loan, manual
    start: float  # balance at the end of last year
    flow: float = 0.0  # logged cash put in each month
    payroll: float = 0.0  # 401(k) and match, which isn't logged
    mu: float = 0.0  # monthly return
    sigma: float = 0.0
    feed_name: str = ""  # the SimpleFIN account name; blank = entered by hand
    owner: str = NAME  # whose bank_accounts_dump it comes from
    contribution: tuple = ()  # the Monthly Savings Contributions row it feeds
    weights: tuple = ()  # (symbols and weights) for holdings, if it has any
    sources: tuple = ()  # (suffix, share) account names a 401(k)'s funds split over


def _accounts() -> list:
    alex_payroll = PAY[NAME] * 2 * (RETIREMENT_RATE + MATCH_RATE)
    sam_payroll = PAY[PARTNER] * 2 * (RETIREMENT_RATE + MATCH_RATE)
    C, I, R, H, L = (
        bt.CASH,
        bt.INVESTMENTS,
        bt.RETIREMENT,
        bt.REAL_ESTATE,
        bt.LIABILITIES,
    )
    return [
        Account(C, "Checking", "Yours", "Atlas Bank", "(1042)", 1, "cash", 7200,
                sigma=0.22, feed_name="Everyday Checking (1042)"),
        Account(C, "Savings", "Yours", "Atlas Bank", "(2217)", 1, "saving", 21000,
                flow=800, mu=0.0034, feed_name="High-Yield Savings 4.10% APY (2217)",
                contribution=("Savings", "Individual")),
        Account(C, "Checking", "Partner's", "Harbor Credit Union", "(3380)", 0,
                "cash", 5600, sigma=0.25, feed_name="Share Checking (3380)",
                owner=PARTNER),
        Account(C, "Savings", "Partner's", "Harbor Credit Union", "(3391)", 0,
                "saving", 12500, flow=400, mu=0.0030,
                feed_name="Share Savings (3391)", owner=PARTNER),
        Account(C, "Joint Savings", "Joint", "Atlas Bank", "(7765)", 0.5, "saving",
                33000, flow=500, mu=0.0033, feed_name="Joint Savings 3.95% APY (7765)",
                contribution=("Savings", "Joint")),
        Account(I, "Brokerage", "Stocks", "Meridian Brokerage", "(5521)", 1, "invest",
                61000, flow=700, mu=0.006, sigma=0.032,
                feed_name="Individual Brokerage - Stocks (5521)",
                contribution=("Brokerage", "Stocks"),
                weights=tuple(STOCK_WEIGHTS.items())),
        Account(I, "Brokerage", "ETF", "Meridian Brokerage", "(5522)", 1, "invest",
                49000, flow=600, mu=0.006, sigma=0.024,
                feed_name="Individual Brokerage - ETFs (5522)",
                contribution=("Brokerage", "ETF"), weights=tuple(ETF_WEIGHTS.items())),
        Account(I, "Crypto", "Crypto", "Coinvault", "(9917)", 1, "invest", 6500,
                flow=100, mu=0.01, sigma=0.12, feed_name="Crypto Wallet (9917)",
                contribution=("Crypto", "Crypto"),
                weights=tuple(CRYPTO_WEIGHTS.items())),
        Account(I, "Bonds", "I-Bonds", "Treasury Direct", "I-Bonds", 1, "saving",
                9000, flow=100, mu=0.0035, contribution=("Bonds", "I-Bonds")),
        Account(R, "Retirement", "401k", "Summit Retirement", "(6630)", 1, "retire",
                128000, payroll=alex_payroll, mu=0.006, sigma=0.026,
                feed_name="Summit 401(k)", weights=tuple(K401_WEIGHTS.items()),
                sources=(("Pre-Tax", 0.75), ("Match", 0.25))),
        Account(R, "Retirement", "Roth IRA", "Summit Retirement", "(6634)", 1, "retire",
                41000, flow=6500 / 12, mu=0.006, sigma=0.028,
                feed_name="Summit Roth IRA (6634)",
                contribution=("Retirement", "Roth IRA"),
                weights=tuple(ROTH_WEIGHTS.items())),
        Account(R, "Retirement", "Traditional IRA", "Summit Retirement", "(6635)", 1,
                "retire", 18500, mu=0.007, sigma=0.02,
                feed_name="Summit Traditional IRA (6635)",
                weights=tuple(TRAD_WEIGHTS.items())),
        Account(R, "Retirement", "Partner's 401k", "Harbor Retirement", "(6701)", 0,
                "retire", 76000, payroll=sam_payroll, mu=0.006, sigma=0.026,
                feed_name="Harbor 401(k) (6701)", owner=PARTNER,
                weights=tuple(PARTNER_K401_WEIGHTS.items())),
        Account(H, "Real Estate", "Home Value", "", "Home Value", 0.5, "home", 598000,
                mu=0.0018, sigma=0.002),
        Account(H, "Liability", "Mortgage Balance (negative)", "Northwind Mortgage",
                "(8890)", 0.5, "mortgage", -392000, flow=500, feed_name="Home Mortgage (8890)",
                contribution=("Real Estate", "Extra Payments")),
        Account(L, "Liability", "Credit Card", "Atlas Bank", "(1188)", 1, "card",
                -1900, feed_name="Rewards Visa (1188)"),
        Account(L, "Liability", "Car Loan", "Harbor Credit Union", "(4471)", 1, "loan",
                -15600, feed_name="Auto Loan (4471)"),
    ]  # fmt: skip


PRINCIPAL_PER_MONTH = 760.0  # the mortgage's regular principal


def _simulate(account: Account, rng: random.Random, months: int, part: float) -> list:
    """Month-end balances for months 1..months (the last month, which is only
    part over, gets that part of the month's flows)."""
    value, series = account.start, []
    for month in range(1, months + 1):
        scale = part if month == months else 1.0
        if account.kind == "cash":
            value = account.start * (1 + rng.uniform(-account.sigma, account.sigma))
        elif account.kind == "card":
            value = -rng.uniform(1100, 3400)
        elif account.kind == "loan":
            value += 480 * scale
        elif account.kind == "mortgage":
            value += (PRINCIPAL_PER_MONTH + account.flow) * scale
        elif account.kind == "home":
            value *= 1 + account.mu + rng.uniform(-account.sigma, account.sigma)
        else:
            value = (
                value * (1 + rng.gauss(account.mu, account.sigma) * scale)
                + (account.flow + account.payroll) * scale
            )
        series.append(round(value, 2))
    return series


def _positions(weights: tuple, balance: float) -> list:
    """(symbol, shares, value) for each weighted holding."""
    result = []
    for symbol, weight in weights:
        price = SECURITIES[symbol][1]
        value = balance * weight
        result.append((symbol, round(value / price, 4), round(value, 2)))
    return result


def build_accounts_data(rng: random.Random, today: datetime.date, year: int) -> dict:
    """Simulate every account through today. Returns the Net Worth rows (past
    months frozen as values, this month live from Accounts), the Accounts
    tab's hand-entered balances, the SimpleFIN-style balances and holdings,
    and the Monthly Savings Contributions rows."""
    months = today.month if today.year == year else 12
    part = (
        today.day / _last_day(year, today.month)
        if today.year == year and today.day < _last_day(year, today.month)
        else 1.0
    )
    sections: list[list] = [[] for _ in range(5)]
    manual, bank, holdings = [], [], []
    contributions: dict[tuple, dict] = {}
    as_of = datetime.datetime.combine(today, datetime.time())

    for account in _accounts():
        series = _simulate(account, rng, months, part)
        current = series[-1]
        frozen = {m: series[m - 1] for m in range(1, months)}
        sections[account.section].append(
            bt.NetWorthRow(
                account.account, account.type, account.institution, account.key,
                account.share, months=frozen,
            )  # fmt: skip
        )
        if account.contribution:
            row = contributions.setdefault(account.contribution, {})
            for month in range(1, months + 1):
                row[month] = round(account.flow * (part if month == months else 1), 2)
        if not account.feed_name:
            manual.append(bt.ManualBalance(account.key, current))
            continue
        if account.sources:
            feeds = [
                (f"{account.feed_name} {suffix} {account.key}", current * fraction)
                for suffix, fraction in account.sources
            ]
        else:
            feeds = [(account.feed_name, current)]
        for name, balance in feeds:
            bank.append(
                (account.owner, [account.institution, name, round(balance, 2), as_of])
            )
            for symbol, shares, value in _positions(account.weights, balance):
                description, price = SECURITIES[symbol][0], SECURITIES[symbol][1]
                holdings.append([
                    account.institution, name, symbol, description, shares, value,
                    round(value * 0.78, 2), round(price * 0.78, 2), "USD", as_of,
                ])  # fmt: skip
    contribution_rows = [
        bt.ContributionRow(kind, detail, months)
        for (kind, detail), months in contributions.items()
    ]
    for row in bt.default_contributions():
        if (row.type, row.detail) not in contributions:
            contribution_rows.append(row)  # a row with no money in it yet
    return {
        "net_worth": sections,
        "manual": manual,
        "bank": bank,
        "holdings": holdings,
        "contributions": contribution_rows,
    }


# ── Dividends ───────────────────────────────────────────────────────────────


def build_dividends(
    holdings: list,
    today: datetime.date,
    rng: random.Random,
    history_months: int = 14,
    institutions: tuple = ("Meridian Brokerage", "Summit Retirement"),
) -> tuple[list, float]:
    """The dividend ledger's rows, from `history_months` back, for every
    dividend-paying holding in the given institutions' accounts (401(k)s
    excluded), plus the yearly dividend those positions project."""
    rows, projected, number = [], 0.0, 1
    start = (pd_month_back(today, history_months)).replace(day=1)
    for h in holdings:
        institution, account, symbol, name, shares, value = h[:6]
        _, price, dividend_yield, pay_months = SECURITIES[symbol]
        if not pay_months or institution not in institutions:
            continue
        if "401(k)" in account:
            continue
        per_payment = price * dividend_yield / len(pay_months)
        projected += per_payment * shares * len(pay_months)
        cursor = start
        while cursor <= today:
            if cursor.month in pay_months:
                posted = cursor.replace(
                    day=min(15, _last_day(cursor.year, cursor.month))
                )
                if posted <= today:
                    # earlier payments were on fewer shares
                    age = (today - posted).days / 365
                    amount = (
                        per_payment
                        * shares
                        * (1 - 0.06 * age)
                        * rng.uniform(0.98, 1.02)
                    )
                    rows.append([
                        f"DIV-{number:05d}",
                        datetime.datetime.combine(posted, datetime.time()),
                        institution, account, name,
                        f"DIVIDEND RECEIVED {name.upper()} ({symbol}) (Cash)",
                        round(amount, 2), symbol,
                    ])  # fmt: skip
                    number += 1
            cursor = (cursor.replace(day=28) + datetime.timedelta(days=4)).replace(
                day=1
            )
    rows.sort(key=lambda r: r[1])
    return rows, round(projected, 2)


def pd_month_back(day: datetime.date, months: int) -> datetime.date:
    index = day.year * 12 + day.month - 1 - months
    return datetime.date(index // 12, index % 12 + 1, 1)


# ── The workbook ────────────────────────────────────────────────────────────


def _write_table(ws, header: list, rows: list, first_row: int = 1, money_cols=()):
    for col, label in enumerate(header, start=1):
        ws.cell(row=first_row, column=col, value=label).font = bt.HEADER_FONT
        ws.cell(row=first_row, column=col).fill = bt.HEADER_FILL
    for r, values in enumerate(rows, start=first_row + 1):
        for col, value in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            if isinstance(value, datetime.datetime):
                cell.number_format = "yyyy-mm-dd"
            elif col in money_cols:
                cell.number_format = bt.MONEY
    for col in range(1, len(header) + 1):
        ws.column_dimensions[bt.column_letter(col)].width = 22
    ws.freeze_panes = ws.cell(row=first_row + 1, column=1)


def add_holdings_tabs(
    wb,
    holdings: list,
    today: datetime.date,
    year: int,
    rng: random.Random,
    institutions: tuple = ("Meridian Brokerage", "Summit Retirement"),
):
    """The tabs FinanceToSheets writes beside the budget: holdings_dump,
    dividends_ledger (for the given institutions' dividend payers) and the
    Stocks tab's projected yearly dividend (K3)."""
    _write_table(wb.create_sheet(HOLDINGS_TAB), HOLDINGS_COLUMNS, holdings,
                 money_cols=(6, 7, 8))  # fmt: skip

    dividends, projected = build_dividends(
        holdings, today, rng, institutions=institutions
    )
    ledger = wb.create_sheet(DIVIDENDS_TAB)
    ledger["A1"] = "Dividend ledger (demo data)"
    ledger["A1"].font = bt.TITLE_FONT
    last = DIVIDENDS_HEADER_ROW + len(dividends) + 100
    for col, institution in enumerate(institutions, start=2):
        letter = bt.column_letter(col)
        ledger[f"{letter}2"] = institution
        ledger[f"{letter}3"] = (
            f"=SUMIFS($G$7:$G${last},$C$7:$C${last},{letter}$2,"
            f'$B$7:$B${last},">="&DATE({year},1,1))'
        )
        ledger[f"{letter}4"] = f"=SUMIFS($G$7:$G${last},$C$7:$C${last},{letter}$2)"
    total = bt.column_letter(len(institutions) + 2)
    first, last_col = "B", bt.column_letter(len(institutions) + 1)
    ledger[f"{total}2"] = "Total"
    ledger[f"{total}3"] = f"=SUM({first}3:{last_col}3)"
    ledger[f"{total}4"] = f"=SUM({first}4:{last_col}4)"
    ledger["A3"], ledger["A4"] = "This year", "All time"
    for col in range(2, len(institutions) + 3):
        for row in (3, 4):
            ledger.cell(row=row, column=col).number_format = bt.MONEY
    _write_table(ledger, DIVIDEND_COLUMNS, dividends, first_row=DIVIDENDS_HEADER_ROW,
                 money_cols=(7,))  # fmt: skip

    stocks = wb.create_sheet(STOCKS_TAB)
    stocks["K2"] = "Projected yearly dividend"
    stocks["K2"].font = bt.TOTAL_FONT
    stocks["K3"] = projected
    stocks["K3"].number_format = bt.MONEY


def build_demo_workbook(
    today: datetime.date | None = None, seed: int = 7, year: int | None = None
):
    """The demo household's spreadsheet as an openpyxl Workbook."""
    today = today or datetime.date.today()
    year = year or today.year
    rng = random.Random(seed)

    expenses = generate_expenses(rng, year, today)
    name_rows, partner_rows = expense_logs(expenses)
    data = build_accounts_data(rng, today, year)
    spec = bt.BudgetSpec(
        name=NAME,
        partner=PARTNER,
        year=year,
        budget=bt.BudgetCells(income_overrides(today, year)),
        categories=[
            bt.Category(group, name, budget, in_totals)
            for group, name, budget, in_totals in CATEGORIES
        ],
        expense_rows=name_rows,
        partner_expense_rows=partner_rows,
        manual_balances=data["manual"],
        net_worth=data["net_worth"],
        contributions=data["contributions"],
    )
    wb = bt.build_workbook(spec)

    # What IMPORTRANGE of each person's bank_accounts_dump would fill in
    accounts = wb[bt.ACCOUNTS]
    for first_col, owner in ((7, NAME), (12, PARTNER)):
        rows = [row for who, row in data["bank"] if who == owner]
        for offset, values in enumerate(rows):
            for col, value in enumerate(values):
                cell = accounts.cell(
                    row=5 + offset, column=first_col + col, value=value
                )
                if col == 2:
                    cell.number_format = bt.MONEY
                elif col == 3:
                    cell.number_format = "yyyy-mm-dd"

    bank_rows = [row for _, row in data["bank"]]
    _write_table(wb.create_sheet(BANK_ACCOUNTS_TAB), BANK_COLUMNS, bank_rows,
                 money_cols=(3,))  # fmt: skip
    add_holdings_tabs(wb, data["holdings"], today, year, rng)
    return wb


def main():
    parser = argparse.ArgumentParser(
        description="Write the demo household's budget sheet"
    )
    parser.add_argument("--out", default="Demo Budget - 2026.xlsx")
    parser.add_argument("--today", help="YYYY-MM-DD; default today")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    today = datetime.date.fromisoformat(args.today) if args.today else None
    build_demo_workbook(today, args.seed).save(args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
