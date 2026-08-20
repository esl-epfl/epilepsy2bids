import os
import shutil
from importlib import resources as impresources
from pathlib import Path
from string import Template

import pandas as pd

from ... import bids
from ...bids.convert2bids import BidsConverter
from ...eeg import Eeg
from ...load_annotations.tuep import load_tuep_annotations, write_events_tsv
from .index import Recording, index_tuep

BIDS_DIR = impresources.files(bids)
DATASET = BIDS_DIR / "tuep"


def _write_channels_tsv(edf_base_name: Path, eeg: Eeg) -> None:
    unit = eeg._signalHeader.get("dimension", "uV")
    rows = [{"name": ch, "type": "EEG", "units": unit} for ch in eeg.channels]
    df = pd.DataFrame(rows)
    channels_base = Path(str(edf_base_name).replace("_eeg", "_channels"))
    df.to_csv(channels_base.with_suffix(".tsv"), sep="\t", index=False)


def _group_records(records: list[Recording]) -> dict[tuple[str, str | None], list[Recording]]:
    grouped: dict[tuple[str, str | None], list[Recording]] = {}
    for record in records:
        key = (record.subject_id, record.session_id)
        grouped.setdefault(key, []).append(record)
    return grouped


def convert(root: Path, outDir: Path):
    root = Path(root)
    outDir = Path(outDir)
    bidsConverter = BidsConverter(BIDS_DIR, DATASET, root, outDir, None)

    records = index_tuep(root)
    records = sorted(
        records,
        key=lambda r: (r.subject_id, r.session_id or "", r.edf_path),
    )

    subjectIdPairs: dict[str, dict] = {}
    for record in records:
        if record.subject_id not in subjectIdPairs:
            subjectIdPairs[record.subject_id] = {
                "subject": f"{len(subjectIdPairs):03}",
                "group": record.group,
                "session": {},
            }
        if record.session_id is not None:
            session_map = subjectIdPairs[record.subject_id]["session"]
            if record.session_id not in session_map:
                session_map[record.session_id] = f"{len(session_map):02}"

    grouped = _group_records(records)
    task = "szMonitoring"
    wrote_events = False

    for (orig_subject, orig_session), recs in grouped.items():
        subject = subjectIdPairs[orig_subject]["subject"]
        session = (
            subjectIdPairs[orig_subject]["session"].get(orig_session)
            if orig_session is not None
            else None
        )
        outPath = outDir / f"sub-{subject}"
        if session is not None:
            outPath = outPath / f"ses-{session}"
        outPath = outPath / "eeg"
        os.makedirs(outPath, exist_ok=True)

        for fileIndex, record in enumerate(sorted(recs, key=lambda r: r.edf_path)):
            if session is not None:
                edfBaseName = (
                    outPath
                    / f"sub-{subject}_ses-{session}_task-{task}_run-{(fileIndex + 1):02}_eeg"
                )
            else:
                edfBaseName = (
                    outPath
                    / f"sub-{subject}_task-{task}_run-{(fileIndex + 1):02}_eeg"
                )

            edfFileName = edfBaseName.with_suffix(".edf")

            eeg = Eeg.loadEdf(record.edf_path, Eeg.Montage.UNIPOLAR, Eeg.ELECTRODES_10_20)
            eeg.standardize(256, Eeg.ELECTRODES_10_20, "Avg")
            eeg.saveEdf(edfFileName.as_posix())

            eegJsonDict = {
                "fs": f"{eeg.fs:d}",
                "channels": f"{eeg.data.shape[0]}",
                "duration": f"{(eeg.data.shape[1] / eeg.fs):.2f}",
                "task": task,
            }
            with open(DATASET / "eeg.json", "r") as f:
                src = Template(f.read())
                eegJsonSidecar = src.substitute(eegJsonDict)
            with open(edfBaseName.with_suffix(".json"), "w") as f:
                f.write(eegJsonSidecar)

            _write_channels_tsv(edfBaseName, eeg)

            events = load_tuep_annotations(record.edf_path)
            if events:
                events_base = Path(str(edfBaseName).replace("_eeg", "_events"))
                events_path = events_base.with_suffix(".tsv")
                write_events_tsv(events, events_path)
                wrote_events = True
            else:
                print(f"No seizure annotations found for {record.edf_path}")

    participants = {"participant_id": [], "group": []}
    for original_id, data in subjectIdPairs.items():
        participants["participant_id"].append(f"sub-{data['subject']}")
        participants["group"].append(data.get("group", "unknown"))

    bidsConverter.saveMetadata(participants, copy_events_json=False)

    if wrote_events:
        events_sidecar = DATASET / "task-szMonitoring_events.json"
        shutil.copy(events_sidecar, outDir / events_sidecar.name)
