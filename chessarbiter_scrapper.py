# do analizy stron
import os
import re
import sys
import time
import traceback
from argparse import ArgumentError
from datetime import datetime

# kolejki są fifo
from queue import Empty, Queue

# współbierzność
from threading import Thread
from urllib.parse import unquote

import bs4

# sprawdza poprawność danych
import pyinputplus as pyip
import requests

# kontrola przeglądarki
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from parser import lichess_download, scrap_livechess
from Throttle import Throttle

FILENAME = "chessarbiter.pgn"
BROWSER_DETECTED = " ok"
BROWSER_NOT_DETECTED = " brak"


def manual_download(
    url: str,
    browser: webdriver.Chrome | webdriver.Firefox | webdriver.Edge | webdriver.Safari,
    found_links: list[str],
    year: int,
) -> None:
    browser.get(url)
    # wyświetlanie 100 gier
    select = browser.find_element(By.TAG_NAME, "select")
    select.send_keys("100")

    games = []

    # linki z grami
    pages = browser.find_elements(
        By.CSS_SELECTOR, "#table_pgn_paginate > span:nth-child(3) > span"
    )

    for i in range(len(pages)):
        # przejdź do gry i pobierz
        pages = browser.find_elements(
            By.CSS_SELECTOR, "#table_pgn_paginate > span:nth-child(3) > span"
        )
        browser.execute_script("arguments[0].click();", pages[i])
        page_links = browser.find_elements(
            By.CSS_SELECTOR, "#table_pgn > tbody > tr > td > a"
        )
        for link in page_links:
            games.append(link.get_attribute("href"))

    for game in games:
        try:
            browser.get(game)
            chess_paste = browser.find_element(By.LINK_TEXT, "PGN")
            href = chess_paste.get_attribute("href")
            if not href:
                raise ValueError("No href for link PGN")
            res = requests.get(href)
            # kodowanie url na zwykły tekst
            notation = unquote(res.text)
            notation = notation.replace("[Round", f'[Date "{year}.??.??][Round')
            notation = notation.replace("][", "]\n[")
            # zamiana polskich znaków
            notation = notation.replace(r"%u0104", "A")
            notation = notation.replace(r"%u0106", "C")
            notation = notation.replace(r"%u0118", "E")
            notation = notation.replace(r"%u0141", "L")
            notation = notation.replace(r"%u0143", "N")
            notation = notation.replace(r"%u00D3", "O")
            notation = notation.replace(r"%u015A", "S")
            notation = notation.replace(r"%u0179", "Z")
            notation = notation.replace(r"%u017B", "Z")

            notation = notation.replace(r"%u0105", "a")
            notation = notation.replace(r"%u0107", "c")
            notation = notation.replace(r"%u0119", "e")
            notation = notation.replace(r"%u0142", "l")
            notation = notation.replace(r"%u0144", "n")
            notation = notation.replace(r"%u00F3", "o")
            notation = notation.replace(r"%u015B", "s")
            notation = notation.replace(r"%u017A", "z")
            notation = notation.replace(r"%u017C", "z")
            notation = notation.replace(" ", "o")
            found_links.append(notation)
        except Exception:
            pass


