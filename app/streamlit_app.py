from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from riskops.reporting import ReviewDraft, make_review_draft

DATA_PATH = ROOT / "data/processed/scored_daily.parquet"
METRICS_PATH = ROOT / "data/processed/metrics.json"
METADATA_PATH = ROOT / "data/processed/run_metadata.json"
FEATURES = ["logon_events", "after_hours_logons", "device_connects", "file_events", "email_events"]
FEATURE_LABELS = {
    "logon_events": "Logon events",
    "after_hours_logons": "After-hours logons",
    "device_connects": "Device connects",
    "file_events": "File events",
    "email_events": "Email events",
}


@st.cache_data(show_spinner=False)
def load_scores(path: str) -> pd.DataFrame:
    return duckdb.sql("SELECT * FROM read_parquet(?)", params=[path]).df()


@st.cache_data(show_spinner=False)
def load_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}


def format_metric(value: object) -> str:
    return f"{float(value):.3f}" if isinstance(value, (float, int)) else str(value or "—")


st.set_page_config(page_title="RiskOps AI", page_icon=":material/shield:", layout="wide")

if not DATA_PATH.exists():
    st.title("RiskOps AI")
    st.info("No local score artifact found. Run `python -m riskops.demo` for the guided demo, or use the official CERT setup in `data/README.md`.", icon=":material/info:")
    st.stop()

df = load_scores(str(DATA_PATH))
metrics = load_json(str(METRICS_PATH))
metadata = load_json(str(METADATA_PATH))
is_demo = metadata.get("source") == "local synthetic demo"

with st.sidebar:
    st.header("Review controls", icon=":material/tune:")
    percentile = st.select_slider("Queue threshold", options=[90, 95, 99], value=95)
    st.caption("Shows the highest-scoring user-days above the selected percentile.")
    st.divider()
    st.subheader("Data source")
    st.write("Local synthetic demo" if is_demo else "Official CERT benchmark")
    st.caption("Generated for UI walkthrough" if is_demo else "Local benchmark artifact")
    st.divider()
    st.caption("Risk scores prioritize review; they do not establish wrongdoing.")

st.title("RiskOps AI")
st.caption("Human-in-the-loop insider-risk analytics • Analyst review workbench")
st.badge("DEMO — generated local data" if is_demo else "CERT benchmark — local artifact", icon=":material/science:", color="orange" if is_demo else "blue")

if is_demo:
    st.info("This walkthrough uses generated local data to demonstrate the interface. It is not CERT data and no evaluation metric here should be presented as a benchmark result.", icon=":material/visibility:")
else:
    st.warning("Research benchmark only: synthetic data, human review required, and no automated employment or access action.", icon=":material/warning:")

threshold = float(df["anomaly_score"].quantile(percentile / 100))
queue = df.loc[df["anomaly_score"] >= threshold].sort_values("anomaly_score", ascending=False).copy()
queue["review_status"] = "Review recommended"
queue["anomaly_score"] = queue["anomaly_score"].round(3)
top_queue = queue.head(12)
high_risk_users = queue["user"].nunique()
latest_day = pd.to_datetime(df["day"]).max().strftime("%d %b %Y")

with st.container(horizontal=True):
    st.metric("Review candidates", len(queue), help="User-days at or above the selected anomaly-score percentile.", border=True)
    st.metric("Distinct users", high_risk_users, help="Unique users represented in the review queue.", border=True)
    st.metric("Review threshold", f"Top {100 - percentile}%", help="Percentile of anomaly scores included in the queue.", border=True)
    st.metric("Latest activity", latest_day, help="Latest day represented in the local score artifact.", border=True)

st.header("Review overview", icon=":material/monitoring:")
left, right = st.columns((1.15, 0.85), gap="large")

with left, st.container(border=True):
    st.subheader("Highest-priority candidates")
    risk_by_user = top_queue.groupby("user", as_index=False)["anomaly_score"].max().sort_values("anomaly_score")
    risk_chart = px.bar(
        risk_by_user,
        x="anomaly_score",
        y="user",
        orientation="h",
        color="anomaly_score",
        color_continuous_scale=["#BFDBFE", "#2563EB", "#1E3A8A"],
        labels={"anomaly_score": "Anomaly score", "user": "User"},
    )
    risk_chart.update_layout(coloraxis_showscale=False, margin={"l": 0, "r": 0, "t": 10, "b": 0}, height=360)
    st.plotly_chart(risk_chart, width="stretch", alt="Ranked bar chart of review candidates by anomaly score.")

