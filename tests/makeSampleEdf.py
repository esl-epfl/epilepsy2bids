"""Script to build a small sample EDF from an EDF recording. The recording header and list of signals are kept the same.
The content of data is white noise. The output file is named input_sample.edf
"""

import argparse
from pathlib import Path

import numpy as np
from pyedflib import highlevel

DURATION = 2
AMPLITUDE = 100


def makeSample(input: Path, outFilename: Path, duration: int = DURATION) -> None:
    signals, signal_headers, header = highlevel.read_edf(str(input))

    if isinstance(signals, np.ndarray):
        signals = signals.tolist()  # Make sure signals is a list

    # Keep only short duration of white noise
    for i in range(len(signals)):
        signals[i] = (
            np.random.rand(int(duration * signal_headers[i]["sample_frequency"])) * AMPLITUDE
        )

    highlevel.write_edf(str(outFilename), signals, signal_headers, header)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Shrink an EDF to a sample two seconds long",
        description="Shrinks an EDF to a sample. The recording header and list of signals are kept the same. "
        "The content of data is white noise. The output file is named input_sample.edf",
    )
    parser.add_argument("input", help="input edf file.")

    args = parser.parse_args()
    makeSample(args.input, args.input[:-4] + "_sample.edf". DURATION)
