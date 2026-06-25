#!/usr/bin/env python3
"""Local active-learning runner for the SQL 50 workspace."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "top_sql_50_manifest.json"
SRC_DIR = ROOT / "src_questions"
DB_DIR = ROOT / "dbs"
ATTEMPT_DIR = ROOT / "attempts"
PROGRESS_FILE = ROOT / ".sql50_progress.json"

RESET = "\033[0m"
GREEN = "\033[38;5;46m"
RED = "\033[31m"
CYAN = "\033[38;5;51m"
ORANGE = "\033[38;5;208m"
BOLD = "\033[1m"


STARTER_FIXTURES = {
    "1757": {
        "setup_sql": """
            DROP TABLE IF EXISTS Products;
            CREATE TABLE Products (
              product_id INTEGER PRIMARY KEY,
              low_fats TEXT NOT NULL,
              recyclable TEXT NOT NULL
            );
            INSERT INTO Products VALUES
              (0, 'Y', 'N'),
              (1, 'Y', 'Y'),
              (2, 'N', 'Y'),
              (3, 'Y', 'Y'),
              (4, 'N', 'N'),
              (5, 'Y', 'Y');
        """,
        "expected_sql": """
            SELECT product_id
            FROM Products
            WHERE low_fats = 'Y' AND recyclable = 'Y'
            ORDER BY product_id;
        """,
        "solution_sql": """
            SELECT product_id
            FROM Products
            WHERE low_fats = 'Y' AND recyclable = 'Y';
        """,
        "hint": "Filter the Products table with two equality checks joined by AND.",
    },
    "584": {
        "setup_sql": """
            DROP TABLE IF EXISTS Customer;
            CREATE TABLE Customer (
              id INTEGER PRIMARY KEY,
              name TEXT NOT NULL,
              referee_id INTEGER
            );
            INSERT INTO Customer VALUES
              (1, 'Will', NULL),
              (2, 'Jane', NULL),
              (3, 'Alex', 2),
              (4, 'Bill', NULL),
              (5, 'Zack', 1),
              (6, 'Mark', 2);
        """,
        "expected_sql": """
            SELECT name
            FROM Customer
            WHERE referee_id IS NULL OR referee_id <> 2
            ORDER BY id;
        """,
        "solution_sql": """
            SELECT name
            FROM Customer
            WHERE referee_id IS NULL OR referee_id <> 2;
        """,
        "hint": "Rows with NULL referee_id should stay. Use IS NULL, not = NULL.",
    },
    "595": {
        "setup_sql": """
            DROP TABLE IF EXISTS World;
            CREATE TABLE World (
              name TEXT PRIMARY KEY,
              continent TEXT NOT NULL,
              area INTEGER NOT NULL,
              population INTEGER NOT NULL,
              gdp INTEGER NOT NULL
            );
            INSERT INTO World VALUES
              ('Afghanistan', 'Asia', 652230, 25500100, 20343000000),
              ('Albania', 'Europe', 28748, 2831741, 12960000000),
              ('Algeria', 'Africa', 2381741, 37100000, 188681000000),
              ('Andorra', 'Europe', 468, 78115, 3712000000),
              ('Brazil', 'South America', 8515767, 210000000, 1800000000000),
              ('India', 'Asia', 3287263, 1380004385, 3170000000000);
        """,
        "expected_sql": """
            SELECT name, population, area
            FROM World
            WHERE area >= 3000000 OR population >= 25000000
            ORDER BY name;
        """,
        "solution_sql": """
            SELECT name, population, area
            FROM World
            WHERE area >= 3000000 OR population >= 25000000;
        """,
        "hint": "A country qualifies if either threshold is met, so this is OR.",
    },
    "1148": {
        "setup_sql": """
            DROP TABLE IF EXISTS Views;
            CREATE TABLE Views (
              article_id INTEGER NOT NULL,
              author_id INTEGER NOT NULL,
              viewer_id INTEGER NOT NULL,
              view_date TEXT NOT NULL
            );
            INSERT INTO Views VALUES
              (1, 3, 5, '2019-08-01'),
              (1, 3, 6, '2019-08-02'),
              (2, 7, 7, '2019-08-01'),
              (2, 7, 7, '2019-08-02'),
              (3, 4, 4, '2019-08-04'),
              (4, 9, 1, '2019-08-05');
        """,
        "expected_sql": """
            SELECT DISTINCT author_id AS id
            FROM Views
            WHERE author_id = viewer_id
            ORDER BY id;
        """,
        "solution_sql": """
            SELECT DISTINCT author_id AS id
            FROM Views
            WHERE author_id = viewer_id
            ORDER BY id;
        """,
        "hint": "Find self-views and remove duplicates with DISTINCT.",
    },
    "1683": {
        "setup_sql": """
            DROP TABLE IF EXISTS Tweets;
            CREATE TABLE Tweets (
              tweet_id INTEGER PRIMARY KEY,
              content TEXT NOT NULL
            );
            INSERT INTO Tweets VALUES
              (1, 'Vote for Biden'),
              (2, 'Let us make SQL fun'),
              (3, 'Short text'),
              (4, 'This tweet is way too long');
        """,
        "expected_sql": """
            SELECT tweet_id
            FROM Tweets
            WHERE LENGTH(content) > 15
            ORDER BY tweet_id;
        """,
        "solution_sql": """
            SELECT tweet_id
            FROM Tweets
            WHERE LENGTH(content) > 15;
        """,
        "hint": "SQLite uses LENGTH(text) to count characters.",
    },
    "1378": {
        "setup_sql": """
            DROP TABLE IF EXISTS Employees;
            DROP TABLE IF EXISTS EmployeeUNI;
            CREATE TABLE Employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE EmployeeUNI (id INTEGER PRIMARY KEY, unique_id INTEGER NOT NULL);
            INSERT INTO Employees VALUES
              (1, 'Alice'), (7, 'Bob'), (11, 'Meir'), (90, 'Winston'), (3, 'Jonathan');
            INSERT INTO EmployeeUNI VALUES
              (3, 1), (11, 2), (90, 3);
        """,
        "expected_sql": """
            SELECT u.unique_id, e.name
            FROM Employees AS e
            LEFT JOIN EmployeeUNI AS u ON e.id = u.id
            ORDER BY e.id;
        """,
        "solution_sql": """
            SELECT u.unique_id, e.name
            FROM Employees AS e
            LEFT JOIN EmployeeUNI AS u ON e.id = u.id;
        """,
        "hint": "Keep every employee even when the unique id is missing: LEFT JOIN.",
    },
    "1068": {
        "setup_sql": """
            DROP TABLE IF EXISTS Sales;
            DROP TABLE IF EXISTS Product;
            CREATE TABLE Product (product_id INTEGER PRIMARY KEY, product_name TEXT NOT NULL);
            CREATE TABLE Sales (
              sale_id INTEGER,
              product_id INTEGER,
              year INTEGER,
              quantity INTEGER,
              price INTEGER
            );
            INSERT INTO Product VALUES (100, 'Nokia'), (200, 'Apple'), (300, 'Samsung');
            INSERT INTO Sales VALUES
              (1, 100, 2008, 10, 5000),
              (2, 100, 2009, 12, 5000),
              (7, 200, 2011, 15, 9000);
        """,
        "expected_sql": """
            SELECT p.product_name, s.year, s.price
            FROM Sales AS s
            JOIN Product AS p ON s.product_id = p.product_id
            ORDER BY s.sale_id;
        """,
        "solution_sql": """
            SELECT p.product_name, s.year, s.price
            FROM Sales AS s
            JOIN Product AS p ON s.product_id = p.product_id;
        """,
        "hint": "Sales has product_id; Product has the readable product_name.",
    },
    "1581": {
        "setup_sql": """
            DROP TABLE IF EXISTS Visits;
            DROP TABLE IF EXISTS Transactions;
            CREATE TABLE Visits (visit_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL);
            CREATE TABLE Transactions (
              transaction_id INTEGER PRIMARY KEY,
              visit_id INTEGER NOT NULL,
              amount INTEGER NOT NULL
            );
            INSERT INTO Visits VALUES
              (1, 23), (2, 9), (4, 30), (5, 54), (6, 96), (7, 54), (8, 54);
            INSERT INTO Transactions VALUES
              (2, 5, 310), (3, 5, 300), (9, 5, 200), (12, 1, 910), (13, 2, 970);
        """,
        "expected_sql": """
            SELECT v.customer_id, COUNT(*) AS count_no_trans
            FROM Visits AS v
            LEFT JOIN Transactions AS t ON v.visit_id = t.visit_id
            WHERE t.transaction_id IS NULL
            GROUP BY v.customer_id
            ORDER BY v.customer_id;
        """,
        "solution_sql": """
            SELECT v.customer_id, COUNT(*) AS count_no_trans
            FROM Visits AS v
            LEFT JOIN Transactions AS t ON v.visit_id = t.visit_id
            WHERE t.transaction_id IS NULL
            GROUP BY v.customer_id;
        """,
        "hint": "Left join visits to transactions, keep missing transaction rows, then count by customer.",
    },
    "197": {
        "setup_sql": """
            DROP TABLE IF EXISTS Weather;
            CREATE TABLE Weather (id INTEGER PRIMARY KEY, recordDate TEXT NOT NULL, temperature INTEGER NOT NULL);
            INSERT INTO Weather VALUES
              (1, '2015-01-01', 10),
              (2, '2015-01-02', 25),
              (3, '2015-01-03', 20),
              (4, '2015-01-04', 30),
              (5, '2015-01-06', 40);
        """,
        "expected_sql": """
            SELECT today.id
            FROM Weather AS today
            JOIN Weather AS yesterday
              ON DATE(today.recordDate, '-1 day') = yesterday.recordDate
            WHERE today.temperature > yesterday.temperature
            ORDER BY today.id;
        """,
        "solution_sql": """
            SELECT today.id
            FROM Weather AS today
            JOIN Weather AS yesterday
              ON DATE(today.recordDate, '-1 day') = yesterday.recordDate
            WHERE today.temperature > yesterday.temperature;
        """,
        "hint": "Self-join Weather: match each row to the row one calendar day before it.",
    },
    "1661": {
        "setup_sql": """
            DROP TABLE IF EXISTS Activity;
            CREATE TABLE Activity (
              machine_id INTEGER,
              process_id INTEGER,
              activity_type TEXT,
              timestamp REAL
            );
            INSERT INTO Activity VALUES
              (0, 0, 'start', 0.712), (0, 0, 'end', 1.520),
              (0, 1, 'start', 3.140), (0, 1, 'end', 4.120),
              (1, 0, 'start', 0.550), (1, 0, 'end', 1.550),
              (1, 1, 'start', 0.430), (1, 1, 'end', 1.420);
        """,
        "expected_sql": """
            SELECT s.machine_id, ROUND(AVG(e.timestamp - s.timestamp), 3) AS processing_time
            FROM Activity AS s
            JOIN Activity AS e
              ON s.machine_id = e.machine_id
             AND s.process_id = e.process_id
             AND s.activity_type = 'start'
             AND e.activity_type = 'end'
            GROUP BY s.machine_id
            ORDER BY s.machine_id;
        """,
        "solution_sql": """
            SELECT s.machine_id, ROUND(AVG(e.timestamp - s.timestamp), 3) AS processing_time
            FROM Activity AS s
            JOIN Activity AS e
              ON s.machine_id = e.machine_id
             AND s.process_id = e.process_id
            WHERE s.activity_type = 'start'
              AND e.activity_type = 'end'
            GROUP BY s.machine_id;
        """,
        "hint": "Join each start row to its end row, subtract timestamps, average per machine.",
    },
    "196": {
        "setup_sql": """
            DROP TABLE IF EXISTS Person;
            CREATE TABLE Person (
              id INTEGER PRIMARY KEY,
              email TEXT NOT NULL
            );
            INSERT INTO Person VALUES
              (1, 'john@example.com'),
              (2, 'bob@example.com'),
              (3, 'john@example.com');
        """,
        "expected_sql": """
            SELECT id, email
            FROM Person
            WHERE id IN (1, 2)
            ORDER BY id;
        """,
        "solution_sql": """
            DELETE FROM Person
            WHERE id NOT IN (
              SELECT MIN(id)
              FROM Person
              GROUP BY email
            );
        """,
        "hint": "Keep the smallest id per email and delete rows whose id is not in that kept set.",
        "verify_table": "Person",
    },
}


def load_manifest() -> list[dict]:
    with MANIFEST.open() as f:
        questions = json.load(f)["questions"]
    paths = source_paths_by_id()
    for question in questions:
        path = paths.get(str(question["id"]))
        if path:
            question["source_path"] = str(path.relative_to(ROOT))
    return questions


def source_paths_by_id() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    if not SRC_DIR.exists():
        return paths
    for path in SRC_DIR.rglob("*.md"):
        if path.name == "README.md":
            continue
        prefix = path.name.split("_", 1)[0]
        if prefix.isdigit():
            paths[str(int(prefix))] = path
    return paths


def load_progress() -> dict:
    if not PROGRESS_FILE.exists():
        return {}
    with PROGRESS_FILE.open() as f:
        return json.load(f)


def save_progress(progress: dict) -> None:
    with PROGRESS_FILE.open("w") as f:
        json.dump(progress, f, indent=2, sort_keys=True)
        f.write("\n")


def key_for(question: dict) -> str:
    return str(question["id"])


def file_stem(question: dict) -> str:
    return f"{question['id']}_{question['slug']}"


def find_question(value: str | None, questions: list[dict]) -> dict:
    if not value:
        raise SystemExit("Pass Q=<id-or-slug>, for example: make test Q=1757")
    lowered = value.lower()
    for question in questions:
        if lowered in {str(question["id"]), question["slug"].lower()}:
            return question
    raise SystemExit(f"Unknown question: {value}")


def ensure_dirs() -> None:
    DB_DIR.mkdir(exist_ok=True)
    ATTEMPT_DIR.mkdir(exist_ok=True)


def db_path(question: dict) -> Path:
    return DB_DIR / f"{file_stem(question)}.sqlite"


def attempt_path(question: dict) -> Path:
    return ATTEMPT_DIR / f"{file_stem(question)}.sql"


def source_path_for(question: dict) -> Path | None:
    rel = question.get("source_path")
    if rel:
        path = ROOT / rel
        if path.exists():
            return path
    return source_paths_by_id().get(str(question["id"]))


def problem_section(markdown: str) -> str:
    marker = "## Problem"
    start = markdown.find(marker)
    if start == -1:
        return markdown.strip()
    start += len(marker)
    end = markdown.find("## Solution", start)
    section = markdown[start:end if end != -1 else None]
    return section.strip()


def split_markdown_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_ascii_table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    rows: list[list[str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if set(stripped.replace("|", "").replace(" ", "")) <= {"-"}:
            continue
        rows.append(split_markdown_table_row(stripped))
    if not rows:
        return [], []
    return rows[0], rows[1:]


def collect_table_block(lines: list[str], start: int) -> tuple[list[str], int]:
    block: list[str] = []
    index = start
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("+") or stripped.startswith("|"):
            block.append(lines[index])
            index += 1
            continue
        if block:
            break
        index += 1
    return block, index


def infer_sql_type(values: list[str]) -> str:
    non_null = [value for value in values if value.upper() not in {"NULL", "N/A"}]
    if non_null and all(re.fullmatch(r"-?\d+", value) for value in non_null):
        return "INTEGER"
    if non_null and all(re.fullmatch(r"-?\d+(\.\d+)?", value) for value in non_null):
        return "REAL"
    return "TEXT"


def sql_literal(value: str) -> str:
    if value.upper() in {"NULL", "N/A"}:
        return "NULL"
    if re.fullmatch(r"-?\d+(\.\d+)?", value):
        return value
    return "'" + value.replace("'", "''") + "'"


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def parse_example_fixture(question: dict) -> dict | None:
    if question["slug"] == "delete-duplicate-emails":
        return None
    path = source_path_for(question)
    if not path:
        return None
    problem = problem_section(path.read_text())
    if "**Input:**" not in problem or "**Output:**" not in problem:
        return None

    input_part = problem.split("**Input:**", 1)[1].split("**Output:**", 1)[0]
    output_part = problem.split("**Output:**", 1)[1]
    for marker in ["**Explanation:**", "\n---"]:
        if marker in output_part:
            output_part = output_part.split(marker, 1)[0]

    input_lines = input_part.splitlines()
    output_lines = output_part.splitlines()
    tables: list[tuple[str, list[str], list[list[str]]]] = []
    index = 0
    while index < len(input_lines):
        match = re.match(r"\s*([A-Za-z][A-Za-z0-9_]*) table:\s*$", input_lines[index])
        if not match:
            index += 1
            continue
        table_name = match.group(1)
        block, index = collect_table_block(input_lines, index + 1)
        columns, rows = parse_ascii_table(block)
        if columns:
            tables.append((table_name, columns, rows))

    output_block, _ = collect_table_block(output_lines, 0)
    expected_columns, expected_rows = parse_ascii_table(output_block)
    if not tables or not expected_columns:
        return None

    setup_parts: list[str] = []
    for table_name, columns, rows in tables:
        column_values = [[row[i] for row in rows if i < len(row)] for i, _ in enumerate(columns)]
        types = [infer_sql_type(values) for values in column_values]
        setup_parts.append(f"DROP TABLE IF EXISTS {quote_ident(table_name)};")
        column_defs = ", ".join(
            f"{quote_ident(column)} {column_type}" for column, column_type in zip(columns, types)
        )
        setup_parts.append(f"CREATE TABLE {quote_ident(table_name)} ({column_defs});")
        for row in rows:
            values = ", ".join(sql_literal(value) for value in row)
            setup_parts.append(f"INSERT INTO {quote_ident(table_name)} VALUES ({values});")

    return {
        "setup_sql": "\n".join(setup_parts),
        "expected_result": (expected_columns, [tuple(row) for row in expected_rows]),
        "solution_sql": "-- Source example fixture only. Try solving before checking external solutions.",
        "hint": "Read the dumped prompt with make question, inspect tables with make schema, then write the SELECT.",
        "source_example": True,
        "order_sensitive": "any order" not in problem.lower(),
    }


def fixture_for(question: dict) -> dict | None:
    return STARTER_FIXTURES.get(key_for(question)) or parse_example_fixture(question)


def connect_fresh(question: dict) -> sqlite3.Connection:
    fixture = fixture_for(question)
    if not fixture:
        raise SystemExit(f"{question['id']} is scaffolded but not runnable yet. Add fixture data later.")
    conn = sqlite3.connect(":memory:")
    conn.executescript(fixture["setup_sql"])
    return conn


def reset_one(question: dict, force: bool = False) -> None:
    fixture = fixture_for(question)
    if not fixture:
        return

    ensure_dirs()
    path = db_path(question)
    conn = sqlite3.connect(path)
    conn.executescript(fixture["setup_sql"])
    conn.commit()
    conn.close()

    attempt = attempt_path(question)
    if force or not attempt.exists():
        attempt.write_text(
            "\n".join(
                [
                    f"-- {question['id']}. {question['title']}",
                    f"-- Category: {question['category']} | Difficulty: {question['difficulty']}",
                    "-- Write your SQL below. Run: make test Q=" + str(question["id"]),
                    "",
                    "SELECT NULL AS todo" if not fixture.get("verify_table") else "-- DELETE ...",
                    "WHERE 0;" if not fixture.get("verify_table") else "",
                    "",
                ]
            )
        )


def execute_select(conn: sqlite3.Connection, sql: str) -> tuple[list[str], list[tuple]]:
    cleaned = sql.strip()
    if not cleaned:
        raise sqlite3.Error("empty SQL")
    cur = conn.execute(cleaned)
    columns = [desc[0] for desc in cur.description or []]
    rows = [tuple(row) for row in cur.fetchall()]
    return columns, rows


def execute_attempt(conn: sqlite3.Connection, sql: str, fixture: dict) -> tuple[list[str], list[tuple]]:
    if fixture.get("verify_table"):
        conn.executescript(sql)
        return execute_select(conn, f"SELECT * FROM {quote_ident(fixture['verify_table'])} ORDER BY id")
    return execute_select(conn, sql)


def print_table(columns: list[str], rows: list[tuple]) -> None:
    if not columns:
        print("(no result columns)")
        return
    widths = [len(col) for col in columns]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(str(value)))
    fmt = " | ".join("{:<" + str(width) + "}" for width in widths)
    print(fmt.format(*columns))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(fmt.format(*(str(value) for value in row)))
    print(f"\n{len(rows)} row(s)")


def print_section(title: str, color: str) -> None:
    print(f"{BOLD}{color}{title}{RESET}")


def normalize(columns: list[str], rows: list[tuple]) -> tuple[tuple[str, ...], list[tuple[str, ...]]]:
    return tuple(columns), [tuple("" if value is None else str(value) for value in row) for row in rows]


def cmd_reset(args: argparse.Namespace) -> None:
    questions = load_manifest()
    if args.question:
        question = find_question(args.question, questions)
        reset_one(question, force=args.force)
        print(f"Reset {question['id']} into {db_path(question).relative_to(ROOT)}")
        return
    for question in questions:
        reset_one(question, force=args.force)
    runnable = sum(1 for question in questions if fixture_for(question))
    print(f"Reset {runnable} runnable question(s). Attempts are in attempts/.")


def cmd_list(_: argparse.Namespace) -> None:
    questions = load_manifest()
    current_category = None
    for question in questions:
        if question["category"] != current_category:
            current_category = question["category"]
            print(f"\n{current_category}")
        fixture = fixture_for(question)
        if not fixture:
            mark = "data later"
        else:
            mark = "sample" if fixture.get("source_example") else "edge"
        source = "src" if source_path_for(question) else "no src"
        print(
            f"  {question['id']:>4}  {question['title']}  "
            f"[{question['difficulty']}, {mark}, {source}]"
        )


def cmd_sources(_: argparse.Namespace) -> None:
    questions = load_manifest()
    paths = source_paths_by_id()
    expected = {str(question["id"]) for question in questions}
    present = expected & set(paths)
    missing = sorted(expected - set(paths), key=int)
    extra = sorted(set(paths) - expected, key=int)
    print(f"Source prompts present: {len(present)} / {len(expected)}")
    if missing:
        print("Missing:")
        for qid in missing:
            question = next(q for q in questions if str(q["id"]) == qid)
            print(f"  {qid} {question['title']}")
    if extra:
        print("Extra files:")
        for qid in extra:
            print(f"  {qid} {paths[qid].relative_to(ROOT)}")


def cmd_question(args: argparse.Namespace) -> None:
    question = find_question(args.question, load_manifest())
    path = source_path_for(question)
    if not path:
        raise SystemExit(f"No dumped source prompt found for {question['id']}.")
    markdown = path.read_text()
    print(f"{question['id']}. {question['title']}")
    print(f"Source: {path.relative_to(ROOT)}\n")
    print(problem_section(markdown))


def cmd_run(args: argparse.Namespace) -> None:
    questions = load_manifest()
    question = find_question(args.question, questions)
    reset_one(question)
    sql_file = attempt_path(question)
    sql = sql_file.read_text()
    conn = sqlite3.connect(db_path(question))
    try:
        columns, rows = execute_attempt(conn, sql, fixture_for(question) or {})
    except sqlite3.Error as exc:
        raise SystemExit(f"SQL error in {sql_file.relative_to(ROOT)}: {exc}") from exc
    finally:
        conn.close()
    print_table(columns, rows)


def cmd_test(args: argparse.Namespace) -> None:
    questions = load_manifest()
    question = find_question(args.question, questions)
    fixture = fixture_for(question)
    if not fixture:
        raise SystemExit(f"{question['id']} has no local fixture yet. Add source data later.")
    reset_one(question)
    sql_file = attempt_path(question)
    attempt_sql = sql_file.read_text()

    try:
        actual_conn = connect_fresh(question)
        actual = execute_attempt(actual_conn, attempt_sql, fixture)
        if "expected_sql" in fixture:
            expected_conn = connect_fresh(question)
            expected = execute_select(expected_conn, fixture["expected_sql"])
        else:
            expected = fixture["expected_result"]
    except sqlite3.Error as exc:
        raise SystemExit(f"SQL error: {exc}") from exc

    actual_norm = normalize(*actual)
    expected_norm = normalize(*expected)
    if fixture.get("order_sensitive", True):
        passed = actual_norm == expected_norm
    else:
        passed = actual_norm[0] == expected_norm[0] and sorted(actual_norm[1]) == sorted(expected_norm[1])

    if passed:
        progress = load_progress()
        progress[str(question["id"])] = "passed"
        save_progress(progress)
        print_section(f"PASS {question['id']} - {question['title']}", GREEN)
        print()
        print_section("Output", CYAN)
        print_table(*actual)
        return

    print_section(f"FAIL {question['id']} - {question['title']}", RED)
    print()
    print_section("Expected", CYAN)
    print_table(*expected)
    print()
    print_section("Your result", ORANGE)
    print_table(*actual)
    raise SystemExit(1)


def cmd_hint(args: argparse.Namespace) -> None:
    question = find_question(args.question, load_manifest())
    fixture = fixture_for(question)
    if not fixture:
        print("Hint pending until source data is added.")
        return
    print(fixture["hint"])


def cmd_schema(args: argparse.Namespace) -> None:
    question = find_question(args.question, load_manifest())
    reset_one(question)
    path = db_path(question)
    conn = sqlite3.connect(path)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        ]
        for table in tables:
            print(f"\n{table}")
            columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
            for column in columns:
                print(f"  {column[1]} {column[2]}")
            print("  sample:")
            sample = conn.execute(f"SELECT * FROM {table} LIMIT 5").fetchall()
            names = [desc[0] for desc in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]
            print_table(names, sample)
    finally:
        conn.close()


def cmd_solution(args: argparse.Namespace) -> None:
    question = find_question(args.question, load_manifest())
    fixture = fixture_for(question)
    if not fixture:
        print("Solution pending until source data is added.")
        return
    print(fixture["solution_sql"].strip())


def cmd_progress(_: argparse.Namespace) -> None:
    questions = load_manifest()
    progress = load_progress()
    runnable = [question for question in questions if fixture_for(question)]
    passed = [question for question in runnable if progress.get(str(question["id"])) == "passed"]
    print(f"Runnable now: {len(runnable)} / {len(questions)}")
    print(f"Passed: {len(passed)} / {len(runnable)}")
    for question in runnable:
        status = "PASS" if progress.get(str(question["id"])) == "passed" else "TODO"
        print(f"{status} {question['id']} {question['title']}")


def cmd_next(_: argparse.Namespace) -> None:
    questions = load_manifest()
    progress = load_progress()
    for question in questions:
        if fixture_for(question) and progress.get(str(question["id"])) != "passed":
            print(f"{question['id']} - {question['title']}")
            print(f"Attempt: {attempt_path(question).relative_to(ROOT)}")
            print(f"Run: make reset Q={question['id']} && make test Q={question['id']}")
            return
    print("All runnable questions are passed. Review weak topics or add stronger edge fixtures.")


def cmd_clean(_: argparse.Namespace) -> None:
    shutil.rmtree(DB_DIR, ignore_errors=True)
    print("Removed dbs/. Attempt files and progress were kept.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SQL 50 local practice runner")
    sub = parser.add_subparsers(required=True)

    reset = sub.add_parser("reset", help="rebuild SQLite dbs and create attempts")
    reset.add_argument("question", nargs="?")
    reset.add_argument("--force", action="store_true", help="overwrite attempt file stubs")
    reset.set_defaults(func=cmd_reset)

    list_cmd = sub.add_parser("list", help="show curriculum")
    list_cmd.set_defaults(func=cmd_list)

    sources = sub.add_parser("sources", help="verify src_questions coverage")
    sources.set_defaults(func=cmd_sources)

    question = sub.add_parser("question", help="print the dumped source prompt")
    question.add_argument("question", nargs="?")
    question.set_defaults(func=cmd_question)

    next_cmd = sub.add_parser("next", help="show next incomplete runnable question")
    next_cmd.set_defaults(func=cmd_next)

    run = sub.add_parser("run", help="run an attempt")
    run.add_argument("question", nargs="?")
    run.set_defaults(func=cmd_run)

    test = sub.add_parser("test", help="test an attempt")
    test.add_argument("question", nargs="?")
    test.set_defaults(func=cmd_test)

    schema = sub.add_parser("schema", help="show tables and sample rows")
    schema.add_argument("question", nargs="?")
    schema.set_defaults(func=cmd_schema)

    hint = sub.add_parser("hint", help="show a hint")
    hint.add_argument("question", nargs="?")
    hint.set_defaults(func=cmd_hint)

    solution = sub.add_parser("solution", help="show a solution")
    solution.add_argument("question", nargs="?")
    solution.set_defaults(func=cmd_solution)

    progress = sub.add_parser("progress", help="show local progress")
    progress.set_defaults(func=cmd_progress)

    clean = sub.add_parser("clean", help="remove generated db files")
    clean.set_defaults(func=cmd_clean)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
