-- 1683. Invalid Tweets
-- Category: Select | Difficulty: Easy
-- Write one SELECT query below. Run: make test Q=1683

SELECT tweet_id
FROM Tweets
WHERE length(content) > 15;
