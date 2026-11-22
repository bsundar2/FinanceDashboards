import marimo

__generated_with = "0.6.0"
app = marimo.App(width="full", html_head_file="heartbeat_head.html")


@app.cell
def __():
    import html

    import marimo as mo
    import pandas as pd

    from src import personal_finance as pf
    from src.dashboard_nav import OVERVIEW, nav_html
    from src.finance_ui import (
        PALETTE,
        STYLE,
        fold,
        kpi_row,
        kpi_tile,
        legend,
        money,
        stacked_bars_svg,
        stat_tile,
        table,
    )
    from src.finance_widgets import ShareBar

    return (
        OVERVIEW,
        PALETTE,
        STYLE,
        ShareBar,
        fold,
        html,
        kpi_row,
        kpi_tile,
        legend,
        mo,
        money,
        nav_html,
        pd,
        pf,
        stacked_bars_svg,
        stat_tile,
        table,
    )


@app.cell
def __(OVERVIEW, mo, nav_html):
    mo.Html(nav_html(OVERVIEW))
    return


@app.cell
def __(STYLE, mo):
    # ── Same dark look as the P&L and spending dashboards ──────────────────
    mo.Html(STYLE)
    return


@app.cell
def __(mo):
    reload = mo.ui.button(
        label="↻ Reload from Sheets", value=0, on_click=lambda n: n + 1
    )
    include_one_offs = mo.ui.checkbox(label="Include them", value=True)
    emergency_months = mo.ui.number(start=1, stop=24, step=1, value=6)
    return emergency_months, include_one_offs, reload


@app.cell
def __(mo, pd, pf, reload):
    # ── Load the budget spreadsheet (re-runs on Reload) ─────────────────────
    reload.value
    spreadsheet_name = pf.budget_spreadsheet_name()
    today = pd.Timestamp.today().normalize()
    try:
        workbook = pf.load_budget_workbook(spreadsheet_name)
        load_error = None
    except Exception as e:  # shown on the page instead of a stack trace
        workbook, load_error = None, f"{type(e).__name__}: {e}"
    return load_error, spreadsheet_name, today, workbook


@app.cell
def __(pf, reload, spreadsheet_name, today, load_error):
    # ── Optional extras: each leaves its section out if it can't be read ────
    reload.value
    _year = pf.budget_year(spreadsheet_name, today)
    previous_expenses = (
        None
        if load_error
        else pf.load_previous_year_expenses(spreadsheet_name, _year, today)
    )
    try:
        dividends = pf.parse_dividends(pf.load_dividends())
        dividends_error = None
    except Exception as e:
        dividends, dividends_error = None, f"{type(e).__name__}: {e}"
    return dividends, dividends_error, previous_expenses


@app.cell
def __(html, load_error, mo, pd, pf, spreadsheet_name, today, workbook):
    # ── Parse every tab once ────────────────────────────────────────────────
    if load_error:
        mo.stop(
            True,
            mo.Html(
                f"""
        <div class="terminal"><div class="t-section">Could not load '{html.escape(spreadsheet_name)}'</div>
        <div class="t-note">{html.escape(load_error)}<br><br>Check that the spreadsheet is shared with the
        service account and that GSHEETS_AUTH_FILE points at its credentials.</div></div>"""
            ),
        )

    year = pf.budget_year(spreadsheet_name, today)
    months = pf.months_of(year, today)
    expenses = pf.parse_expense_logs(workbook, year, today)
    budgets = pf.parse_category_budgets(workbook[pf.MONTHLY_EXPENSES_TAB])
    net_worth = pf.parse_net_worth(workbook[pf.NET_WORTH_TAB], months)
    budget_items = pf.parse_budget_items(workbook[pf.BUDGET_TAB])
    savings_log = (
        pf.parse_savings_log(workbook[pf.SAVINGS_LOG_TAB])
        if pf.SAVINGS_LOG_TAB in workbook
        else {}
    )
    buckets = pf.contribution_buckets(workbook[pf.NET_WORTH_TAB], months)
    debt = pf.debt_balance(workbook[pf.NET_WORTH_TAB], months)
    month_labels = [m.strftime("%b") for m in months]
    return (
        budget_items,
        budgets,
        buckets,
        debt,
        expenses,
        month_labels,
        months,
        net_worth,
        savings_log,
        year,
    )


