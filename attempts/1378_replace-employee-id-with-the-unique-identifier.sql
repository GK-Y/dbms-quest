-- 1378. Replace Employee ID With The Unique Identifier
-- Category: Basic Joins | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=1378

SELECT eu.unique_id,e.name
FROM Employees as e
LEFT JOIN EmployeeUNI as eu 
  ON e.id = eu.id 

