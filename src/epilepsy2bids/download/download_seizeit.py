"""Script to download the SeizeIT dataset doi:10.48804/P5Q0OJ.
The script requires a valid API key and depends on the requests library.
"""

import hashlib
import json
import logging
import os
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry


def downloadSeizeit(destination: str, apiToken: str) -> None:
    """Download the SeizeIT dataset.

    Args:
        destination (str): Path to the destination folder.
        apiToken (str): API key for the SeizeIT dataset.
    """

    SERVER_URL = "https://rdr.kuleuven.be"
    ID = "2407"
    VERSION = "1.0"

    logging.basicConfig(
        filename=os.path.join(destination, "downloadScript.log"),
        filemode="a",
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
    )

    # Initialize session
    s = requests.Session()

    retries = Retry(total=5, backoff_factor=1)

    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))

    # Get list of Files
    url = SERVER_URL + "/api/datasets/" + ID + "/versions/" + VERSION + "/files"
    respFileList = s.get(url)
    if respFileList.ok:
        fileList = json.loads(respFileList.content)

        # Download each file
        for file in fileList["data"]:
            if "directoryLabel" not in file.keys():
                file["directoryLabel"] = "."
            # Create directory structure
            Path(os.path.join(destination, file["directoryLabel"])).mkdir(
                parents=True, exist_ok=True
            )
            filename = os.path.join(
                destination, file["directoryLabel"], file["dataFile"]["filename"]
            )

            # if file exists skip file:
            if os.path.exists(filename):
                md5Hash = hashlib.md5(open(filename, "rb").read()).hexdigest()
                if md5Hash == file["dataFile"]["md5"]:
                    logging.info("Skipping alreday dowloaded file {}".format(filename))
                    continue

            # Download file
            try:
                url = SERVER_URL + "/api/access/datafile/" + str(file["dataFile"]["id"])
                headers = {"X-Dataverse-key": apiToken}
                resp = s.get(url, headers=headers)
            except Exception as e:
                logging.error("{} - {}".format(file["dataFile"]["id"], e))
            if resp.ok:
                # Chec md5 hash
                md5Hash = hashlib.md5(resp.content).hexdigest()
                if md5Hash == file["dataFile"]["md5"]:
                    # Write file to disk
                    with open(filename, "wb") as edfFile:
                        edfFile.write(resp.content)
                else:
                    logging.error(
                        "{} - MD5 hash difference".format(file["dataFile"]["id"])
                    )
            else:
                logging.error(
                    "{} - Failed to download file : {}".format(
                        file["dataFile"]["id"], resp.status_code
                    )
                )
    else:
        logging.error(
            "Failed to retrieve dataset list status : {}".format(
                respFileList.status_code
            )
        )
