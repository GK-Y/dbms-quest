#!/usr/bin/env python3
"""Build site/data.js from the SQL 50 workspace contents.

Pulls the curriculum manifest, the dumped source prompts in src_questions/,
the lessons, and the hints/solutions baked into scripts/sql50.py, then emits a
single JS file the static site loads with no server needed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sql50  # noqa: E402


def inline_code(text: str) -> str:
    """Convert `code` spans to <code>code</code>, escaping inner HTML."""
    result: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end == -1:
                result.append(text[i:])
                break
            inner = text[i + 1:end].replace("<", "&lt;").replace(">", "&gt;")
            result.append(f"<code>{inner}</code>")
            i = end + 1
        else:
            result.append(text[i])
            i += 1
    return "".join(result)


def md_to_html(text: str) -> str:
    """Tiny markdown-ish renderer tuned to the dumped prompts."""
    out: list[str] = []
    in_code = False
    in_table = False
    table_rows: list[str] = []

    def flush_table() -> None:
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        rows = [r.strip().strip("|").split("|") for r in table_rows if r.strip().startswith("|")]
        rows = [[c.strip() for c in r] for r in rows]
        if len(rows) >= 2:
            header = rows[0]
            body = [r for r in rows[2:] if r and not set("".join(r)) <= {"-"}]
            out.append('<table class="schema"><thead><tr>')
            out.append("".join(f"<th>{c}</th>" for c in header))
            out.append("</tr></thead><tbody>")
            for r in body:
                r = r + [""] * (len(header) - len(r))
                out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
            out.append("</tbody></table>")
        table_rows = []
        in_table = False

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()

        if stripped.startswith("```"):
            if not in_code:
                out.append("<pre><code>")
                in_code = True
            else:
                out.append("</code></pre>")
                in_code = False
            continue
        if in_code:
            out.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            continue

        if stripped.startswith("|"):
            in_table = True
            table_rows.append(stripped)
            continue
        if in_table:
            flush_table()

        if stripped.startswith("+") and set(stripped.replace("+", "").replace("-", "")) <= {""}:
            continue
        if stripped.startswith("+") and in_table:
            table_rows.append(stripped)
            continue

        if stripped.startswith("### "):
            out.append(f"<h4>{inline_code(stripped[4:])}</h4>")
        elif stripped.startswith("## "):
            out.append(f"<h3>{inline_code(stripped[3:])}</h3>")
        elif stripped.startswith("# "):
            out.append(f"<h2>{inline_code(stripped[2:])}</h2>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            out.append(f"<li>{inline_code(stripped[2:])}</li>")
        elif stripped.startswith("**") and stripped.endswith("**") and len(stripped) > 4:
            out.append(f"<h3>{stripped[2:-2]}</h3>")
        elif stripped:
            inline = inline_code(stripped)
            inline = inline.replace("**", "<strong>").replace("__", "<em>")
            out.append(f"<p>{inline}</p>")
    if in_table:
        flush_table()
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def main() -> int:
    out = {
        "source": "https://leetcode.com/studyplan/top-sql-50/",
        "seedProgress": sql50.load_progress(),
        "categories": [],
        "questions": [],
        "lessons": [],
    }

    questions = sql50.load_manifest()
    seen_categories: dict[str, dict] = {}

    for q in questions:
        category = q["category"]
        if category not in seen_categories:
            entry = {"name": category, "questionIds": []}
            seen_categories[category] = entry
            out["categories"].append(entry)

        fixture = sql50.fixture_for(q)
        hint = "Hint pending until source data is added."
        solution = "Solution pending until source data is added."
        runnable = False
        fixture_kind = "none"
        if fixture:
            runnable = True
            hint = fixture.get("hint", hint)
            solution = fixture.get("solution_sql", solution).strip()
            fixture_kind = "sample" if fixture.get("source_example") else "edge"

        prompt_html = ""
        path = sql50.source_path_for(q)
        if path and path.exists():
            prompt_html = md_to_html(sql50.problem_section(path.read_text()))

        seen_categories[category]["questionIds"].append(str(q["id"]))
        out["questions"].append({
            "id": q["id"],
            "slug": q["slug"],
            "title": q["title"],
            "category": category,
            "difficulty": q["difficulty"],
            "runnable": runnable,
            "fixtureKind": fixture_kind,
            "hasSource": bool(path and path.exists()),
            "leetcode": f"https://leetcode.com/problems/{q['slug']}/",
            "promptHtml": prompt_html,
            "hint": hint,
            "solution": solution,
        })

    lessons_dir = ROOT / "lessons"
    if lessons_dir.exists():
        for path in sorted(lessons_dir.glob("*.md")):
            raw = path.read_text()
            title = path.stem
            first = raw.splitlines()[0] if raw.splitlines() else title
            if first.startswith("#"):
                title = first.lstrip("# ").strip()
            out["lessons"].append({
                "id": path.stem,
                "title": title,
                "html": md_to_html(raw),
            })

    target = ROOT / "site" / "data.js"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "// AUTO-GENERATED by site/build.py. Do not edit by hand.\n"
        "window.DBMS_DATA = " + json.dumps(out, indent=2) + ";\n",
        encoding="utf-8",
    )
    print(f"Wrote {target.relative_to(ROOT)} "
          f"({len(out['questions'])} questions, {len(out['lessons'])} lessons)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
