import pytest

from src import dashboard_nav as nav


class TestNavLinks:
    def test_defaults_are_the_servers_own_paths(self, monkeypatch):
        for var in (
            "FINANCE_DASHBOARD_URL",
            "NET_WORTH_DASHBOARD_URL",
            "PNL_DASHBOARD_URL",
            "SPENDING_DASHBOARD_URL",
        ):
            monkeypatch.delenv(var, raising=False)
        assert nav.nav_links(nav.OVERVIEW) == [
            ("Yearly Overview", "/", True, False),
            ("Net Worth", "/net-worth", False, False),
        ]

    def test_swing_trading_link_appears_once_its_url_is_set(self, monkeypatch):
        monkeypatch.setenv("PNL_DASHBOARD_URL", "https://pnl.example.com")
        assert (
            "Swing Trading",
            "https://pnl.example.com",
            False,
            True,
        ) in nav.nav_links(nav.OVERVIEW)

    def test_spending_link_appears_once_its_url_is_set(self, monkeypatch):
        monkeypatch.setenv("SPENDING_DASHBOARD_URL", "https://spending.example.com")
        assert (
            "Spending",
            "https://spending.example.com",
            False,
            True,
        ) in nav.nav_links(nav.OVERVIEW)

    def test_html_marks_the_current_page_and_escapes(self, monkeypatch):
        monkeypatch.setenv("SPENDING_DASHBOARD_URL", "https://x.example/?a=1&b=2")
        monkeypatch.setenv("PNL_DASHBOARD_URL", "https://pnl.example.com")
        page = nav.nav_html(nav.OVERVIEW)
        assert '<a href="/" target="_top" class="active">Yearly Overview</a>' in page
        assert 'href="https://x.example/?a=1&amp;b=2"' in page
        assert ">Swing Trading<svg" in page

    def test_separate_apps_get_the_external_icon(self, monkeypatch):
        monkeypatch.setenv("SPENDING_DASHBOARD_URL", "https://spending.example.com")
        monkeypatch.setenv("PNL_DASHBOARD_URL", "https://pnl.example.com")
        page = nav.nav_html(nav.OVERVIEW)
        assert page.count('class="t-nav-ext"') == 2
        assert ">Yearly Overview</a>" in page
        assert ">Net Worth</a>" in page


class TestDemoTag:
    def test_no_tag_on_the_real_app(self, monkeypatch):
        monkeypatch.delenv("DEMO_MODE", raising=False)
        assert "t-nav-demo" not in nav.nav_html(nav.OVERVIEW).split("</style>")[1]

    @pytest.mark.parametrize("flag", ["1", "true", "YES", " on "])
    def test_demo_data_tag_in_the_menu_bar(self, monkeypatch, flag):
        monkeypatch.setenv("DEMO_MODE", flag)
        bar = nav.nav_html(nav.OVERVIEW).split("</style>")[1]
        assert '<span class="t-nav-demo"' in bar and "Demo data" in bar

    def test_other_values_leave_it_off(self, monkeypatch):
        monkeypatch.setenv("DEMO_MODE", "0")
        assert not nav.demo_mode()
