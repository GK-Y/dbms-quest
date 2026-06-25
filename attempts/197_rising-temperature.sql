-- 197. Rising Temperature
-- Category: Basic Joins | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=197

SELECT today.id 
FROM weather as today
JOIN weather as yesterday 
  ON DATE(today.recordDate, '-1 day') = yesterday.recordDate -- basically if today(3/4/26 -> 2/4/26) = yt(2/4/26) find the 2/4/26 in this table 
where today.temperature > yesterday.temperature
