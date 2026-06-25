-- 595. Big Countries
-- Category: Select | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=595

SELECT name, population, area
FROM world
WHERE area >= 3000000 OR 25000000 <= population;