@app.cell
def __(include_one_offs, mo, reload):
    mo.Html(f"""
    <div class="t-controls">
      <div>{reload}</div>
      <div>{include_one_offs}</div>
    </div>""")
    return


@app.cell
def __(expenses, mo, money, pf):
    # The biggest expenses to pick one-offs from. Created here, apart from the
    # cell that draws it, so ticking the box below doesn't reset the picks.
    _candidates = pf.one_off_candidates(expenses)
    _labels = {}
    for _row in _candidates.itertuples():
        _label = f"{_row.date:%Y-%m-%d} · {_row.description} · {_row.category} · {money(_row.my_share)}"
        while _label in _labels:
            _label += " "
        _labels[_label] = _row.key
    # max_selections keeps marimo from offering "Select all", which would mark
    # every candidate as a one-off in one click
    one_off_picker = mo.ui.multiselect(
        options=_labels,
        label="",
        full_width=True,
        max_selections=max(len(_labels), 1),
    )
    return (one_off_picker,)


@app.cell
def __(include_one_offs, mo, one_off_picker):
    mo.stop(not one_off_picker.options)
    mo.Html(f"""
    <div class="t-controls">
      <div style="flex: 1; min-width: 0;">
        <span class="t-control-label">Mark specific expenses as one-offs, to leave them out of the charts</span>
        <div style="{'opacity: 0.35; pointer-events: none;' if include_one_offs.value else ''}">{one_off_picker}</div>
      </div>
    </div>""")
    return


@app.cell
def __(
    budget_items,
    budgets,
    debt,
    expenses,
    include_one_offs,
    months,
    net_worth,
    one_off_picker,
    pf,
):
    # ── Everything the sections below draw ──────────────────────────────────
    everyday, one_offs = pf.split_marked(expenses, one_off_picker.value)
    if include_one_offs.value:
        # Checked: every expense is charted and counted, one-offs included
        everyday = expenses
    by_group = pf.monthly_by_group(everyday, budgets, months)
    monthly_spend = by_group.sum(axis=1)
    # What you logged as saved each month: the Net Worth tab's contributions
    savings = net_worth[pf.CONTRIBUTIONS]
    # 401(k) and match only come as yearly figures, so they're split evenly
    _retirement = sum(
        budget_items.get(k, (0.0, 0.0))[0] for k in ("401k", "401k_match")
    )
    changes = pf.net_worth_changes(net_worth, debt, _retirement)
    return by_group, changes, everyday, monthly_spend, one_offs, savings


@app.cell
def __(
    budget_items,
    include_one_offs,
    mo,
    money,
    monthly_spend,
    net_worth,
    pf,
    savings,
    spreadsheet_name,
    html,
    year,
):
    # ── Header and KPIs ─────────────────────────────────────────────────────
    _oo = "incl." if include_one_offs.value else "excl."
    _spent = monthly_spend.sum()
    _saved = savings.sum()
    # Like the Total savings tile: what the Budget tab plans for the year
    _saved_sub = (
        f"{money(budget_items['take_home_savings'][1])} budgeted"
        if "take_home_savings" in budget_items
        else f"{money(_saved / len(savings))} / month · logged contributions"
    )
    _nw = net_worth[pf.NET_WORTH]
    _nw_change = _nw.iloc[-1] - _nw.iloc[0]

    def _kpi(label, value, sub, cls):
        return f"""<div class="t-kpi {cls}"><div class="t-kpi-label">{label}</div>
        <div class="t-kpi-value {cls}">{value}</div><div class="t-kpi-sub">{sub}</div></div>"""

    header_html = f"""
    <div class="terminal">
      <div class="t-header">
        <div>
          <div class="t-title">⬡ Yearly Overview</div>
          <div class="t-subtitle">{html.escape(spreadsheet_name)} · Year to Date</div>
        </div>
      </div>
      <div class="t-kpis">
        {_kpi("Spent (your share)", money(_spent), f"{money(_spent / len(monthly_spend))} / month · {_oo} one-offs", "amb")}
        {_kpi("Take-home savings", money(_saved), _saved_sub, "pos" if _saved >= 0 else "neg")}
        {_kpi("Net worth", money(_nw.iloc[-1]), f"as of {_nw.index[-1].strftime('%b')}", "pos")}
        {_kpi("Net worth change", money(_nw_change, signed=True), "", "pos" if _nw_change >= 0 else "neg")}
      </div>
    </div>"""
    return (header_html,)


