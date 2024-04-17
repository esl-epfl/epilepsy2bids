# README

This dataset is a BIDS compatible version of the SeizeIT dataset. It reorganizes the file structure to comply with the BIDS specification. To this effect:

- Metadata was organized according to BIDS.
- Data in the EEG edf files was modified to keep only the 19 channels from a 10-20 EEG system.
- Annotations were formatted as BIDS-score compatible `tsv` files.

## Details related to access to the data

### License

The dataset is released under the original [Custom KU Leuven license](https://www.kuleuven.be/rdm/en/rdr/custom-kuleuven). It is a restrive license which requires a data sharing agreement with KU Leuven to access the files.

### Contact person

The original SeizeIT dataset was published by Christos Chatzichristos. This BIDS compatible version of the dataset was published by [Jonathan Dan](mailto:jonathan.dan@epfl.ch) - [ORCiD 0000-0002-2338-572X](https://orcid.org/0000-0002-2338-572X).

### Practical information to access the data

The original SeizeIT dataset is available on the [KU Leuven website](https://rdr.kuleuven.be/dataset.xhtml?persistentId=doi:10.48804/P5Q0OJ).

## Overview

### Project name

SeizeIT dataset

### Year that the project ran

2023

### Brief overview of the tasks in the experiment

This dataset was obtained during an ICON project (2017-2018) in collaboration with KU Leuven (ESAT-STADIUS), UZ Leuven, UCB, Byteflies and Pilipili. The goal of this project was to design a system using Behind the ear (bhE) EEG electrodes for monitoring the patient in a home environment. The dataset was acquired in the hospital during presurgical evaluation. During the presurgical evaluation, patients are monitored using the vEEG for multiple days (typically a week). Patients are however restricted to move within their room because of the wiring and video analysis.

### Description of the contents of the dataset

In this dataset, the following data is available for 42 subjects: Full 10-20 scalp EEG data of the patient during the presurgical evaluation. The number of seizures per patient ranged from 1 to 22, with a median of 3 seizures per patient. The duration of the seizures, the time difference of seizure EEG onset and end, varied between 11 and 695 seconds with a median of 50 seconds. 89% of the seizures were Focal Impaired Awareness seizures. 91% of the seizures originated from the (fronto-) temporal lobe. Seizures annotations are provided by a certified neurologist.

## Methods

### Subjects

42 patients with epileptic seizures.
