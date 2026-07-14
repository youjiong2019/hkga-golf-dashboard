# HKGA Players 2026 — Live Dashboard

Live site: **https://youjiong2019.github.io/hkga-golf-dashboard/**

Tracks all 179 players across the five official GAHKC (Golf Association of Hong Kong, China) squads — worldwide tournament results and news for the 2026 season.

The published page (`index.html`) is **password-gated** (StatiCrypt, AES-256). The password is shared privately by YJ — it is never stored in this repository. The un-encrypted dashboard must never be committed here: the repository is private, but everything on the `main` branch is served publicly by GitHub Pages.

## How it updates

| Layer | Cadence | Mechanism |
|---|---|---|
| Live feed (news + fresh results) | Daily, 05:00 HKT | GitHub Action (`.github/workflows/daily.yml`) runs `scripts/update_feed.py`, which pulls APGC, AGIF, GAHKC news/tournament pages, HJGT and Google News (AJGA / US Kids / USGA juniors), then commits `data/feed.json` (80-item cap) |
| Verified results (monthly tables, player records, standings) | Weekly, Monday | A Claude scheduled task re-verifies results against official leaderboards, rebuilds the dashboard, re-encrypts it with the shared password, and ships a new `index.html` |

## Repository contents

- `index.html` — the encrypted dashboard (safe to publish)
- `data/feed.json` — plaintext news headlines only
- `scripts/update_feed.py` + `.github/workflows/daily.yml` — the daily feed pipeline

## Data sources

hkga.com · wagr.com · bluegolf.com (IJGT/JWGC/FCG) · uskidsgolf.com · apgc.online · agif.asia · randa.org · ajga.org · usga.org · hjgt.org · amateurgolf.com

All results are from public leaderboards and press coverage. Results are marked provisional until verified against an official leaderboard.
