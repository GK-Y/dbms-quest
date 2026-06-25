-- 1757. Recyclable and Low Fat Products
-- Category: Select | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=1757

SELECT p.product_id
From Products as p
WHERE p.low_fats ='Y' AND p.recyclable = 'Y';
