"""Eeg class unit testing"""

import copy
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.epilepsy2bids.eeg import Eeg, FileFormat


class TestDataLoading(unittest.TestCase):
    def test_loadEdf(self):
        fileConfigurations = [
            {  # CHB-MIT
                "fileName": "tests/chb01_01_sample.edf",
                "montage": Eeg.Montage.BIPOLAR,
                "electrodes": Eeg.BIPOLAR_DBANANA,
            },
            {  # TUH
                "fileName": "tests/aaaaaaac_s001_t000_sample.edf",
                "montage": Eeg.Montage.UNIPOLAR,
                "electrodes": Eeg.ELECTRODES_10_20,
            },
            {  # Siena
                "fileName": "tests/PN00-5_sample.edf",
                "montage": Eeg.Montage.UNIPOLAR,
                "electrodes": Eeg.ELECTRODES_10_20,
            },
            {  # SeizeIT
                "fileName": "tests/P_ID10_r5_sample.edf",
                "montage": Eeg.Montage.UNIPOLAR,
                "electrodes": Eeg.ELECTRODES_10_20,
            },
        ]

        for fileConfig in fileConfigurations:
            eeg = Eeg.loadEdf(
                fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
            )
            self.assertEqual(eeg.data.shape[0], len(fileConfig["electrodes"]))
            self.assertEqual(len(eeg.channels), len(fileConfig["electrodes"]))
            self.assertEqual(eeg.montage, fileConfig["montage"])

    def test_resampling(self):
        fileConfig = {  # Siena
            "fileName": "tests/PN00-5_sample.edf",
            "montage": Eeg.Montage.UNIPOLAR,
            "electrodes": Eeg.ELECTRODES_10_20,
        }
        eeg = Eeg.loadEdf(
            fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
        )
        fileDuration = eeg.data.shape[1] / eeg.fs
        newFs = 256
        eeg.resample(newFs)
        newFileDuration = eeg.data.shape[1] / newFs

        self.assertEqual(fileDuration, newFileDuration)
        self.assertEqual(eeg.fs, newFs)

    def test_reReference(self):
        fileConfig = {  # Siena
            "fileName": "tests/PN00-5_sample.edf",
            "montage": Eeg.Montage.UNIPOLAR,
            "electrodes": Eeg.ELECTRODES_10_20,
        }
        eeg = Eeg.loadEdf(
            fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
        )
        # Common average
        eegAvg = copy.deepcopy(eeg)
        eegAvg.reReferenceToCommonAverage()
        # average of common average ref should be zero
        np.testing.assert_allclose(
            np.mean(eegAvg.data, axis=0),
            np.zeros((eeg.data.shape[1],)),
            rtol=1e-07,
            atol=1e-14,
        )
        # channel[0] should be data[0] - common average
        np.testing.assert_array_equal(
            eegAvg.data[0], eeg.data[0] - np.mean(eeg.data, axis=0)
        )
        # Cz Reference
        eegCz = copy.deepcopy(eeg)
        eegCz.reReferenceToReferential("Cz")
        # cz should be zero
        CzIndex = Eeg._findChannelIndex(eegCz.channels, "Cz", eegCz.montage)
        np.testing.assert_allclose(
            eegCz.data[CzIndex],
            np.zeros((eeg.data.shape[1],)),
            rtol=1e-07,
            atol=1e-14,
        )
        # Fz should be Fz - Cz
        FzIndex = Eeg._findChannelIndex(eegCz.channels, "Fz", eegCz.montage)
        np.testing.assert_array_equal(
            eegCz.data[FzIndex], eeg.data[FzIndex] - eeg.data[CzIndex]
        )
        # Check bipolar channel
        eegBp = copy.deepcopy(eeg)
        eegBp.reReferenceToBipolar()
        i0 = Eeg._findChannelIndex(
            eeg.channels, Eeg.BIPOLAR_DBANANA[0].split("-")[0], eeg.montage
        )
        i1 = Eeg._findChannelIndex(
            eeg.channels, Eeg.BIPOLAR_DBANANA[0].split("-")[1], eeg.montage
        )
        np.testing.assert_array_equal(eegBp.data[0], eeg.data[i0] - eeg.data[i1])

    def test_saveEdf(self):
        fileConfig = {  # Siena
            "fileName": "tests/PN00-5_sample.edf",
            "montage": Eeg.Montage.UNIPOLAR,
            "electrodes": Eeg.ELECTRODES_10_20,
        }
        eeg = Eeg.loadEdf(
            fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
        )
        eeg.standardize()
        eeg.saveEdf("test.edf")

        standardEeg = Eeg.loadEdf(
            "test.edf", fileConfig["montage"], fileConfig["electrodes"]
        )
        self.assertEqual(standardEeg.fs, 256)
        self.assertListEqual(standardEeg.channels, eeg.channels)
        np.testing.assert_allclose(
            standardEeg.data, eeg.data, rtol=1e-7, atol=1e-2
        )  # TODO absolute error is high might need to be checked
        Path("test.edf").unlink()

    def test_savecsv(self):
        fileConfig = {  # Siena
            "fileName": "tests/PN00-5_sample.edf",
            "montage": Eeg.Montage.UNIPOLAR,
            "electrodes": Eeg.ELECTRODES_10_20,
        }
        eeg = Eeg.loadEdf(
            fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
        )
        eeg.standardize()
        
        for ext in [FileFormat.CSV, FileFormat.CSV_GZIP, FileFormat.PARQUET_GZIP]:
            eeg.saveDataFrame(f"test.{ext}", ext)
            match ext:
                case FileFormat.CSV:
                    tblData = pd.read_csv(f"test.{ext}")
                case FileFormat.CSV_GZIP:
                    tblData = pd.read_csv(f"test.{ext}", compression="gzip")
                case FileFormat.PARQUET_GZIP:
                    tblData = pd.read_parquet(f"test.{ext}")
            self.assertListEqual(list(tblData), eeg.channels)
            np.testing.assert_allclose(eeg.data, tblData.to_numpy().transpose())
            Path(f"test.{ext}").unlink()


if __name__ == "__main__":
    unittest.main()
