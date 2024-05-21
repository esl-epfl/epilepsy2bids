import os
import shutil
from string import Template

import pandas as pd

from ..eeg import Eeg

class BidsConverter:
    def __init__(self, BIDS_DIR, DATASET, root, outDir, loadAnnotationsFromEdf, montage = Eeg.Montage.UNIPOLAR, electrodes = Eeg.ELECTRODES_10_20):
        self.BIDS_DIR = BIDS_DIR
        self.DATASET = DATASET
        self.root = root
        self.outDir = outDir
        self.loadAnnotationsFromEdf = loadAnnotationsFromEdf
        self.montage = montage
        self.electrodes = electrodes


    def buildBIDSHierarchy(self, edfFiles, subject, session = "01", task = "szMonitoring", addEegJsonDict = None):        
        # Create BIDS hierarchy
        outPath = self.outDir / f"sub-{subject}" / f"ses-{session}" / "eeg"
        os.makedirs(outPath, exist_ok=True)
        for fileIndex, edfFile in enumerate(edfFiles):
            edfBaseName = (
                outPath / f"sub-{subject}_ses-{session}_task-{task}_run-{(fileIndex + 1):02}_eeg"
            )
            edfFileName = edfBaseName.with_suffix(".edf")
            # Load EEG and standardize it
            eeg = Eeg.loadEdf(edfFile.as_posix(), self.montage, self.electrodes)
            eeg.standardize(256, self.electrodes, "Avg")

            # Save EEG
            eeg.saveEdf(edfFileName.as_posix())

            # Save JSON sidecar
            eegJsonDict = {
                "fs": f"{eeg.fs:d}",
                "channels": f"{eeg.data.shape[0]}",
                "duration": f"{(eeg.data.shape[1] / eeg.fs):.2f}",
                "task": task,
            }
            if addEegJsonDict is not None:
                eegJsonDict = eegJsonDict | addEegJsonDict

            with open(self.DATASET / "eeg.json", "r") as f:
                src = Template(f.read())
                eegJsonSidecar = src.substitute(eegJsonDict)
            with open(edfBaseName.with_suffix(".json"), "w") as f:
                f.write(eegJsonSidecar)

            # Load annotation
            annotations = self.loadAnnotationsFromEdf(edfFile.as_posix())
            annotations.saveTsv(edfBaseName.as_posix()[:-4] + "_events.tsv")


    def saveMetadata(self, participants):
        participantsDf = pd.DataFrame(participants)
        participantsDf.sort_values(by=["participant_id"], inplace=True)
        participantsDf.to_csv(self.outDir / "participants.tsv", sep="\t", index=False)
        participantsJsonFileName = self.DATASET / "participants.json"
        shutil.copy(participantsJsonFileName, self.outDir)

        # Copy Readme file
        readmeFileName = self.DATASET / "README.md"
        shutil.copyfile(readmeFileName, self.outDir / "README")

        # Copy dataset description
        descriptionFileName = self.DATASET / "dataset_description.json"
        shutil.copy(descriptionFileName, self.outDir)

        # Copy Events JSON Sidecar
        eventsFileName = self.BIDS_DIR / "events.json"
        shutil.copy(eventsFileName, self.outDir)
