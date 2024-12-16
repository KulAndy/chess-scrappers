# do analizy stron
import os
import sys
from datetime import datetime
# kolejki są fifo
from queue import Queue, Empty
# współbierzność
from threading import Thread, Lock
from urllib.parse import unquote

import bs4
import numpy as np
# sprawdza poprawność danych
import pyinputplus as pyip
import re
import requests
import time
# kontrola przeglądarki
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from parser import lichess_download, scrap_livechess


class Throttle:
    """
    klasa do dławienia programu
    """

    def __init__(self, rate):
        self.__consume_lock = Lock()
        self.rate = rate
        self.tokens = 0
        self.last = None

    def consume(self, amount=1):
        """
        na podstawie liczby tokenów określa się czy można działać, czy czekać
        """
        with self.__consume_lock:
            now = time.time()

            if self.last is None:
                self.last = now

            elapsed = now - self.last

            if elapsed * self.rate > 1:
                self.tokens += elapsed * self.rate
                self.last = now

            self.tokens = min(self.rate, self.tokens)

            if self.tokens >= amount:
                self.tokens -= amount
                return amount
            return 0


def manual_download(url, browser, found_links, year):
    try:
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
                chessPaste = browser.find_element(By.LINK_TEXT, "PGN")
                res = requests.get(chessPaste.get_attribute("href"))
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
            except:
                pass
    except:
        pass


def searchPGN(tournament, browser, year):
    """szukanie pgnów"""
    found_links = []
    href = tournament["href"]
    JS_PATTERN = r"</?\w+|function|if|var|let|;|\(.*\)"
    EMPTY_YEAR_PATTERN = r"(1899|\?\?\?\?)[.-]\.[.-]\."
    if "http://chessarbiter.com/turnieje/open.php?" in href:
        try:
            browser.get(href)
            links = browser.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    linkUrl = link.get_attribute("href")
                    # dodawanie plików pgn
                    if ".pgn" in linkUrl:
                        try:
                            # pobieranie strony
                            remoteFile = requests.get(linkUrl, timeout=10)
                            remoteFile.raise_for_status()
                            # jeśli nie xml/javascript
                            if not re.search(JS_PATTERN, remoteFile.text):
                                # uzupełnij rok jeśli nie ma
                                found_links.append(
                                    re.sub(
                                        EMPTY_YEAR_PATTERN,
                                        f"{year}.??.??",
                                        remoteFile.text,
                                    )
                                )
                            else:
                                if not re.search(
                                    EMPTY_YEAR_PATTERN, remoteFile.text
                                ) and not re.search(
                                    JS_PATTERN,
                                    remoteFile.text,
                                ):
                                    found_links.append(remoteFile.text)
                                raise Exception("Nie znaleziono roku gry")
                            found_links.append(
                                re.sub(
                                    EMPTY_YEAR_PATTERN,
                                    f"{year}.??.??",
                                    remoteFile.text,
                                )
                            )
                        except Exception as err:
                            overChessarbiterUrl = re.compile(
                                r"chessarbiter\.com/turnieje/2[0-9]{3}/t[id]_[0-9]+/(?=.*\.[a-z]{2,3})"
                            )
                            if overChessarbiterUrl.search(linkUrl):
                                if not re.search(
                                    JS_PATTERN,
                                    remoteFile.text,
                                ):
                                    found_links.append(
                                        re.sub(
                                            EMPTY_YEAR_PATTERN,
                                            f"{year}.??.??",
                                            remoteFile.text,
                                        )
                                    )
                            pass
                    # jeśli jest zakładka pgn
                    elif "pgn.html" in linkUrl:
                        tournamentUrl = "/".join(linkUrl.split("/")[:-1])
                        try:
                            # spróbuj pobrać wszystkie gry
                            remoteFile = requests.get(
                                tournamentUrl + "/games.pgn", timeout=10
                            )
                            remoteFile.raise_for_status()
                            if not re.search(JS_PATTERN, remoteFile.text):
                                found_links.append(
                                    re.sub(
                                        EMPTY_YEAR_PATTERN,
                                        f"{year}.??.??",
                                        remoteFile.text,
                                    )
                                )
                            found_links.append(
                                re.sub(
                                    EMPTY_YEAR_PATTERN,
                                    f"{year}.??.??",
                                    remoteFile.text,
                                )
                            )
                        except:
                            try:
                                # jeśli nie ma wszystkich gier razem to pobierz pojedynczo
                                manual_download(linkUrl, browser, found_links, year)
                            except:
                                pass
                            pass
                    elif "lichess.org/broadcast/" in linkUrl:
                        lichess_download(linkUrl, browser)

                    elif "view.livechesscloud.com" in linkUrl:
                        try:
                            found_links.append(scrap_livechess(linkUrl))
                        except:
                            pass
                except:
                    pass
        except:
            pass
    return found_links






