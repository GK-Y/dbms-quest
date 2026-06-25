# Joins

A join combines rows from two tables. Use it when one table has facts and
another table has names, categories, or related events.

```sql
SELECT e.name, b.bonus
FROM Employee AS e
LEFT JOIN Bonus AS b
  ON e.empId = b.empId;
```

Join types you need first:

- `INNER JOIN`: keep only matching rows from both sides.
- `LEFT JOIN`: keep every row from the left table, even when the right side is
  missing.

Use `LEFT JOIN ... WHERE right_table.id IS NULL` to find missing related rows.

```sql
SELECT v.customer_id
FROM Visits AS v
LEFT JOIN Transactions AS t
  ON v.visit_id = t.visit_id
WHERE t.transaction_id IS NULL;
```

For 1581, think in two steps. First, keep visits that have no matching
transaction:

```sql
FROM Visits AS v
LEFT JOIN Transactions AS t
  ON v.visit_id = t.visit_id
WHERE t.transaction_id IS NULL
```

After that filter, each remaining row is one visit with no transaction. The
question wants the count per customer, so group by customer:

```sql
SELECT v.customer_id, COUNT(*) AS count_no_trans
FROM Visits AS v
LEFT JOIN Transactions AS t
  ON v.visit_id = t.visit_id
WHERE t.transaction_id IS NULL
GROUP BY v.customer_id;
```

The important detail: put `t.transaction_id IS NULL` in `WHERE` after the
`LEFT JOIN`. That means "there was no matching transaction row."

Aliases make joins readable. Once you write `Employee AS e`, use `e.name` and
`e.empId` instead of the full table name.

Self-join means joining a table to itself. It is useful for comparisons between
two rows, such as today versus yesterday.

SQLite date helper for "previous day":

```sql
DATE(today.recordDate, '-1 day') = yesterday.recordDate
```

For paired events such as start/end rows, join on every shared identifier:

```sql
s.machine_id = e.machine_id
AND s.process_id = e.process_id
```

Active chunk:

- 1378: simple left join for optional data
- 1068: inner join for product names
- 1581: left join plus `IS NULL`
- 197: self-join by previous date
- 1661: aliases, paired start/end rows, `AVG`, `ROUND`
