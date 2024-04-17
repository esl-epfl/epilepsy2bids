"""Annotation class unit testing"""

import unittest
from pathlib import Path

from src.epilepsy2bids.annotations import Annotations


class TestAnnotations(unittest.TestCase):
    def test_loadTsv(self):
        annotations = Annotations.loadTsv("tests/sample.tsv")
        loadTsv


if __name__ == "__main__":
    unittest.main()