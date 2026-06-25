-- 1068. Product Sales Analysis I
-- Category: Basic Joins | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=1068

SELECT p.product_name,s.year, s.price
FROM sales as s
JOIN Product as p 
  ON p.product_id = s.product_id
