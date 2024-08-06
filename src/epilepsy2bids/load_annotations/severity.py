"""load annotations from the Severity dataset to an Annotations object."""

from dateutil import parser
import pytz

import numpy as np
import pandas as pd

from ..annotations import Annotation, Annotations, EventType, SeizureType


def preLoadAnnotations(annotFile):
    dfAnnotations = pd.read_csv(annotFile)
    for col in [
        "focal_start",
        "clinical_seizure_start",
        "tonic_start",
        "clonic_start",
        "clonic_end",
        "gtcs_start",
        "tonic_end",
    ]:
        dfAnnotations[col] = dfAnnotations[col].apply(
            lambda x: parser.parse(x) if not pd.isnull(x) else None
        )
    return dfAnnotations


def trc2events(df, trcFile, startTime, duration):
    TRC_fn = trcFile.split("/")[-1]
    events = df.query(f'TRC_fn == "{TRC_fn}"')

    annotations = Annotations()
    for _, seizure in events.iterrows():
        start_utc = startTime.astimezone(pytz.timezone(seizure["timezone"]))

        # TODO handle the different timings events of the seizure
        if (
            start_utc < seizure["focal_start"]
            and (seizure["focal_start"] - start_utc).seconds < duration
        ):
            annotation = Annotation()
            annotation["onset"] = (start_utc - seizure["focal_start"]).seconds
            end = np.max([seizure["tonic_end"], seizure["clonic_end"]])
            print(end)
            if pd.isna(end):
                annotation["duration"] = "n/a"
            else:
                annotation["duration"] = min(duration, (end - start_utc).seconds)
            annotation["eventType"] = SeizureType.sz
            annotation["confidence"] = "n/a"
            annotation["channels"] = "n/a"
            annotation["dateTime"] = startTime
            annotation["recordingDuration"] = duration
            annotations.events.append(annotation)

    # Populate dictionary
    if len(annotations.events) == 0:
        annotation = Annotation()
        annotation["onset"] = 0
        annotation["duration"] = duration
        annotation["eventType"] = EventType.bckg
        annotation["confidence"] = "n/a"
        annotation["channels"] = "n/a"
        annotation["dateTime"] = startTime
        annotation["recordingDuration"] = duration
        annotations.events.append(annotation)

    return annotations