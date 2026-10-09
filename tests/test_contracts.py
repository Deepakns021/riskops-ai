import pandas as pd
import pytest

from riskops.contracts import assert_no_label_leakage, label_user_days


def test_labels_expand_to_daily_windows():
    labels = pd.DataFrame({"dataset": ["4.2"], "user": ["U1"], "start": ["2011-01-01"],
                           "end": ["2011-01-03"], "scenario": [2]})
    result = label_user_days(labels)
    assert len(result) == 3
    assert result.is_malicious.eq(1).all()


def test_labels_are_blocked_from_model_features():
    with pytest.raises(ValueError, match="Label leakage"):
        assert_no_label_leakage(["logon_events", "is_malicious"])
