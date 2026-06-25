# Filtering And Projection

Projection means choosing columns. Filtering means choosing rows.

```sql
SELECT product_id
FROM Products
WHERE low_fats = 'Y' AND recyclable = 'Y';
```

Common filters:

```sql
WHERE population >= 25000000
WHERE area >= 3000000 OR population >= 25000000
WHERE referee_id IS NULL OR referee_id <> 2
WHERE LENGTH(content) > 15
```

Use `DISTINCT` when the answer should list each value only once:

```sql
SELECT DISTINCT author_id AS id
FROM Views
WHERE author_id = viewer_id;
```

Use `AS` to rename an output column when the prompt asks for a specific name:

```sql
SELECT author_id AS id
```

For LeetCode SQL, returning extra columns is usually wrong. Return only the
columns requested, with the requested names.

Sorting only matters when the prompt asks for it:

```sql
ORDER BY id ASC;
ORDER BY created_at DESC;
```

Active chunk:

- 1757: two `AND` filters
- 595: `OR`
- 584: `NULL` plus not equal
- 1148: self-view filter, `DISTINCT`, and `AS id`
- 1683: string length

Pattern to remember: find the table, identify the wanted rows, then project only
the answer columns.
