import os
from importlib import resources as impresources
from pathlib import Path
from string import Template

import pandas as pd

from ... import bids
from ...bids.convert2bids import BidsConverter
from ...eeg import Eeg
from ...load_annotations.chbmit import loadAnnotationsFromEdf

BIDS_DIR = impresources.files(bids)
DATASET = BIDS_DIR / "chbmit"


def convert(root: Path, outDir: Path):
    root = Path(root)
    outDir = Path(outDir)
    bidsConverter = BidsConverter(BIDS_DIR, DATASET, root, outDir, loadAnnotationsFromEdf)
    subjects = []
    for _, directory, _ in os.walk(root):
        for subject in directory:
            subjects.append(subject)
    for folder in subjects:
        print(folder)
        # Extract subject & session ID
        subject = os.path.split(folder)[-1][3:5]
        session = "01"
        task = "szMonitoring"
        if subject == "21":
            subject = "01"
            session = "02"

        # Create BIDS hierarchy
        outPath = outDir / f"sub-{subject}" / f"ses-{session}" / "eeg"
        os.makedirs(outPath, exist_ok=True)

        edfFiles = sorted((root / folder).glob("*.edf"))
        for fileIndex, edfFile in enumerate(edfFiles):
            edfBaseName = (
                outPath
                / f"sub-{subject}_ses-{session}_task-{task}_run-{fileIndex:02}_eeg"
            )
            edfFileName = edfBaseName.with_suffix(".edf")
            # Load EEG and standardize it
            if os.path.basename(edfFile) not in (
                "chb12_27.edf",
                "chb12_28.edf",
                "chb12_29.edf",
            ):
                eeg = Eeg.loadEdf(
                    edfFile.as_posix(), Eeg.Montage.BIPOLAR, Eeg.BIPOLAR_DBANANA
                )
                eeg.standardize(256, Eeg.BIPOLAR_DBANANA, "bipolar")
            else:
                eeg = Eeg.loadEdf(
                    edfFile.as_posix(), Eeg.Montage.UNIPOLAR, Eeg.ELECTRODES_10_20
                )
                eeg.standardize(256, Eeg.ELECTRODES_10_20, "bipolar")

            # Save EEG
            eeg.saveEdf(edfFileName.as_posix())

            # Save JSON sidecar
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

            # Load annotation
            annotations = loadAnnotationsFromEdf(edfFile.as_posix())
            annotations.saveTsv(edfBaseName.as_posix()[:-4] + "_events.tsv")

    # Build participant metadata
    subjectInfo = pd.read_csv(
        root / "SUBJECT-INFO", delimiter="\t", skip_blank_lines=True
    )
    participants = {"participant_id": [], "age": [], "sex": [], "comment": []}
    for folder in outDir.glob("sub-*"):
        subject = os.path.split(folder)[-1]
        originalSubjectName = f"chb{subject[4:6]}"
        if originalSubjectName in subjectInfo.Case.values:
            participants["participant_id"].append(subject)
            participants["age"].append(
                subjectInfo[subjectInfo.Case == originalSubjectName][
                    "Age (years)"
                ].values[0]
            )
            participants["sex"].append(
                subjectInfo[subjectInfo.Case == originalSubjectName]
                .Gender.values[0]
                .lower()
            )
            if subject == "sub-01":
                participants["comment"].append("ses-02 recorded at 13 years old")
            else:
                participants["comment"].append("n/a")

        else:
            participants["participant_id"].append(subject)
            participants["age"].append("n/a")
            participants["sex"].append("n/a")
            participants["comment"].append("n/a")

    bidsConverter.saveMetadata(participants)
