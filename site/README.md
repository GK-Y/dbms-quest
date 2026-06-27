# DBMS QUEST // SQL 50 (Retro Edition)

**Live:** https://dbms-quest-ecru.vercel.app/

A retro-arcade-style site for grinding the LeetCode Top SQL 50. Runs SQL two
ways: a **real MariaDB backend** when running locally, and an **in-browser
SQLite (sql.js) fallback** on static hosting like Vercel. The frontend
auto-detects which engine is available.

## Run it

```bash
# one-time: set up the venv (backend deps)
python3 -m venv site/.venv
site/.venv/bin/pip install fastapi "uvicorn[standard]" pymysql

# one-time: download portable MariaDB (no root needed) into mysql/
curl -fsSL -o /tmp/mariadb.tar.gz \
  "https://archive.mariadb.org/mariadb-10.11.11/bintar-linux-systemd-x86_64/mariadb-10.11.11-linux-systemd-x86_64.tar.gz"
mkdir -p mysql && tar -xzf /tmp/mariadb.tar.gz -C mysql --strip-components=1

# start the server (auto-manages mysqld)
site/.venv/bin/python site/server.py
# open http://localhost:8000/
```

The server auto-starts a portable MariaDB on a project-local socket, creates
a `dbms_quest` database, and serves both the API and the static site.

## Features

- **Real MySQL execution** — RUN and TEST buttons execute your SQL against
  MariaDB, not SQLite. MySQL-specific syntax (`DATE_SUB`, `IF()`, etc.) works.
- **In-browser SQL editor** — textarea with Tab indent, Ctrl+Enter to RUN,
  Shift+Ctrl+Enter to TEST. Your SQL is saved per-question in localStorage.
- **Pass/fail matching** — TEST compares your result against the expected
  output and shows side-by-side EXPECTED vs YOURS on failure.
- **Retro title screen** — readable "DBMS QUEST" wordmark with glow animation,
  floating pixel-art sprites, animated starfield, CRT scanlines.
- **Avatar picker** — choose KNIGHT / MAGE / ROGUE / ROBOT (saved to
  localStorage, shown in the HUD).
- **Pixel-art icons** — 15 hand-drawn SVG sprites for trophies, swords,
  shields, scrolls, keys, skulls, controllers, crystals, etc.
- **Quest log** — 50 quests with difficulty badges (shield/sword/skull),
  status icons, filter by all/todo/cleared and by category.
- **Guide** (formerly Codex) — 5 lessons with clickable question-number links
  that jump directly to that quest.
- **Stats** — progress bars by total, category, and difficulty; level counter.
- **Web Audio sound effects** — square-wave beeps for navigation, pass, fail.
- **State persistence** — progress and saved SQL persist in localStorage,
  seeded from `.sql50_progress.json` on first visit.

## Regenerate the data

```bash
python3 site/build.py
```

This imports `scripts/sql50.py` and bakes all 50 questions, 5 lessons, hints,
solutions, and SQL fixtures into `site/data.js`.

## API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/health` | GET | Check MySQL is running, return version |
| `/api/schema/{qid}` | GET | Show tables, columns, and sample rows |
| `/api/run` | POST | Run user SQL against a fresh fixture |
| `/api/test` | POST | Run + compare against expected output |

## Files

- `index.html` — title screen, HUD, view templates
- `style.css` — CRT scanlines, neon palette, pixel borders, animations
- `app.js` — routing, localStorage, sprites, starfield, avatars, editor
- `build.py` — generates `data.js` from the workspace
- `server.py` — FastAPI backend, manages MariaDB lifecycle
- `data.js` — generated, all 50 questions + 5 lessons (committed)