@app.cell
def __(
    budget_items,
    header_html,
    kpi_row,
    kpi_tile,
    mo,
    money,
    net_worth,
    pf,
    savings,
    savings_log,
    stat_tile,
):
    # ── Income, savings and investment income, as on the sheet's Dashboard tab ─
    # A tile only appears when its row is found. Dividends, interest and
    # realized gain/loss come from the older sheet's Savings Log, so a sheet
    # without one shows only the market change.
    def _budget_tile(key, label, sub=None):
        if key not in budget_items:
            return ""
        actual, budget = budget_items[key]
        return kpi_tile(label, actual, sub or f"{money(budget)} budgeted", "amb")

    _market, _share = pf.market_change(net_worth, budget_items)

    def _logged(key, label):
        return (
            kpi_tile(label, savings_log[key], "Savings Log")
            if key in savings_log
            else ""
        )

    _match = budget_items.get("401k_match", (0.0, 0.0))[0]
    _rates = pf.savings_rates(budget_items, savings.sum())

    def _rate_tile(key, label, sub):
        if key not in _rates:
            return ""
        return stat_tile(label, f"{_rates[key]:.1%}", sub, "amb")

    # One output with the header above, so there's no cell gap between them
    mo.Html(header_html + f"""
    <div class="terminal">
      {kpi_row("Savings rate", [
          _rate_tile("take_home", "Of take-home pay", "Take-Home Savings on the Budget tab"),
          _rate_tile("total", "Of gross income", "Total Savings on the Budget tab"),
      ])}
      {kpi_row("Income &amp; savings", [
          _budget_tile("gross_income", "Gross income"),
          _budget_tile("take_home", "Take-home pay"),
          _budget_tile("401k", "401(k) contributions", f"+ {money(_match)} company match" if _match else None),
          _budget_tile("total_savings", "Total savings"),
      ])}
      {kpi_row("Investment income", [
          _logged("dividends", "Dividends"),
          _logged("interest", "Interest"),
          _logged("stock_gain", "Realized gain/loss"),
          kpi_tile("Market change", _market, f"{_share:.1%} of the net worth change · after contributions and 401(k)"),
      ])}
    </div>""")
    return


@app.cell
def __(PALETTE, ShareBar, by_group, mo, money, month_labels, stacked_bars_svg):
    # ── 1. Spending: by group, click one for its sub-categories ────────────
    _colors = PALETTE[: len(by_group.columns)]
    _chart = stacked_bars_svg(
        month_labels, {g: list(by_group[g]) for g in by_group.columns}, _colors
    )
    # The group bar doubles as the chart's legend. A group whose refunds
    # outweigh its spending has no share to draw, so it's a chip only.
    _totals = by_group.sum()
    _shown = [g for g in by_group.columns if _totals[g] > 0]
    group_bar = mo.ui.anywidget(
        ShareBar(
            names=_shown,
            values=[float(_totals[g]) for g in _shown],
            colors=[_colors[list(by_group.columns).index(g)] for g in _shown],
            chips=[
                [g, f"{g} {money(_totals[g])}"]
                for g in by_group.columns
                if g not in _shown
            ],
            allow_none=True,
            height=22,
        )
    )
    mo.Html(f"""
    <div class="terminal">
      <div class="t-section">1 · Spending by month (your share)</div>
      <div class="t-chart">{group_bar}</div>
      <div class="t-chart">{_chart}</div>
      <div class="t-note">Click a group, in the bar or its chip, to see its sub-categories; click it again to close them.</div>
    </div>""")
    return (group_bar,)


