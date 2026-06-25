-- 1661. Average Time of Process per Machine
-- Category: Basic Joins | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=1661

select pre.machine_id 
from activity as pre
JOIN activity as post 
ON pre.machine_id = post.machine_id AND pre.process_id = post.machine_id and post.activity_type = end

