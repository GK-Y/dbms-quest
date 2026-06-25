-- 1581. Customer Who Visited but Did Not Make Any Transactions
-- Category: Basic Joins | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=1581

select v.customer_id, COUNT(*) AS count_no_trans 
FROM visits as v
left join Transactions as t 
  ON v.visit_id = t.visit_id
where t.transaction_id IS NULL
GROUP BY v.customer_id

