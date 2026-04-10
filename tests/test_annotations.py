"""Annotation class unit testing"""

import unittest
from pathlib import Path

import numpy as np

from epilepsy2bids.annotations import Annotations


class TestAnnotations(unittest.TestCase):
    def test_loadTsv(self):
        annotations = Annotations.loadTsv("tests/sample.tsv")
        # Test loading of event
        self.assertEqual(len(annotations.events), 3)
        self.assertEqual(len(annotations.getEvents()), 3)
        self.assertEqual(len(annotations.getMask(1)), 3600)

    def test_getMask_empty_events_no_error(self):
        annotations = Annotations()
        mask = annotations.getMask(fs=256)
        self.assertEqual(len(mask), 0)

    def test_getMask_empty_events_correct_length(self):
        annotations = Annotations()
        annotations.recordingDuration = 3600.0
        mask = annotations.getMask(fs=1)
        self.assertEqual(len(mask), 3600)
        self.assertTrue(np.all(mask == 0))

    def test_saveTsv(self):
        annotations = Annotations.loadTsv("tests/sample.tsv")
        annotations.saveTsv("test.tsv")
        test = Annotations.loadTsv("test.tsv")
        self.assertEqual(len(test.events), len(annotations.events))
        np.testing.assert_array_equal(test.getMask(1), annotations.getMask(1))
        Path("test.tsv").unlink()

if __name__ == "__main__":
    unittest.main()