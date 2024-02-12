# Rail Data Marketplace scraper

Python script to scrape files from Rail Data Marketplace products.

## Usage

> [!IMPORTANT]  
> The instructions below assume that the relevant Python venv package is installed (e.g. `python3.10-venv` on Ubuntu 22.04), and that `python` points at a Python 3.x interpreter (requires `python-is-python3` on some distros).

Set up your Python environment:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Shove your username and password into environment variables:

```
export RDM_USERNAME="yourusername..."
export RDM_PASSWORD="hunter2..."
# ...or you can use a .env file
```

User accounts with MFA enabled also need an additional `RDM_TOTP_URI` environment variable which contains the `otpauth://` URI. To get the TOTP URI, use Inspect Element while setting up TOTP in-browser. Browse for a hidden input field, which will contain the URI, or scan the QR code with another device.

```
export RDM_TOTP_URI="otpauth://totp/Rail Data Marketplace:yourusername..."
```

Grab the product ID (`P-...`) whose files you want to download from the URL (e.g., https://raildata.org.uk/dashboard/dataProduct/P-03d4750c-27dd-4b3a-91ed-dec96174d179/overview), and run the script:

```
python ./scraper.py P-03d4750c-27dd-4b3a-91ed-dec96174d179 ./data
```

## Example

```
ubuntu@ddavid:~/rdm-scraper$ python ./scraper.py P-03d4750c-27dd-4b3a-91ed-dec96174d179 ./data
Logging in...
Got bearer token!
Finding data sources...
Listing files for data source DSP-3afb77d1-bb69-4ebd-b4dc-4db67f91cc91...
Found 5 files: ['CoachTypes.csv', 'InventoryClassDescriptions.csv', 'SeatProperties.csv', 'SeatPropertyDescriptions.csv', 'Seats.csv']
Downloading CoachTypes.csv...
Downloading InventoryClassDescriptions.csv...
Downloading SeatProperties.csv...
Downloading SeatPropertyDescriptions.csv...
Downloading Seats.csv...
```
