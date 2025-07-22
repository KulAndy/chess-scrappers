import os
from urllib.parse import urlparse
import requests
import zstandard as zstd

DOWNLOAD_DIR = "lichess_downloaded"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
PGN_DIR = "lichess_pgns"
os.makedirs(PGN_DIR, exist_ok=True)

url = "https://database.lichess.org/broadcast/list.txt"
response = requests.get(url)
response.raise_for_status()
content = response.text

for line in content.splitlines():
    url = line.strip()
    if not url:
        continue

    filename = os.path.basename(urlparse(url).path)
    dest_path = os.path.join(DOWNLOAD_DIR, filename)

    if os.path.exists(dest_path):
        print(f"Already downloaded: {filename}")
        continue

    print(f"Downloading: {filename} ...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(dest_path, "wb") as f_out:
            f_out.write(response.content)
        print(f"Saved: {dest_path}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")


for filename in os.listdir(DOWNLOAD_DIR):
    if not filename.endswith(".pgn.zst"):
        continue

    src_path = os.path.join(DOWNLOAD_DIR, filename)
    output_filename = filename.replace(".zst", "")
    output_path = os.path.join(PGN_DIR, output_filename)

    if os.path.exists(output_path):
        print(f"Already decompressed: {output_filename}")
        continue

    print(f"Decompressing: {filename} -> {output_filename}")
    try:
        with open(src_path, "rb") as compressed:
            dctx = zstd.ZstdDecompressor()
            with open(output_path, "wb") as decompressed:
                dctx.copy_stream(compressed, decompressed)
        print(f"Decompressed: {output_path}")
    except Exception as e:
        print(f"Failed to decompress {filename}: {e}")
