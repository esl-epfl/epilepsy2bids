from __future__ import annotations

import re
from pathlib import Path

EDF_NAME_PATTERN = re.compile(
    r"^sub-[A-Za-z0-9]+(_ses-[A-Za-z0-9]+)?_task-[A-Za-z0-9]+_run-[0-9]{2}_eeg\.edf$"
)


def validate_bids(out_dir: Path) -> list[str]:
    errors: list[str] = []
    out_dir = Path(out_dir)

    dataset_description = out_dir / "dataset_description.json"
    participants = out_dir / "participants.tsv"
    if not dataset_description.exists():
        errors.append("Missing dataset_description.json in output root.")
    if not participants.exists():
        errors.append("Missing participants.tsv in output root.")

    edf_files = sorted(out_dir.rglob("*.edf"))
    if not edf_files:
        errors.append("No EDF files found in output directory.")
        return errors

    for edf in edf_files:
        rel = edf.relative_to(out_dir)
        parts = rel.parts

        if parts[0].startswith("sub-"):
            subject = parts[0]
        else:
            errors.append(f"EDF not under a sub- folder: {rel.as_posix()}")
            continue

        session = None
        if len(parts) >= 2 and parts[1].startswith("ses-"):
            session = parts[1]
            if len(parts) < 3 or parts[2] != "eeg":
                errors.append(f"EDF not under eeg folder: {rel.as_posix()}")
                continue
        else:
            if len(parts) < 2 or parts[1] != "eeg":
                errors.append(f"EDF not under eeg folder: {rel.as_posix()}")
                continue

        if not EDF_NAME_PATTERN.match(edf.name):
            errors.append(f"EDF filename does not match BIDS pattern: {rel.as_posix()}")
            continue

        if not edf.name.startswith(subject):
            errors.append(
                f"EDF filename subject does not match folder: {rel.as_posix()}"
            )

        if session is not None and f"_{session}_" not in edf.name:
            errors.append(
                f"EDF filename session does not match folder: {rel.as_posix()}"
            )
        if session is None and "_ses-" in edf.name:
            errors.append(
                f"EDF filename includes session but path has none: {rel.as_posix()}"
            )

    return errors


def print_validation_report(out_dir: Path, errors: list[str]) -> None:
    if errors:
        print("Validation errors:")
        for i, err in enumerate(errors, start=1):
            print(f"{i}. {err}")
    else:
        print(f"Validation OK for {out_dir.as_posix()}.")
