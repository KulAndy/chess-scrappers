import io
import os
import time
import re
import zipfile
from contextlib import redirect_stderr
from datetime import datetime, date, timedelta
from pathlib import Path
import chess.pgn

import requests
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

DOWNLOAD_DIR = Path.home() / "Dokumenty" / "chess-results_pgns"


def accept_cookies(browser):
    try:
        btn_allow = WebDriverWait(browser, 5).until(
            EC.element_to_be_clickable((By.ID, 'CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll'))
        )
        btn_allow.click()
        time.sleep(1)
    except TimeoutException:
        pass


def download_pgn(browser, data):
    try:
        btn_download = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, 'P1_linkbutton_DownLoadPGN'))
        )
        browser.execute_script("arguments[0].scrollIntoView(true);", btn_download)
        time.sleep(0.5)
        btn_download.click()
    except Exception as e:
        print(f"Error processing: {data}")


def process_tournament_links(browser):
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    time.sleep(3)

    links = browser.find_elements(By.TAG_NAME, 'a')
    transmission_ids = set()
    for link in links:
        href = link.get_attribute('href')
        if href:
            match = re.search(r"/tnr(\d+)\.aspx", href)
            if match:
                tournament_id = match.group(1)
                downloaded = DOWNLOAD_DIR / f"{tournament_id}.pgn"
                if not downloaded.exists():
                    transmission_ids.add(match.group(1))

    print(f"Found {len(transmission_ids)} tournaments")

    for tournament_id in transmission_ids:
        url = f"https://chess-results.com/PartieSuche.aspx?lan=3&id=50023&tnr={tournament_id}&art=3"
        browser.get(url)
        accept_cookies(browser)
        download_pgn(browser, url)

        time.sleep(3)


def scrap_latest_tournaments(browser):
    browser.get("https://chess-results.com/Default.aspx?lan=3")

    accept_cookies(browser)
    tournament_select = browser.find_element(By.ID, 'combo_tur_sel')
    select = Select(tournament_select)
    select.select_by_index(7)
    process_tournament_links(browser)


def scrap_tournament_rage(browser, start_date, end_date):
    browser.get("https://s2.chess-results.com/turniersuche.aspx?lan=3")
    print(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    wait = WebDriverWait(browser, 10)

    accept_cookies(browser)

    time.sleep(3)
    von_input = wait.until(
        EC.presence_of_element_located((By.ID, "P1_txt_von_tag"))
    )
    von_input.clear()
    von_input.send_keys(start_date.strftime("%d%m%Y"))

    bis_input = wait.until(
        EC.presence_of_element_located((By.ID, "P1_txt_bis_tag"))
    )
    bis_input.clear()
    bis_input.send_keys(end_date.strftime("%d%m%Y"))

    zu_ende_checkbox = wait.until(
        EC.element_to_be_clickable((By.ID, "P1_cbox_zuEnde"))
    )
    if not zu_ende_checkbox.is_selected():
        zu_ende_checkbox.click()

    partien_checkbox = wait.until(
        EC.element_to_be_clickable((By.ID, "P1_cbox_partien_vorhanden"))
    )
    if not partien_checkbox.is_selected():
        partien_checkbox.click()

    select_rows = Select(
        wait.until(
            EC.presence_of_element_located(
                (By.ID, "P1_combo_anzahl_zeilen")
            )
        )
    )
    select_rows.select_by_index(5)

    bis_input.send_keys(Keys.ENTER)
    process_tournament_links(browser)


def download_fide_list():
    response = requests.get("https://ratings.fide.com/download/standard_rating_list.zip")
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall()


def scrap_players(browser):
    download_fide_list()
    wait10 = WebDriverWait(browser, 10)
    wait3 = WebDriverWait(browser, 3)
    with open("standard_rating_list.txt") as f:
        next(f)
        for line in f:
            fideid = line[0:15].strip()
            if not fideid.isdecimal():
                continue
            browser.get("https://s1.chess-results.com/partiesuche.aspx?lan=3")
            accept_cookies(browser)
            select_box = wait10.until(
                EC.presence_of_element_located((By.NAME, "ctl00$P1$combo_anzahl_zeilen"))
            )
            select = Select(select_box)
            select.select_by_value("5")

            input_box = wait10.until(
                EC.presence_of_element_located((By.NAME, "ctl00$P1$Txt_FideID"))
            )

            input_box.click()
            input_box.send_keys(fideid)
            input_box.send_keys(Keys.ENTER)
            wait10.until(EC.staleness_of(input_box))
            try:
                wait3.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#P1_GridView1 tbody tr")
                    )
                )
                download_pgn(browser, fideid)
                print(fideid)
            except TimeoutException:
                continue


