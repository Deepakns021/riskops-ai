# Responsible use and n8n setup

Import `n8n/riskops-review-queue.json` into n8n. It accepts a candidate payload such as:

```json
{"user":"ABC123","day":"2011-02-03","anomaly_score":0.81,"evidence":{"device_connects":4}}
```

The workflow validates fields and sets `PENDING_HUMAN_REVIEW`; it does not send messages, revoke access, change HR records, or make a decision. Add a ticketing/notification connector only after organizational policy, access control, data-retention, and human-review requirements have been approved. Store n8n credentials in n8n's credential manager, never in this repository.

For any future LLM integration, send only the reviewed evidence package, require citations to displayed values, retain the reviewer disposition, and prohibit autonomous adverse action.
