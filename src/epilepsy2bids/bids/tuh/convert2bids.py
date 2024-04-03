from importlib import resources as impresources
import os
from pathlib import Path
import shutil
from string import Template

import pandas as pd

from ... import bids
from ...eeg import Eeg
from ...load_annotations.tuh import loadAnnotationsFromEdf

BIDS_DIR = impresources.files(bids)
DATASET = BIDS_DIR / "tuh"


def convert(root: Path, outDir: Path):
    root = Path(root)
    outDir = Path(outDir)

    subjectIdPairs = {}

    for subset in ["train", "dev", "eval"]:
        subRoot = root / subset
        for subjectFolder in sorted(subRoot.glob("*")):
            # Extract subject & session ID

            # Build dictionary of ID pairs
            if subjectFolder.name in subjectIdPairs.keys():
                subject = subjectIdPairs[subjectFolder.name]["subject"]
            else:
                subject = f"{len(subjectIdPairs):03}"
                subjectIdPairs[subjectFolder.name] = {}
                subjectIdPairs[subjectFolder.name]["subject"] = subject
                subjectIdPairs[subjectFolder.name]["subset"] = subset
                subjectIdPairs[subjectFolder.name]["session"] = {}

            for sessionFolder in sorted(subjectFolder.glob("*")):
                if sessionFolder.name in subjectIdPairs[subjectFolder.name]["session"]:
                    session = subjectIdPairs[subjectFolder.name]["session"][
                        sessionFolder.name
                    ]
                else:
                    session = f"{len(subjectIdPairs[subjectFolder.name]["session"]):02}"
                    subjectIdPairs[subjectFolder.name]["session"][
                        sessionFolder.name
                    ] = session
                task = "szMonitoring"

                # Create BIDS hierarchy
                outPath = outDir / f"sub-{subject}" / f"ses-{session}" / "eeg"
                os.makedirs(outPath, exist_ok=True)

                edfFiles = sorted((root / sessionFolder).glob("**/*.edf"))
                for fileIndex, edfFile in enumerate(edfFiles):
                    edfBaseName = (
                        outPath
                        / f"sub-{subject}_ses-{session}_task-{task}_run-{fileIndex:02}_eeg"
                    )
                    edfFileName = edfBaseName.with_suffix(".edf")
                    # Load EEG and standardize it
                    eeg = Eeg.loadEdf(
                        edfFile.as_posix(), Eeg.Montage.UNIPOLAR, Eeg.ELECTRODES_10_20
                    )
                    eeg.standardize(256, Eeg.ELECTRODES_10_20, "Avg")

                    # Save EEG
                    eeg.saveEdf(edfFileName.as_posix())

                    # Save JSON sidecar
                    eegJsonDict = {
                        "fs": f"{eeg.fs:d}",
                        "channels": f"{eeg.data.shape[0]}",
                        "duration": f"{(eeg.data.shape[1] / eeg.fs):.2f}",
                        "task": task,
                        "split": subset,
                        "subject": subjectFolder.name,
                        "session": sessionFolder.name
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
        participants = {"participant_id": [], "TUH_id": [], "split": []}
        for folder in sorted(outDir.glob("sub-*")):
            subject = os.path.split(folder)[-1]
            participants["participant_id"].append(subject)
            subject = subject[4:]
            tuhId = list(subjectIdPairs.keys())[[x["subject"] for x in subjectIdPairs.values()].index(subject)]
            participants["TUH_id"].append(tuhId)
            participants["split"].append(subjectIdPairs[tuhId]["subset"])

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
