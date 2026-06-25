#!/usr/bin/env python3
"""Fetch all 50 LeetCode Top SQL 50 study plan questions and save as categorized markdown files."""

import json
import os
import re
import time
import urllib.request
import urllib.parse
import html2text

GRAPHQL_URL = "https://leetcode.com/graphql"

# Study plan subgroups (slug -> human-readable folder name)
SUBGROUPS = [
    ("Select", "01_select"),
    ("Basic Joins", "02_basic_joins"),
    ("Basic Aggregate Functions", "03_basic_aggregate_functions"),
    ("Sorting and Grouping", "04_sorting_and_grouping"),
    ("Advanced Select and Joins", "05_advanced_select_and_joins"),
    ("Subqueries", "06_subqueries"),
    ("Advanced String Functions / Regex / Clause", "07_advanced_string_functions_regex_clause"),
]

# (groupName, slug, title, titleSlug, difficulty) tuples gathered from the study plan
QUESTIONS = [
    # Select
    ("Select", "recyclable-and-low-fat-products", "Recyclable and Low Fat Products", "EASY"),
    ("Select", "find-customer-referee", "Find Customer Referee", "EASY"),
    ("Select", "big-countries", "Big Countries", "EASY"),
    ("Select", "article-views-i", "Article Views I", "EASY"),
    ("Select", "invalid-tweets", "Invalid Tweets", "EASY"),
    # Basic Joins
    ("Basic Joins", "replace-employee-id-with-the-unique-identifier", "Replace Employee ID With The Unique Identifier", "EASY"),
    ("Basic Joins", "product-sales-analysis-i", "Product Sales Analysis I", "EASY"),
    ("Basic Joins", "customer-who-visited-but-did-not-make-any-transactions", "Customer Who Visited but Did Not Make Any Transactions", "EASY"),
    ("Basic Joins", "rising-temperature", "Rising Temperature", "EASY"),
    ("Basic Joins", "average-time-of-process-per-machine", "Average Time of Process per Machine", "EASY"),
    ("Basic Joins", "employee-bonus", "Employee Bonus", "EASY"),
    ("Basic Joins", "students-and-examinations", "Students and Examinations", "EASY"),
    ("Basic Joins", "managers-with-at-least-5-direct-reports", "Managers with at Least 5 Direct Reports", "MEDIUM"),
    ("Basic Joins", "confirmation-rate", "Confirmation Rate", "MEDIUM"),
    # Basic Aggregate Functions
    ("Basic Aggregate Functions", "not-boring-movies", "Not Boring Movies", "EASY"),
    ("Basic Aggregate Functions", "average-selling-price", "Average Selling Price", "EASY"),
    ("Basic Aggregate Functions", "project-employees-i", "Project Employees I", "EASY"),
    ("Basic Aggregate Functions", "percentage-of-users-attended-a-contest", "Percentage of Users Attended a Contest", "EASY"),
    ("Basic Aggregate Functions", "queries-quality-and-percentage", "Queries Quality and Percentage", "EASY"),
    ("Basic Aggregate Functions", "monthly-transactions-i", "Monthly Transactions I", "MEDIUM"),
    ("Basic Aggregate Functions", "immediate-food-delivery-ii", "Immediate Food Delivery II", "MEDIUM"),
    ("Basic Aggregate Functions", "game-play-analysis-iv", "Game Play Analysis IV", "MEDIUM"),
    # Sorting and Grouping
    ("Sorting and Grouping", "number-of-unique-subjects-taught-by-each-teacher", "Number of Unique Subjects Taught by Each Teacher", "EASY"),
    ("Sorting and Grouping", "user-activity-for-the-past-30-days-i", "User Activity for the Past 30 Days I", "EASY"),
    ("Sorting and Grouping", "product-sales-analysis-iii", "Product Sales Analysis III", "MEDIUM"),
    ("Sorting and Grouping", "classes-with-at-least-5-students", "Classes With at Least 5 Students", "EASY"),
    ("Sorting and Grouping", "find-followers-count", "Find Followers Count", "EASY"),
    ("Sorting and Grouping", "biggest-single-number", "Biggest Single Number", "EASY"),
    ("Sorting and Grouping", "customers-who-bought-all-products", "Customers Who Bought All Products", "MEDIUM"),
    # Advanced Select and Joins
    ("Advanced Select and Joins", "the-number-of-employees-which-report-to-each-employee", "The Number of Employees Which Report to Each Employee", "EASY"),
    ("Advanced Select and Joins", "primary-department-for-each-employee", "Primary Department for Each Employee", "EASY"),
    ("Advanced Select and Joins", "triangle-judgement", "Triangle Judgement", "EASY"),
    ("Advanced Select and Joins", "consecutive-numbers", "Consecutive Numbers", "MEDIUM"),
    ("Advanced Select and Joins", "product-price-at-a-given-date", "Product Price at a Given Date", "MEDIUM"),
    ("Advanced Select and Joins", "last-person-to-fit-in-the-bus", "Last Person to Fit in the Bus", "MEDIUM"),
    ("Advanced Select and Joins", "count-salary-categories", "Count Salary Categories", "MEDIUM"),
    # Subqueries
    ("Subqueries", "employees-whose-manager-left-the-company", "Employees Whose Manager Left the Company", "EASY"),
    ("Subqueries", "exchange-seats", "Exchange Seats", "MEDIUM"),
    ("Subqueries", "movie-rating", "Movie Rating", "MEDIUM"),
    ("Subqueries", "restaurant-growth", "Restaurant Growth", "MEDIUM"),
    ("Subqueries", "friend-requests-ii-who-has-the-most-friends", "Friend Requests II: Who Has the Most Friends", "MEDIUM"),
    ("Subqueries", "investments-in-2016", "Investments in 2016", "MEDIUM"),
    ("Subqueries", "department-top-three-salaries", "Department Top Three Salaries", "HARD"),
    # Advanced String Functions / Regex / Clause
    ("Advanced String Functions / Regex / Clause", "fix-names-in-a-table", "Fix Names in a Table", "EASY"),
    ("Advanced String Functions / Regex / Clause", "patients-with-a-condition", "Patients With a Condition", "EASY"),
    ("Advanced String Functions / Regex / Clause", "delete-duplicate-emails", "Delete Duplicate Emails", "EASY"),
    ("Advanced String Functions / Regex / Clause", "second-highest-salary", "Second Highest Salary", "MEDIUM"),
    ("Advanced String Functions / Regex / Clause", "group-sold-products-by-the-date", "Group Sold Products By The Date", "EASY"),
    ("Advanced String Functions / Regex / Clause", "list-the-products-ordered-in-a-period", "List the Products Ordered in a Period", "EASY"),
    ("Advanced String Functions / Regex / Clause", "find-users-with-valid-e-mails", "Find Users With Valid E-Mails", "EASY"),
]

