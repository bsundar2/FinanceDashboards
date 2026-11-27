import datetime

import openpyxl
import pandas as pd
import pytest

from src import budget_template as bt
from src import demo_data as dd
from src import personal_finance as pf
from tests.test_budget_template import _has_calc, _recalculate

TODAY = datetime.date(2026, 11, 27)


@pytest.fixture(scope="module")
def built():
    return dd.build_demo_workbook(TODAY, seed=7)


def _rows(ws, first=2):
    return [list(r) for r in ws.iter_rows(min_row=first, values_only=True)]


class TestExpenses:
    def test_same_seed_gives_the_same_year(self):
        a = dd.build_demo_workbook(TODAY, seed=3)[bt.EXPENSE_LOG]
        b = dd.build_demo_workbook(TODAY, seed=3)[bt.EXPENSE_LOG]
        assert _rows(a) == _rows(b)

    def test_nothing_is_dated_after_today_or_outside_the_year(self, built):
        dates = [r[0].date() for r in _rows(built[bt.EXPENSE_LOG])]
        assert min(dates) >= datetime.date(2026, 1, 1) and max(dates) <= TODAY

    def test_a_shared_bill_is_in_both_logs_and_owed_adds_up(self, built):
        mine = {r[11]: r for r in _rows(built[bt.EXPENSE_LOG]) if r[5] == "partner"}
        theirs = {r[11]: r for r in _rows(built[bt.PARTNER_EXPENSE_LOG])}
        assert mine and set(mine) <= set(theirs)
        for expense_id, row in mine.items():
            assert row[8] + theirs[expense_id][8] == pytest.approx(row[1])
            assert row[7] + theirs[expense_id][7] == pytest.approx(row[1])

    def test_personal_expenses_stay_in_their_owners_log(self, built):
        own = [r for r in _rows(built[bt.EXPENSE_LOG]) if r[5] == "self"]
        assert own and all(r[7] == r[8] == r[1] for r in own)

    def test_a_few_big_one_offs_for_the_picker(self, built):
        amounts = [r[1] for r in _rows(built[bt.EXPENSE_LOG]) if r[5] == "partner"]
        assert sum(a >= 1000 for a in amounts) >= 6


class TestPipelineTabs:
    def test_tabs_use_the_pipelines_columns(self, built):
        assert [c.value for c in built[dd.BANK_ACCOUNTS_TAB][1]] == dd.BANK_COLUMNS
        assert [c.value for c in built[dd.HOLDINGS_TAB][1]] == dd.HOLDINGS_COLUMNS
        ledger = built[dd.DIVIDENDS_TAB]
        header = [c.value for c in ledger[dd.DIVIDENDS_HEADER_ROW]]
        assert header == dd.DIVIDEND_COLUMNS

    def test_each_brokerage_feed_is_fully_invested_or_holds_some_cash(self, built):
        balances = {r[1]: r[2] for r in _rows(built[dd.BANK_ACCOUNTS_TAB])}
        invested: dict = {}
        for row in _rows(built[dd.HOLDINGS_TAB]):
            invested[row[1]] = invested.get(row[1], 0) + row[5]
        assert invested
        for name, value in invested.items():
            assert 0.9 * balances[name] <= value <= balances[name] + 1

    def test_projected_dividend_sits_in_stocks_k3(self, built):
        assert built[dd.STOCKS_TAB]["K3"].value > 0

    def test_dividends_are_not_in_the_future(self, built):
        ledger = built[dd.DIVIDENDS_TAB]
        rows = _rows(ledger, dd.DIVIDENDS_HEADER_ROW + 1)
        assert rows and max(r[1].date() for r in rows) <= TODAY
        assert len({r[0] for r in rows}) == len(rows)  # unique transaction ids


