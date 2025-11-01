import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def accept_cookies(browser):
    try:
        btn_allow = WebDriverWait(browser, 5).until(
            EC.element_to_be_clickable((By.ID, 'CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll'))
        )
        btn_allow.click()
        time.sleep(1)
    except TimeoutException:
        pass


def main():
    browser = webdriver.Firefox()
    browser.get("https://chess-results.com/Default.aspx?lan=3")

    accept_cookies(browser)
    tournament_select = browser.find_element(By.ID, 'combo_tur_sel')
    select = Select(tournament_select)
    select.select_by_index(7)

    WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    time.sleep(3)

    links = browser.find_elements(By.TAG_NAME, 'a')
    transmission_ids = set()
    for link in links:
        href = link.get_attribute('href')
        if href:
            match = re.search(r"/tnr(\d+)\.aspx", href)
            if match:
                transmission_ids.add(match.group(1))

    print(f"Found {len(transmission_ids)} tournaments")

    for tournament_id in transmission_ids:
        url = f"https://chess-results.com/PartieSuche.aspx?lan=3&id=50023&tnr={tournament_id}&art=3"
        browser.get(url)
        accept_cookies(browser)

        try:
            btn_download = WebDriverWait(browser, 10).until(
                EC.element_to_be_clickable((By.ID, 'P1_linkbutton_DownLoadPGN'))
            )
            browser.execute_script("arguments[0].scrollIntoView(true);", btn_download)
            time.sleep(0.5)
            btn_download.click()
        except Exception as e:
            print(f"Error processing: {url}")

        time.sleep(3)

    input("Press Enter to close browser...")
    browser.quit()


if __name__ == '__main__':
    main()
