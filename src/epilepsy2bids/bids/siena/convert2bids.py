import os
from importlib import resources as impresources
from pathlib import Path

import pandas as pd

from ... import bids
from ...bids.convert2bids import BidsConverter
from ...load_annotations.siena import loadAnnotationsFromEdf

BIDS_DIR = impresources.files(bids)
DATASET = BIDS_DIR / "siena"


def convert(root: Path, outDir: Path):
    root = Path(root)
    outDir = Path(outDir)
    bidsConverter = BidsConverter(BIDS_DIR, DATASET, root, outDir, loadAnnotationsFromEdf)

    for folder in root.glob("PN*"):
        print(folder)
        # Extract subject & session ID
        subject = folder.name[-2:]
        edfFiles = sorted((root / folder).glob("*.edf"))
        bidsConverter.buildBIDSHierarchy(edfFiles, subject)

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
                subjectInfo[subjectInfo.patient_id == originalSubjectName][" gender"]
                .values[0]
                .lower()[0]
            )

        else:
            participants["participant_id"].append(subject)
            participants["age"].append("n/a")
            participants["sex"].append("n/a")

    bidsConverter.saveMetadata(participants)
