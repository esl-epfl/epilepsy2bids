"""load annotations from the Siena dataset https://physionet.org/content/siena-scalp-eeg/1.0.0/ to a Annotations object."""

import os
import re
import time
from pathlib import Path

import pandas as pd
import pyedflib

from ..annotations import Annotation, Annotations, EventType, SeizureType
from ..eeg import Eeg


def _parseTimeStamp(string: str) -> float:
    """Parses timestamps from Siena annotation files and returns a float representing the time from the earliest system time.

    Accepts the following formats with any random string before the timestamp :
    - 'Registration start time: 19.00.44'
    - 'Start time: 21:51:02'

    Args:
        string (str): string to be parsed as a timestamp

    Returns:
        float: timestamp in seconds from the earliest system time
    """
    timeStamp = re.findall(".*[ |:]([0-9]+.[0-9]+.[0-9]+).*", string)[0]
    return time.mktime(time.strptime(timeStamp.replace(":", "."), "%H.%M.%S"))


def _substractTimeStamps(time1: float, time2: float) -> float:
    """Substract time2 timestamp from time1 in seconds"""
    difference = time1 - time2
    if difference < 0:
        difference += 24 * 60 * 60  # Correct for day shift
    return difference


def _loadSeizures(edfFile: str) -> list[tuple]:
    """Load seizures from a Siena Seizures-list-Pxx.txt file

    Args:
        edfFile (str): full path to the EDF for which annotations should be extracted.

    Raises:
        ValueError: raises a ValueError if txt file format is unknown.

    Returns:
        seizures: A list of (start, end) tuples for each seizure in seconds from the beginning of the file.
    """

    subject = os.path.basename(os.path.dirname(edfFile))
    correctedEdfFileName = _correctEdfFileNameTypos(edfFile)

    seizures = []
    summaryFile = Path(os.path.dirname(edfFile)) / f"Seizures-list-{subject}.txt"
    with open(summaryFile, "r") as summary:
        # Search for mention of edfFile in summary
        line = summary.readline()
        while line:
            if re.search(r"File name: {} *\n".format(correctedEdfFileName), line):
                firstLine = summary.readline()
                # PN01 exception
                if correctedEdfFileName == "PN01.edf":
                    registrationStart = _parseTimeStamp(firstLine)
                    _ = summary.readline()
                    _ = summary.readline()
                    for _ in range(2):
                        _ = summary.readline()
                        start = _parseTimeStamp(summary.readline())
                        end = _parseTimeStamp(summary.readline())
                        _ = summary.readline()
                        seizures.append(
                            (
                                _substractTimeStamps(start, registrationStart),
                                (_substractTimeStamps(end, registrationStart)),
                            )
                        )
                elif correctedEdfFileName == "PN00-3.edf":  # seizure last 1hour
                    registrationStart = _parseTimeStamp(firstLine)
                    _ = summary.readline()
                    start = _parseTimeStamp(summary.readline())
                    end = _parseTimeStamp(summary.readline())
                    end = _parseTimeStamp(
                        "Seizure end time: 18.29.29\n"
                    )  # correct time
                    seizures.append(
                        (
                            _substractTimeStamps(start, registrationStart),
                            (_substractTimeStamps(end, registrationStart)),
                        )
                    )
                elif correctedEdfFileName == "PN10-7.8.9.edf":  # seizure last 1hour
                    if (
                        firstLine == "Registration start time:1 6.49.25\n"
                    ):  # extra space
                        firstLine = "Registration start time:16.49.25\n"
                    registrationStart = _parseTimeStamp(firstLine)
                    _ = summary.readline()
                    start = _parseTimeStamp(summary.readline())
                    end = _parseTimeStamp(summary.readline())
                    seizures.append(
                        (
                            _substractTimeStamps(start, registrationStart),
                            (_substractTimeStamps(end, registrationStart)),
                        )
                    )
                # PN12 exception
                elif "Seizure start time: " in firstLine:
                    start = _parseTimeStamp(firstLine)
                    end = _parseTimeStamp(summary.readline())
                    seizures.append(
                        (
                            _substractTimeStamps(start, registrationStart),
                            (_substractTimeStamps(end, registrationStart)),
                        )
                    )
                # Standard format
                elif "Registration start time:" in firstLine:
                    registrationStart = _parseTimeStamp(firstLine)
                    _ = summary.readline()
                    start = _parseTimeStamp(summary.readline())
                    end = _parseTimeStamp(summary.readline())
                    seizures.append(
                        (
                            _substractTimeStamps(start, registrationStart),
                            (_substractTimeStamps(end, registrationStart)),
                        )
                    )
                else:
                    raise ValueError("Unknown format for Siena summary file.")
            line = summary.readline()
    return seizures


