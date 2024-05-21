import os
from importlib import resources as impresources
from pathlib import Path

from ... import bids
from ...bids.convert2bids import BidsConverter
from ...load_annotations.tuh import loadAnnotationsFromEdf

BIDS_DIR = impresources.files(bids)
DATASET = BIDS_DIR / "tuh"


def convert(root: Path, outDir: Path):
    root = Path(root)
    outDir = Path(outDir)
    bidsConverter = BidsConverter(
        BIDS_DIR, DATASET, root, outDir, loadAnnotationsFromEdf
    )

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
                    session = f"{len(subjectIdPairs[subjectFolder.name]['session']):02}"
                    subjectIdPairs[subjectFolder.name]["session"][
                        sessionFolder.name
                    ] = session

                edfFiles = sorted((root / sessionFolder).glob("**/*.edf"))
                bidsConverter.buildBIDSHierarchy(edfFiles, subject, session)

    # Build participant metadata
    participants = {"participant_id": [], "TUH_id": [], "split": []}
    for folder in sorted(outDir.glob("sub-*")):
        subject = os.path.split(folder)[-1]
        participants["participant_id"].append(subject)
        subject = subject[4:]
        tuhId = list(subjectIdPairs.keys())[
            [x["subject"] for x in subjectIdPairs.values()].index(subject)
        ]
        participants["TUH_id"].append(tuhId)
        participants["split"].append(subjectIdPairs[tuhId]["subset"])

    bidsConverter.saveMetadata(participants)
