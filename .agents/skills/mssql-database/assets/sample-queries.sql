-- Sample queries for SuperCompany database

-- 1. Users per country
SELECT country, COUNT(*) AS user_count
FROM Users
GROUP BY country
ORDER BY user_count DESC;

-- 2. Average salary by country
SELECT country, AVG(salary) AS avg_salary, MIN(salary) AS min_salary, MAX(salary) AS max_salary
FROM Users
GROUP BY country
ORDER BY avg_salary DESC;

-- 3. Top 10 earners
SELECT TOP 10 UsersID, name, surname, country, city, salary
FROM Users
ORDER BY salary DESC;

-- 4. Users with salary above average
SELECT UsersID, name, surname, email, salary
FROM Users
WHERE salary > (SELECT AVG(salary) FROM Users)
ORDER BY salary DESC;

-- 5. Duplicate email check
SELECT email, COUNT(*) AS cnt
FROM Users
GROUP BY email
HAVING COUNT(*) > 1;

-- 6. Country-city distribution
SELECT country, city, COUNT(*) AS cnt
FROM Users
GROUP BY country, city
ORDER BY country, cnt DESC;

-- 7. Salary distribution (buckets)
SELECT
    CASE
        WHEN salary < 3000 THEN 'Low (<3000)'
        WHEN salary < 6000 THEN 'Mid (3000-6000)'
        WHEN salary < 10000 THEN 'High (6000-10000)'
        ELSE 'Premium (10000+)'
    END AS salary_band,
    COUNT(*) AS cnt
FROM Users
GROUP BY
    CASE
        WHEN salary < 3000 THEN 'Low (<3000)'
        WHEN salary < 6000 THEN 'Mid (3000-6000)'
        WHEN salary < 10000 THEN 'High (6000-10000)'
        ELSE 'Premium (10000+)'
    END
ORDER BY MIN(salary);
