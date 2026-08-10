import re
from threading import Semaphore
from urllib.parse import urlparse
import requests
from unidecode import unidecode

download_semaphore = Semaphore(2)


def lichess_download(link):
    res = requests.get(link, timeout=10)
    if res.ok:
        link = res.url

    pgn = ""
    with download_semaphore:
        match = re.search(r"https://lichess\.org/broadcast/([^/?#]+)$", link)
        lichess_url = None
        if match:
            lichess_url = "https://lichess.org/api/broadcast/" + match.group(1)

        match = re.search(r"https://lichess\.org/broadcast/([^/?#]+/[^/?#]+/[^/?#]+)$", link)
        if match:
            lichess_url = "https://lichess.org/api/broadcast/" + match.group(1)

        if lichess_url:
            response = requests.get(lichess_url, timeout=10)
            if response.ok:
                data = response.json()
                group_id = data.get("group", {}).get("id", None)
                if group_id:
                    res = requests.get(f"https://lichess.org/api/stream/broadcast/group/{group_id}.pgn", timeout=10)
                    if res.ok:
                        pgn += res.text + "\n\n"
                else:
                    res = requests.get(f"{lichess_url}.pgn", timeout=10)
                    if res.ok:
                        pgn += res.text + "\n\n"
        else:
            match = re.search(r"https://lichess\.org/broadcast/.*/([^/?#]+)$", link)

            if match:
                for part in ["group", "tour", "round"]:
                    try:
                        url = ("https://lichess.org/api/stream/broadcast/"
                               + part
                               + "/"
                               + match.group(1)
                               + ".pgn"
                               )
                        response = requests.get(url, timeout=10)
                        response.raise_for_status()

                        if response.ok:
                            pgn += response.text + "\n\n"
                            break
                    except:
                        pass

        return unidecode(pgn)


def scrap_livechess(url):
    pgn = ""
    parsed_url = urlparse(url)
    tournament_id = parsed_url.fragment
    tournament_response = requests.get(
        f"https://1.pool.livechesscloud.com/get/{tournament_id}/tournament.json",
        timeout=10
    )
    tournament_json = tournament_response.json()
    rounds = tournament_json["rounds"]
    for i in range(len(rounds)):
        round_response = requests.get(
            f"https://1.pool.livechesscloud.com/get/{tournament_id}/round-{i + 1}/index.json",
            timeout=10
        )
        round_json = round_response.json()
        for j in range(len(round_json["pairings"])):
            response = requests.get(
                f"https://1.pool.livechesscloud.com/get/{tournament_id}/round-{i + 1}/game-{j + 1}.json?poll",
                timeout=10
            )
            if response.ok:
                metadata = round_json["pairings"][j]
                metadata["date"] = round_json["date"]
                metadata["round"] = i + 1
                metadata.update(tournament_json)
                pgn += json2pgn(response.json(), metadata)
    return unidecode(pgn)


def json2pgn(data, metadata):
    tournament = "?"
    if metadata["name"]:
        tournament = str(metadata["name"]).replace('"', "")

    site = "?"
    if metadata["location"]:
        site = str(metadata["location"]).replace('"', "")

    date = "????.??.??"
    if metadata["date"]:
        date = str(metadata["date"] or "????.??.??").replace("-", ".")

    white = []
    if metadata["white"]:
        if metadata["white"]["lname"]:
            white.append(metadata["white"]["lname"].replace('"', ""))
        if metadata["white"]["fname"]:
            white.append(metadata["white"]["fname"].replace('"', ""))
        white = ", ".join(white)
    else:
        white = "N, N"

    black = []
    if metadata["black"]:
        if metadata["black"]["lname"]:
            black.append(metadata["black"]["lname"].replace('"', ""))
        if metadata["black"]["fname"]:
            black.append(metadata["black"]["fname"].replace('"', ""))
        black = ", ".join(black)
    else:
        black = "N, N"

    moves = ""
    for i in range(len(data["moves"])):
        if i % 2 == 0:
            moves += str(i // 2 + 1) + ". "
        moves += data["moves"][i].split(" ")[0] + " "
    moves += metadata["result"]
    pgn = f"""
[Event "{tournament or "?"}"]
[Site "{site or "?"}"]
[Date "{date}"]
[Round "{metadata["round"] or "?"}"]
[White "{white or "N, N"}"]
[Black "{black or "N, N"}"]
[Result "{metadata["result"] or "*"}"]
{moves}
"""
    return pgn
