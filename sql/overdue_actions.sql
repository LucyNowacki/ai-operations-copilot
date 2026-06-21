SELECT
  b.brief_id,
  b.title,
  a.action,
  a.owner,
  a.due_date,
  a.status
FROM actions a
JOIN briefs b ON b.brief_id = a.brief_id
WHERE a.status != 'done'
  AND a.due_date IS NOT NULL
  AND date(a.due_date) < date('now')
ORDER BY date(a.due_date), b.brief_id;
