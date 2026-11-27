import datetime

import openpyxl
import pandas as pd
import pytest

from src import demo_anonymize as da
from src import personal_finance as pf
from tests.test_budget_template import _has_calc, _recalculate

TODAY = datetime.date(2026, 11, 27)
SHEET_ID = "1" + "x" * 43  # what an IMPORTRANGE's spreadsheet id looks like


def _dummy(formula: str, cached) -> str:
    """How Google Sheets' .xlsx export wraps a function Excel lacks."""
    inner = formula[1:].replace('"', '""')
    return f'=IFERROR(__xludf.DUMMYFUNCTION("{inner}"),{cached!r})'


def _real_looking_sheet(path):
    """A made-up sheet in the layout of the real export, with names, figures
    and Google-wrapped formulas that must not survive anonymizing."""
    wb = openpyxl.Workbook()
    log = wb.active
    log.title = "Expense Log"
    log.append(["Date", "Amount", "Category", "Description", "Details", "Split Type",
                "Participant Names", "My Paid", "My Owed", "My Net", "Splitwise ID",
                "Transaction Fingerprint"])  # fmt: skip
    log.append([datetime.datetime(2026, 1, 3), 123.45, "Groceries", "Zebra Pantry Co",
                "Sunday run", "partner", "Quincy Rivera, Blake Jones", 123.45, 61.72,
                61.73, 4242, "fingerprint-zebra-9f3"])  # fmt: skip
    log["D2"].hyperlink = "https://example.com/receipt/zebra"

    budget = wb.create_sheet("Budget")
    budget["C3"], budget["D3"] = "Actual Yearly", "Budget Yearly"
    budget["B5"], budget["F5"], budget["C5"] = "Gross Salary", 12345.67, 296296.08
    budget["E5"], budget["D5"] = "=F5*2", "=E5*12"
    budget["B6"], budget["C6"], budget["D6"] = "Bonus", 55555, 55555
    budget["B9"], budget["C9"] = "Federal Tax", 77777.77
    budget["D9"] = "=(E9*12)+(0.4*D6*0.6)"
    budget["B10"], budget["C10"] = "State Tax", "=3690.29+22394.63"
    budget["A14"], budget["A15"], budget["B15"] = "PRE-TAX", None, "Commuter card"
    budget["C15"], budget["E15"] = 4321, 360.08
    budget["A19"], budget["C19"] = "💵 Take-Home Pay", "=C5+C6-C9-C10"
    budget["A20"] = "EXPENSES"
    for row, (group, name) in enumerate(
        [("Food and drink", "Groceries"), ("Home", "Mortgage")], start=21
    ):
        budget[f"A{row}"], budget[f"B{row}"], budget[f"D{row}"] = group, name, 98765
    budget["B23"] = "Total Expenses"

    savings = wb.create_sheet("Savings Log")
    savings["A1"], savings["B1"] = "Conversion Rate", _dummy(
        '=GOOGLEFINANCE("X")', 0.0105
    )
    savings["A5"], savings["B5"] = "Zenith Stocks Close", 88888.88
    savings["A9"], savings["B9"] = "Stock Gain/Loss", "=-1164.22-2386.94"
    savings["A10"] = "Dividends Received "
    savings["B10"] = _dummy(f'=753.86+IMPORTRANGE("{SHEET_ID}", "Stocks!D5")', 900)
    savings["A11"], savings["B11"] = "Interest", 31337.13
    savings["D1"] = _dummy(f'=IMPORTRANGE("{SHEET_ID}", "bank_accounts_dump!A1:D25")',
                           "Institution")  # fmt: skip
    for row, (inst, name, balance) in enumerate(
        [("Zenith Bank", "Checking Plus (4455)", 5432.1),
         ("Quartz Brokerage", "Individual Stocks (9911)", 88888.88)], start=2
    ):  # fmt: skip
        savings[f"D{row}"] = _dummy('="COMPUTED_VALUE"', inst)
        savings[f"E{row}"] = _dummy('="COMPUTED_VALUE"', name)
        savings[f"F{row}"] = _dummy('="COMPUTED_VALUE"', balance)

    nw = wb.create_sheet("Net Worth")
    for month, name in enumerate(da.MONTHS):
        nw.cell(row=4, column=5 + month, value=name)
    layout = {
        5: ("Cash Accounts", None, None, None),
        6: (None, "Checking ", "Individual", "Zenith Bank"),
        7: ("Subtotal – Checking & Savings", None, None, None),
        9: ("INVESTMENTS", None, None, None),
        10: (None, "Brokerage", "Stocks", "Quartz Brokerage"),
        11: ("Subtotal – Investments", None, None, None),
        13: ("RETIREMENT", None, None, None),
        14: (None, "Retirement", "401k", "Quartz Brokerage"),
        15: ("Subtotal – Retirement", None, None, None),
        17: ("REAL ESTATE", None, None, None),
        18: (None, "Real Estate", "Home Value", None),
        19: (None, "Liability", "Mortgage Balance", None),
        20: ("Subtotal – Real Estate", None, None, None),
        22: ("LIABILITIES", None, None, None),
        23: (None, "Liability", "Credit Card", "Zenith Bank (1234)"),
        24: ("Subtotal – Liabilities", None, None, None),
        26: ("NET WORTH (Assets − Liabilities)", None, None, None),
        28: ("Monthly Savings Contributions  (enter cash deposited each month)",
             None, None, None),
        29: (None, "Brokerage", "Stocks", None),
        30: ("Total Contributed (YTD)", None, None, None),
    }  # fmt: skip
    for row, (a, b, c, d) in layout.items():
        nw[f"A{row}"], nw[f"B{row}"], nw[f"C{row}"], nw[f"D{row}"] = a, b, c, d
    for col in range(5, 15):  # Jan-Oct hard-coded
        for row, value in ((6, 4321.09), (10, 77777.7), (14, 150000.5), (18, 999999.99),
                           (19, 333333.33), (23, -1234.56)):  # fmt: skip
            nw.cell(row=row, column=col, value=value)
        nw.cell(row=29, column=col, value=987.65)
    for col in (15, 16):  # Nov-Dec live
        nw.cell(row=6, column=col, value="='Savings Log'!$F$2")
        nw.cell(row=10, column=col, value="='Savings Log'!$F$3")
        nw.cell(row=14, column=col, value="='Savings Log'!$B$5")
        nw.cell(row=18, column=col, value="=1555000*0.6")
        nw.cell(row=19, column=col, value="=-0.6*'Savings Log'!$F$3")
        nw.cell(row=23, column=col, value=-4567.89)
    for col in range(5, 17):
        letter = openpyxl.utils.get_column_letter(col)
        nw[f"{letter}7"] = f"=SUM({letter}6:{letter}6)"
        nw[f"{letter}11"] = f"=SUM({letter}10:{letter}10)"
        nw[f"{letter}15"] = f"=SUM({letter}14:{letter}14)"
        nw[f"{letter}20"] = f"={letter}18-{letter}19"
        nw[f"{letter}24"] = f"=SUM({letter}23:{letter}23)"
        nw[f"{letter}26"] = (
            f"=SUM({letter}7,{letter}11,{letter}15,{letter}20,{letter}24)"
        )
        nw[f"{letter}30"] = f"=SUM({letter}29:{letter}29)"

    dash = wb.create_sheet("Dashboard")
    dash["A5"] = _dummy(
        "=IFERROR(SORT('Monthly Expenses'!A5:A47, 1, FALSE))", "Zebra Cat"
    )
    dash["B5"] = _dummy('="COMPUTED_VALUE"', 31415.92)
    wb.properties.creator = "Quincy Rivera"
    wb.save(path)


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    source = tmp_path_factory.mktemp("real") / "real.xlsx"
    _real_looking_sheet(source)
    return str(source), da.anonymize(str(source), TODAY, seed=7)


