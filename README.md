# HKGA Players 2026 — Live Dashboard

Live site: **https://youjiong2019.github.io/hkga-golf-dashboard/**

Tracks all 179 players across the five official GAHKC (Golf Association of Hong Kong, China) squads — worldwide tournament results and news for the 2026 season.

## How it updates

| Layer | Cadence | Mechanism |
|---|---|---|
| Live feed (news + fresh results) | Daily, 05:00 HKT | GitHub Action (`.github/workflows/daily.yml`) runs `scripts/update_feed.py`, which pulls APGC, AGIF, GAHKC news/tournament pages and Google News, then commits `data/feed.json` |
| Verified results (monthly tables, player records, standings) | Weekly, Monday | A Claude scheduled task re-verifies results against official leaderboards (WAGR, BlueGolf, R&A, NCAA sites) and pushes an updated `index.html` |

## Data sources

hkga.com · wagr.com · jwgc.bluegolf.com · fcg.bluegolf.com · apgc.online · agif.asia · randa.org · ajga.org · NCAA athletics sites · europeangolfrankings.com · amateurgolf.com

All results are from public leaderboards and press. Corrections welcome via issues.
