# TUEP v2.0.1 (Epilepsy)

This converter targets the `00_epilepsy` portion of the TUH EEG Epilepsy
Corpus (TUEP) v2.0.1.

The conversion:

- indexes EDF recordings by subject, session, and montage;
- keeps the standard 10-20 EEG channels;
- resamples recordings to 256 Hz;
- applies a common-average reference;
- writes BIDS EEG recordings and sidecars;
- converts supported `*.csv_bi` seizure annotations to `events.tsv`.

Acquisition metadata shared with the existing TUH converter includes a
60 Hz power-line frequency and Temple University Hospital provenance.

Only `*.csv_bi` seizure annotations are currently supported.
