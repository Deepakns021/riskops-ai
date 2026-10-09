# Architecture

```mermaid
flowchart LR
  A[Official CERT r4.2 local ignored files] --> B[Schema gate and chunked Pandas aggregation]
  K[Official answer key local ignored file] --> L[Evaluation-only labels]
  B --> C[DuckDB Parquet score artifact]
  L --> D[Chronological held-out evaluation]
  C --> D
  C --> E[Streamlit analyst workspace]
  D --> E
  E --> F[Evidence-grounded draft human disposition]
  E --> G[n8n candidate webhook]
  G --> H[Pending human review no automated action]
```

The model is Isolation Forest trained only on the first 75% of time. Labels are excluded from feature selection and model fitting. The answer key is joined only after scores are generated for benchmark evaluation.
