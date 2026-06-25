-- 1148. Article Views I
-- Category: Select | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=1148

SELECT DISTINCT author_id AS id
FROM Views
WHERE id = viewer_id
ORDER BY id;
