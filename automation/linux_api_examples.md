# Linux and API Examples

The default demo runs offline:

```bash
export AI_PROVIDER=offline
export DATABASE_PATH=outputs/career_proof.db
python -m ai_ops_copilot.cli run-demo
```

Inspect the generated summary with `jq`:

```bash
jq '.priority_distribution, .review_queue_count' outputs/career_proof_summary.json
```

Review a high-risk brief:

```bash
python -m ai_ops_copilot.cli review \
  --brief-id BRIEF-0001 \
  --status approved \
  --notes "Reviewed for portfolio demo; keep medical output advisory."
```

Example webhook trigger with `curl`:

```bash
curl -X POST "https://ops.example.test/webhooks/career-proof/project-note" \
  -H "Content-Type: application/json" \
  -d @automation/webhook_payload_example.json
```

Never commit real API keys. Use `.env.example` as a template and keep local secrets in an ignored `.env` file.
