# Grouping And Aggregates

Aggregates turn many rows into one value.

```sql
COUNT(*)
COUNT(DISTINCT subject_id)
SUM(amount)
AVG(price)
MIN(order_date)
MAX(order_date)
```

`GROUP BY` makes one result row per group:

```sql
SELECT customer_id, COUNT(*) AS visits
FROM Visits
GROUP BY customer_id;
```

`WHERE` filters rows before grouping. `HAVING` filters groups after grouping.

```sql
SELECT class
FROM Courses
GROUP BY class
HAVING COUNT(student) >= 5;
```

For averages in LeetCode, watch rounding:

```sql
ROUND(AVG(value), 2)
```

Useful grouping patterns in this study plan:

```sql
COUNT(DISTINCT user_id)
SUM(CASE WHEN status = 'confirmed' THEN 1 ELSE 0 END)
ROUND(100.0 * good_count / total_count, 2)
```

Use `CASE` when a prompt asks you to count or label rows conditionally:

```sql
CASE
  WHEN income < 20000 THEN 'Low Salary'
  ELSE 'Other'
END
```

Active habit:

1. Decide the output grain: one row per what?
2. Put that grain in `GROUP BY`.
3. Aggregate the remaining facts.
4. Use `HAVING` only for conditions on aggregate results.

Questions in this chunk use: `%` modulo for odd/even IDs, `BETWEEN` for date
ranges, `ROUND`, `COUNT(DISTINCT ...)`, `SUM(...)`, and `CASE`.
