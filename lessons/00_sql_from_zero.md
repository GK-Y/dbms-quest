# SQL From Zero

SQL is how you ask a relational database questions. A database has tables. A
table has rows and columns. A query returns another table.

The core shape is:

```sql
SELECT columns
FROM table
WHERE row_filter;
```

Read it in this order: `FROM` chooses the table, `WHERE` keeps rows, and
`SELECT` chooses the columns to show.

Small example:

```sql
SELECT name, city
FROM Customers
WHERE city = 'Pune';
```

Important beginner rules:

- Single quotes are for text values: `'Y'`, `'India'`.
- `=` checks equality. `<>` means not equal.
- `AND` means both conditions must be true.
- `OR` means at least one condition must be true.
- `NULL` means unknown or missing. Use `IS NULL`, not `= NULL`.

Active drill:

1. Run `make reset Q=1757`.
2. Run `make question Q=1757` to read the actual question.
3. Run `make schema Q=1757` to see the table and sample rows.
4. Open `attempts/1757_recyclable-and-low-fat-products.sql`.
5. Write a query with `SELECT`, `FROM`, and `WHERE`.
6. Run `make test Q=1757`.

Do not rush to the solution. A failed test is useful: inspect what your query
returned, then tighten the filter.