@app.cell
def __(
    include_one_offs,
    PALETTE,
    budgets,
    by_group,
    everyday,
    expenses,
    fold,
    group_bar,
    html,
    legend,
    mo,
    money,
    month_labels,
    months,
    pf,
    stacked_bars_svg,
    table,
    today,
    year,
):
    # ── The selected group's sub-categories, on demand ─────────────────────
    _oo = "incl." if include_one_offs.value else "excl."
    _group = group_bar.value["selected"]
    mo.stop(not _group)
    _df = pf.monthly_by_category(everyday, budgets, months, _group)
    _colors = [PALETTE[i % len(PALETTE)] for i in range(len(_df.columns))]
    _chart = stacked_bars_svg(
        month_labels,
        {html.escape(c): list(_df[c]) for c in _df.columns},
        _colors,
        line=list(by_group[_group]),
    )
    # Budget to date counts one-offs too, as in the tables below
    _vs = pf.budget_vs_actual(expenses, budgets, today, year)
    _vs = _vs[_vs["group"] == _group].set_index("category")
    _spent = _df.sum()
    _rows = []
    for _c in _df.columns:
        _r = _vs.loc[_c] if _c in _vs.index else None
        _rows.append(
            [
                (html.escape(_c), "tk"),
                (money(_spent[_c]), ""),
                (money(_spent[_c] / len(_df)), ""),
                (money(_r["actual"]) if _r is not None else "–", ""),
                (money(_r["budget"]) if _r is not None else "–", ""),
                (
                    (money(_r["over"], signed=True), "neg" if _r["over"] > 0 else "pos")
                    if _r is not None
                    else ("–", "")
                ),
            ]
        )
    _total = by_group[_group].sum()
    mo.Html(f"""
    <div class="terminal">
      <div class="t-section">{html.escape(_group)} · {money(_total)} · {money(_total / len(by_group))} / month</div>
      {legend([html.escape(c) for c in _df.columns] + [f"{html.escape(_group)} total"], _colors + ["#e8edf5"])}
      <div class="t-chart">{_chart}</div>
      {fold(f"{len(_rows)} sub-categories", f"{money(_total)} {_oo} one-offs", table(["Sub-category", f"Spent ({_oo} one-offs)", "Per month", "Spent (all)", "Budget to date", "Over / under"], _rows))}
      <div class="t-note">Sub-categories are the Expense Log's categories, grouped as on the Monthly Expenses tab;
      beyond eight the smallest are summed into Other. The chart {"counts" if include_one_offs.value else "leaves out"} one-offs, like the one above; the
      last three columns count them, as the budget tables below do.</div>
    </div>""")
    return


