from urllib.parse import urlparse

import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from unidecode import unidecode


def lichess_download(link, browser):
    try:
        browser.get(link + "#games")

        wait = WebDriverWait(browser, 1)
        games = wait.until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "mini-game"))
        )

        if games:
            games[0].click()

            share = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "share")))
            share.click()

            download_all_rounds = wait.until(
                EC.element_to_be_clickable(
                    (By.PARTIAL_LINK_TEXT, "POBIERZ WSZYSTKIE RUNDY")
                )
            )
            download_all_rounds.click()
    except:
        try:
            wait = WebDriverWait(browser, 1)
            download_all_rounds = wait.until(
                EC.element_to_be_clickable(
                    (By.PARTIAL_LINK_TEXT, "DOWNLOAD ALL ROUNDS")
                )
            )
            download_all_rounds.click()
        except:
            print(f"Error processing link: {link}")


def scrap_livechess(url):
    pgn = ""
    parsed_url = urlparse(url)
    tournament_id = parsed_url.fragment
    tournament_response = requests.get(
        f"https://1.pool.livechesscloud.com/get/{tournament_id}/tournament.json"
    )
    tournament_json = tournament_response.json()
    rounds = tournament_json["rounds"]
    for i in range(len(rounds)):
        round_response = requests.get(
            f"https://1.pool.livechesscloud.com/get/{tournament_id}/round-{i + 1}/index.json"
        )
        round_json = round_response.json()
        for j in range(len(round_json["pairings"])):
            response = requests.get(
                f"https://1.pool.livechesscloud.com/get/{tournament_id}/round-{i + 1}/game-{j + 1}.json?poll"
            )
            if response.ok:
                metadata = round_json["pairings"][j]
                metadata["date"] = round_json["date"]
                metadata["round"] = i + 1
                metadata.update(tournament_json)
                pgn += json2pgn(response.json(), metadata)
    return unidecode(pgn)


def json2pgn(data, metadata):
    tournament = str(metadata["name"]).replace('"', "")
    site = str(metadata["location"]).replace('"', "")
    date = str(metadata["date"] or "????.??.??").replace("-", ".")
    white = str(metadata["white"]["lname"] + ", " + metadata["white"]["fname"]).replace(
        '"', ""
    )
    black = str(metadata["black"]["lname"] + ", " + metadata["black"]["fname"]).replace(
        '"', ""
    )
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