DIFF_BADGE = {"EASY": "Easy", "MEDIUM": "Medium", "HARD": "Hard"}


def graphql(query, variables):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_question(title_slug):
    q = (
        "query getQuestion($titleSlug: String!){"
        "question(titleSlug:$titleSlug){"
        "questionFrontendId title difficulty content "
        "codeSnippets{lang code} topicTags{name}"
        "}}"
    )
    data = graphql(q, {"titleSlug": title_slug})
    return data["data"]["question"]


def html_to_md(html):
    h = html2text.HTML2Text()
    h.body_width = 0  # don't wrap
    h.ignore_images = True
    h.ignore_links = False
    h.protect_links = True
    md = h.handle(html or "")
    # tidy excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md).strip()
    return md


def get_mysql_snippet(code_snippets):
    if not code_snippets:
        return ""
    for snip in code_snippets:
        if snip["lang"] == "MySQL":
            return snip["code"].strip()
    return ""


def slugify(name):
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"^_+|_+$", "", s)
    return s


def build_folder_map():
    m = {}
    for pretty, folder in SUBGROUPS:
        m[pretty] = folder
    return m


def write_question(folder_map, group, title_slug, title, difficulty, q):
    folder = folder_map[group]
    os.makedirs(folder, exist_ok=True)
    fid = q["questionFrontendId"]
    fname = f"{fid.zfill(4)}_{title_slug}.md"
    path = os.path.join(folder, fname)

    body_md = html_to_md(q["content"])
    mysql_template = get_mysql_snippet(q.get("codeSnippets"))
    tags = ", ".join(t["name"] for t in q.get("topicTags", []))

    lines = []
    lines.append(f"# {fid}. {title}\n")
    lines.append(f"**Difficulty:** {DIFF_BADGE.get(difficulty, difficulty)}  ")
    lines.append(f"**Category:** {group}  ")
    lines.append(f"**LeetCode:** https://leetcode.com/problems/{title_slug}/  ")
    if tags:
        lines.append(f"**Tags:** {tags}  ")
    lines.append("\n---\n")
    lines.append("## Problem\n")
    lines.append(body_md)
    lines.append("\n")
    lines.append("---\n")
    lines.append("## Solution\n")
    lines.append("```sql")
    lines.append(mysql_template if mysql_template else "-- Write your solution here")
    lines.append("```\n")

    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path


