import os
from importlib import resources as impresources
from pathlib import Path

from ... import bids
from ...bids.convert2bids import BidsConverter
from ...load_annotations.seizeit import loadAnnotationsFromEdf

BIDS_DIR = impresources.files(bids)
DATASET = BIDS_DIR / "seizeit"


def convert(root: Path, outDir: Path):
    root = Path(root)
    outDir = Path(outDir)
    bidsConverter = BidsConverter(BIDS_DIR, DATASET, root, outDir, loadAnnotationsFromEdf)
    for folder in root.glob("P_ID*"):
        print(folder)
        # Extract subject & session ID
        subject = folder.name[-2:]
        edfFiles = sorted((root / folder).glob("*.edf"))
        bidsConverter.buildBIDSHierarchy(edfFiles, subject)

    # Build participant metadata
    participants = {"participant_id": [], "age": [], "sex": []}
    for folder in outDir.glob("P_ID*"):
        print(folder)
        subject = os.path.split(folder)[-1]
        originalSubjectName = f"P_ID{subject[-2:]}"
        # Get information from header in one of the metadata files
        annotationFile = next((root / originalSubjectName).glob("*_a1.tsv"), None)
        with open(annotationFile, "r") as f:
            lines = f.readlines()
            age = int(lines[4].split(": ")[-1])
            sex = lines[3].split(": ")[-1][0].lower()
        participants["participant_id"].append(subject)
        participants["age"].append(age)
        participants["sex"].append(sex)

    bidsConverter.saveMetadata(participants)
