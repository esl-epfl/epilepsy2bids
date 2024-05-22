"""Script to build a small sample EDF from an EDF recording. The recording header and list of signals are kept the same.
The content of data is white noise. The output file is named input_sample.edf
"""

import argparse
from itertools import islice
import os
from pathlib import Path
import shutil

from makeSampleEdf import makeSample

DURATION = 2
AMPLITUDE = 100


def makeSampleChb(input: Path, output: Path, numSubjects: int = 2) -> None:
    output.mkdir(parents=True, exist_ok=True)

    # Copy subject infor
    shutil.copy(input / "SUBJECT-INFO", output)

    folders = input.glob("*/")
    for folder in islice(folders, numSubjects - 1):
        subject = folder.name

        # Copy sz summary
        (output / subject).mkdir(parents=True, exist_ok=True)
        shutil.copy(folder / f"{subject}-summary.txt", output / subject)

        # Copy truncated EDF recordings
        for edfFile in folder.glob("*.edf"):
            makeSample(edfFile, output / subject / edfFile.name)


def makeSampleSiena(input: Path, output: Path, numSubjects: int = 2) -> None:
    output.mkdir(parents=True, exist_ok=True)

    # Copy subject info
    shutil.copy(input / "subject_info.csv", output)

    folders = input.glob("PN*/")
    for folder in islice(folders, numSubjects - 1):
        subject = folder.name

        # Copy sz summary
        (output / subject).mkdir(parents=True, exist_ok=True)
        shutil.copy(folder / f"Seizures-list-{subject}.txt", output / subject)

        # Copy truncated EDF recordings
        for edfFile in folder.glob("*.edf"):
            makeSample(edfFile, output / subject / edfFile.name)


def makeSampleSeizeit(input: Path, output: Path, numSubjects: int = 2) -> None:
    output.mkdir(parents=True, exist_ok=True)

    folders = input.glob("*/")
    for folder in islice(folders, numSubjects - 1):
        subject = folder.name
        (output / subject).mkdir(parents=True, exist_ok=True)
        # Copy truncated EDF recordings and annotations
        for edfFile in folder.glob("*.edf"):
            makeSample(edfFile, output / subject / edfFile.name)
            shutil.copy(
                edfFile.with_stem(f"{edfFile.stem}_a1").with_suffix(".tsv"),
                output / subject,
            )


def makeSampleTuh(input: Path, output: Path, numSubjects: int = 2) -> None:
    for subset in ["train", "dev", "eval"]:
        subRoot = input / subset
        folders = subRoot.glob("*/")
        for folder in islice(folders, numSubjects - 1):                    
            for edfFile in folder.glob("**/*.edf"):
                (output / os.path.join(*edfFile.parts[-5:-1])).mkdir(parents=True, exist_ok=True)
                print(edfFile)
                makeSample(
                    edfFile, output / os.path.join(*edfFile.parts[-5:])
                )
                shutil.copy(
                    edfFile.with_suffix(".csv_bi"),
                    output / os.path.join(*edfFile.parts[-5:-1]),
                )

        subject = folder.name
        (output / subject).mkdir(parents=True, exist_ok=True)
        # Copy truncated EDF recordings and annotations
        for edfFile in folder.glob("*.edf"):
            makeSample(edfFile, output / subject / edfFile.name)
            shutil.copy(
                edfFile.with_stem(f"{edfFile.stem}_a1").with_suffix(".tsv"),
                output / subject,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Extract an anonymized sample from a dataset",
        description="Shrinks an EDF to a sample. The recording header and list of signals are kept the same. "
        "The content of data is white noise. The output file is named input_sample.edf",
    )
    parser.add_argument("input", help="input folder.")
    parser.add_argument("output", help="output folder.")
    parser.add_argument("dataset", help="chbmit, siena, seizeit, tuh")

    args = parser.parse_args()
    match args.dataset:
        case "chbmit":
            makeSampleChb(Path(args.input), Path(args.output), 3)
        case "siena":
            makeSampleSiena(Path(args.input), Path(args.output), 3)
        case "seizeit":
            makeSampleSeizeit(Path(args.input), Path(args.output), 3)
        case "tuh":
            makeSampleTuh(Path(args.input), Path(args.output), 3)
        case _:
            raise ValueError(f"Unknown dataset: {args.dataset}.")
