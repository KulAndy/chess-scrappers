import os
import re
import requests
import zstandard as zstd
import chess.pgn
from io import StringIO
from urllib.parse import urlparse
from concurrent.futures import ProcessPoolExecutor

DOWNLOAD_DIR = "lichess_downloaded"
PGN_DIR = "lichess_pgns"
MAX_WORKERS = 6
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(PGN_DIR, exist_ok=True)


def download_list():
    url = "https://database.lichess.org/broadcast/list.txt"
    response = requests.get(url)
    response.raise_for_status()
    return response.text.strip().splitlines()


def download_file(url):
    filename = os.path.basename(urlparse(url).path)
    dest_path = os.path.join(DOWNLOAD_DIR, filename)

    if os.path.exists(dest_path):
        print(f"[SKIP] Already downloaded: {filename}")
        return

    print(f"[DOWNLOAD] {filename}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(response.content)
        print(f"[SAVED] {dest_path}")
    except Exception as e:
        print(f"[ERROR] Failed to download {url}: {e}")


def decompress_and_fix(filename):
    if not filename.endswith(".pgn.zst"):
        return

    src_path = os.path.join(DOWNLOAD_DIR, filename)
    output_filename = filename.replace(".zst", "")
    output_path = os.path.join(PGN_DIR, output_filename)

    match = re.search(r"(\d{4})-(\d{2})", filename)
    if not match:
        print(f"[SKIP] No date info in filename: {filename}")
        return

    year, month = match.groups()
    default_date = f"{year}.{month}.??"

    try:
        if not os.path.exists(output_path):
            print(f"[DECOMPRESS] {filename}")
            with open(src_path, "rb") as compressed:
                dctx = zstd.ZstdDecompressor()
                with open(output_path, "wb") as decompressed:
                    dctx.copy_stream(compressed, decompressed)
            print(f"[DONE] Decompressed: {output_path}")
        else:
            print(f"[SKIP] Already decompressed: {output_filename}")

        with open(output_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        pgn_io = StringIO(raw_content)
        games = []
        while True:
            game = chess.pgn.read_game(pgn_io)
            if game is None:
                break
            games.append(game)

        print(f"[INFO] {output_filename}: {len(games)} games")

        updated_pgn = ""
        for game in games:
            headers = game.headers
            if "Date" not in headers or headers["Date"] in {"????.??.??", "0000.00.00", ""}:
                headers["Date"] = default_date
            updated_pgn += str(game).strip() + "\n\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(updated_pgn.strip() + "\n")

        print(f"[FIXED] {output_filename}")

    except Exception as e:
        print(f"[ERROR] {filename}: {e}")


def main():
    urls = download_list()
    for url in urls:
        download_file(url.strip())

    files = os.listdir(DOWNLOAD_DIR)
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        executor.map(decompress_and_fix, files)


if __name__ == '__main__':
    main()
