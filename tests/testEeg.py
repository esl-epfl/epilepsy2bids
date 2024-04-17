"""Eeg class unit testing"""

import copy
import unittest

import numpy as np

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
        # TODO write tests
        eeg.standardize()
        eeg.saveEdf("test.edf")

    def test_savecsv(self):
        fileConfig = {  # Siena
            "fileName": "tests/PN00-5_sample.edf",
            "montage": Eeg.Montage.UNIPOLAR,
            "electrodes": Eeg.ELECTRODES_10_20,
        }
        eeg = Eeg.loadEdf(
            fileConfig["fileName"], fileConfig["montage"], fileConfig["electrodes"]
        )
        # TODO write tests
        eeg.standardize()
        eeg.saveDataFrame("test.csv", FileFormat.CSV)


if __name__ == "__main__":
    unittest.main()
