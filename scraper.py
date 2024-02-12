"""
This module provides a script to download data files from the Rail Data Market API.
"""

import os
import sys
from typing import Any
import dotenv
import requests
from rdm_auth import get_bearer_token


BROWSER_USER_AGENT: str = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_1) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                          "Version/18.0 Safari/605.1.15")
RDM_CLOUD_STORE_LIST_FILES_URI = "https://raildata.org.uk/ContractManagementService/cloudstore/listfiles"
RDM_DATA_SOURCE_URI: str = "https://raildata.org.uk/MetaDataService/fetch/dataSourceInfo/byProductCodeNew/"

dotenv.load_dotenv()


def list_data_files(product_id: str, bearer_token: str):
    """

    :param product_id: The P- prefixed RDM data product identifier from the user-facing URL e.g.
                       https://raildata.org.uk/dashboard/dataProduct/P-ABCDEF
    :param bearer_token: The bearer token to authenticate with the RDM API
    :return: A list of data files for the RDM product
    """

    print("Finding data sources...")
    data_source_info_r = requests.get(
        f"{RDM_DATA_SOURCE_URI}{product_id}",
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": BROWSER_USER_AGENT,
            "Cookie": "cookie_consent=true; ISL_SCR=true",
            "Origin": "https://raildata.org.uk",
            "Referer": f"https://raildata.org.uk/dashboard/dataProduct/{product_id}",
        },
        timeout=30,
    )

    data_source_info = data_source_info_r.json()

    data_sources: list[str] = []

    for data_source in data_source_info:
        if data_source["dataSourceType"] != "FILE":
            print(f"Non-file data source for {product_id} is not yet supported")
            continue

        data_sources.append(data_source["dsParentNew"]["dataSourceParentCode"])

    files: list[Any] = []

    for source in data_sources:
        print(f"Listing files for data source {source}...")
        _files = requests.post(
            RDM_CLOUD_STORE_LIST_FILES_URI,
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "User-Agent": BROWSER_USER_AGENT,
                "Cookie": "cookie_consent=true; ISL_SCR=true",
                "Origin": "https://raildata.org.uk",
                "Referer": f"https://raildata.org.uk/dashboard/dataProduct/{product_id}",
            },
            json={"dsCode": source, "dsStatus": "Active"},
            timeout=30,
        ).json()

        for f in _files:
            f["dsCode"] = source

        files += _files

    return files


def get_download_url(
    product_id: str, data_source_code: str, file_name: str, bearer_token: str
) -> str:
    """
    Get a signed GCS URL to download a specific data file from an RDM product.
    :param product_id: The P- prefixed RDM data product identifier
    :param data_source_code: The data source code for the data file, retrieved by list_data_files
    :param file_name: The name of the file to download
    :param bearer_token: The bearer token to authenticate with the RDM API
    :return: A GCS URL to download the file
    """
    return requests.post(
        "https://raildata.org.uk/ContractManagementService/cloudstore/generate/signedurl/download",
        json={
            "dataProductCode": product_id,
            "dsCode": data_source_code,
            "dsStatus": "Active",
            "fileName": file_name,
        },
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": BROWSER_USER_AGENT,
            "Cookie": "cookie_consent=true; ISL_SCR=true",
            "Origin": "https://raildata.org.uk",
            "Referer": f"https://raildata.org.uk/dashboard/dataProduct/{product_id}/dataFiles",
        },
        timeout=30,
    ).text


def main():
    """
    Script entry-point
    """
    _usr = os.getenv("RDM_USERNAME")
    _pwd = os.getenv("RDM_PASSWORD")

    if _usr is None or _usr == "":
        print(
            "No username provided. Please provide a valid username through env var RDM_USERNAME."
        )
        sys.exit(1)
    if _pwd is None or _pwd == "":
        print(
            "No password provided. Please provide a valid password through env var RDM_PASSWORD."
        )
        sys.exit(1)

    _otp = os.getenv("RDM_TOTP_URI")
    print("Logging in...")
    token = get_bearer_token(_usr, _pwd, _otp)
    print("Got bearer token!")

    product = sys.argv[1]
    out_dir_relative = sys.argv[2]

    if token is None or token == "":
        print(
            "No token provided. Please provide a valid token through env var RDM_TOKEN."
        )
        sys.exit(1)

    if out_dir_relative is None or out_dir_relative == "":
        print("No output directory provided.")
        sys.exit(1)

    out_dir = os.path.join(os.path.dirname(__file__), sys.argv[2])

    if not os.path.exists(out_dir):
        print("Provided output directory does not exist. Please create it first.")
        print(out_dir)
        sys.exit(1)

    files = list_data_files(product, token)

    file_names = [f["fileName"] for f in files]
    print(f"Found {len(files)} files: {file_names}")

    download_urls = [
        {
            "fileName": f["fileName"],
            "url": get_download_url(
                product_id=product,
                bearer_token=token,
                data_source_code=f["dsCode"],
                file_name=f["fileName"],
            ),
        }
        for f in files
    ]

    for data in download_urls:
        print(f"Downloading {data['fileName']}...")
        r = requests.get(data["url"], timeout=30)
        with open(os.path.join(out_dir, data["fileName"]), "wb") as f:
            f.write(r.content)


if __name__ == "__main__":
    main()
