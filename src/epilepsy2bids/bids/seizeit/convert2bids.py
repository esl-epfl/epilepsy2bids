from importlib import resources as impresources
import os
from pathlib import Path
import shutil
from string import Template

import pandas as pd

from ... import bids
from ...eeg import Eeg
from ...load_annotations.seizeit import loadAnnotationsFromEdf

BIDS_DIR = impresources.files(bids)
DATASET = BIDS_DIR / "seizeit"


def convert(root: Path, outDir: Path):
    root = Path(root)
    outDir = Path(outDir)
    for folder in root.glob("P_ID*"):
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
    participants = {"participant_id": [], "age": [], "sex": []}
    for folder in outDir.glob("sub-*"):
        subject = os.path.split(folder)[-1]
        originalSubjectName = f"P_ID{subject[-2:]}"
        # Get information from header in one of the metadata files
        annotationFile = next((root / originalSubjectName).glob("*_a1.tsv"), None)
        with open(annotationFile, 'r') as f:
            lines = f.readlines()
            age = int(lines[4].split(': ')[-1])
            sex = lines[3].split(': ')[-1][0].lower()
        participants["participant_id"].append(subject)
        participants["age"].append(age)
        participants["sex"].append(sex)

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
