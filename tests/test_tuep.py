import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from epilepsy2bids.bids.tuep.convert2bids import convert
from epilepsy2bids.load_annotations.tuep import load_tuep_annotations

DATA_DIR = (
    Path(__file__).parent
    / "data"
    / "tuh"
    / "dev"
    / "aaaaaool"
    / "s004_2013"
    / "01_tcp_ar"
)

EDF = DATA_DIR / "aaaaaool_s004_t001.edf"
CSV = DATA_DIR / "aaaaaool_s004_t001.csv_bi"


def test_tuep_seizure_annotation_parser():
    events = load_tuep_annotations(EDF)

    assert len(events) == 1

    event = events[0]

    assert event.onset == pytest.approx(733.9656)
    assert event.duration == pytest.approx(84.0546)
    assert event.trial_type == "seizure"
    assert event.channels == "n/a"


def test_tuep_conversion_with_seizure(tmp_path):
    input_root = tmp_path / "input"
    output_root = tmp_path / "output"

    target = (
        input_root
        / "00_epilepsy"
        / "aaaaaool"
        / "s004_2013"
        / "01_tcp_ar"
    )

    target.mkdir(parents=True)

    shutil.copy2(EDF, target / EDF.name)
    shutil.copy2(CSV, target / CSV.name)

    convert(input_root, output_root)

    events_files = list(output_root.rglob("*_events.tsv"))
    eeg_json_files = list(output_root.rglob("*_eeg.json"))

    assert len(events_files) == 1
    assert len(eeg_json_files) == 1

    events = pd.read_csv(events_files[0], sep="\t")

    assert len(events) == 1
    assert events.loc[0, "trial_type"] == "seizure"
    assert events.loc[0, "onset"] == pytest.approx(733.9656)
    assert events.loc[0, "duration"] == pytest.approx(84.0546)

    dataset_description = json.loads(
        (output_root / "dataset_description.json").read_text()
    )

    assert dataset_description["License"] == "Custom TUH"
    assert len(dataset_description["Authors"]) >= 2

    eeg_json = json.loads(eeg_json_files[0].read_text())

    assert eeg_json["EEGReference"] == "Common Average"
    assert eeg_json["PowerLineFrequency"] == 60
    assert eeg_json["RecordingType"] == "discontinuous"
    assert eeg_json["InstitutionName"] == "Temple University Hospital"

    assert (
        output_root / "task-szMonitoring_events.json"
    ).exists()

    text_files = [
        output_root / "dataset_description.json",
        output_root / "participants.json",
        output_root / "README",
        eeg_json_files[0],
    ]

    for path in text_files:
        assert "TODO" not in path.read_text()