@app.cell
def __(
    include_one_offs,
    budgets,
    everyday,
    expenses,
    fold,
    html,
    mo,
    money,
    one_offs,
    pf,
    table,
    today,
    year,
):
    # ── Budget, merchants and one-offs ──────────────────────────────────────

    # Every expense counts against its budget, one-offs included: they're
    # only left out of the charts, where they'd dwarf everything else
    _vs = pf.budget_vs_actual(expenses, budgets, today, year)
    _over = _vs[_vs["over"] > 0].head(8)
    _under = _vs[_vs["over"] < 0].sort_values("over").head(8)

    def _vs_rows(df):
        return [
            [
                (html.escape(r.category), "tk"),
                (money(r.actual), ""),
                (money(r.budget), ""),
                (money(r.over, signed=True), "neg" if r.over > 0 else "pos"),
                (money(r.annual), ""),
            ]
            for r in df.itertuples()
        ]

    _merchants = pf.top_merchants(everyday)
    _merchant_rows = [
        [(html.escape(r.description), "tk"), (money(r.total), ""), (str(r.count), "")]
        for r in _merchants.itertuples()
    ]
    _one_off_rows = [
        [
            (r.date.strftime("%Y-%m-%d"), ""),
            (html.escape(r.description), "tk"),
            (html.escape(r.category), ""),
            (money(r.my_share), "neg" if r.my_share > 0 else "pos"),
        ]
        for r in one_offs.sort_values("date").itertuples()
    ]

    mo.Html(f"""
    <div class="terminal">
      <div class="t-two-col">
        <div>
          <div class="t-section">Over budget so far</div>
          {fold(f"{len(_over)} categories", f"{money(_over['over'].sum(), signed=True)} over", table(["Category", "Spent", "Budget to date", "Over", "Year budget"], _vs_rows(_over)), "neg")}
        </div>
        <div>
          <div class="t-section">Under budget so far</div>
          {fold(f"{len(_under)} categories", f"{money(-_under['over'].sum())} under", table(["Category", "Spent", "Budget to date", "Under", "Year budget"], _vs_rows(_under)), "pos")}
        </div>
      </div>
      <div class="t-two-col">
        <div>
          <div class="t-section">Top merchants</div>
          {fold(f"{len(_merchants)} merchants", f"{money(_merchants['total'].sum())} total", table(["Description", "Your share", "Count"], _merchant_rows))}
        </div>
        <div>
          <div class="t-section">One-offs {"counted in" if include_one_offs.value else "left out of"} the charts ({len(one_offs)})</div>
          {fold(f"{len(one_offs)} expenses", f"{money(one_offs['my_share'].sum())} net", table(["Date", "Description", "Category", "Your share"], _one_off_rows))}
        </div>
      </div>
      <div class="t-note">Spent includes one-offs, whether or not the box is ticked. Budget to date is each category's monthly budget from the Monthly
      Expenses tab times the months elapsed, with the current month prorated by day; the sheet's Variance column
      compares against the whole year's budget instead. Bills dated after today aren't counted yet.</div>
    </div>""")
    return


@app.cell
def __(
    include_one_offs,
    everyday,
    expenses,
    fold,
    html,
    mo,
    money,
    pf,
    previous_expenses,
    table,
    today,
):
    # ── Biggest changes in spending: vs recent months, and vs last year ─────
    _movers, _month, _n = pf.category_movers(everyday, today)

    def _pct(r):
        return (
            ("new", "")
            if r.pct != r.pct
            else (f"{r.pct:+.0%}", "neg" if r.pct > 0 else "pos")
        )

    def _rows(df, new, old):
        return [
            [
                (html.escape(r.category), "tk"),
                (money(getattr(r, new)), ""),
                (money(getattr(r, old)), ""),
                (money(r.change, signed=True), "neg" if r.change > 0 else "pos"),
                _pct(r),
            ]
            for r in df.itertuples()
        ]

    _blocks = []
    if _month is not None:
        _rows_m = _rows(_movers.head(10), "latest", "baseline")
        _blocks.append(
            f"""
        <div class="t-section">{_month.strftime("%B")} against the {_n} month{"s" if _n > 1 else ""} before it</div>
        {fold(f"{len(_rows_m)} biggest changes", f"{money(_movers["change"].sum(), signed=True)} in total", table(["Category", _month.strftime("%b"), f"Average of previous {_n}", "Change", "%"], _rows_m))}"""
        )
    if previous_expenses is not None and len(previous_expenses):
        _yoy = pf.year_over_year(expenses[expenses["date"] <= today], previous_expenses)
        _rows_y = _rows(_yoy.head(10), "this_year", "last_year")
        _blocks.append(
            f"""
        <div class="t-section">This year so far against the same stretch of last year</div>
        {fold(f"{len(_rows_y)} biggest changes", f"{money(_yoy["change"].sum(), signed=True)} in total", table(["Category", "This year", "Last year", "Change", "%"], _rows_y))}"""
        )
    mo.stop(not _blocks)
    mo.Html(f"""
    <div class="terminal">
      <div class="t-section">Where spending moved</div>
      {"".join(_blocks)}
      <div class="t-note">Your share of each sub-category, one-offs {"counted" if include_one_offs.value else "left out"}, red where spending rose. The month
      comparison uses the last complete month; a sub-category with no spending in the earlier months shows as new.
      Last year comes from the previous year's budget sheet (its name with the year changed), shown when it can be read.</div>
    </div>""")
    return