def worker(work_queue, results_queue, throttle, chooseBrowser, year):
    # switch-case w pythonie
    try:
        browser = None
        match chooseBrowser:
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
                    result = searchPGN(item, browser, year)
                except Exception as err:
                    results_queue.put(err)
                else:
                    if (
                        isinstance(result, (list, tuple, np.ndarray))
                        and len(result) > 0
                    ):
                        results_queue.put(result)
                finally:
                    work_queue.task_done()
            try:
                input("Chessarbiter czeka na kliknięcie klawisza")
            except:
                pass
            browser.quit()
        else:
            print("nie udało się otworzyć przeglądarki")
    except Exception as e:
        print(e)


def main():
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
        print(" ok")
    except:
        print(" brak")

    print("Firefox", end="")
    try:
        options = FirefoxOptions()
        options.add_argument("--headless")
        browser = webdriver.Firefox(options=options)
        browsers.append("Firefox")
        browser.quit()
        print(" ok")
    except:
        print(" brak")

    # dla windowsa
    if sys.platform == "win32":
        print("Edge", end="")
    try:
        if sys.platform == "win32":
            options = EdgeOptions()
            options.use_chromium = True
            options.add_argument("headless")
            options.add_argument("disable-gpu")
            browser = webdriver.Edge()
            browsers.append("Edge")
            browser.quit()
            print(" ok")
    except:
        print(" brak")

    # dla maca
    if sys.platform == "darwin":
        print("Safari", end="")
    try:
        if sys.platform == "darwin":
            browser = webdriver.Safari()
            browsers.append("Safari")
            browser.quit()
            print(" ok")
    except:
        print(" brak")

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
        chooseBrowser = pyip.inputMenu(
            browsers,
            default=1,
            blank=True,
            prompt="Wybierz przglądarkę:\n",
            numbered=True,
        )
    except:
        chooseBrowser = browsers[0]

    # dolny limit chessarbitra
    minimum = 2004
    # górny limit chessarbitra
    maximum = int(datetime.now().year)

    # zakres przeszukiwania
    print("Podaj zakres")
    minYear = pyip.inputInt("Dolna granica ", min=minimum, max=maximum, blank=True)
    if minYear == "":
        minYear = maximum
    maxYear = pyip.inputInt("Górna granica ", min=minYear, max=maximum, blank=True)
    if maxYear == "":
        maxYear = maximum

    # gry są zapisywane dopiero po przeanalizowaniu całego roku
    print(
        'gry będą zapisywane do pliku "chessArbiter.pgn" po sprawdzeniu w całości każdego roku'
    )
    # sprawdzenie czy plik istnieje
    if os.path.isfile("chessArbiter.pgn"):
        print("taki plik już istnieje")
        chooseFile = pyip.inputMenu(
            ["nadpisać", "dodać partie na koniec pliku", "anulować"],
            prompt="Co chesz zrobić?\n",
            numbered=True,
        )
        if chooseFile == "nadpisać":
            tmp = open("chessArbiter.pgn", "w")
            tmp.close()
        elif chooseFile == "anulować":
            sys.exit()

    # wyszukiwanie turniejów z danego roku
    for i in range(maxYear, minYear - 1, -1):
        print(f"Pobieranie turniejów z roku {i}")
        res = requests.get(
            f"http://chessarbiter.com/turnieje.php?rok={i}&miesiac=0&idz=Wy%C5%9Bwietl"
        )

        try:
            # sprawdzenie błędów
            res.raise_for_status()
            mainSoup = bs4.BeautifulSoup(res.text, "lxml")
            # linki z kontenera z linkami turniejowymi
            tournaments = mainSoup.select("#zawartosc > table > tr > td > a")

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
                    args=(work_queue, results_queue, throttle, chooseBrowser, i),
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
                        r"(([1-9][0-9]*\.)? ?(([RBNQK]?[a-h1-8]?x?[a-h][1-8][+#]?|0-0-0|O-O-O|0-0|O-O) ?({.*})? ?){,2})+|(0-1|1-0|1\/2-1\/2|0,5-0,5|0.5-0.5|\*)|^\*$",
                        x,
                    ),
                    result,
                )
                # nie xml
                result = filter(lambda x: not re.search("</?.*>|&", x), result)

                games = "\n".join(result)
                # zapis do pliku
                with open("chessArbiter.pgn", "a") as file:
                    regex = r'Date \"(None|(\?\?\?\?|1899)\.\?\?\.\?\?)\"'
                    file.write(re.sub(regex, f'{i}.??.??', games))

        except Exception as err:
            print(err)



# wywołanie jako samodzielny plik, a nie moduł
if __name__ == "__main__":
    main()
