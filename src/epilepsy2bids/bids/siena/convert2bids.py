from importlib import resources as impresources
import os
from pathlib import Path
import shutil
from string import Template

import pandas as pd

from ... import bids
from ...eeg import Eeg
from ...load_annotations.siena import loadAnnotationsFromEdf

BIDS_DIR = impresources.files(bids)
DATASET = BIDS_DIR / "siena"


def convert(root: Path, outDir: Path):
    root = Path(root)
    outDir = Path(outDir)
    for folder in root.glob("PN*"):
        print(folder)
        # Extract subject & session ID
        subject = folder.name[-2:]
        session = "01"
        task = "szMonitoring"

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
            eeg = Eeg.loadEdf(edfFile.as_posix(), Eeg.Montage.UNIPOLAR, Eeg.ELECTRODES_10_20)
            eeg.standardize(256, Eeg.ELECTRODES_10_20, "Avg")

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
    subjectInfo = pd.read_csv(root / "subject_info.csv")
    participants = {"participant_id": [], "age": [], "sex": []}
    for folder in outDir.glob("sub-*"):
        subject = os.path.split(folder)[-1]
        originalSubjectName = f"PN{subject[-2:]}"
        if originalSubjectName in subjectInfo.patient_id.values:
            participants["participant_id"].append(subject)
            participants["age"].append(
                subjectInfo[subjectInfo.patient_id == originalSubjectName][
                    " age_years"
                ].values[0]
            )
            participants["sex"].append(
                subjectInfo[subjectInfo.patient_id == originalSubjectName][" gender"].values[0]
                .lower()[0]
            )

        else:
            participants["participant_id"].append(subject)
            participants["age"].append("n/a")
            participants["sex"].append("n/a")

    participantsDf = pd.DataFrame(participants)
    participantsDf.sort_values(by=["participant_id"], inplace=True)
    participantsDf.to_csv(outDir / "participants.tsv", sep="\t", index=False)
    participantsJsonFileName = DATASET / "participants.json"
    shutil.copy(participantsJsonFileName, outDir)

    # Copy Readme file
    readmeFileName = DATASET / "README.md"
    shutil.copyfile(readmeFileName, outDir / "README")

    # Copy dataset description
    descriptionFileName = DATASET / "dataset_description.json"
    shutil.copy(descriptionFileName, outDir)

    # Copy Events JSON Sidecar
    eventsFileName = BIDS_DIR / "events.json"
    shutil.copy(eventsFileName, outDir)