@app.cell
def __(
    PALETTE,
    buckets,
    fold,
    html,
    legend,
    mo,
    money,
    month_labels,
    savings,
    stacked_bars_svg,
    table,
):
    # ── 2. Savings by month, split by the bucket each part went to ─────────
    mo.stop(
        buckets.empty,
        mo.Html(
            '<div class="terminal"><div class="t-section">2 · Savings by month</div><div class="t-note">No savings contributions logged this year.</div></div>'
        ),
    )
    _names = list(buckets.columns)
    _colors = [PALETTE[i % len(PALETTE)] for i in range(len(_names))]
    _chart = stacked_bars_svg(
        month_labels,
        {html.escape(b): list(buckets[b]) for b in _names},
        _colors,
        line=list(savings),
    )
    _total = savings.sum()

    def _cell(v):
        return (money(v), "pos" if v > 0 else "neg" if v < 0 else "")

    _rows = [
        [(m.strftime("%b"), "tk")]
        + [_cell(buckets.loc[m, b]) for b in _names]
        + [_cell(t), _cell(c)]
        for m, t, c in zip(buckets.index, savings, savings.cumsum())
    ]
    _rows.append(
        [("Total", "tk")]
        + [_cell(buckets[b].sum()) for b in _names]
        + [_cell(_total), ("", "")]
    )
    mo.Html(f"""
    <div class="terminal">
      <div class="t-section">2 · Savings by month</div>
      {legend([html.escape(b) for b in _names] + ["Take-home savings"], _colors + ["#e8edf5"])}
      <div class="t-chart">{_chart}</div>
      {fold(f"{len(savings)} months · {len(_names)} buckets", f"{money(_total)} take-home savings", table(["Month", *[html.escape(b) for b in _names], "Total", "Year to date"], _rows), "pos" if _total >= 0 else "neg")}
      <div class="t-note">Take-home savings is the Monthly Savings Contributions rows at the bottom of the Net Worth tab, one bucket
      per row, the same figure as the Budget tab's Take-Home Savings, so without the 401(k). Beyond eight buckets the smallest are summed into
      Other, and a bar below zero is money taken out. It's what you logged as put away, not take-home minus spending,
      so a big purchase paid from savings, like a down payment, doesn't lower it.</div>
    </div>""")
    return


