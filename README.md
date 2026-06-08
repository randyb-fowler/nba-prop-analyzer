# 🏀 NBA Prop Analyzer

[![Live Demo](https://img.shields.io/badge/live%20demo-online-brightgreen.svg)](https://nba-prop-analyzer-w19a.onrender.com)
[![CI](https://github.com/randyb-fowler/nba-prop-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/randyb-fowler/nba-prop-analyzer/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)

**🔗 Live demo: https://nba-prop-analyzer-w19a.onrender.com**
*(free tier — first load may take ~50s while the server wakes up)*

A web app that analyzes NBA player prop bets using **live game data**. Enter a
player, a stat, and a betting line — it returns hit rates over recent windows,
home/away splits, a full game log, and a recommended lean (Over / Under / Pass).

This is how real prop research tools (PropFinder, Outlier) work: instead of
guessing, you see how often a player has actually cleared a line.

![NBA Prop Analyzer screenshot](docs/screenshot.png)

> ⚠️ Educational / portfolio project. **Not betting advice.**

---

## Features

- 🔎 **Player search** with live autocomplete (active NBA players)
- 📊 **Hit rates** over last 5, last 10, and the full season
- 🏠 **Home vs. away splits** — often the difference on a prop
- 🗓️ **Today's slate** — see the day's NBA games, expand a team's roster, and click a player to jump into the analyzer with the opponent pre-filled
- 🗓️ **Season selector** — analyze any season from 2020-21 to 2025-26
- 🆚 **Opponent splits** — filter to "how does he do vs. this team?"
- ⚔️ **Player comparison** — two players head-to-head on the same line, winner highlighted
- 📍 **Per-game venue** — arena and city for every game in the log
- 🏥 **Team injury report** — live from ESPN (nba_api has no injury feed)
- 🎯 **Combo stats**: PTS, REB, AST, STL, BLK, 3PM, TOV, plus PRA / PR / PA / RA
- 📈 **Game log** with every game marked HIT or MISS against the line
- 🤖 **Lean engine** weighting recent form and the average-vs-line margin
- 🔐 **Accounts** (Google sign-in) with a **Pro** tier via Stripe — comparison, opponent splits, and past seasons are Pro features (server-enforced)
- ✅ **Unit-tested** prop engine (`pytest`)
- 🖥️ Also includes the original **command-line tool** for quick game-log lookups

---

## Tech stack

| Layer    | Tech                          |
|----------|-------------------------------|
| Data     | [nba_api](https://github.com/swar/nba_api) (live NBA.com stats) |
| Backend  | FastAPI + Uvicorn             |
| Frontend | Vanilla HTML/CSS/JS (no build step) |
| CLI      | Python + tabulate             |

---

## Project structure

```
.
├── src/
│   ├── nba_stats.py    # player lookup (accent-insensitive) + game-log engine
│   ├── props.py        # prop hit-rate / splits / venue / lean engine
│   ├── teams.py        # 30-team reference (arenas, cities, names)
│   └── injuries.py     # ESPN injury feed (best-effort, graceful fallback)
├── api/
│   └── app.py          # FastAPI backend + serves the frontend
├── web/
│   ├── index.html      # single-page UI
│   ├── style.css       # dark sportsbook theme
│   └── app.js          # fetches the API, renders results
├── tests/
│   └── test_props.py   # pytest suite (no network — synthetic game logs)
├── main.py             # original CLI tool
├── requirements.txt
└── README.md
```

---

## Setup

Requires **Python 3.11+**.

```bash
pip install -r requirements.txt
```

---

## Run the web app

```bash
python -m uvicorn api.app:app --reload
```

Then open **http://127.0.0.1:8000** in your browser.

Type a player (e.g. *Nikola Jokic*), pick a stat (e.g. *PRA*), enter a line
(e.g. *48.5*), choose Over/Under, and hit **Analyze**.

### Shareable links

Analyses are linkable — the app auto-runs from URL query params, so you can
share a specific prop directly:

```
https://nba-prop-analyzer-w19a.onrender.com/?player=Nikola+Jokic&stat=PRA&line=48.5
https://nba-prop-analyzer-w19a.onrender.com/?player=LeBron+James&compare=Stephen+Curry&stat=PTS&line=24.5
```

---

## Run the CLI (bonus)

Quick last-10 game log for any player:

```bash
python main.py "LeBron James"
```

---

## API reference

| Endpoint                                             | Description                       |
|------------------------------------------------------|-----------------------------------|
| `GET /api/stats`                                     | Supported stat keys               |
| `GET /api/seasons`                                   | Selectable seasons + default      |
| `GET /api/teams`                                     | Team abbreviations + names        |
| `GET /api/players?q=leb`                             | Player autocomplete               |
| `GET /api/analyze?player=...&stat=PTS&line=24.5&over=true&opponent=BOS&season=2024-25` | Full prop analysis (opponent + season optional) |
| `GET /api/compare?player_a=...&player_b=...&stat=PTS&line=24.5&over=true&season=2024-25` | Two players head-to-head |
| `GET /api/injuries?team=LAL`                         | Team injury report (via ESPN)     |
| `GET /api/slate?date=2025-01-15`                     | Games on a date (defaults today)  |
| `GET /api/roster?team=BOS`                           | A team's roster                   |
| `GET /api/me`                                        | Current user + Pro status         |
| `GET /api/auth/login` · `/callback` · `POST /logout` | Google OAuth sign-in              |
| `POST /api/billing/checkout` · `/portal` · `/webhook`| Stripe subscription flow          |

Example:

```bash
curl "http://127.0.0.1:8000/api/analyze?player=LeBron+James&stat=PTS&line=24.5&over=true"
```

## Deploying live (free)

The app is ready to deploy as-is. Config files included:

- `render.yaml` — [Render](https://render.com) Blueprint (recommended, free tier)
- `Procfile` + `runtime.txt` — works on Railway, Heroku-style platforms

### Deploy to Render (recommended)

1. Push this repo to GitHub (see above).
2. Go to [dashboard.render.com](https://dashboard.render.com) → **New +** → **Blueprint**.
3. Connect your GitHub and select this repo. Render reads `render.yaml`
   automatically — name, build command, start command, and Python version are
   all preconfigured.
4. Click **Apply**. First build takes a few minutes (installs numpy/pandas).
5. You get a public URL like `https://nba-prop-analyzer.onrender.com`.

> Free-tier services sleep after ~15 min idle and take ~30s to wake on the next
> request. Fine for a portfolio demo.

The production start command (used by every platform) is:

```bash
uvicorn api.app:app --host 0.0.0.0 --port $PORT
```

## Accounts & Pro tier (Phase 2)

Sign-in is **Google OAuth**; user data lives in **Postgres** (Neon in prod;
SQLite locally with zero setup). Premium features are **server-enforced** — the
frontend locks them, and the API independently returns `402`/`401`:

| Tier | What you get |
|------|--------------|
| **Free / anonymous** | Single-player analysis, current season, today's slate |
| **Pro** ($9.99/mo) | Player comparison, opponent splits, all past seasons |

### Configuration

Copy `.env.example` → `.env` (gitignored) and fill in:

| Var | Purpose |
|-----|---------|
| `SECRET_KEY` | Session cookie signing |
| `APP_BASE_URL` | Public URL (OAuth redirect + Stripe return) |
| `DATABASE_URL` | Neon Postgres (unset → local SQLite) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth client |
| `STRIPE_SECRET_KEY` / `STRIPE_PRICE_ID` / `STRIPE_WEBHOOK_SECRET` | Stripe billing |

External setup (each is free): a **Neon** project, a **Google Cloud** OAuth
client (redirect URI `{APP_BASE_URL}/api/auth/callback`), and a **Stripe**
account in test mode with a recurring Price and a webhook to
`{APP_BASE_URL}/api/billing/webhook`. In production set the secrets in Render's
**Environment** tab (the non-secret `APP_BASE_URL`/`SECRET_KEY` come from
`render.yaml`). The app boots and runs without these — auth/billing routes just
return `503` until configured.

## Running the tests

```bash
python -m pytest tests/ -q
```

The suite feeds synthetic game logs into the pure analysis functions, so it
runs offline and fast — no NBA API calls.

## A note on the injury feed

`nba_api` does not provide injuries, so the injury report is pulled from
ESPN's public endpoint as a best-effort feature. If ESPN is unreachable or
changes its format, the app degrades gracefully ("Injury report unavailable")
rather than erroring. Injuries are **current**, while game-log stats reflect
the configured season — so during the offseason you'll see live injury news
alongside last season's stats.

---

## How the "lean" is calculated

The recommendation blends recent and season-long hit rates, then checks the
average-vs-line margin:

```
score = 0.6 * (last-10 hit rate) + 0.4 * (season hit rate)

score ≥ 60 and avg above line  → OVER
score ≤ 40 and avg below line  → UNDER
otherwise                      → PASS
```

This is intentionally transparent and easy to tune — see `_lean()` in
[`src/props.py`](src/props.py).

---

## Roadmap (future / monetization ideas)

- [ ] Opponent-specific splits (vs. this team / vs. defensive rank)
- [ ] Multi-season trends and rest-day (back-to-back) splits
- [ ] Cache responses (Redis) to speed up repeat lookups
- [ ] Deploy live (Render / Railway / Fly.io)
- [ ] User accounts + saved players (Free vs. Pro tier with Stripe)
- [ ] Daily slate view: today's games and auto-pulled prop lines

---

## License

[MIT](LICENSE) © 2026 Randy Blake Fowler

## Disclaimer

Data is sourced from the public NBA.com stats API and may be delayed or
incomplete. This project is for educational purposes and is **not** affiliated
with the NBA. Nothing here is betting advice.
