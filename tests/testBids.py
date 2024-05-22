from importlib import resources as impresources
import json
import re
from shutil import rmtree
import subprocess
import unittest

from termcolor import cprint

from src.epilepsy2bids.bids.chbmit.convert2bids import convert as convertChbmit
from src.epilepsy2bids.bids.seizeit.convert2bids import convert as convertSeizeit
from src.epilepsy2bids.bids.siena.convert2bids import convert as convertSiena
from src.epilepsy2bids.bids.tuh.convert2bids import convert as convertTuh
import tests

TEST_DIR = impresources.files(tests) / "data"


class TestConvert(unittest.TestCase):
    def test_convert(self):
        for dataset, convert in zip(
            ("chbmit", "seizeit", "siena", "tuh"),
            (convertChbmit, convertSeizeit, convertSiena, convertTuh),
        ):
            convert(TEST_DIR / dataset, TEST_DIR / "bids" / dataset)
            rmtree(TEST_DIR / "bids" / dataset)
            cprint(
                f"Successfully converted {dataset.upper()} to BIDS.", "green", attrs=["bold"]
            )

    def test_bids_validator(self):
        for dataset, convert in zip(
            ("chbmit", "seizeit", "siena", "tuh"),
            (convertChbmit, convertSeizeit, convertSiena, convertTuh),
        ):
            convert(TEST_DIR / dataset, TEST_DIR / "bids" / dataset)
            output = subprocess.run(
                [
                    f"docker run -ti --rm -v {TEST_DIR / 'bids' / dataset}:/data:ro bids/validator /data --ignoreSubjectConsistency --json"
                ],
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
            )
            if output.stdout != b"":
                try:
                    out = output.stdout.decode()
                    out = re.findall('{.*}', out)[0]
                    out = json.loads(out)
                    out = out["issues"]
                    if len(out["errors"]):
                        raise RuntimeError(
                            f"docker bids-validator returned the following errors : {out['errors']}"
                        )
                    if len(out["warnings"]):
                        raise RuntimeWarning(
                            f"docker bids-validator returned the following warnings : {out['warnings']}"
                        )
                except AttributeError:
                    continue
            rmtree(TEST_DIR / "bids" / dataset)

            cprint(
                f"Successfully run BIDS-validator on {dataset.upper()}.",
                "green",
                attrs=["bold"],
            )
