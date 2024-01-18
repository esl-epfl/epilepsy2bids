import glob
import os
from pathlib import Path
import shutil
from string import Template

import pandas as pd

import dataIo
from dataIo.eeg import Eeg
from dataIo.load_annotations.load_annotations_chb import loadAnnotationsFromEdf

# TODO switch to Path
BIDS_DIR = os.path.join(os.path.dirname(dataIo.__file__), "bids")


def convert(root: Path, outDir: Path):
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

        edfFiles = sorted(glob.glob(root / folder / "*.edf"))
        for fileIndex, edfFile in enumerate(edfFiles):
            edfBaseName = (
                outPath
                / f"sub-{subject}_ses-{session}_task-{task}_run-{fileIndex:02}_eeg"
            )
            edfFileName = edfBaseName + ".edf"
            # Load EEG and standardize it
            if os.path.basename(edfFile) not in (
                "chb12_27.edf",
                "chb12_28.edf",
                "chb12_29.edf",
            ):
                eeg = Eeg.loadEdf(edfFile, Eeg.Montage.BIPOLAR, Eeg.BIPOLAR_DBANANA)
                eeg.standardize(256, Eeg.BIPOLAR_DBANANA, "bipolar")
            else:
                eeg = Eeg.loadEdf(edfFile, Eeg.Montage.UNIPOLAR, Eeg.ELECTRODES_10_20)
                eeg.standardize(256, Eeg.ELECTRODES_10_20, "bipolar")

            # Save EEG
            eeg.saveEdf(edfFileName)

            # Save JSON sidecar
            eegJsonDict = {
                "fs": f"{eeg.fs:d}",
                "channels": f"{eeg.data.shape[0]}",
                "duration": f"{(eeg.data.shape[1] / eeg.fs):.2f}",
                "task": task,
            }

            with open(BIDS_DIR / "chbmit" / "eeg.json", "r") as f:
                src = Template(f.read())
                eegJsonSidecar = src.substitute(eegJsonDict)
            with open(edfBaseName + ".json", "w") as f:
                f.write(eegJsonSidecar)

            # Load annotation
            annotations = loadAnnotationsFromEdf(edfFile)
            annotations.saveTsv(edfBaseName[:-4] + "_events.tsv")

    # Build participant metadata
    subjectInfo = pd.read_csv(
        root / "SUBJECT-INFO", delimiter="\t", skip_blank_lines=True
    )
    participants = {"participant_id": [], "age": [], "sex": [], "comment": []}
    for folder in glob.iglob(outDir / "sub-*"):
        subject = os.path.split(folder)[-1]
        originalSubjectName = "chb{}".format(subject[4:6])
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

    participantsDf = pd.DataFrame(participants)
    participantsDf.sort_values(by=["participant_id"], inplace=True)
    participantsDf.to_csv(outDir / "participants.tsv", sep="\t", index=False)
    participantsJsonFileName = BIDS_DIR / "chbmit" / "participants.json"
    shutil.copy(participantsJsonFileName, outDir)

    # Copy Readme file
    readmeFileName = BIDS_DIR / "chbmit" / "README.md"
    shutil.copyfile(readmeFileName, outDir / "README")

    # Copy dataset description
    descriptionFileName = BIDS_DIR / "chbmit" / "dataset_description.json"
    shutil.copy(descriptionFileName, outDir)

    # Copy Events JSON Sidecar
    eventsFileName = BIDS_DIR / "events.json"
    shutil.copy(eventsFileName, outDir)
