# README

This dataset is a BIDS compatible version of the Siena Scalp EEG Database. It reorganizes the file structure to comply with the BIDS specification. To this effect:

- Metadata was organized according to BIDS.
- Data in the EEG edf files was modified to keep only the 19 channels from a 10-20 EEG system.
- Annotations were formatted as BIDS-score compatible `tsv` files.

## Details related to access to the data

### License

The dataset is released under the [Open Data Commons Attribution License v1.0](https://physionet.org/content/chbmit/view-license/1.0.0/).

### Contact person

The original Physionet Siena Scalp EEG Database was published by Paolo Detti. This BIDS compatible version of the dataset was published by [Jonathan Dan](mailto:jonathan.dan@epfl.ch) - [ORCiD 0000-0002-2338-572X](https://orcid.org/0000-0002-2338-572X).

### Practical information to access the data

The original Physionet Siena Scalp EEG Database is available on the [Physionet website](https://physionet.org/content/siena-scalp-eeg/1.0.0/).

## Overview

### Project name

Siena Scalp EEG Database

### Year that the project ran

2020

### Brief overview of the tasks in the experiment

The Unit of Neurology and Neurophysiology at the University of Siena, Italy, acquired the data of 14 epileptic patients, collected during the national interdisciplinary research project PANACEE.

### Description of the contents of the dataset

Each folder refers to a specific subject including between 1 and 5 data files with a maximum size of 2.11 GB each.
Each folder (sub-01, sub-01, etc.) contains between 1 and 5 continuous .edf files from a single subject.

The EEG is recorded at 256 Hz. The recordings are referenced in a common average montage with 19 channels from the 10-20 electrode system.

The dataset also contains seizure annotations as start and stop times.

## Methods

### Subjects

14 patients with epileptic seizures, 9 males (ages 36–71) and 5 females (ages 20–58)

### Apparatus

The data were acquired employing EB Neuro and Natus Quantum LTM amplifiers, and reusable silver/gold cup electrodes.