def _getSeizureType(edfFile: str) -> SeizureType:
    """Get seizure type associated to an EDF file from the subject_info.csv file.

    Args:
        edfFile (str): full path to the EDF for which annotations should be extracted.

    Raises:
        ValueError: raises a ValueError if the seizure type is unknown.

    Returns:
        SeizureType: the seizure type of the subject (Siena only records one seizure type per subject).
    """
    # Load CSV
    subject_info = pd.read_csv(Path(edfFile).parents[1] / "subject_info.csv")
    subject = os.path.basename(os.path.dirname(edfFile))

    seizureType = subject_info[subject_info.patient_id == subject][" seizure"].iloc[0]
    if seizureType == "IAS":
        seizureType = SeizureType.sz_foc_ia
    elif seizureType == "WIAS":
        seizureType = SeizureType.sz_foc_a
    elif seizureType == "FBTC":
        seizureType = SeizureType.sz_foc_f2b
    else:
        raise ValueError(f"Unknown seizure type ({seizureType}) for Siena dataset.")

    return seizureType


def _getChannels(edfFile: str) -> list[str]:
    """Get channels associated with a seizure from the subject_info.csv file.

    The subject_info.csv file provides lateralization and localization information for each subject. Electrodes from the
    10-20 system associated with the lateralization and localization are returned.

    Args:
        edfFile (str): full path to the EDF for which annotations should be extracted.

    Raises:
        ValueError: raises a ValueError if the lateralization or localization is unknown.

    Returns:
        channels: List of electrodes names from the 10-20 system associated associated with a seizure.
    """
    # Load CSV
    subject_info = pd.read_csv(Path(edfFile).parents[1] / "subject_info.csv")
    subject = os.path.basename(os.path.dirname(edfFile))

    localization = subject_info[subject_info.patient_id == subject][
        " localization"
    ].iloc[0]
    lateralization = subject_info[subject_info.patient_id == subject][
        " lateralization"
    ].iloc[0]
    channels = Eeg.ELECTRODES_10_20
    if localization == "T":  # Temporal
        r = re.compile("^T.*")
    elif localization == "F":  # Frontal
        r = re.compile("^F.*")
    else:
        raise ValueError(f"Unknown localization for Siena dataset: {localization}.")
    channels = list(filter(r.match, channels))

    if lateralization == "R":
        r = re.compile(".*[02468]$")
    elif lateralization == "L":
        r = re.compile(".*[13579]$")
    elif lateralization == "Bilateral":
        r = re.compile(".*")
    else:
        raise ValueError(f"Unknown lateralization for Siena dataset: {lateralization}.")
    channels = list(filter(r.match, channels))

    return channels


def _correctEdfFileNameTypos(filename: str) -> str:
    """Correct typos in filenames in .txt file when compared to .edf files"""
    correctedEdfFileName = os.path.basename(filename)
    if correctedEdfFileName == "PN01-1.edf":
        correctedEdfFileName = "PN01.edf"
    elif correctedEdfFileName == "PN06-1.edf":
        correctedEdfFileName = "PNO6-1.edf"  # big o instead of 0
    elif correctedEdfFileName == "PN06-2.edf":
        correctedEdfFileName = "PNO6-2.edf"  # big o instead of 0
    elif correctedEdfFileName == "PN06-4.edf":
        correctedEdfFileName = "PNO6-4.edf"  # big o instead of 0
    elif correctedEdfFileName == "PN11-1.edf":
        correctedEdfFileName = "PN11-.edf"
    return correctedEdfFileName


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

    # Get Seizure type
    seizureType = _getSeizureType(edfFile)

    # Load Seizures
    seizures = _loadSeizures(edfFile)

    # Confidence
    confidence = "n/a"

    # Channels
    channels = _getChannels(edfFile)

    # Populate dictionary
    if len(seizures) == 0:
        seizureType = EventType.bckg
        seizures.append((0, duration))

    annotations = Annotations()
    for seizure in seizures:
        annotation = Annotation()
        annotation["onset"] = seizure[0]
        annotation["duration"] = seizure[1] - seizure[0]
        annotation["eventType"] = seizureType
        annotation["confidence"] = confidence
        annotation["channels"] = channels
        annotation["dateTime"] = dateTime
        annotation["recordingDuration"] = duration
        annotations.events.append(annotation)

    return annotations
