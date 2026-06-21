SELECT
  review_state,
  COUNT(*) AS project_count,
  ROUND(AVG(confidence), 3) AS average_confidence
FROM briefs
GROUP BY review_state
ORDER BY project_count DESC, review_state;
