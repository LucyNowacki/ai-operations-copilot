SELECT
  b.brief_id,
  b.title,
  b.domain,
  b.priority,
  r.severity,
  r.description,
  r.mitigation,
  r.requires_review
FROM risks r
JOIN briefs b ON b.brief_id = r.brief_id
WHERE r.requires_review = 1 OR r.severity IN ('high', 'critical')
ORDER BY
  CASE r.severity
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    ELSE 4
  END,
  b.brief_id;
