"""load annotations from the SeizeIT dataset https://doi.org/10.48804/P5Q0OJ to a Annotations object."""

import math
import os
import re
from pathlib import Path

import pandas as pd
import pyedflib

from ..annotations import Annotation, Annotations, EventType, SeizureType
from ..eeg import Eeg


def _loadSeizures(
    edfFile: str,
) -> tuple[list[tuple], list[SeizureType], list[list[str]], list]:
    """Load seizures from a seizeIT .tsv file

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
    seizures = []
    types = []
    confidence = []
    channels = []
    tsvFile = Path(os.path.dirname(edfFile)) / (Path(edfFile).stem + "_a1.tsv")
    annotations = pd.read_csv(
        tsvFile,
        comment="#",
        delimiter="\t",
        names=["start", "stop", "type", "comments"],
    )
    for _, row in annotations.iterrows():
        # Seizure Timing
        if not math.isnan(row["stop"]):
            seizures.append((row["start"], row["stop"]))
            confidence.append("n/a")
        # 12 weizures do not mark the end time, consider a default seizure time of 30 seconds
        else:
            seizures.append((row["start"], row["start"] + 30))
            confidence.append(0.5)

        # Seizure Type
        seizureType = row["type"]
        if seizureType == "FIA":
            seizureType = SeizureType.sz_foc_ia
        elif seizureType == "FA":
            seizureType = SeizureType.sz_foc_a
        elif seizureType == "F-BTC":
            seizureType = SeizureType.sz_foc_f2b
        else:
            raise ValueError(f"Unknown seizure type ({seizureType}) for Siena dataset.")
        types.append(seizureType)

        # Seizure localization
        channels.append(_getChannels(row["comments"]))

    return seizures, types, confidence, channels


def _getChannels(descriptor: str) -> list[str]:
    """Get channels associated with a seizure from the channel description.

    Args:
        descriptor (str): SeizeIT channel description

    Raises:
        ValueError: raises a ValueError if the lateralization or localization is unknown.

    Returns:
        channels: List of electrodes names from the 10-20 system associated associated with a seizure.
    """
    localization = descriptor.split(", ")[1].split(":")[1].lower()
    lateralization = descriptor.split(", ")[0].split(":")[1]
    channels = Eeg.ELECTRODES_10_20
    r = list()
    if "temp" in localization:  # Temporal
        r.append(re.compile("^T.*"))
    if "fronto" in localization:  # Frontal
        r.append(re.compile("^F.*"))
    if "occipito" in localization:  # Occipital
        r.append(re.compile("^O.*"))
    if "par" in localization:  # Occipital
        r.append(re.compile("^P.*"))
    if localization == "NC":
        r = None
    if r is not None:
        channels = []
        for regex in r:
            channels += list(filter(regex.match, Eeg.ELECTRODES_10_20))
    else:
        channels = "n/a"

    match lateralization:
        case "R":
            r = re.compile(".*[02468]$")
        case "L":
            r = re.compile(".*[13579]$")
        case "bi":
            r = re.compile(".*")
        case "NC":
            r = None
        case _:
            raise ValueError(
                f"Unknown lateralization for SeizeIT dataset: {lateralization}."
            )
    if r is not None:
        channels = list(filter(r.match, channels))
    else:
        channels = "n/a"

    return channels


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