with right, st.container(border=True):
    st.subheader("Why this matters")
    st.markdown("Review candidates are ranked from behavioral signals, then verified by an analyst before any follow-up.")
    st.markdown("**Analyst workflow**")
    st.markdown("1. Review the observed event pattern.\n2. Validate context and data quality.\n3. Record a human disposition.")
    st.caption("Scores are triage aids—not findings of misconduct.")

st.header("Analyst review queue", icon=":material/fact_check:")
st.caption("Select one user-day to inspect the observed evidence. The queue is intentionally capped at 12 candidates for focused review.")
st.dataframe(
    top_queue[["day", "user", "anomaly_score", "scenario", "review_status"]],
    column_config={
        "day": st.column_config.DateColumn("Observed day", format="DD MMM YYYY"),
        "user": st.column_config.TextColumn("User", pinned=True),
        "anomaly_score": st.column_config.NumberColumn("Risk score", format="%.3f"),
        "scenario": st.column_config.TextColumn("Scenario"),
        "review_status": st.column_config.TextColumn("Recommended action"),
    },
    hide_index=True,
    height=330,
    width="stretch",
    alt="Table of the highest-priority review candidates.",
)

if top_queue.empty:
    st.info("No candidates meet this threshold. Lower the queue threshold from the sidebar.", icon=":material/filter_alt:")
    st.stop()

choice = st.selectbox(
    "Select a candidate for evidence review",
    top_queue.index,
    format_func=lambda index: f"{top_queue.at[index, 'user']} — {pd.to_datetime(top_queue.at[index, 'day']).strftime('%d %b %Y')}",
)
selected = top_queue.loc[choice]

detail_left, detail_right = st.columns((0.9, 1.1), gap="large")
with detail_left, st.container(border=True):
    st.subheader("Observed signal profile")
    evidence = pd.DataFrame({
        "Signal": [FEATURE_LABELS[feature] for feature in FEATURES],
        "Events": [float(selected[feature]) for feature in FEATURES],
    })
    signal_chart = px.bar(
        evidence,
        x="Events",
        y="Signal",
        orientation="h",
        color="Events",
        color_continuous_scale=["#DBEAFE", "#1D4ED8"],
    )
    signal_chart.update_layout(coloraxis_showscale=False, margin={"l": 0, "r": 0, "t": 10, "b": 0}, height=290)
    st.plotly_chart(signal_chart, width="stretch", alt="Bar chart of event counts for the selected review candidate.")

with detail_right, st.container(border=True):
    st.subheader("Recommended analyst action")
    st.markdown("**Validate context before escalating.** Check approved work, role expectations, event completeness, and identity mappings.")
    st.caption("No action is automated. Every candidate requires human review under organizational policy.")
    with st.expander("Open evidence-grounded review draft", icon=":material/article:"):
        st.markdown(make_review_draft(ReviewDraft(
            str(selected.user),
            str(pd.to_datetime(selected.day).date()),
            float(selected.anomaly_score),
            {FEATURE_LABELS[feature]: float(selected[feature]) for feature in FEATURES},
        )))

with st.expander("Evaluation and methodology", icon=":material/analytics:"):
    st.caption("Metrics are available for benchmark evaluation only; they are not shown as portfolio claims in demo mode.")
    if is_demo:
        st.write("Run the official CERT pipeline to generate benchmark evaluation metrics.")
    else:
        st.dataframe(pd.DataFrame([{
            "Precision": format_metric(metrics.get("precision")),
            "Recall": format_metric(metrics.get("recall")),
            "F1": format_metric(metrics.get("f1")),
            "PR-AUC": format_metric(metrics.get("pr_auc")),
            "Split": metrics.get("split", "—"),
        }]), hide_index=True, width="stretch", alt="Table of held-out benchmark evaluation metrics.")
        st.caption("Chronological holdout; labels are excluded from model features and fitting.")