def search_pgn(
    tournament: bs4.element.Tag,
    browser: webdriver.Chrome | webdriver.Firefox | webdriver.Edge | webdriver.Safari,
    year: int,
) -> list[str]:
    """szukanie pgnów"""
    found_links = []
    href = tournament["href"]
    JS_PATTERN = r"</?\w+|function|if|var|let|;|\(.*\)"
    EMPTY_YEAR_PATTERN = r"(1899|\?\?\?\?)[.-].{1,2}[.-].{1,2}"
    if "https://chessarbiter.com/turnieje/open.php?" in href:
        try:
            browser.get(href)
            links = browser.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    link_url = link.get_attribute("href")
                    if not link_url:
                        continue

                    # dodawanie plików pgn
                    if ".pgn" in link_url:
                        remote_file = requests.get(link_url, timeout=10)
                        try:
                            # pobieranie strony
                            remote_file.raise_for_status()
                            # jeśli nie xml/javascript
                            if not re.search(JS_PATTERN, remote_file.text):
                                # uzupełnij rok jeśli nie ma
                                found_links.append(
                                    re.sub(
                                        EMPTY_YEAR_PATTERN,
                                        f"{year}.??.??",
                                        remote_file.text,
                                    )
                                )
                            else:
                                if not re.search(
                                    EMPTY_YEAR_PATTERN, remote_file.text
                                ) and not re.search(
                                    JS_PATTERN,
                                    remote_file.text,
                                ):
                                    found_links.append(remote_file.text)
                                raise ArgumentError("Nie znaleziono roku gry")
                            found_links.append(
                                re.sub(
                                    EMPTY_YEAR_PATTERN,
                                    f"{year}.??.??",
                                    remote_file.text,
                                )
                            )
                        except Exception:
                            over_chessarbiter_url = re.compile(
                                r"chessarbiter\.com/turnieje/2\d{3}/t[id]_\d+/(?=.*\.[a-z]{2,3})"
                            )
                            if over_chessarbiter_url.search(link_url) and not re.search(
                                JS_PATTERN,
                                remote_file.text,
                            ):
                                found_links.append(
                                    re.sub(
                                        EMPTY_YEAR_PATTERN,
                                        f"{year}.??.??",
                                        remote_file.text,
                                    )
                                )
                    # jeśli jest zakładka pgn
                    elif "pgn.html" in link_url:
                        tournament_url = "/".join(link_url.split("/")[:-1])
                        try:
                            # spróbuj pobrać wszystkie gry
                            remote_file = requests.get(
                                tournament_url + "/games.pgn", timeout=10
                            )
                            remote_file.raise_for_status()
                            if not re.search(JS_PATTERN, remote_file.text):
                                found_links.append(
                                    re.sub(
                                        EMPTY_YEAR_PATTERN,
                                        f"{year}.??.??",
                                        remote_file.text,
                                    )
                                )
                            found_links.append(
                                re.sub(
                                    EMPTY_YEAR_PATTERN,
                                    f"{year}.??.??",
                                    remote_file.text,
                                )
                            )
                        except Exception:
                            try:
                                # jeśli nie ma wszystkich gier razem to pobierz pojedynczo
                                manual_download(link_url, browser, found_links, year)
                            except Exception:
                                pass
                    elif "lichess.org/broadcast/" in link_url:
                        found_links.append(lichess_download(link_url))

                    elif "view.livechesscloud.com" in link_url:
                        found_links.append(scrap_livechess(link_url))
                except Exception as e:
                    print(f"Error processing: {href}")
                    if link_url:
                        print(f"Error processing: {link_url}")
                    print(e)
                    print(traceback.format_exc())
        except Exception:
            pass
    return found_links


def worker(
    work_queue: Queue,
    results_queue: Queue,
    throttle: Throttle,
    choose_browser: str,
    year: int,
) -> None:
    # switch-case w pythonie
    try:
        browser = None
        match choose_browser:
            case "Chrome":
                browser = webdriver.Chrome()
            case "Firefox":
                browser = webdriver.Firefox()
            case "Edge":
                browser = webdriver.Edge()
            case "Safari":
                browser = webdriver.Safari()

        # dopóki są zadania
        if browser:
            while not work_queue.empty():
                try:
                    # get bez limitu czasu
                    item = work_queue.get_nowait()
                except Empty:
                    break

                # thorrling
                while not throttle.consume():
                    time.sleep(0.1)

                try:
                    # szukanie pgnów
                    result = search_pgn(item, browser, year)
                except Exception as err:
                    results_queue.put(err)
                else:
                    if isinstance(result, (list, tuple)) and len(result) > 0:
                        results_queue.put(result)
                finally:
                    work_queue.task_done()
            try:
                input("Chessarbiter czeka na kliknięcie klawisza")
            except Exception:
                pass
            browser.quit()
        else:
            print("nie udało się otworzyć przeglądarki")
    except Exception as e:
        print(e)