class TestScrubCached:
    def test_keeps_the_formula_and_empties_the_cached_result(self):
        wrapped = _dummy("=SORT(A1:A9, 1, FALSE)", "Secret Merchant")
        assert da._scrub_cached(wrapped) == (
            '=IFERROR(__xludf.DUMMYFUNCTION("SORT(A1:A9, 1, FALSE)"),"")'
        )

    def test_handles_parentheses_and_quotes_inside_the_formula(self):
        wrapped = _dummy('=IF(A1="a)b", (1+2), "x")', 55.5)
        assert da._scrub_cached(wrapped).endswith('""x"")"),"")')
        assert "55.5" not in da._scrub_cached(wrapped)

    def test_other_values_pass_through(self):
        assert da._scrub_cached("=SUM(A1:A2)") == "=SUM(A1:A2)"
        assert da._scrub_cached(12.5) == 12.5


class TestNames:
    def test_one_real_institution_is_one_fake_one_per_role(self):
        names = da._Names()
        first = names.institution("Acme ", "bank")
        assert first == names.institution(" ACME", "bank")
        assert first in da.POOLS["bank"]
        assert names.institution("Acme", "broker") in da.POOLS["broker"]

    def test_each_kind_of_account_draws_from_its_own_pool(self):
        names = da._Names()
        for role in (
            "bank",
            "broker",
            "retirement",
            "crypto",
            "overseas",
            "card",
            "loan",
        ):
            assert names.institution("x", role) in da.POOLS[role]

    def test_a_name_the_real_sheet_also_uses_is_skipped(self):
        taken = {da._norm(da.POOLS["bank"][0])}
        names = da._Names(avoid=taken)
        assert names.institution("anything", "bank") == da.POOLS["bank"][1]

    def test_the_pool_wraps_with_a_number_when_it_runs_out(self):
        names = da._Names()
        pool = da.POOLS["loan"]
        found = [names.institution(f"lender {i}", "loan") for i in range(len(pool) + 1)]
        assert found[: len(pool)] == pool and found[-1] == f"{pool[0]} 2"

    def test_blank_stays_blank(self):
        assert da._Names().institution(None, "bank") is None

    @pytest.mark.parametrize(
        "section, b, c, role",
        [
            ("cash accounts", "Checking", "Individual", "bank"),
            ("cash accounts", "Brokerage", "Uninvested", "broker"),
            ("cash accounts", "Savings", "Foreign", "overseas"),
            ("investments", "Brokerage", "Crypto", "crypto"),
            ("investments", "Brokerage", "ETF", "broker"),
            ("investments", "Bonds", "I-Bonds", "bonds"),
            ("retirement", "Retirement", "401k", "retirement"),
            ("liabilities", "Liability", "Credit Card", "card"),
            ("liabilities", "Liability", "Car Loan", "loan"),
        ],
    )
    def test_role_comes_from_the_generic_labels(self, section, b, c, role):
        assert da._role(section, b, c) == role


