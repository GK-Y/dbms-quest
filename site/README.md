# DBMS QUEST // SQL 50 (Retro Edition)

A single-page, retro-arcade-style site for grinding the LeetCode Top SQL 50.
All 50 problems, the 5 lessons, hints, and solutions are baked into `data.js`
so the site needs no server, no backend, and no internet (after the first load
of the Google pixel font).

## Run it

Open `index.html` directly in a browser, or serve the folder:

```bash
python3 -m http.server -d site 8080
# visit http://localhost:8080
```

## State

Progress is stored in `localStorage` under `dbms_quest_progress_v1`. On first
visit it is seeded from `.sql50_progress.json` (the 9 questions already passed
in the workspace). Use **TITLE > RESET SAVE** to wipe it.

## Regenerate the data

Whenever the workspace contents change (new source prompts, new lessons, new
fixtures in `scripts/sql50.py`), rebuild the data:

```bash
python3 site/build.py
```

`build.py` imports `scripts/sql50.py` and pulls:

- the curriculum manifest (`data/top_sql_50_manifest.json`)
- the dumped prompts in `src_questions/`
- hints and solutions baked into `STARTER_FIXTURES` (and the auto-generated
  example fixtures from `parse_example_fixture`)
- the lessons in `lessons/`

The website itself is just three static files plus the generated `data.js`:

- `index.html` - title screen, HUD, view templates
- `style.css`  - CRT scanlines, neon palette, Press Start 2P + VT323 fonts
- `app.js`     - routing, localStorage state, Web Audio beeps, rendering
