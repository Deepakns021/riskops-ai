import pandas as pd

from riskops.pipeline import FEATURE_COLUMNS, score


def test_score_keeps_labels_out_of_features():
    days = pd.date_range("2024-01-01", periods=20, freq="D")
    features = pd.DataFrame({"user": ["U1"] * 20, "day": days,
        **{column: list(range(20)) for column in FEATURE_COLUMNS}})
    labels = pd.DataFrame({"user": ["U1"], "day": [days[-1]], "is_malicious": [1], "scenario": ["1"]})
    scored, metrics = score(features, labels)
    assert "is_malicious" in scored
    assert metrics["split"] == "chronological 75/25"
