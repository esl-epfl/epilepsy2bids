"""Load TUEP seizure annotations into a simple internal event model."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import pandas as pd

SEIZURE_LABELS = {
    "SEIZ",
    "FNSZ",
    "GNSZ",
    "SPSZ",
    "CPSZ",
    "ABSZ",
    "TNSZ",
    "CNSZ",
    "TCSZ",
    "ATSZ",
    "MYSZ",
}


@dataclass(frozen=True)
class TuepEvent:
    onset: float
    duration: float
    trial_type: str
    channels: str


def _parse_csv_bi(csv_path: Path) -> List[TuepEvent]:
    df = pd.read_csv(csv_path, comment="#", delimiter=",")
    events: list[TuepEvent] = []
    for _, row in df.iterrows():
        label = str(row.get("label", "")).strip().upper()
        if label not in SEIZURE_LABELS:
            continue
        try:
            onset = float(row["start_time"])
            stop = float(row["stop_time"])
        except (KeyError, ValueError, TypeError):
            continue
        if stop < onset:
            continue
        channel = str(row.get("channel", "n/a")).strip()
        if channel.upper() == "TERM":
            channel = "n/a"
        events.append(
            TuepEvent(
                onset=onset,
                duration=stop - onset,
                trial_type="seizure",
                channels=channel,
            )
        )
    return events


def load_tuep_annotations(edf_path: str | Path) -> List[TuepEvent]:
    """Load seizure annotations for a given EDF file.

    Supported formats:
    - <edf_stem>.csv_bi (TUH-style CSV annotations)
    """
    edf_path = Path(edf_path)
    csv_bi = edf_path.with_suffix(".csv_bi")
    if csv_bi.exists():
        return _parse_csv_bi(csv_bi)
    other_sidecars = sorted(
        p
        for p in edf_path.parent.glob(f"{edf_path.stem}.*")
        if p.is_file() and p.suffix.lower() != ".edf"
    )
    if other_sidecars:
        extras = ", ".join(p.name for p in other_sidecars)
        print(f"TODO: Unsupported annotation format for {edf_path}: {extras}")
    return []


def write_events_tsv(events: Iterable[TuepEvent], out_path: Path) -> bool:
    rows = [
        {
            "onset": event.onset,
            "duration": event.duration,
            "trial_type": event.trial_type,
            "channels": event.channels,
        }
        for event in events
    ]
    if not rows:
        return False
    df = pd.DataFrame(rows)
    df.to_csv(out_path, sep="\t", index=False)
    return True
