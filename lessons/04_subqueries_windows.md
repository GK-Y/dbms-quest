# Subqueries And Window Functions

A subquery is a query used inside another query. It helps when you need a
temporary answer.

```sql
SELECT name
FROM Employee
WHERE salary > (SELECT AVG(salary) FROM Employee);
```

Useful forms:

```sql
WHERE id IN (SELECT ...)
WHERE NOT EXISTS (SELECT ...)
FROM (SELECT ...) AS derived
LIMIT 1 OFFSET 1
```

Window functions calculate across related rows without collapsing them:

```sql
ROW_NUMBER() OVER (PARTITION BY departmentId ORDER BY salary DESC)
SUM(weight) OVER (ORDER BY turn) AS running_weight
DENSE_RANK() OVER (PARTITION BY departmentId ORDER BY salary DESC)
```

Use windows for ranking, consecutive rows, running totals, and "top N per
group" questions.

String tools used near the end:

```sql
LOWER(name)
UPPER(SUBSTR(name, 1, 1))
SUBSTR(name, 2)
LIKE 'DIAB1%' OR LIKE '% DIAB1%'
GROUP_CONCAT(product, ',')
```

Mutation question `196` uses `DELETE`, not `SELECT`. The pattern is: identify
duplicate rows with a subquery, then delete the rows you do not want to keep.

Active habit:

- If the output still needs individual rows, consider a window function.
- If the output needs one row per group, use `GROUP BY`.
- If you need to compare against a derived set, use a subquery or CTE.

CTEs make complex queries readable:

```sql
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (ORDER BY salary DESC) AS rn
  FROM Employee
)
SELECT salary
FROM ranked
WHERE rn = 2;
```
