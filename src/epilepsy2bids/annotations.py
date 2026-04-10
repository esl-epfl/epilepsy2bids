import enum
import json
from dataclasses import dataclass
from datetime import datetime
from importlib import resources as impresources
from typing import List, Tuple

import numpy as np
import pandas as pd
from timescoring.annotations import Annotation as MaskEvents

from . import bids

# Load Seizure types defined in the HED-SCORE JSON event file
BIDS_LOC = impresources.files(bids)
szTypes = dict()
with open(BIDS_LOC / "events.json", "r") as f:
    eventsJSON = json.load(f)
    szTypes = eventsJSON["Levels"]
    del szTypes["bckg"]

for key, _ in szTypes.items():
    szTypes[key] = key

SeizureType = enum.Enum("SeizureType", szTypes)

EVENT_TYPES = szTypes.copy()
EVENT_TYPES["bckg"] = "bckg"
EventType = enum.Enum("EventType", EVENT_TYPES)

# TODO Subclass dataFrame
# Q? Expose dataFrame or getter class to get masks and annotations


@dataclass
class Annotation:
    onset: float | None = None                  # start time from beginning of recording, in seconds
    duration: float | None = None               # duration of the event, in seconds
    eventType: EventType | None = None          # type of the event
    confidence: float | None = None             # confidence in the event label [0–1]
    channels: list[str] | None = None           # channels on which the event appears
    dateTime: datetime | None = None            # start date time of the recording file
    recordingDuration: float | None = None      # duration of the recording in seconds


class Annotations:
    def __init__(self):
        self.events: list[Annotation] = list()
        self.recordingDuration: float = 0.0

    @classmethod
    def loadTsv(cls, filename: str):
        df = pd.read_csv(filename, delimiter="\t")
        annotations = cls()
        for _, row in df.iterrows():
            annotation = Annotation()
            try:
                annotation.onset = float(row["onset"])
            except (ValueError, KeyError):
                annotation.onset = None
            try:
                annotation.duration = float(row["duration"])
            except (KeyError, ValueError):
                annotation.duration = None
            try:
                annotation.eventType = EventType[row["eventType"]]
            except KeyError:
                annotation.eventType = None
            try:
                annotation.confidence = float(row["confidence"])
            except (KeyError, ValueError):
                annotation.confidence = None
            try:
                if "," in row["channels"]:
                    annotation.channels = row["channels"].split(",")
                elif row["channels"] == "n/a":
                    annotation.channels = None
                else:
                    annotation.channels = [row["channels"]]
            except (KeyError, TypeError):
                annotation.channels = None
            try:
                annotation.dateTime = datetime.strptime(
                    row["dateTime"], "%Y-%m-%d %H:%M:%S"
                )
            except (KeyError, TypeError, ValueError):
                annotation.dateTime = None
            try:
                annotation.recordingDuration = float(row["recordingDuration"])
                annotations.recordingDuration = annotation.recordingDuration
            except (KeyError, ValueError):
                annotation.recordingDuration = None
            annotations.events.append(annotation)

        return annotations

    @classmethod
    def loadMask(cls, mask, fs):
        maskEvent = MaskEvents(mask, fs)
        return cls.loadEvents(maskEvent.events, len(mask) / fs)

    @classmethod
    def loadEvents(cls, events: List[Tuple[float, float]], duration: float):
        annotations = cls()
        for event in events:
            annotations.events.append(Annotation(
                onset=event[0],
                duration=event[1] - event[0],
                eventType=SeizureType.sz,
                recordingDuration=duration,
            ))
        if len(events) == 0:
            annotations.events.append(Annotation(
                onset=0,
                duration=duration,
                eventType=EventType.bckg,
                recordingDuration=duration,
            ))
        return annotations

    def getEvents(self) -> list[(float, float)]:
        events = list()
        for event in self.events:
            if event.eventType is not None and event.eventType.value in SeizureType._member_names_:
                events.append((event.onset, event.onset + event.duration))
        return events

    def getMask(self, fs: int) -> np.ndarray:
        if not self.events:
            return np.zeros(int(self.recordingDuration * fs))
        mask = np.zeros(int(self.events[0].recordingDuration * fs))
        for event in self.events:
            if event.eventType is not None and event.eventType.value in SeizureType._member_names_:
                mask[
                    int(event.onset * fs) : int(
                        (event.onset + event.duration) * fs
                    )
                ] = 1
        return mask

    def saveTsv(self, filename: str):
        with open(filename, "w") as f:
            line = "\t".join(list(Annotation.__annotations__.keys()))
            line += "\n"
            f.write(line)
            for event in self.events:
                line = ""
                line += "{:.2f}\t".format(event.onset)
                line += "{:.2f}\t".format(event.duration)
                line += "{}\t".format(event.eventType.value)
                if isinstance(event.confidence, (int, float)):
                    line += "{:.2f}\t".format(event.confidence)
                else:
                    line += "n/a\t"
                if isinstance(event.channels, (list, tuple)):
                    line += ",".join(event.channels)
                    line += "\t"
                else:
                    line += "n/a\t"
                if isinstance(event.dateTime, datetime):
                    line += "{}\t".format(event.dateTime.strftime("%Y-%m-%d %H:%M:%S"))
                else:
                    line += "n/a\t"
                line += "{:.2f}".format(event.recordingDuration)
                line += "\n"
                f.write(line)
