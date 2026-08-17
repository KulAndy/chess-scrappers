import argparse
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

DOWNLOAD_DIR = Path.home() / "Dokumenty" / "chess-results_pgns"
CR_URL = "https://chess-results.com/"
PARTIE_SUCHE_URL = "https://s2.chess-results.com/PartieSuche.aspx"


def get_hidden_fields(soup: BeautifulSoup) -> dict[str, str]:
    hidden_fields: dict[str, str] = {}

    for field in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]:
        element = soup.find("input", {"name": field})

        if isinstance(element, Tag):
            value = element.get("value")
            if isinstance(value, str):
                hidden_fields[field] = value

    return hidden_fields


def get_input_value(soup: BeautifulSoup, name: str) -> str:
    element = soup.find("input", {"name": name})

    if not isinstance(element, Tag):
        raise ValueError(f"Missing input field: {name}")

    value = element.get("value", "")

    if not isinstance(value, str):
        raise ValueError(f"Invalid value for input field: {name}")

    return value


def main(compare_downloaded: bool = False) -> None:
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pl-PL,pl;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": PARTIE_SUCHE_URL,
            "Origin": "https://s2.chess-results.com",
            "DNT": "1",
            "Upgrade-Insecure-Requests": "1",
        }
    )

    response = session.get(CR_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    if not soup:
        raise ValueError("Cannot parse html")

    viewstate = get_input_value(soup, "__VIEWSTATE")
    viewstate_generator = get_input_value(soup, "__VIEWSTATEGENERATOR")
    eventvalidation = get_input_value(soup, "__EVENTVALIDATION")

    data = {
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": viewstate_generator,
        "__EVENTVALIDATION": eventvalidation,
        "__EVENTTARGET": "combo_sel",
        "__EVENTARGUMENT": "",
        "combo_tur_sel": "7",
        "combo_sort": "0",
    }

    response = session.post(CR_URL, data=data)
    response.raise_for_status()

    matches = re.findall(
        r'href=["\']([^"\']*/tnr(\d+)\.aspx[^"\']*)["\']',
        response.text,
        flags=re.IGNORECASE,
    )
    transmission_ids = set()
    for _href, tournament_id in matches:
        downloaded = DOWNLOAD_DIR / f"{tournament_id}.pgn"
        if not compare_downloaded or not downloaded.exists():
            transmission_ids.add(tournament_id)

    with open("chessresults.pgn", "w") as file:
        for tournament_id in transmission_ids:
            game_url = f"{PARTIE_SUCHE_URL}?lan=1&id=50023&tnr={tournament_id}&art=3"
            response = session.get(game_url)
            soup = BeautifulSoup(response.text, "html.parser")
            hidden_fields = get_hidden_fields(soup)

            data = {
                "__LASTFOCUS": "",
                "__VIEWSTATE": hidden_fields["__VIEWSTATE"],
                "__VIEWSTATEGENERATOR": hidden_fields["__VIEWSTATEGENERATOR"],
                "__EVENTVALIDATION": hidden_fields["__EVENTVALIDATION"],
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "ctl00$P1$combo_anzahl_zeilen": "1",
                "ctl00$P1$cb_DownLoadPGN": "Download as PGN-File",
                "ctl00$P1$txt_von_tag": "",
                "ctl00$P1$txt_bis_tag": "",
                "ctl00$P1$txt_rdbis": "",
                "ctl00$P1$txt_rdvon": "",
                "ctl00$P1$txt_dbkey": tournament_id,
                "ctl00$P1$txt_bez": "",
                "ctl00$P1$txt_vorname": "",
                "ctl00$P1$Txt_FideID": "",
                "ctl00$P1$Txt_NatID": "",
                "ctl00$P1$txt_nachname": "",
                "ctl00$P1$combo_spielerfarbe": "-",
                "ctl00$P1$combo_ergebnis": "-",
            }

            response = session.post(game_url, data=data)
            if response.ok:
                file.write(response.text)
                file.write("\n\n")

                if compare_downloaded:
                    with open(DOWNLOAD_DIR / f"{tournament_id}.pgn", "w") as games:
                        games.write(response.text)
            else:
                print(f"HTTP {response.status_code} for {tournament_id}")
            time.sleep(2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--compare-downloaded",
        action="store_true",
        help="Check that file exists in downloaded",
    )

    args = parser.parse_args()

    main(args.compare_downloaded)
