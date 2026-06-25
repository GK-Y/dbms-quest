#!/usr/bin/env python3
"""Retro DBMS Quest backend: serves the static site + a real-MySQL SQL API.

Runs a portable MariaDB from ./mysql (no root needed) on a project-local
socket, and exposes endpoints the frontend calls to RUN / TEST user SQL
against the same fixtures the Python CLI uses (scripts/sql50.py).

Run it with:
    site/.venv/bin/python site/server.py
then open http://localhost:8000/
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pymysql
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = Path(__file__).resolve().parent
MYSQL_DIR = ROOT / "mysql"           # portable mariadb basedir (gitignored)
DATA_DIR = ROOT / "mysql_data"        # mysqld datadir (gitignored)
SOCKET = MYSQL_DIR / "mysql.sock"
PIDFILE = MYSQL_DIR / "mysqld.pid"
ERRLOG = ROOT / "mysql_err.log"
PORT = 13306

sys.path.insert(0, str(ROOT / "scripts"))
import sql50  # noqa: E402

# Per-fixture MySQL fixups (only where SQLite syntax would fail on MySQL).
MYSQL_FIXUPS = {
    "197": {
        # SQLite: DATE(recordDate, '-1 day')   MySQL: DATE_SUB(..., INTERVAL 1 DAY)
        "expected_sql": (
            "SELECT today.id\n"
            "FROM Weather AS today\n"
            "JOIN Weather AS yesterday\n"
            "  ON DATE_SUB(today.recordDate, INTERVAL 1 DAY) = yesterday.recordDate\n"
            "WHERE today.temperature > yesterday.temperature\n"
            "ORDER BY today.id"
        ),
        "solution_sql": (
            "SELECT today.id\n"
            "FROM Weather AS today\n"
            "JOIN Weather AS yesterday\n"
            "  ON DATE_SUB(today.recordDate, INTERVAL 1 DAY) = yesterday.recordDate\n"
            "WHERE today.temperature > yesterday.temperature"
        ),
    },
}


# ---------- MariaDB lifecycle ----------
def basedir() -> Path:
    if MYSQL_DIR.exists() and (MYSQL_DIR / "bin" / "mysqld").exists():
        return MYSQL_DIR
    cand = [d for d in MYSQL_DIR.iterdir() if d.is_dir() and (d / "bin" / "mysqld").exists()] if MYSQL_DIR.exists() else []
    if not cand:
        raise RuntimeError(
            f"MariaDB not found under {MYSQL_DIR}. Download the portable tarball and "
            f"extract it so that {MYSQL_DIR}/bin/mysqld (or {MYSQL_DIR}/<ver>/bin/mysqld) exists."
        )
    return cand[0]


def ensure_initialized(base: Path) -> None:
    if DATA_DIR.exists() and any(DATA_DIR.iterdir()):
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MYSQL_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(base / "scripts" / "mysql_install_db"),
        f"--basedir={base}",
        f"--datadir={DATA_DIR}",
        f"--user={os.getenv('USER', 'root')}",
        "--auth-root-authentication-method=normal",
        "--skip-test-db",
    ]
    print("[mysql] initializing datadir ...", flush=True)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def is_running() -> bool:
    return SOCKET.exists()


def start_mysql() -> None:
    if is_running():
        return
    base = basedir()
    ensure_initialized(base)
    MYSQL_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(base / "bin" / "mysqld"),
        f"--basedir={base}",
        f"--datadir={DATA_DIR}",
        f"--socket={SOCKET}",
        f"--pid-file={PIDFILE}",
        f"--port={PORT}",
        f"--user={os.getenv('USER', 'root')}",
        "--bind-address=127.0.0.1",
        "--skip-networking=0",
        "--innodb-buffer-pool-size=64M",
        "--max-connections=20",
    ]
    print("[mysql] starting mysqld ...", flush=True)
    with ERRLOG.open("ab") as log:
        subprocess.Popen(cmd, stdout=log, stderr=log, start_new_session=True)
    for _ in range(120):
        if is_running():
            print(f"[mysql] ready, socket={SOCKET}", flush=True)
            return
        time.sleep(0.5)
    tail = ERRLOG.read_text(errors="replace")[-1200:] if ERRLOG.exists() else ""
    raise RuntimeError(f"mysqld did not start in time. Last log:\n{tail}")


DB_NAME = "dbms_quest"


def ensure_db() -> None:
    start_mysql()
    conn = pymysql.connect(unix_socket=str(SOCKET), user="root", charset="utf8mb4", autocommit=True)
    conn.cursor().execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    conn.close()


def connect(db: str | None = DB_NAME) -> pymysql.connections.Connection:
    start_mysql()
    conn = pymysql.connect(
        unix_socket=str(SOCKET),
        user="root",
        database=db,
        charset="utf8mb4",
        autocommit=True,
        init_command="SET SESSION sql_mode='ANSI_QUOTES,NO_ENGINE_SUBSTITUTION'",
    )
    return conn


# ---------- SQL helpers ----------
COMMENT_RE = re.compile(r"--.*?$|/\*.*?\*/", re.S)


def split_statements(sql: str) -> list[str]:
    cleaned = COMMENT_RE.sub("", sql)
    out = [s.strip() for s in cleaned.split(";")]
    return [s for s in out if s]


def fixture_for(q: dict) -> dict | None:
    fx = sql50.fixture_for(q)
    if not fx:
        return None
    fix = MYSQL_FIXUPS.get(str(q["id"]))
    if fix:
        fx = {**fx, **fix}
    return fx


def reset_schema(conn, fx: dict) -> None:
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [r[0] for r in cur.fetchall()]
    for t in tables:
        cur.execute(f'DROP TABLE IF EXISTS "{t.replace(chr(34), chr(34)*2)}"')
    for stmt in split_statements(fx["setup_sql"]):
        cur.execute(stmt)


def run_select(conn, sql: str) -> dict:
    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description] if cur.description else []
    rows = [list(r) for r in cur.fetchall()]
    return {"columns": cols, "rows": rows}


def run_user(conn, fx: dict, user_sql: str) -> dict:
    if fx.get("verify_table"):
        for stmt in split_statements(user_sql):
            if stmt:
                conn.cursor().execute(stmt)
        qt = fx["verify_table"].replace('"', '""')
        return run_select(conn, f'SELECT * FROM "{qt}" ORDER BY id')
    return run_select(conn, user_sql)


def get_expected(conn, fx: dict) -> dict | None:
    if fx.get("expected_sql"):
        if fx.get("verify_table"):
            for stmt in split_statements(fx["expected_sql"]):
                if stmt:
                    conn.cursor().execute(stmt)
            qt = fx["verify_table"].replace('"', '""')
            return run_select(conn, f'SELECT * FROM "{qt}" ORDER BY id')
        return run_select(conn, fx["expected_sql"])
    if fx.get("expected_result"):
        er = fx["expected_result"]
        return {"columns": list(er[0]), "rows": [list(r) for r in er[1]]}
    return None


def norm(rows):
    return [tuple("" if v is None else str(v) for v in r) for r in rows]


def matches(actual, expected, order_sensitive):
    if not expected:
        return False
    if actual["columns"] != expected["columns"]:
        return False
    a = [tuple(r) for r in norm(actual["rows"])]
    e = [tuple(r) for r in norm(expected["rows"])]
    if order_sensitive:
        return a == e
    if len(a) != len(e):
        return False
    return sorted(a) == sorted(e)


# ---------- API ----------
app = FastAPI(title="DBMS Quest API")


class SqlReq(BaseModel):
    id: int
    sql: str


@app.get("/api/health")
def health():
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT VERSION()")
        ver = cur.fetchone()[0]
        conn.close()
        return {"ok": True, "db": "mysql", "version": ver, "socket": str(SOCKET)}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=503)


@app.get("/api/schema/{qid}")
def schema(qid: int):
    q = find_q(qid)
    fx = fixture_for(q)
    if not fx:
        raise HTTPException(404, "no fixture")
    conn = connect()
    try:
        reset_schema(conn, fx)
        cur = conn.cursor()
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]
        out = []
        for t in tables:
            cur.execute(
                "SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s", (t,)
            )
            cols = cur.fetchall()
            cur.execute(f'SELECT * FROM "{t.replace(chr(34),chr(34)*2)}" LIMIT 5')
            sample = cur.fetchall()
            scols = [d[0] for d in cur.description]
            out.append({"name": t, "columns": [list(c) for c in cols],
                        "sample": {"columns": scols, "rows": [list(r) for r in sample]}})
        return {"tables": out}
    finally:
        conn.close()


@app.post("/api/run")
def run(req: SqlReq):
    q = find_q(req.id)
    fx = fixture_for(q)
    if not fx:
        raise HTTPException(404, "no fixture")
    if not req.sql.strip():
        raise HTTPException(400, "empty SQL")
    conn = connect()
    try:
        reset_schema(conn, fx)
        actual = run_user(conn, fx, req.sql)
        return {"ok": True, "result": actual}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


@app.post("/api/test")
def test(req: SqlReq):
    q = find_q(req.id)
    fx = fixture_for(q)
    if not fx:
        raise HTTPException(404, "no fixture")
    if not req.sql.strip():
        raise HTTPException(400, "empty SQL")
    conn = connect()
    try:
        reset_schema(conn, fx)
        actual = run_user(conn, fx, req.sql)
        expected = get_expected(conn, fx)
        passed = matches(actual, expected, fx.get("order_sensitive", True))
        return {"ok": True, "passed": passed, "actual": actual, "expected": expected}
    except Exception as e:
        return {"ok": False, "error": str(e), "passed": False}
    finally:
        conn.close()


def find_q(qid):
    for q in sql50.load_manifest():
        if q["id"] == qid:
            return q
    raise HTTPException(404, "unknown question")


# Serve the static site last (so /api routes win)
app.mount("/", StaticFiles(directory=str(SITE_DIR), html=True), name="site")


if __name__ == "__main__":
    import uvicorn
    start_mysql()
    ensure_db()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