def get_list_of_empty_date_files():
    needle1 = 'Date ""'
    needle2 = 'Date "????.??.??"'

    files = []

    for path in Path(DOWNLOAD_DIR).rglob("*"):
        if path.is_file():
            try:
                with path.open("r", errors="ignore") as f:
                    if any(
                            needle1 in line or
                            needle2 in line
                            for line in f):
                        files.append(path)
            except OSError as e:
                print(path)
                print(e)
                pass

    return files


def add_missing_date_tag():
    date_re = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")

    with open(os.devnull, "w") as fnull, redirect_stderr(fnull):
        for path in Path(DOWNLOAD_DIR).glob("*.pgn"):
            if not path.is_file():
                continue

            print("processing", path)

            ok = True
            tmp_name = "__tmp"
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            with open(path, "r") as fin, open(tmp_name, 'w') as fout:
                while True:
                    game = chess.pgn.read_game(fin)
                    if game is None:
                        break

                    headers = game.headers
                    if (
                            "Date" not in headers or
                            not date_re.match(headers["Date"])
                    ):
                        headers["Date"] = ""
                        ok = False
                        print("not ok", path)

                    fout.write(str(game).strip())
                    fout.write("\n\n")
            try:
                if not ok:
                    print("replace", path)
                    os.replace(tmp_name, path)

            except Exception as e:
                print(f"Error processing {path}: {e}")
            finally:
                try:
                    if os.path.exists(tmp_name):
                        os.unlink(tmp_name)
                except Exception:
                    pass


def correct_date_from_cr(browser, file):
    print(file)
    tournamentId = file.stem
    browser.get("https://s2.chess-results.com/turniersuche.aspx?lan=3")
    wait3 = WebDriverWait(browser, 3)
    wait10 = WebDriverWait(browser, 10)

    accept_cookies(browser)

    input_box = wait10.until(
        EC.presence_of_element_located((By.NAME, "ctl00$P1$txt_tnr"))
    )

    input_box.click()
    input_box.send_keys(tournamentId)

    input_box.send_keys(Keys.ENTER)
    wait10.until(EC.staleness_of(input_box))
    try:
        rows = wait3.until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, ".CRs2 tbody tr")
            )
        )

        rows = rows[::]

        if len(rows) >= 2:
            row = rows[1]
            cols = row.find_elements(By.TAG_NAME, "td")

            if len(cols) >= 7:
                start_date_string = cols[5].text
                end_date_string = cols[6].text
                start_date = datetime.strptime(start_date_string, "%Y/%m/%d").date()
                end_date = datetime.strptime(end_date_string, "%Y/%m/%d").date()

                new_date = start_date.strftime("%Y.")
                new_date += start_date.strftime("%m.") if start_date.month == end_date.month else "??."
                new_date += start_date.strftime("%d") if start_date.month == end_date.month else "??"

                content = file.read_text()
                content = content.replace('Date ""', new_date)
                content = content.replace('Date "????.??.??"', new_date)
                file.write_text(content)

    except TimeoutException:
        pass


def main():
    browser = webdriver.Chrome()
    #
    # scrap_players(browser)
    # scrap_latest_tournaments(browser)
    #
    today = date.today()
    first_day_current_month = date.today().replace(day=1)
    first_day_prev_month = (first_day_current_month - timedelta(days=1)).replace(day=1)
    first_day_prev_month = first_day_prev_month
    scrap_tournament_rage(browser, first_day_prev_month, today)
    #
    # for i in range(today.year, 2006, -1):
    #     start_date = date(i, 1, 1)
    #     end_date = date(i, 6, 30)
    #     scrap_tournament_rage(browser, start_date, end_date)
    #     start_date = date(i, 7, 1)
    #     end_date = date(i, 12, 31)
    #     scrap_tournament_rage(browser, start_date, end_date)
    #
    # for i in range(2006, 1960, -10):
    #     start_date = date(i - 9, 1, 1)
    #     end_date = date(i, 12, 31)
    #     scrap_tournament_rage(browser, start_date, end_date)
    #
    print("missing tag")
    add_missing_date_tag()

    print("searching empty")
    to_correct = get_list_of_empty_date_files()
    print("correcting")
    for tournament in to_correct:
        correct_date_from_cr(browser, tournament)

    input("Press Enter to close browser...")
    browser.quit()


if __name__ == '__main__':
    main()
