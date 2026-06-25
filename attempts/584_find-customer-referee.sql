-- 584. Find Customer Referee
-- Category: Select | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=584


SELECT name 
FROM Customer
WHERE referee_id IS NULL OR referee_id <> 2;
