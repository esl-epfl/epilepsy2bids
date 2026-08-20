# Epilepsy2Bids

Library for converting EEG datasets of people with epilepsy to [EEG-BIDS](https://doi.org/10.1038/s41597-019-0104-8) compatible datasets. These datasets comply with the [ILAE and IFCN minimum recording standards](https://doi.org/10.1016/j.clinph.2023.01.002). They provide annotations that are [HED-SCORE](http://arxiv.org/pdf/2310.15173) compatible. The datasets are formatted to be operated by the [SzCORE seizure validation framework](https://doi.org/10.1111/epi.18113).

The library provides tools to:

- Convert EEG datasets to BIDS.
- Load and manipulate EDF files.
- Load and manipulate seizure annotation files.

Currently, the following datasets are supported:

- [PhysioNet CHB-MIT Scalp EEG Database v1.0.0](https://doi.org/10.13026/C2K01R)
- [KULeuven SeizeIT1](https://doi.org/10.48804/P5Q0OJ)
- [Siena Scalp EEG Database v1.0.0](https://doi.org/10.13026/s309-a395)
- [TUH EEG Seizure Corpus](https://isip.piconepress.com/projects/nedc/html/tuh_eeg/)

## Installation

The epilepsy2bids package is released for macOS, Windows, and Linux, on [PyPI](https://pypi.org/project/epilepsy2bids/). It can be installed using pip:

```bash
python -m pip install -U pip
python -m pip install -U epilepsy2bids
```

It can also be installed from source with a modern build of `pip` :

```bash
python -m pip install -U pip
git clone https://github.com/esl-epfl/epilepsy2bids.git
cd epilepsy2bids
python -m pip install -e .
```

## Code

The primary function of `epilepsy2bids` is to convert EEG dataset to BIDS by calling the `convert()` for a given dataset.

```python
from epilepsy2bids.bids.chbmit.convert2bids import convert

convert(root: Path, outDir: Path)
```

In addition, the library provides the `Eeg` and `Annotation` classes that be used to manipulate EEG recordings.

### Adding support for a new dataset

All dataset converters should implement the `convert()` method. To assist many helper functions and generic code is already available in `src.epilepsy2bids.bids.convert2bids.py`. Examples of implementation are available in the supported datasets.

## TUEP: tuep2bids

`tuep2bids` is a CLI converter for the TUH EEG Epilepsy (TUEP) corpus (v2.0.1). It indexes the dataset, standardizes EDF recordings (10-20 montage, 256 Hz, common-average), and writes a minimal BIDS EEG structure with participants and per-recording metadata.

### Run the conversion

```
tuep2bids --input /path/to/aging/EEG/tuh_eeg_epilepsy/v2.0.1 --output /path/to/bids_out
```

### Example command

```
tuep2bids --input /data/aging/EEG/tuh_eeg_epilepsy/v2.0.1 --output /data/bids/tuep
```

### Output BIDS structure (minimal)

```
bids_out/
  dataset_description.json
  participants.tsv
  participants.json
  README
  sub-<id>/
    [ses-<id>/]
      eeg/
        sub-<id>[_ses-<id>]_task-szMonitoring_run-XX_eeg.edf
        sub-<id>[_ses-<id>]_task-szMonitoring_run-XX_eeg.json
        sub-<id>[_ses-<id>]_task-szMonitoring_run-XX_channels.tsv
        sub-<id>[_ses-<id>]_task-szMonitoring_run-XX_events.tsv (only if seizures are annotated)
```

### Known limitations / TODOs

- Metadata fields in `bids/tuep/eeg.json` and `dataset_description.json` still contain TODO values.
- Seizure annotations are parsed only from `*.csv_bi` sidecars; other formats are TODO.
- `events.tsv` is created only when seizure annotations are present; otherwise it is skipped.