class TestAnonymize:
    def test_nothing_personal_survives(self, demo):
        source, wb = demo
        assert da.leaks(source, wb) == []
        assert da.leaked_numbers(source, wb) == []
        assert da.audit(wb) == []
        assert wb.properties.creator == "Demo"

    def test_every_tab_of_the_real_sheet_is_kept_and_the_pipeline_tabs_added(
        self, demo
    ):
        _, wb = demo
        assert wb.sheetnames[:5] == ["Expense Log", "Budget", "Savings Log", "Net Worth",
                                     "Dashboard"]  # fmt: skip
        assert {"holdings_dump", "dividends_ledger", "Stocks"} <= set(wb.sheetnames)

    def test_expense_log_is_a_fresh_year_in_the_same_columns(self, demo):
        _, wb = demo
        ws = wb["Expense Log"]
        assert [c.value for c in ws[1]][:3] == ["Date", "Amount", "Category"]
        rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
        assert len(rows) > 300 and all(len(r) == 12 for r in rows)
        assert not any(c.hyperlink for row in ws.iter_rows() for c in row)

    def test_pay_inputs_are_replaced_and_hard_coded_constants_gone(self, demo):
        _, wb = demo
        ws = wb["Budget"]
        assert ws["C5"].value == da.SALARY and ws["F5"].value == round(
            da.SALARY / 24, 2
        )
        assert ws["E5"].value == "=F5*2"  # structure stays
        assert "0.4" not in ws["D9"].value and "3690" not in str(ws["C10"].value)
        assert ws["C15"].value == da.COMMUTER_YEARLY
        assert ws["D21"].value != 98765

    def test_live_months_read_the_savings_log_like_the_real_sheet(self, demo):
        _, wb = demo
        nw, log = wb["Net Worth"], wb["Savings Log"]
        assert nw["O6"].value.startswith("='Savings Log'!$F$")
        assert nw["O6"].value == nw["P6"].value
        row = int(nw["O6"].value.rsplit("$", 1)[1])
        assert log[f"D{row}"].value in da.POOLS["bank"]
        mortgage = nw["O19"].value
        assert mortgage.startswith("=-'Savings Log'!")  # the mortgage is held positive

    def test_savings_log_keeps_the_labels_the_parser_reads(self, demo):
        _, wb = demo
        matrix = [[c.value for c in row] for row in wb["Savings Log"].iter_rows()]
        assert set(pf.parse_savings_log(matrix)) == {
            "stock_gain",
            "dividends",
            "interest",
        }


