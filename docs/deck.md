---
marp: true
title: Personal finance on autopilot
paginate: true
backgroundColor: "#0A0C0F"
color: "#E8EDF5"
style: |
  section { font-family: 'IBM Plex Sans', Arial, sans-serif; font-size: 30px; padding: 64px 80px; }
  h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; color: #E8EDF5; }
  h1 { font-size: 72px; } h2 { font-size: 46px; margin-bottom: 24px; }
  .eyebrow { font-family: 'IBM Plex Mono', monospace; font-size: 20px; letter-spacing: .14em; text-transform: uppercase; color: #E8890C; }
  section.alt { background: #121620; }
  section.stmt { background: #E8890C; color: #0A0C0F; } section.stmt h2, section.stmt .eyebrow { color: #0A0C0F; }
  section::after { font-family: 'IBM Plex Mono', monospace; color: #8793AB; font-size: 18px; }
  .cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
  .cols2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
  .card { background: #171C28; border: 2px solid #262D3D; border-radius: 12px; padding: 20px 24px; font-size: 24px; }
  .card b { display: block; font-family: 'IBM Plex Mono', monospace; font-size: 28px; margin-bottom: 8px; }
  .flow { display: grid; grid-template-columns: 1fr 40px 1fr 40px 1fr 40px 1fr; align-items: center; font-size: 22px; }
  .flow .arrow { color: #E8890C; font-size: 40px; text-align: center; }
  .flow .card { margin-bottom: 16px; }
  .small { color: #8793AB; font-size: 22px; }
  img { border: 2px solid #262D3D; border-radius: 8px; }
---
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap">

<!-- _paginate: false -->
<p class="eyebrow">FinDash · A live demo</p>

# Personal finance on autopilot

Splitwise and SimpleFIN feed a Google Sheet. Two dashboards read it live.

<p class="small">Everything shown here is made-up data.</p>

---
<!-- _class: alt -->
<p class="eyebrow">The problem</p>

## Where did the money go?

<div class="cols">
<div class="card"><b>Spending is scattered</b>Cards, cash and shared bills with a partner, each in a different place.</div>
<div class="card"><b>Balances are everywhere</b>Checking, savings, brokerages, a 401(k) and an IRA, each with its own login.</div>
<div class="card"><b>Spreadsheets go stale</b>A budget that needs typing is a budget that stops being updated by March.</div>
</div>

---
<p class="eyebrow">Architecture</p>

## Two feeds, one sheet, two dashboards

<div class="flow">
<div><div class="card"><b>Splitwise</b>Expenses, shares, categories</div><div class="card"><b>SimpleFIN Bridge</b>Balances and holdings</div></div>
<div class="arrow">→</div>
<div><div class="card"><b>SplitwiseToSheets</b>GitHub Actions, 3× a day</div><div class="card"><b>FinanceToSheets</b>GitHub Actions, every 5 hours</div></div>
<div class="arrow">→</div>
<div><div class="card" style="border-color:#E8890C"><b>Google Sheets</b>Expense Log, Budget, Net Worth, holdings, dividends</div></div>
<div class="arrow">→</div>
<div><div class="card"><b>Yearly Overview</b>Spending, savings, runway</div><div class="card"><b>Net Worth</b>Allocation and holdings</div></div>
</div>

---
<!-- _class: alt -->
<p class="eyebrow">The feeds</p>

## Nothing typed by hand

<div class="cols">
<div class="card"><b>Spending</b>Linked cards sync into Splitwise. Splits and categories are fixed there once, and the sheet copies them.</div>
<div class="card"><b>Balances</b>Every linked bank, card, brokerage and retirement account, plus the securities each one holds.</div>
<div class="card"><b>The record</b>A yearly workbook with formulas anyone can read, and a ledger that grows run over run.</div>
</div>

---
<p class="eyebrow">Live demo · 1 of 2</p>

## Yearly Overview

![w:760](img/shot_overview.png)

Spent, saved and net worth so far · savings rate · spending by month and what moved · runway and dividends

---
<!-- _class: alt -->
<p class="eyebrow">Live demo · 2 of 2</p>

## Net Worth

![w:680](img/shot_networth.png)

Cash, investments, retirement and real estate · click a category to drill in

---
<p class="eyebrow">Live demo · drill-down</p>

## Down to the fund

![w:720](img/shot_holdings.png)

Pick an account or see them all · each account's holdings add up to its balance

---
<!-- _class: alt -->
<p class="eyebrow">The budget template</p>

## One sheet for the whole household

<div class="cols2">
<div class="card"><b>Shared, not merged</b>Each partner has their own pay and expense log. Budget, Net Worth and Dashboard add both up.</div>
<div class="card"><b>Plain and auditable</b>Settings, Income, Accounts and Net Worth tabs. Every total is a formula you can click into.</div>
<div class="card"><b>Bring an old sheet</b>A script moves a single-person budget onto the template and keeps its history.</div>
<div class="card"><b>Rebuilt from code</b>The workbook is generated, so a new year is one command.</div>
</div>

---
<p class="eyebrow">How it was built</p>

## Built with Claude Code

<div class="cols">
<div class="card"><b>CLAUDE.md</b>Each repo explains its layout, commands and rules, so every session starts informed.</div>
<div class="card"><b>Tests</b>Sheets calls are mocked, and formula tests recalculate the workbook in LibreOffice.</div>
<div class="card"><b>Pull requests</b>Changes arrive as reviewed PRs, merged by me, then deployed.</div>
</div>

---
<!-- _class: alt -->
<p class="eyebrow">Privacy by design</p>

## Personal data stays out of the repo

<div class="cols2">
<div class="card"><b>Code</b>Account numbers, names and balances live in secrets and the sheet, never in code, tests or docs.</div>
<div class="card"><b>Access</b>A login gate with a signed cookie that expires daily. The service won't start without a password.</div>
<div class="card"><b>Sheets</b>A service account sees only the sheets shared with it.</div>
<div class="card"><b>Logs</b>Public workflow logs show tab names and counts, never accounts or amounts.</div>
</div>

---
<p class="eyebrow">About the demo data</p>

## The demo data is made up

<div class="cols">
<div class="card"><b>1 · Export</b>Start from the real layout: same tabs, formulas and charts.</div>
<div class="card"><b>2 · Replace</b>Spending, pay, balances and holdings are generated. Institutions are well-known examples.</div>
<div class="card"><b>3 · Check</b>The tool compares the demo with the real file and flags any real figure or name left behind.</div>
</div>

<p class="small">The installed app is named FinDash Demo, with a blue icon and a DEMO DATA tag.</p>

---
<!-- _class: stmt -->
<!-- _paginate: false -->
<p class="eyebrow">What to copy</p>

## Let the sheet fill itself, then read it with simple dashboards.

Start with one feed and one tab. Keep the data out of git.

---
<!-- _class: alt -->
<p class="eyebrow">Q&amp;A</p>

## Questions

<div class="cols">
<div class="card"><b>FinanceDashboards</b>Dashboards and the budget template</div>
<div class="card"><b>FinanceToSheets</b>Bank and brokerage feed</div>
<div class="card"><b>SplitwiseToSheets</b>Splitwise feed</div>
</div>

<p class="small">All three: github.com/bsundar2</p>
