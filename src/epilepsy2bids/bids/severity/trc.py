# coding=utf-8
# Copyright 2022 NeuroTech, CHUV. All rights reserved.
"""MultiModalSignal for Micromed EEG data."""

import datetime
import warnings
from pathlib import Path
from typing import Any, ByteString

import numpy as np
import pandas as pd
import wonambi

from epilepsy2bids.eeg import Eeg


def _decode_byte_to_str(
    byte_str: ByteString, encoding_list: list[str] = ["utf-8"]
) -> str | None:
    """
    Try to decode the byte_str with the provided encoding.

    Args:
        byte_str (ByteString): The byte string to decode.
        encoding_list (list[str], optional): A list of encoding names to try for decoding.
            Defaults to ['utf-8'].

    Returns:
        Union[str, None]: The decoded string if successful, None if decoding failed.

    Raises:
        Warning: If the byte string could not be decoded with any of the provided encodings.
    """
    decoded = None
    for encoding in encoding_list:
        try:
            decoded = byte_str.decode(encoding)
            return decoded
        except UnicodeDecodeError:
            pass

    if decoded is None:
        warnings.warn(
            "The byte-string could not be decoded with any of the provided "
            f"encoding : {', '.join(encoding_list)}."
        )

    return decoded


def load_from_TRC(
    raw_file_path: str | Path,
    channels: list[str] | None = None,
    anonymize: bool = True,
    timezone_source: str = "UTC",
    timezone_convert: str = "UTC",
) -> tuple[
    pd.DataFrame,
    float,
    dict[str, tuple[datetime.datetime, datetime.datetime]],
    list[tuple[datetime.datetime, str]],
    dict[str, Any],
]:
    """
    Load TRC data into the multimodal signal.

    The EEG data is loaded as a single signal named 'EEG'. The different segments of signal are
    loaded individually and concatenated together. If there are more than one segments, the segments' boundaries are
    added to the events of the signal under the name 'segment_<i>'. Micromed notes are loaded and added to the tags
    of the signals. All the metadata from the Micromed file is added to the signal metadata.

    Args:
        raw_file_path (str | Path): Path to a Micromed .TRC file to load.
        channels (List[str] | None): List of channel names to load. If None, all channels are loaded.
        anonymize (bool): Whether the name, surname, and birthdate should be anonymized. The name and surname are
            set to '' and the birthdate is set to 01.01.1900.
        timezone_source (str): The timezone in which the time-series is given.
        timezone_convert (str): The timezone in which the time series should be converted.
    """
    d = wonambi.Dataset(raw_file_path)

    raw_header = d.header["orig"]
    sampling_rate = raw_header["s_freq"]

    if isinstance(channels, list):
        valid_channels = [c for c in channels if c in d.header["chan_name"]]
        if len(valid_channels) == 0:
            warnings.warn(f"None of channels {channels} found in the TRC.")
    else:
        valid_channels = None

    print(valid_channels)

    # extract whole recording data as unique signal
    segment_data_list = _parse_segments(
        data=d.read_data(chan=valid_channels),
        raw_segment_info=raw_header["segments"],
        raw_start_time=raw_header["start_time"],
        sampling_rate=sampling_rate,
        timezone_source=timezone_source,
        timezone_convert=timezone_convert,
    )
    recording = pd.concat(segment_data_list, axis=0)

    # get the start and end time of each segment
    segments_bounds = {}
    if len(segment_data_list) > 1:
        for i, segment_df in enumerate(segment_data_list):
            start = segment_df.index[0]
            end = segment_df.index[-1]
            # add event 'segment_{i+1}' to signal
            segments_bounds[f"segment_{i+1}"] = (start, end)

    # parse notes and add them as tags
    notes = _parse_notes(raw_notes_info=raw_header["notes"], time_index=recording.index)

    # parse metadata
    if anonymize:
        raw_header.update(
            {"surname": "", "name": "", "date_of_birth": datetime.date(1900, 1, 1)}
        )

    return recording, sampling_rate, segments_bounds, notes, raw_header


