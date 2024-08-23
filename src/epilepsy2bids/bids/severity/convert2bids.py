import os
from importlib import resources as impresources
from pathlib import Path
import shutil
from string import Template

from natsort import natsorted
import pandas as pd

from ...eeg import Eeg
from ...load_annotations.severity import preLoadAnnotations, trc2events
from ... import bids
from . import trc

BIDS_DIR = impresources.files(bids)
DATASET = BIDS_DIR / "severity"


class BidsConverter:
    def __init__(
        self,
        BIDS_DIR,
        DATASET,
        root,
        outDir,
        montage=Eeg.Montage.UNIPOLAR,
        electrodes=Eeg.ELECTRODES_10_20,
    ):
        self.BIDS_DIR = BIDS_DIR
        self.DATASET = DATASET
        self.root = root
        self.outDir = outDir
        self.montage = montage
        self.electrodes = electrodes

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


def convert(root: Path, outDir: Path):
    # Set root and output folders
    root = Path(root)
    outDir = Path(outDir)
    bidsConverter = BidsConverter(BIDS_DIR, DATASET, root, outDir)

    # Load raw annotations
    dfAnnotations = preLoadAnnotations("../seizures_from_eeg.csv")
    subjectID = dict()

    # Loop over folders
    for subject, folder in enumerate(natsorted(root.glob("PAT*", case_sensitive=False))):
        exclusions = ["PAT_188", 
                    "PAT_189", 
                    "PAT_190", 
                    "PAT_191", 
                    "PAT_192", 
                    "PAT_193", 
                    "PAT_194", 
                    "PAT_195", 
                    "PAT_196", 
                    "PAT_197", 
                    "PAT_198", 
                    "PAT_199", 
                    "PAT_200", 
                    "PAT_201", 
                    "PAT_202", 
                    "PAT_217", 
                    "PAT_203", 
                    "PAT_218", 
                    "PAT_204", 
                    "PAT_205", 
                    "PAT_219", 
                    "PAT_206", 
                    "PAT_207", 
                    "PAT_208", 
                    "PAT_220", 
                    "PAT_209", 
                    "PAT_216", 
                    "PAT_228", 
                    "PAT_229", 
                    "PAT_230", 
                    "PAT_210", 
                    "PAT_211", 
                    "PAT_212", 
                    "PAT_213", 
                    "PAT_227", 
                    "PAT_214", 
                    "PAT_215", 
                    "PAT_187",
                    "PAT_99"]
        for exclude in exclusions:
            if exclude == folder.name:
                print(f"Excluding {folder.name}")
                continue
        print(folder)
        # Extract subject & session ID
        subject += 1
        trcFiles = natsorted((root / folder).glob("EEG_*.TRC"))
        task = "szMonitoring"
        subjectID[subject] = folder.name
        
        outPath = (
                    bidsConverter.outDir
                    / f"sub-{subject:02}"
        )
        if outPath.exists():
            continue
        # Loop over TRC files
        for fileIndex, trcFile in enumerate(trcFiles):
            print(trcFile)
            # Load TRC segments
            segments = trc.load_Eeg_TRC(trcFile)
            # Loop over segments
            for segmentIndex, segment in enumerate(segments):
                outPath = (
                    bidsConverter.outDir
                    / f"sub-{subject:02}"
                    / f"ses-{(fileIndex + 1):02}"
                    / "eeg"
                )
                os.makedirs(outPath, exist_ok=True)
                
                if len(segment.channels) < 1:
                    print(f"No scalp EEG channels found in {trcFile}. Skipping...")
                    continue

                edfBaseName = outPath / (
                    f"sub-{subject:02}"
                    + f"_ses-{(fileIndex + 1):02}"
                    + f"_task-{task}"
                    + f"_run-{(segmentIndex + 1):02}"
                    + "_eeg"
                )
                edfFileName = edfBaseName.with_suffix(".edf")

                # Load EEG and standardize it
                eeg = segment
                eeg.standardize(256, bidsConverter.electrodes, "Avg")

                # Save EEG
                eeg.saveEdf(edfFileName.as_posix())

                # Save JSON sidecar
                eegJsonDict = {
                    "fs": f"{eeg.fs:d}",
                    "channels": f"{eeg.data.shape[0]}",
                    "duration": f"{(eeg.data.shape[1] / eeg.fs):.2f}",
                    "task": task
                }

                with open(bidsConverter.DATASET / "eeg.json", "r") as f:
                    src = Template(f.read())
                    eegJsonSidecar = src.substitute(eegJsonDict)
                with open(edfBaseName.with_suffix(".json"), "w") as f:
                    f.write(eegJsonSidecar)

                # Load annotation
                annotations = trc2events(
                    dfAnnotations,
                    str(trcFile),
                    eeg._fileHeader["recording_start_time"],
                    eeg.data.shape[1] / eeg.fs,
                )
                annotations.saveTsv(edfBaseName.as_posix()[:-4] + "_events.tsv")

    # Build participant metadata
    participants = {"participant_id": [],
                    "micromed_id": []}
    for folder in outDir.glob("sub-*"):
        subject = os.path.split(folder)[-1]
        participants["participant_id"].append(subject)
        participants["micromed_id"].append(subjectID[int(subject[4:])])
    bidsConverter.saveMetadata(participants)
