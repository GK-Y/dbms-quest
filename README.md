# SQL 50 Active Learning Workspace

This directory is a two-hour SQL practice lab built around LeetCode Top SQL 50.

The real source prompts can be added later. For now the workspace already has:

- a 50-question curriculum manifest by topic
- short lessons for zero-to-working SQL knowledge
- a local SQLite runner using Python 3, no DB server required
- reset, run, test, hint, solution, and progress commands
- runnable SQLite fixtures for all 50 questions
- stronger edge-case fake data for the opening Select and Join chunk
- source-example fixtures for the rest, generated from the dumped examples

## Quick Start

```bash
make reset
make list
make next
make run Q=1757
make test Q=1757
```

Your attempt files live in `attempts/`. Edit the SQL file for a question, then run
`make test Q=<id-or-slug>`.

Example:

```bash
make reset Q=1757
$EDITOR attempts/1757_recyclable-and-low-fat-products.sql
make test Q=1757
```

## Two-Hour Plan

Use a timer. The goal is not to memorize syntax; it is to recognize patterns.

1. 0-15 min: read `lessons/00_sql_from_zero.md`, run `make reset`, pass 1757 and 595.
2. 15-35 min: read `lessons/01_filtering.md`, finish the Select chunk.
3. 35-60 min: read `lessons/02_joins.md`, practice join questions with fake data.
4. 60-85 min: read `lessons/03_grouping.md`, practice `GROUP BY`, `HAVING`, and aggregates.
5. 85-110 min: read `lessons/04_subqueries_windows.md`, practice nested queries and ranking.
6. 110-120 min: run `make progress`, retry failed questions, then review solutions.

## Commands

```bash
make reset          # rebuild local DBs and create attempt files
make reset Q=1757   # reset one question
make list           # show the whole curriculum
make next           # show the next incomplete runnable question
make sources        # verify dumped src_questions coverage
make question Q=1757 # print the actual dumped prompt
make run Q=1757     # run your current attempt
make test Q=1757    # compare your answer to expected output
make schema Q=1757  # inspect tables and sample rows
make hint Q=1757    # show a pattern hint
make solution Q=1757
make progress
```

## Dumped Question Source

The actual dumped prompts live in `src_questions/`. Use:

```bash
make sources
make question Q=620
```

The runner treats `src_questions` as read-only source material. It does not edit
those markdown files; attempts stay in `attempts/`, generated databases stay in
`dbs/`, and local progress stays in `.sql50_progress.json`.

## Adding More Runnable Fixtures

The source prompts are now present. To make a question locally testable, add a
fixture to `STARTER_FIXTURES` in `scripts/sql50.py`. Each fixture needs:

- `id`
- `slug`
- `title`
- `category`
- `difficulty`
- `setup_sql`
- `expected_sql`
- `solution_sql`
- `hint`

The runner labels fixtures as `edge` or `sample` in `make list`.

- `edge`: hand-built fake data with extra cases.
- `sample`: generated from the dumped example input/output.

Sample fixtures are good for quick practice, but they are not a proof of full
LeetCode correctness. Edge fixtures are better because they expose traps and
stop you from memorizing outputs.

## Why SQLite

SQLite ships with Python 3, runs instantly, and stores databases under `dbs/`.
Most Top SQL 50 ideas transfer directly: `SELECT`, `WHERE`, joins, grouping,
subqueries, string functions, dates, and window functions. MySQL-specific syntax
can be noted in lessons when needed.