@app.cell
def __(
    PALETTE,
    changes,
    fold,
    legend,
    mo,
    money,
    month_labels,
    net_worth,
    pf,
    stacked_bars_svg,
    table,
):
    # ── 3. Net worth ────────────────────────────────────────────────────────
    _components = list(pf.NET_WORTH_COMPONENTS.values())
    _colors = ["#4da3ff", "#00d17a", "#c77dff", "#E8890C", "#ff4d6a"]
    _chart = stacked_bars_svg(
        month_labels,
        {c: list(net_worth[c]) for c in _components},
        _colors,
        line=list(net_worth[pf.NET_WORTH]),
    )
    _change_colors = [PALETTE[1], PALETTE[3], PALETTE[0], PALETTE[2]]
    _change_chart = stacked_bars_svg(
        [m.strftime("%b") for m in changes.index],
        {
            "You put in": list(changes["saved"]),
            "Debt paid down": list(changes["debt"]),
            "401(k) + match (even split)": list(changes["retirement"]),
            "Market & other": list(changes["market"]),
        },
        _change_colors,
        line=list(changes["change"]),
    )
    _rows = [
        [
            (m.strftime("%b"), "tk"),
            (money(r.change, signed=True), "pos" if r.change >= 0 else "neg"),
            (money(r.saved, signed=True), "pos" if r.saved >= 0 else "neg"),
            (money(r.debt, signed=True), "pos" if r.debt >= 0 else "neg"),
            (money(r.retirement, signed=True), "pos" if r.retirement >= 0 else "neg"),
            (money(r.market, signed=True), "pos" if r.market >= 0 else "neg"),
        ]
        for m, r in zip(changes.index, changes.itertuples())
    ]
    mo.Html(f"""
    <div class="terminal">
      <div class="t-section">3 · Net worth by month</div>
      {legend(_components + ["Net worth"], _colors + ["#e8edf5"])}
      <div class="t-chart">{_chart}</div>
      <div class="t-section">Where each month's change came from</div>
      {legend(["You put in", "Debt paid down", "401(k) + match (even split)", "Market & other", "Total change"], _change_colors + ["#e8edf5"])}
      <div class="t-chart">{_change_chart}</div>
      {fold(f"{len(changes)} months", f"{money(changes['change'].sum(), signed=True)} change", table(["Month", "Change", "You put in", "Debt paid down", "401(k) + match", "Market & other"], _rows), "pos" if changes["change"].sum() >= 0 else "neg")}
      <div class="t-note">"You put in" is the Monthly Savings Contributions rows at the bottom of the Net Worth tab.
      "Debt paid down" is how much less you owe than the month before (the Liabilities subtotal and any mortgage
      row). The sheet has only a yearly figure for the 401(k) and its match, so that part is spread evenly over the
      months. "Market &amp; other" is the rest: market moves, home value, and cash left over from pay.
      The current month keeps changing until you paste its values at month end.</div>
    </div>""")
    return


@app.cell
def __(
    include_one_offs,
    emergency_months,
    fold,
    kpi_row,
    kpi_tile,
    mo,
    money,
    monthly_spend,
    net_worth,
    pf,
    stat_tile,
    table,
    today,
):
    _oo = "incl." if include_one_offs.value else "excl."
    # ── 4. Liquidity and runway ─────────────────────────────────────────────
    _spend = pf.average_monthly_spend(monthly_spend, today)
    _liq = pf.liquidity(net_worth, _spend)
    _fund = pf.emergency_fund(_liq["cash"], _spend, emergency_months.value)

    def _months(value):
        return f"{value / _spend:.1f}" if _spend > 0 else "–"

    _ladder = [
        ("Cash &amp; savings", "available now", _liq["cash"]),
        ("Investments", "taxable, a sale away", _liq["invested"]),
        ("Retirement", "locked until retirement age", _liq["locked"]),
        ("Real estate", "illiquid", _liq["home"]),
        ("Liabilities", "owed", _liq["debts"]),
    ]
    _assets = sum(v for _, _, v in _ladder[:4])
    _rows = [
        [
            (name, "tk"),
            (note, ""),
            (money(value), "pos" if value >= 0 else "neg"),
            (f"{value / _assets:.0%}" if _assets and value >= 0 else "", ""),
            (_months(value) if value >= 0 else "", ""),
        ]
        for name, note, value in _ladder
    ]
    _short = _fund["surplus"] < 0
    mo.Html(f"""
    <div class="terminal">
      <div class="t-section">4 · Liquidity and runway</div>
      {kpi_row("At today's spending", [
          kpi_tile("Spending / month", _spend, f"average of complete months · {_oo} one-offs", "amb"),
          stat_tile("Cash runway", f"{_liq['runway_cash']:.1f} mo" if "runway_cash" in _liq else "–", "cash &amp; savings alone", "pos"),
          stat_tile("Cash + investments", f"{_liq['runway_liquid']:.1f} mo" if "runway_liquid" in _liq else "–", "if you sold the taxable accounts", "pos"),
          kpi_tile("Emergency fund " + ("shortfall" if _short else "surplus"), _fund["surplus"], f"cash against {emergency_months.value:g} months of spending ({money(_fund['target'])})"),
      ])}
      <div class="t-controls"><div><span class="t-control-label">Months of spending to keep in cash</span>{emergency_months}</div></div>
      {fold(f"{len(_rows)} groups", f"{money(_assets)} in assets", table(["Where it sits", "How liquid", "Balance", "Share of assets", "Months of spending"], _rows))}
      <div class="t-note">Spending is the average of the complete months so far, one-offs {"counted, so a down payment shortens your runway" if include_one_offs.value else "left out, so a down payment doesn't shrink your runway"}. Real Estate is the sheet's subtotal, net of the mortgage where the sheet subtracts it there.</div>
    </div>""")
    return


