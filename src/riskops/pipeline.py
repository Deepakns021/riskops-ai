from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, precision_recall_fscore_support
from sklearn.preprocessing import RobustScaler

from .contracts import DatasetLayout, assert_no_label_leakage, inspect_schema, label_user_days

FEATURE_COLUMNS = ["logon_events", "after_hours_logons", "device_connects", "file_events", "email_events"]


def _daily_counts(path: Path, feature: str, activity: str | None = None) -> pd.DataFrame:
    usecols = lambda name: name in {"date", "user", "activity"}
    parts: list[pd.DataFrame] = []
    for chunk in pd.read_csv(path, usecols=usecols, chunksize=250_000):
        chunk["day"] = pd.to_datetime(chunk["date"], errors="coerce").dt.normalize()
        chunk = chunk.dropna(subset=["day", "user"])
        if activity is not None and "activity" in chunk:
            chunk = chunk.loc[chunk["activity"].astype(str).str.lower() == activity.lower()]
        parts.append(chunk.groupby(["user", "day"]).size().rename(feature).reset_index())
    return pd.concat(parts, ignore_index=True).groupby(["user", "day"], as_index=False)[feature].sum()


def build_features(layout: DatasetLayout) -> pd.DataFrame:
    inspect_schema(layout)
    base = layout.release_dir
    logons = _daily_counts(base / "logon.csv", "logon_events", "logon")
    # Time parsing is deliberately separate: malformed timestamps are rejected rather than guessed.
    after_hours_parts: list[pd.DataFrame] = []
    for chunk in pd.read_csv(base / "logon.csv", usecols=["date", "user", "activity"], chunksize=250_000):
        timestamp = pd.to_datetime(chunk["date"], errors="coerce")
        masked = chunk.loc[(chunk["activity"].astype(str).str.lower() == "logon") &
                           ((timestamp.dt.hour < 6) | (timestamp.dt.hour >= 19))].copy()
        masked["day"] = timestamp.loc[masked.index].dt.normalize()
        after_hours_parts.append(masked.dropna(subset=["day"]).groupby(["user", "day"]).size()
                                 .rename("after_hours_logons").reset_index())
    after_hours = pd.concat(after_hours_parts, ignore_index=True).groupby(["user", "day"], as_index=False).sum()
    frames = [logons, after_hours,
              _daily_counts(base / "device.csv", "device_connects", "connect"),
              _daily_counts(base / "file.csv", "file_events"),
              _daily_counts(base / "email.csv", "email_events")]
    output = frames[0]
    for frame in frames[1:]:
        output = output.merge(frame, on=["user", "day"], how="outer")
    return output.fillna(0).sort_values(["day", "user"]).reset_index(drop=True)


def score(features: pd.DataFrame, labels: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | int | str]]:
    assert_no_label_leakage(FEATURE_COLUMNS)
    cutoff = features["day"].quantile(0.75)
    train = features.loc[features.day < cutoff].copy()
    test = features.loc[features.day >= cutoff].copy()
    if train.empty or test.empty:
        raise ValueError("Need at least two chronological periods to make a leakage-safe split.")
    scaler = RobustScaler().fit(train[FEATURE_COLUMNS])
    model = IsolationForest(n_estimators=250, contamination="auto", random_state=42, n_jobs=-1)
    model.fit(scaler.transform(train[FEATURE_COLUMNS]))
    scored = features.copy()
    scored["anomaly_score"] = -model.score_samples(scaler.transform(features[FEATURE_COLUMNS]))
    scored = scored.merge(labels[["user", "day", "is_malicious", "scenario"]], on=["user", "day"], how="left")
    scored["is_malicious"] = scored["is_malicious"].fillna(0).astype(int)
    scored["scenario"] = scored["scenario"].fillna("none")
    threshold = scored.loc[scored.day < cutoff, "anomaly_score"].quantile(0.99)
    scored["alert"] = (scored.anomaly_score >= threshold).astype(int)
    held_out = scored.loc[scored.day >= cutoff]
    precision, recall, f1, _ = precision_recall_fscore_support(
        held_out.is_malicious, held_out.alert, average="binary", zero_division=0
    )
    metrics: dict[str, float | int | str] = {"split": "chronological 75/25", "cutoff": str(cutoff.date()),
        "held_out_rows": len(held_out), "positives": int(held_out.is_malicious.sum()),
        "precision": round(float(precision), 4), "recall": round(float(recall), 4), "f1": round(float(f1), 4)}
    if held_out.is_malicious.nunique() == 2:
        metrics["pr_auc"] = round(float(average_precision_score(held_out.is_malicious, held_out.anomaly_score)), 4)
    else:
        metrics["pr_auc"] = "unavailable: only one class in held-out window"
    return scored, metrics


def run(raw_dir: Path, answers_dir: Path, output_dir: Path) -> dict[str, object]:
    layout = DatasetLayout(raw_dir, answers_dir)
    features = build_features(layout)
    labels = label_user_days(pd.read_csv(layout.labels_path))
    scored, metrics = score(features, labels)
    output_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.register("scored", scored)
    con.execute(f"COPY scored TO '{(output_dir / 'scored_daily.parquet').as_posix()}' (FORMAT PARQUET)")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return {"metrics": metrics, "rows": len(scored)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build RiskOps scored user-day data from official CERT files.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--answers-dir", type=Path, default=Path("data/answers"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.raw_dir, arguments.answers_dir, arguments.output_dir), indent=2))
