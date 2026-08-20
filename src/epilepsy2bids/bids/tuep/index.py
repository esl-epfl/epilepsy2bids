from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, List

SESSION_PATTERN = re.compile(r"^s\d{3}_\d{4}$")


@dataclass(frozen=True)
class Recording:
    edf_path: str
    subject_id: str
    session_id: str | None
    montage: str
    group: str
    annotation_paths: list[str] = field(default_factory=list)
    extra_metadata: dict | None = None


def _resolve_epilepsy_root(root_path: Path) -> Path:
    """Resolve the expected 00_epilepsy root under the TUEP v2.0.1 root."""
    root_path = Path(root_path)
    candidate = root_path / "00_epilepsy"
    if candidate.exists():
        return candidate
    raise ValueError(
        "Expected root path to be the TUEP v2.0.1 directory containing '00_epilepsy'. "
        f"Got: {root_path.as_posix()}"
    )


def _iter_dirs(path: Path) -> Iterable[Path]:
    return sorted(p for p in path.iterdir() if p.is_dir())


def _derive_subject_id_from_path(edf_path: Path) -> str:
    parts = edf_path.parts
    try:
        group_idx = parts.index("00_epilepsy")
        return parts[group_idx + 1]
    except (ValueError, IndexError):
        return "TODO"


def _derive_session_id_from_path(edf_path: Path) -> str | None:
    parts = edf_path.parts
    for part in parts:
        if SESSION_PATTERN.match(part):
            return part
    return None


def _derive_group_from_path(edf_path: Path) -> str:
    parts = edf_path.parts
    if "00_epilepsy" in parts:
        return "epilepsy"
    return "unknown"


def _find_annotation_paths(edf_path: Path) -> list[str]:
    parent = edf_path.parent
    stem = edf_path.stem
    matches = sorted(
        p
        for p in parent.glob(f"{stem}.*")
        if p.is_file() and p.suffix.lower() != ".edf"
    )
    return [p.as_posix() for p in matches]


def index_tuep(root_path: Path | str) -> List[Recording]:
    """Index TUEP v2.0.1 EDF recordings under 00_epilepsy.

    Expected layout:
      <root>/00_epilepsy/<subject_id>/<session_id>/<montage>/*.edf
    """
    epilepsy_root = _resolve_epilepsy_root(Path(root_path))
    recordings: list[Recording] = []

    for subject_dir in _iter_dirs(epilepsy_root):
        subject_id = subject_dir.name
        for session_dir in _iter_dirs(subject_dir):
            session_id = session_dir.name
            if not SESSION_PATTERN.match(session_id):
                continue
            for montage_dir in _iter_dirs(session_dir):
                montage = montage_dir.name
                for edf_file in sorted(montage_dir.glob("*.edf")):
                    derived_subject = _derive_subject_id_from_path(edf_file)
                    derived_session = _derive_session_id_from_path(edf_file)
                    annotation_paths = _find_annotation_paths(edf_file)
                    recordings.append(
                        Recording(
                            edf_path=edf_file.as_posix(),
                            subject_id=derived_subject
                            if derived_subject != "TODO"
                            else subject_id,
                            session_id=derived_session or session_id,
                            montage=montage,
                            group=_derive_group_from_path(edf_file),
                            annotation_paths=annotation_paths,
                            extra_metadata=None,
                        )
                    )

    return recordings


def print_index_summary(records: List[Recording], sample_size: int = 5) -> None:
    total = len(records)
    print(f"TUEP index: {total} EDF recordings found.")
    if total:
        print(f"Sample {min(sample_size, total)} records:")
        for record in records[:sample_size]:
            print(
                "- {edf_path} | subject_id={subject_id} "
                "session_id={session_id} montage={montage} group={group} "
                "annotations={annotations}".format(
                    annotations=len(record.annotation_paths),
                    **asdict(record),
                )
            )
    print(
        "Note: Only directories matching <root>/00_epilepsy/<subject_id>/"
        "<session_id>/<montage>/*.edf are indexed. "
        "Sessions are limited to the pattern sXXX_YYYY."
    )


def write_index_json(
    root_path: Path | str,
    out_path: Path | str,
    min_records: int = 20,
    sample_size: int = 5,
) -> List[Recording]:
    records = index_tuep(root_path)
    if len(records) < min_records:
        raise ValueError(
            f"Found {len(records)} recordings, but at least {min_records} are required."
        )

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump([asdict(record) for record in records], f, indent=2)

    print_index_summary(records, sample_size=sample_size)
    print(f"Wrote index JSON: {out_path.as_posix()}")
    return records


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Index TUEP v2.0.1 EDF recordings and write index.json."
    )
    parser.add_argument(
        "root",
        type=str,
        help="Path to the TUEP v2.0.1 root containing 00_epilepsy.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="index.json",
        help="Output JSON path.",
    )
    parser.add_argument(
        "--min-records",
        type=int,
        default=20,
        help="Minimum recordings required to write index.",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Number of sample records to print.",
    )
    args = parser.parse_args()

    write_index_json(
        args.root,
        args.out,
        min_records=args.min_records,
        sample_size=args.sample_size,
    )
