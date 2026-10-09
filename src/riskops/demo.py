"""Create a tiny, clearly labelled synthetic demo for UI and pipeline verification.

This is not CERT data and must never be reported as a CERT benchmark result.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .pipeline import run


def _events(users: list[str], days: pd.DatetimeIndex, rng: np.random.Generator) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for user in users:
        for day in days:
            count = int(rng.integers(1, 5))
            for index in range(count):
                rows.append({"date": day + pd.Timedelta(hours=9 + index), "user": user, "activity": "Logon"})
    return pd.DataFrame(rows)


def build_demo(root: Path = Path("data/demo")) -> dict[str, object]:
    """Build a local demo artifact at data/processed without overwriting source data."""
    rng = np.random.default_rng(42)
    users = [f"DEMO-{number:03d}" for number in range(1, 31)]
    days = pd.date_range("2025-01-01", periods=60, freq="D")
    raw = root / "raw" / "r4.2"
    answers = root / "answers"
    raw.mkdir(parents=True, exist_ok=True)
    answers.mkdir(parents=True, exist_ok=True)

    logons = _events(users, days, rng)
    # Inject obvious late-period review candidates so the demo evaluation is runnable.
    for user, day in [("DEMO-001", days[52]), ("DEMO-002", days[56])]:
        additions = pd.DataFrame({"date": [day + pd.Timedelta(hours=hour) for hour in range(20, 24)],
                                  "user": user, "activity": "Logon"})
        logons = pd.concat([logons, additions], ignore_index=True)
    logons.to_csv(raw / "logon.csv", index=False)
    pd.DataFrame(columns=["date", "user", "activity"]).to_csv(raw / "device.csv", index=False)
    pd.DataFrame(columns=["date", "user"]).to_csv(raw / "file.csv", index=False)
    pd.DataFrame(columns=["date", "user"]).to_csv(raw / "email.csv", index=False)
    pd.DataFrame({"dataset": ["4.2", "4.2"], "user": ["DEMO-001", "DEMO-002"],
                  "start": [str(days[52].date()), str(days[56].date())],
                  "end": [str(days[52].date()), str(days[56].date())], "scenario": ["demo", "demo"]}).to_csv(
        answers / "insiders.csv", index=False
    )
    result = run(root / "raw", answers, Path("data/processed"))
    Path("data/processed/run_metadata.json").write_text(json.dumps({
        "source": "local synthetic demo", "warning": "Not CERT data. Metrics are for UI verification only."
    }, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build_demo(), indent=2))
