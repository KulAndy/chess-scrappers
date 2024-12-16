import os
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

import requests


def calculate_date_difference(start_date, end_date):
    delta = end_date - start_date
    return delta.days


def ensure_directories_exist(*dirs):
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)


def download_file(url, dest_path):
    if not dest_path.exists():
        print(f"Downloading: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            with open(dest_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f"Downloaded: {dest_path}")
        else:
            print(f"Failed to download {url} (status code: {response.status_code})")
    else:
        print(f"File already exists: {dest_path}")


def unzip_file(zip_path, extract_dir):
    try:
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    except Exception as e:
        print(f"Failed to unzip {zip_path}: {e}")


if __name__ == "__main__":
    start_date = datetime(2012, 6, 25).date()
    current_date = datetime.now().date()

    total_days = calculate_date_difference(start_date, current_date)
    total_weeks = total_days // 7

    downloaded_dir = Path("twic_downloaded")
    pgns_dir = Path("twic_pgns")
    ensure_directories_exist(downloaded_dir, pgns_dir)

    for week in range(total_weeks + 1):
        zip_filename = f"twic{920 + week}g.zip"
        zip_url = f"https://theweekinchess.com/zips/{zip_filename}"
        zip_path = downloaded_dir / zip_filename

        download_file(zip_url, zip_path)
        unzip_file(zip_path, pgns_dir)
