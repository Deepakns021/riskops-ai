from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

RELEASE = "r4.2"
EVENT_FILES = ("logon.csv", "device.csv", "file.csv", "email.csv")
REQUIRED_COMMON = {"date", "user"}
REQUIRED_EVENT_COLUMNS = {
    "logon.csv": REQUIRED_COMMON | {"activity"},
    "device.csv": REQUIRED_COMMON | {"activity"},
    "file.csv": REQUIRED_COMMON,
    "email.csv": REQUIRED_COMMON,
}


@dataclass(frozen=True)
class DatasetLayout:
    raw_dir: Path
    answers_dir: Path
    release: str = RELEASE

    @property
    def release_dir(self) -> Path:
        return self.raw_dir / self.release

    @property
    def labels_path(self) -> Path:
        return self.answers_dir / "insiders.csv"


def inspect_schema(layout: DatasetLayout) -> dict[str, list[str]]:
    """Return first-row schemas and fail clearly before processing multi-GB files."""
    schemas: dict[str, list[str]] = {}
    for filename in EVENT_FILES:
        path = layout.release_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing {path}. See data/README.md.")
        columns = list(pd.read_csv(path, nrows=0).columns)
        missing = REQUIRED_EVENT_COLUMNS[filename] - set(columns)
        if missing:
            raise ValueError(f"{filename} missing required columns: {sorted(missing)}")
        schemas[filename] = columns
    if not layout.labels_path.exists():
        raise FileNotFoundError(f"Missing {layout.labels_path}. Obtain it from answers.tar.bz2.")
    label_columns = list(pd.read_csv(layout.labels_path, nrows=0).columns)
    expected = {"dataset", "user", "start", "end"}
    if missing := expected - set(label_columns):
        raise ValueError(f"insiders.csv missing required columns: {sorted(missing)}")
    schemas["insiders.csv"] = label_columns
    return schemas


def label_user_days(labels: pd.DataFrame, release: str = RELEASE) -> pd.DataFrame:
    """Create evaluation-only user-day labels from CERT's answer-key time windows."""
    release_value = release.removeprefix("r")
    selected = labels.loc[labels["dataset"].astype(str) == release_value].copy()
    selected["start"] = pd.to_datetime(selected["start"], errors="raise")
    selected["end"] = pd.to_datetime(selected["end"], errors="raise")
    rows: list[dict[str, object]] = []
    for _, item in selected.iterrows():
        for day in pd.date_range(item.start.normalize(), item.end.normalize(), freq="D"):
            rows.append({"user": item.user, "day": day, "is_malicious": 1,
                         "scenario": str(item.get("scenario", "unknown"))})
    if not rows:
        return pd.DataFrame(columns=["user", "day", "is_malicious", "scenario"])
    return pd.DataFrame(rows).drop_duplicates(["user", "day"])


def assert_no_label_leakage(columns: Iterable[str]) -> None:
    forbidden = {"is_malicious", "scenario", "label", "target", "insider"}
    leaked = [column for column in columns if column.lower() in forbidden]
    if leaked:
        raise ValueError(f"Label leakage: these columns cannot enter model features: {leaked}")