@pytest.mark.skipif(not _has_calc(), reason="needs LibreOffice Calc")
class TestDashboardReadsIt:
    @pytest.fixture(scope="class")
    def calc(self, tmp_path_factory):
        wb = dd.build_demo_workbook(TODAY, seed=7)
        return _recalculate(wb, tmp_path_factory.mktemp("demo"))

    def matrix(self, calc, tab):
        def convert(v):
            if isinstance(v, datetime.datetime):
                return (v - datetime.datetime(1899, 12, 30)).days
            return "" if v is None else v

        return [[convert(v) for v in r] for r in calc[tab].iter_rows(values_only=True)]

    def test_parsers_read_spending_budget_and_net_worth(self, calc):
        today = pd.Timestamp(TODAY)
        months = pf.months_of(2026, today)
        workbook = {t: self.matrix(calc, t) for t in bt.EXPENSE_LOGS}
        expenses = pf.parse_expense_logs(workbook, 2026, today)
        budgets = pf.parse_category_budgets(self.matrix(calc, bt.MONTHLY_EXPENSES))
        net_worth = pf.parse_net_worth(self.matrix(calc, bt.NET_WORTH), months)
        items = pf.parse_budget_items(self.matrix(calc, bt.BUDGET))

        assert len(expenses) > 500 and expenses["my_share"].sum() > 50_000
        assert len(budgets) == len(dd.CATEGORIES)
        assert net_worth[pf.NET_WORTH].iloc[-1] > net_worth[pf.NET_WORTH].iloc[0] > 0
        assert items["take_home"][0] > 0 and "take_home_savings" in items

    def test_every_account_row_reconciles_with_its_holdings(self, calc):
        today = pd.Timestamp(TODAY)
        months = pf.months_of(2026, today)
        accounts = pf.net_worth_accounts(self.matrix(calc, bt.NET_WORTH), months)
        holdings_rows = self.matrix(calc, dd.HOLDINGS_TAB)
        holdings = pd.DataFrame(holdings_rows[1:], columns=holdings_rows[0])
        sources = pf.holdings_accounts(accounts, holdings)
        invested = accounts[accounts["Category"].isin(pf.INVESTED)]
        assert len(invested) == 8
        for i in invested.index:
            rows = pf.account_holdings(holdings, accounts.loc[i], sources[i])
            assert rows["Value"].sum() == pytest.approx(accounts.at[i, "Balance"])
        # Everything but the hand-entered I-Bonds row has securities behind it
        assert [i for i in invested.index if not sources[i]] == [
            accounts.index[accounts["Key"] == "I-Bonds"][0]
        ]

    def test_dividend_ledger_and_projection_parse(self, calc):
        ledger = self.matrix(calc, dd.DIVIDENDS_TAB)
        header = next(i for i, r in enumerate(ledger) if "Transaction ID" in r)
        raw = pd.DataFrame(
            ledger[header + 1 :], columns=[str(c) for c in ledger[header]]
        )
        dividends = pf.parse_dividends(raw)
        run_rate = pf.dividend_run_rate(dividends, pd.Timestamp(TODAY))
        assert set(dividends["institution"]) == {
            "Meridian Brokerage",
            "Summit Retirement",
        }
        assert run_rate and not run_rate["estimated"]
        assert calc[dd.STOCKS_TAB]["K3"].value > 0


@pytest.mark.skipif(not _has_calc(), reason="needs LibreOffice Calc")
class TestStoredResults:
    @pytest.fixture(scope="class")
    def saved(self, tmp_path_factory):
        path = tmp_path_factory.mktemp("stored") / "demo.xlsx"
        dd.build_demo_workbook(TODAY, seed=7).save(path)
        return path, dd.add_cached_values(str(path))

    def test_formula_tabs_show_numbers_in_a_viewer_that_does_not_recalculate(
        self, saved
    ):
        path, filled = saved
        shown = openpyxl.load_workbook(path, data_only=True)
        assert filled > 500
        assert shown[bt.BUDGET]["C7"].value > 0
        assert shown[bt.MONTHLY_EXPENSES]["B5"].value  # a category name from a formula
        assert shown[bt.DASHBOARD]["A5"].value is not None

    def test_the_formulas_are_still_there_for_google_sheets(self, saved):
        path, _ = saved
        formulas = openpyxl.load_workbook(path)
        assert formulas[bt.BUDGET]["D5"].value == "=Income!D5+Income!I5"
