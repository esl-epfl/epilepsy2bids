"""load annotations from the TUH Sz Corpus dataset https://isip.piconepress.com/projects/tuh_eeg/downloads/tuh_eeg_seizure/ to a Annotations object."""

import os
from pathlib import Path

import pandas as pd
import pyedflib

from ..annotations import Annotation, Annotations, EventType, SeizureType


def _loadSeizures(
    edfFile: str,
) -> tuple[list[tuple], list[SeizureType], list[list[str]], list]:
    """Load seizures from a TUH .csv_bi file

    Args:
        edfFile (str): full path to the EDF for which annotations should be extracted.

    Raises:
        ValueError: raises a ValueError if txt file format is unknown.

    Returns:
        seizures: A list of (start, end) tuples for each seizure in seconds from the beginning of the file.
        types: A list off seizureType
        confidence: A list of confidence for each seizure. The value is 0.5 for the 12 seizures that do not have an endt-time.
        channels: A list of channels the seizure is visible on for each seizure.
    """

    MAPPING = {
        "BCKG": EventType.bckg,
        "SEIZ": SeizureType.sz,
        "FNSZ": SeizureType.sz_foc,
        "GNSZ": SeizureType.sz_gen,
        "SPSZ": SeizureType.sz_foc_a,
        "CPSZ": SeizureType.sz_foc_ia,
        "ABSZ": SeizureType.sz_gen_nm,
        "TNSZ": SeizureType.sz_gen_m_tonic,
        "CNSZ": SeizureType.sz_gen_m_clonic,
        "TCSZ": SeizureType.sz_gen_m_tonicClonic,
        "ATSZ": SeizureType.sz_gen_m_atonic,
        "MYSZ": SeizureType.sz_gen_nm_myoclonic,
    }
    seizures = []
    types = []
    confidence = []
    channels = []
    csvFile = Path(os.path.dirname(edfFile)) / (Path(edfFile).stem + ".csv_bi")
    annotations = pd.read_csv(csvFile, comment="#", delimiter=",")
    for _, row in annotations.iterrows():
        # Seizure Timing
        seizures.append((row["start_time"], row["stop_time"]))
        types.append(MAPPING[row["label"].upper()])
        confidence.append(float(row["confidence"]))  # TODO

        # Seizure localization
        if row["channel"] == "TERM":
            channels.append("n/a")
        else:
            raise ValueError(f"Unknown channel: {row['channel']}")

    return seizures, types, confidence, channels


def loadAnnotationsFromEdf(edfFile: str) -> Annotations:
    """Loads annotations related to an EDF recording in the Siena dataset.

    Args:
        edfFile (str): full path to the EDF for which annotations should be extracted.

    Returns:
        Annotations: an Annotations object
    """
    # dateTime and duration
    with pyedflib.EdfReader(edfFile) as edf:
        dateTime = edf.getStartdatetime()
        duration = edf.getFileDuration()
        edf._close()

    # Load event file
    seizures, types, confidence, channels = _loadSeizures(edfFile)

    # Populate dictionary
    if len(seizures) == 0:
        types = [EventType.bckg]
        confidence = ["n/a"]
        channels = ["n/a"]
        seizures.append((0, duration))

    annotations = Annotations()
    for i, seizure in enumerate(seizures):
        annotation = Annotation()
        annotation["onset"] = seizure[0]
        annotation["duration"] = seizure[1] - seizure[0]
        annotation["eventType"] = types[i]
        annotation["confidence"] = confidence[i]
        annotation["channels"] = channels[i]
        annotation["dateTime"] = dateTime
        annotation["recordingDuration"] = duration
        annotations.events.append(annotation)

    return annotations