@app.cell
def __(
    PALETTE,
    dividends,
    dividends_error,
    fold,
    html,
    kpi_row,
    kpi_tile,
    legend,
    mo,
    money,
    month_labels,
    months,
    pf,
    stacked_bars_svg,
    stat_tile,
    table,
    today,
    year,
):
    # ── 5. Dividend income, from the pipeline's dividends ledger ────────────
    def _note(text):
        return mo.Html(
            f'<div class="terminal"><div class="t-section">5 · Dividend income</div><div class="t-note">{text}</div></div>'
        )

    mo.stop(
        dividends is None,
        _note(
            f"Couldn't read the dividends ledger ({html.escape(str(dividends_error))})."
        ),
    )
    mo.stop(
        dividends.empty,
        _note("The dividends ledger has no rows yet."),
    )
    _by_month = pf.dividends_by_month(dividends, months)
    _names = list(_by_month.columns)
    _colors = [PALETTE[i % len(PALETTE)] for i in range(len(_names))]
    _total = _by_month.sum().sum()
    _rate = pf.dividend_run_rate(dividends, today)
    _payers = pf.top_dividend_payers(dividends, year)
    _payer_rows = [
        [(html.escape(r.name), "tk"), (money(r.total), "pos"), (str(r.count), "")]
        for r in _payers.itertuples()
    ]
    mo.Html(f"""
    <div class="terminal">
      <div class="t-section">5 · Dividend income</div>
      {kpi_row("From the dividends ledger", [
          kpi_tile("This year", _total, f"{money(_total / len(months))} / month so far", "pos"),
          kpi_tile("Last 12 months", _rate["last_12_months"], "all accounts in the ledger", "pos") if _rate else "",
          kpi_tile("Yearly pace", _rate["per_year"], (f"scaled up from {_rate['months_of_history']:.0f} months of history" if _rate["estimated"] else "the last 12 months"), "amb") if _rate else "",
      ])}
      {legend([html.escape(n) for n in _names], _colors)}
      <div class="t-chart">{stacked_bars_svg(month_labels, {html.escape(n): list(_by_month[n]) for n in _names}, _colors, line=list(_by_month.sum(axis=1)))}</div>
      {fold(f"{len(_payer_rows)} biggest payers", f"{money(_payers['total'].sum())}", table(["Security", "Received", "Payments"], _payer_rows), "pos")}
      <div class="t-note">Wells Fargo and Fidelity dividends the pipeline has recorded; the ledger only grows from when it
      started, so a yearly pace over less than a year of history is an estimate. Securities are shown by ticker where the
      ledger has one.</div>
    </div>""")
    return


if __name__ == "__main__":
    app.run()