@pytest.mark.skipif(not _has_calc(), reason="needs LibreOffice Calc")
class TestDashboardReadsIt:
    @pytest.fixture(scope="class")
    def calc(self, tmp_path_factory, demo):
        return _recalculate(demo[1], tmp_path_factory.mktemp("anon"))

    def matrix(self, calc, tab):
        def convert(v):
            if isinstance(v, datetime.datetime):
                return (v - datetime.datetime(1899, 12, 30)).days
            return "" if v is None else v

        return [[convert(v) for v in r] for r in calc[tab].iter_rows(values_only=True)]

    def test_net_worth_current_month_matches_the_savings_log(self, calc):
        nw = calc["Net Worth"]
        balances = {r[3].value: r[5].value for r in calc["Savings Log"].iter_rows(min_row=2)
                    if r[3].value}  # fmt: skip
        assert nw["O6"].value in balances.values()
        assert nw["O7"].value == pytest.approx(nw["O6"].value)

    def test_parsers_read_spending_budget_and_net_worth(self, calc):
        today = pd.Timestamp(TODAY)
        months = pf.months_of(2026, today)
        expenses = pf.parse_expense_logs({"Expense Log": self.matrix(calc, "Expense Log")},
                                         2026, today)  # fmt: skip
        net_worth = pf.parse_net_worth(self.matrix(calc, "Net Worth"), months)
        items = pf.parse_budget_items(self.matrix(calc, "Budget"))
        assert expenses["my_share"].sum() > 20_000
        assert net_worth[pf.NET_WORTH].iloc[-1] > 0
        assert items["take_home"][0] > 50_000

    def test_each_investment_row_matches_its_holdings(self, calc):
        today = pd.Timestamp(TODAY)
        months = pf.months_of(2026, today)
        accounts = pf.net_worth_accounts(self.matrix(calc, "Net Worth"), months)
        rows = self.matrix(calc, "holdings_dump")
        holdings = pd.DataFrame(rows[1:], columns=rows[0])
        sources = pf.holdings_accounts(accounts, holdings)
        invested = accounts[accounts["Category"].isin(pf.INVESTED)]
        assert len(invested) == 2
        for i in invested.index:
            assert sources[i]
            held = pf.account_holdings(holdings, accounts.loc[i], sources[i])
            assert held["Value"].sum() == pytest.approx(accounts.at[i, "Balance"])
