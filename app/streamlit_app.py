from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from riskops.reporting import ReviewDraft, make_review_draft  # noqa: E402

st.set_page_config(page_title="RiskOps AI", page_icon="🛡️", layout="wide")
st.title("RiskOps AI")
st.caption("Research MVP • synthetic CERT Insider Threat Test Dataset • human review required")
st.warning("This dashboard is not a production monitoring system and does not contain real employee data.")
data_path = ROOT / "data/processed/scored_daily.parquet"
metrics_path = ROOT / "data/processed/metrics.json"
if not data_path.exists():
    st.info("No local score artifact found. Follow data/README.md, then run `python -m riskops.pipeline`.")
    st.stop()

df = pd.read_parquet(data_path)
metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
metrics_cols = st.columns(4)
for column, (label, key) in zip(metrics_cols, [("Precision", "precision"), ("Recall", "recall"), ("F1", "f1"), ("PR-AUC", "pr_auc")]):
    column.metric(label, str(metrics.get(key, "—")))
threshold = st.sidebar.slider("Minimum anomaly score", float(df.anomaly_score.min()), float(df.anomaly_score.max()), float(df.anomaly_score.quantile(.99)))
view = df.loc[df.anomaly_score >= threshold].sort_values("anomaly_score", ascending=False)
st.plotly_chart(px.scatter(view, x="day", y="anomaly_score", color="alert", hover_data=["user", "scenario"], title="Ranked anomaly signals"), use_container_width=True)
st.subheader("Review queue")
st.dataframe(view[["day", "user", "anomaly_score", "alert", "scenario"]].head(100), use_container_width=True, hide_index=True)
if not view.empty:
    choice = st.selectbox("Create evidence-grounded review draft", view.index, format_func=lambda i: f"{view.at[i, 'user']} — {view.at[i, 'day'].date()}")
    row = view.loc[choice]
    st.markdown(make_review_draft(ReviewDraft(str(row.user), str(row.day.date()), float(row.anomaly_score), {key: float(row[key]) for key in ["logon_events", "after_hours_logons", "device_connects", "file_events", "email_events"]})))