def main() -> None:
    # ilość procesów scrapujących
    POOL_SIZE = 2
    # lista przglądarek
    browsers = []
    print("Sprawdzanie dostępnych przeglądarek")
    print("Chrome", end="")
    try:
        options = ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        browser = webdriver.Chrome(options=options)
        browsers.append("Chrome")
        browser.quit()
        print(BROWSER_DETECTED)
    except Exception:
        print(BROWSER_NOT_DETECTED)

    print("Firefox", end="")
    try:
        options = FirefoxOptions()
        options.add_argument("--headless")
        browser = webdriver.Firefox(options=options)
        browsers.append("Firefox")
        browser.quit()
        print(BROWSER_DETECTED)
    except Exception:
        print(BROWSER_NOT_DETECTED)

    # dla windowsa
    if sys.platform == "win32":
        print("Edge", end="")
        try:
            options = EdgeOptions()
            options.add_argument("headless")
            options.add_argument("disable-gpu")
            browser = webdriver.Edge()
            browsers.append("Edge")
            browser.quit()
            print(BROWSER_DETECTED)
        except Exception:
            print(BROWSER_NOT_DETECTED)

    # dla maca
    if sys.platform == "darwin":
        print("Safari", end="")
        try:
            browser = webdriver.Safari()
            browsers.append("Safari")
            browser.quit()
            print(BROWSER_DETECTED)
        except Exception:
            print(BROWSER_NOT_DETECTED)

    del browser
    if len(browsers) == 0:
        sys.exit(
            f"""Brak przeglądarek do sterowania
                pobierz jedną
                Firefox
                https://github.com/mozilla/geckodriver/releases
                Chrome
                https://sites.google.com/a/chromium.org/chromedriver/downloads
                Edge
                https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/
                Safari
                https://webkit.org/blog/6900/webdriver-support-in-safari-10/
                i dodaj do jednego z katalogów
                {os.environ["PATH"]}
                 """
        )
    try:
        # wybór przeglądarki, domyślnie pierwsza
        choose_browser = pyip.inputMenu(
            browsers,
            default=1,
            blank=True,
            prompt="Wybierz przglądarkę:\n",
            numbered=True,
        )
    except Exception:
        choose_browser = browsers[0]

    # dolny limit chessarbitra
    minimum = 2004
    # górny limit chessarbitra
    maximum = int(datetime.now().year)

    # zakres przeszukiwania
    print("Podaj zakres")
    min_year = pyip.inputInt("Dolna granica ", min=minimum, max=maximum, blank=True)
    if min_year == "":
        min_year = maximum
    max_year = pyip.inputInt("Górna granica ", min=min_year, max=maximum, blank=True)
    if max_year == "":
        max_year = maximum

    # gry są zapisywane dopiero po przeanalizowaniu całego roku
    print(
        f'gry będą zapisywane do pliku "{FILENAME}" po sprawdzeniu w całości każdego roku'
    )
    # sprawdzenie czy plik istnieje
    if os.path.isfile(FILENAME):
        print("taki plik już istnieje")
        choose_file = pyip.inputMenu(
            ["nadpisać", "dodać partie na koniec pliku", "anulować"],
            prompt="Co chesz zrobić?\n",
            numbered=True,
        )
        if choose_file == "nadpisać":
            tmp = open(FILENAME, "w")
            tmp.close()
        elif choose_file == "anulować":
            sys.exit()

    # wyszukiwanie turniejów z danego roku
    for i in range(max_year, min_year - 1, -1):
        print(f"Pobieranie turniejów z roku {i}")
        res = requests.get(
            f"https://chessarbiter.com/turnieje.php?rok={i}&miesiac=0&idz=Wy%C5%9Bwietl"
        )

        try:
            # sprawdzenie błędów
            res.raise_for_status()
            main_soup = bs4.BeautifulSoup(res.text, "lxml")
            # linki z kontenera z linkami turniejowymi
            tournaments = main_soup.select("#zawartosc > table > tr > td > a")

            # kolejka zadań
            work_queue = Queue()
            # kolejka wyników
            results_queue = Queue()

            # throttling choć trzeba samemu sprawdźić czy nie będzie za dużo zapytań
            throttle = Throttle(3)

            for tournament in tournaments:
                work_queue.put(tournament)

            # współbierznie będą wykonywane funkcje worker z paramaterami
            threads = [
                Thread(
                    target=worker,
                    args=(work_queue, results_queue, throttle, choose_browser, i),
                )
                for _ in range(POOL_SIZE)
            ]

            for thread in threads:
                # rozpoczęcie wykonywania procesów
                thread.start()

            # oczekiwanie na zakończenie
            work_queue.join()

            print(f"zapisaywanie partii z roku {i}")

            # dopóki są jeszcze jakieś wyniki
            while not results_queue.empty():
                # pobieranie pierwszego elementu z kolejki
                result = results_queue.get()
                # jeśli błąd przejdź do kolejnej iteracji
                if isinstance(result, Exception):
                    continue

                # niepuste wyniki
                result = filter(lambda x: len(x) != 0, result)
                # zawierające tagi pgn
                result = filter(lambda x: re.search(r'\[\w+ ".*"]', x), result)
                # zawierające notacje algebraiczną
                result = filter(
                    lambda x: re.search(
                        r"(([1-9]\d*\.)? ?(([RBNQK]?[a-h1-8]?x?[a-h][1-8][+#]?|0-0-0|O-O-O|0-0|O-O) ?({.*})? ?){,"
                        r"2})+|(0-1|1-0|1/2-1/2|0,5-0,5|0.5-0.5|\*)|^\*$",
                        x,
                    ),
                    result,
                )
                # nie xml
                result = filter(lambda x: not re.search("</?.*>|&", x), result)

                games = "\n".join(result)
                # zapis do pliku
                with open(FILENAME, "a") as file:
                    regex = r"Date \"(None|(\?\?\?\?|1899)\.\?\?\.\?\?)\""
                    file.write(re.sub(regex, f"{i}.??.??", games))

        except Exception as err:
            print(err)


# wywołanie jako samodzielny plik, a nie moduł
if __name__ == "__main__":
    main()
