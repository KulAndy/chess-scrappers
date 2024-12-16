import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def main():
    browser = webdriver.Firefox()
    browser.get("https://chess-results.com/Default.aspx?lan=3")

    # Wait for the cookie consent button and click it
    btn_allow = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, 'CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll'))
    )
    btn_allow.click()

    # Select the tournament (example: selecting by index 7)
    tournament_select = browser.find_element(By.ID, 'combo_tur_sel')
    select = Select(tournament_select)
    select.select_by_index(7)

    # Wait for the page to load (you can adjust the wait time as needed)
    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    time.sleep(5)

    # Find all links on the page and extract those matching the pattern "/tnr\d+\.aspx"
    links = browser.find_elements(By.TAG_NAME, 'a')
    transmission_ids = set()
    for link in links:
        href = link.get_attribute('href')
        match = re.search(r"/tnr(\d+)\.aspx", href)
        if match:
            tournament_id = match.group(1)  # Extract the digits (\d+) between "tnr" and ".aspx"
            transmission_ids.add(tournament_id)

    print(len(transmission_ids))
    for tournament_id in transmission_ids:
        url=f"https://chess-results.com/PartieSuche.aspx?lan=3&id=50023&tnr={tournament_id}&art=3"
        print(url)
        browser.get(url)
        btn_download = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, 'P1_linkbutton_DownLoadPGN'))
        )
        btn_download.click()

    time.sleep(5)

    try:
        input("chessresults czeka na kliknięcie klawisza")
    except:
        pass

    browser.quit()


if __name__ == '__main__':
    main()