def write_index(folder_map, results):
    # results: list of (group, q)
    lines = []
    lines.append("# LeetCode Top SQL 50 - Study Plan\n")
    lines.append("> Source: https://leetcode.com/studyplan/top-sql-50/\n")
    lines.append(f"> Total questions: **{len(results)}**\n")
    lines.append("---\n")
    # stats
    diff_counts = {"EASY": 0, "MEDIUM": 0, "HARD": 0}
    for _, _, _, diff in QUESTIONS:
        diff_counts[diff] = diff_counts.get(diff, 0) + 1
    lines.append("## Overview\n")
    lines.append(f"- Easy: {diff_counts['EASY']}")
    lines.append(f"- Medium: {diff_counts['MEDIUM']}")
    lines.append(f"- Hard: {diff_counts['HARD']}\n")
    lines.append("---\n")
    # per category
    by_group = {}
    for group, title_slug, title, diff in QUESTIONS:
        by_group.setdefault(group, []).append((title_slug, title, diff))
    lines.append("## Categories\n")
    for pretty, folder in SUBGROUPS:
        items = by_group.get(pretty, [])
        lines.append(f"### {pretty}  _(folder: `{folder}/` — {len(items)} questions)_\n")
        for title_slug, title, diff in items:
            # find frontend id from results
            fid = next((q["questionFrontendId"] for g, ts, q in results if g == pretty and ts == title_slug), "?")
            badge = DIFF_BADGE.get(diff, diff)
            lines.append(f"- {fid}. [{title}]({folder}/{fid.zfill(4)}_{title_slug}.md) `#{badge}`")
        lines.append("")
    with open("src_questions/README.md", "w") as f:
        f.write("\n".join(lines))


def main():
    folder_map = build_folder_map()
    # create base + folders
    os.makedirs("src_questions", exist_ok=True)

    results = []
    total = len(QUESTIONS)
    for i, (group, title_slug, title, diff) in enumerate(QUESTIONS, 1):
        try:
            q = fetch_question(title_slug)
        except Exception as e:
            print(f"[{i}/{total}] FAILED {title_slug}: {e}")
            continue
        # write into src_questions/<folder>
        folder = folder_map[group]
        full_folder = os.path.join("src_questions", folder)
        os.makedirs(full_folder, exist_ok=True)
        fid = q["questionFrontendId"]
        fname = f"{fid.zfill(4)}_{title_slug}.md"
        path = os.path.join(full_folder, fname)

        body_md = html_to_md(q["content"])
        mysql_template = get_mysql_snippet(q.get("codeSnippets"))
        tags = ", ".join(t["name"] for t in q.get("topicTags", []))

        lines = []
        lines.append(f"# {fid}. {title}\n")
        lines.append(f"**Difficulty:** {DIFF_BADGE.get(diff, diff)}  ")
        lines.append(f"**Category:** {group}  ")
        lines.append(f"**LeetCode:** https://leetcode.com/problems/{title_slug}/  ")
        if tags:
            lines.append(f"**Tags:** {tags}  ")
        lines.append("\n---\n")
        lines.append("## Problem\n")
        lines.append(body_md)
        lines.append("\n")
        lines.append("---\n")
        lines.append("## Solution\n")
        lines.append("```sql")
        lines.append(mysql_template if mysql_template else "-- Write your solution here")
        lines.append("```\n")
        with open(path, "w") as f:
            f.write("\n".join(lines))

        results.append((group, title_slug, q))
        print(f"[{i}/{total}] OK {fid} {title_slug}")
        time.sleep(0.3)

    # write index README inside src_questions
    write_index(folder_map, results)
    print(f"\nDone. {len(results)}/{total} questions saved.")


if __name__ == "__main__":
    main()