def _parse_segments(
    data: wonambi.ChanTime,
    raw_segment_info: list[tuple[int, int]],
    raw_start_time: datetime.datetime,
    sampling_rate: float,
    timezone_source: str = "UTC",
    timezone_convert: str = "UTC",
) -> list[pd.DataFrame]:
    """
    Parse segments in the micromed data.

    Args:
        data (wonambi.ChanTime): The data extracted from the TRC by `wonambi`. The data is obtained by
            ```
            d = wonambi.Dataset(raw_file_path)
            data = d.read_data()
            ```
        raw_segment_info (list[tuple[int, int]]): The part of the micromed header holding the segment information.
            Obtained by :
            ```
            d = wonambi.Dataset(raw_file_path)
            raw_segment_info = d.header['orig']['segments']
            ```
        raw_start_time (datetime.datetime): The start time registered in the TRC metadata. Obtained by :
            ```
            d = wonambi.Dataset(raw_file_path)
            raw_segment_info = d.header['orig']['start_time']
            ```
        sampling_rate (float): The data sampling rate. Obtained by:
            ```
            d = wonambi.Dataset(raw_file_path)
            raw_segment_info = d.header['orig']['s_freq']
            ```
        timezone_source (str, optional): The timezone in which the time-serie is provided. Defaults to 'UTC'.
        timezone_convert (str | None, optional): The timezone to which the time-serie should be converted. Defaults
            to None.

    Returns:
        list[pd.DataFrame]: A list of pandas DataFrames holding the EEG data of each segment.
    """
    # put the start time in UTC.
    raw_start_time = (
        pd.Timestamp(raw_start_time)
        .tz_localize(timezone_source, ambiguous=True)
        .tz_convert("UTC")
    )

    segment_list = (
        raw_segment_info.tolist()
        if isinstance(raw_segment_info, np.ndarray)
        else raw_segment_info
    )
    segment_list = [segment for segment in segment_list if segment != (0, 0)]
    # if no segment specified, use the whole recording
    if len(segment_list) == 0:
        segment_list.append((0, 0))

    # if the first segment does not take the first data points add a segment
    # that start from the beginning
    if segment_list[0][1] != 0:
        segment_list.insert(0, (0, 0))

    end_segment = [segment[1] for segment in segment_list[1:]] + [None]
    segment_list = [
        (
            raw_start_time + datetime.timedelta(seconds=segment[0] / sampling_rate),
            segment[1],
            end_point,
        )
        for segment, end_point in zip(segment_list, end_segment)
    ]

    df_list = []
    # extract each segment separately
    for segment in segment_list:
        start_time, start_idx, end_idx = segment
        df = pd.DataFrame(
            data=data.data[0].T[start_idx:end_idx, :],
            columns=data.axis["chan"][0],
            index=data.axis["time"][0][start_idx:end_idx],
        )

        # set the index as the datetime
        df = df.reset_index().rename(columns={"index": "timedelta"})
        df["time"] = start_time
        df.timedelta -= df.loc[0, "timedelta"]
        df["time"] += pd.to_timedelta(df.timedelta, unit="s")
        df.set_index("time", inplace=True)
        # Convert to the right timezone
        df.index = df.index.tz_convert(tz=timezone_convert)
        df.drop(columns="timedelta", inplace=True)

        df_list.append(df)

    return df_list


def _parse_notes(
    raw_notes_info: list[tuple[int, ByteString]], time_index: list
) -> list[tuple[datetime.datetime, str]]:
    """
    Parse Notes from the raw micromed header.

    Args:
        raw_notes_info (list[tuple[int, ByteString]]): The part of the micromed header holding the notes information
            Obtained by :
            ```
            d = wonambi.Dataset(raw_file_path)
            raw_segment_info = d.header['orig']['notes']
            ```
        time_index (list): The datetime index of the loaded data.

    Returns:
        list[tuple[datetime.datetime, str]]: A list of 2-tuples (time, note).
    """
    notes = (
        raw_notes_info.tolist()
        if isinstance(raw_notes_info, np.ndarray)
        else raw_notes_info
    )

    parsed_notes = [
        (time_index[note[0]], _decode_byte_to_str(note[1], ["utf-8", "latin1"]))
        for note in notes
        if ((note[0] > 0) and (note[0] < len(time_index)))
    ]

    return parsed_notes


def load_Eeg_TRC(
    raw_file_path: str | Path, electrodes: list[str] = Eeg.ELECTRODES_10_20
):
    # Find electrodes
    d = wonambi.Dataset(raw_file_path)
    channels = None
    # If electrodes are provided, load them
    if electrodes is not None:
        channels = list()
        for electrode in electrodes:
            try:
                index = Eeg._findChannelIndex(
                    d.header["chan_name"], electrode, Eeg.Montage.UNIPOLAR
                )
                channels.append(d.header["chan_name"][index])
            except ValueError:
                print(f"Missing electrode {electrode} in file {raw_file_path} skipped.")

    # Load TRC
    recording, sampling_rate, segments_bounds, _, _ = load_from_TRC(
        raw_file_path, channels
    )

    # Process segments
    if len(segments_bounds.keys()) == 0:
        segments_bounds["segment_1"] = (recording.index[0], recording.index[-1])

    segments = list()
    for i in range(len(segments_bounds.keys())):
        fileHeader = Eeg.DEFAULT_FILE_HEADER
        fileHeader["recording_start_time"] = segments_bounds[f"segment_{i + 1}"][0]

        eeg = Eeg(
            recording[
                segments_bounds[f"segment_{i + 1}"][0] : segments_bounds[
                    f"segment_{i + 1}"
                ][1]
            ].T.to_numpy(),
            list(recording.keys()),
            sampling_rate,
        )
        segments.append(eeg)

    return segments
