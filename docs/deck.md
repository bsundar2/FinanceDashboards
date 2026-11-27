---
marp: true
title: Personal finance on autopilot
paginate: true
backgroundColor: "#0A0C0F"
color: "#E8EDF5"
style: |
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap');
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
  .rows .row { background: #0A0C0F; border: 2px solid #262D3D; border-radius: 12px; padding: 14px 24px; margin-bottom: 14px; font-size: 26px; display: grid; grid-template-columns: 210px 1fr; align-items: center; }
  .rows .row b { font-family: 'IBM Plex Mono', monospace; color: #E8890C; font-size: 28px; }
  img { border: 2px solid #262D3D; border-radius: 8px; }
---
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

![h:430](img/architecture.svg)

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

## One sheet for the household

<div class="rows">
<div class="row"><b>Shared</b>Each partner has their own pay and expense log. Budget and Net Worth add both up.</div>
<div class="row"><b>Auditable</b>Every total is a formula you can click into.</div>
<div class="row"><b>Migration</b>A script moves an old single-person budget onto the template.</div>
<div class="row"><b>Generated</b>The workbook is built from code, so a new year is one command.</div>
</div>

---
<!-- _class: alt -->
<p class="eyebrow">Privacy by design</p>

## Data stays out of the repo

<div class="rows">
<div class="row"><b>Code</b>Names, account numbers and balances live in secrets and the sheet, never in code.</div>
<div class="row"><b>Access</b>One password and a signed cookie that expires daily. No password, no start.</div>
<div class="row"><b>Sheets</b>A service account sees only the sheets shared with it.</div>
<div class="row"><b>Logs</b>Public workflow logs show counts and tab names, never accounts or amounts.</div>
</div>
