import random
import re
import time

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

MIN_ACTION_DELAY = 1.5  # seconds
MAX_ACTION_DELAY = 3.5

MIN_TOURNAMENT_DELAY = 4  # seconds
MAX_TOURNAMENT_DELAY = 8

COOLDOWN_EVERY = 20  # pause after every N tournaments
COOLDOWN_SECONDS = 60  # cooldown duration


def execute_script(
    browser: webdriver.Chrome,
    script: str,
) -> object:
    return browser.execute_script(script)  # type: ignore[no-untyped-call]


def wait_for_page_load(browser: webdriver.Chrome, timeout: int = 30) -> None:
    WebDriverWait(browser, timeout).until(
        lambda d: execute_script(browser, "return document.readyState") == "complete"
    )


def human_delay(min_s: float, max_s: float) -> None:
    time.sleep(random.uniform(min_s, max_s))


def scrap_tournament(url: str, browser: webdriver.Chrome) -> None:
    wait = WebDriverWait(browser, 20)

    browser.get(url)
    wait_for_page_load(browser)

    human_delay(MIN_ACTION_DELAY, MAX_ACTION_DELAY)

    kebab_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[.//img[@alt='kebab']]"))
    )
    kebab_button.click()
    human_delay(MIN_ACTION_DELAY, MAX_ACTION_DELAY)

    download_tournament = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//div[normalize-space()='Download tournament']")
        )
    )
    download_tournament.click()
    human_delay(MIN_ACTION_DELAY, MAX_ACTION_DELAY)

    download_pgn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//span[normalize-space()='Download PGN file']")
        )
    )
    download_pgn.click()


def collect_archived_tournaments(
    browser: webdriver.Chrome, timeout_minutes: int = 30
) -> list[str]:
    browser.get("https://media.idchess.com/en/tournaments/archived")
    wait_for_page_load(browser)

    actions = ActionChains(browser)

    collected_links: set[str] = set()
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    no_growth_cycles = 0
    MAX_NO_GROWTH = 8

    # Click body to ensure focus
    browser.find_element(By.TAG_NAME, "body").click()
    time.sleep(1)

    while time.time() - start_time < timeout_seconds:
        previous_count = len(collected_links)

        # === HUMAN SCROLLING ===
        for _ in range(6):
            actions.send_keys(Keys.PAGE_DOWN).perform() # type: ignore[no-untyped-call]
            time.sleep(random.uniform(0.4, 0.8))

        time.sleep(2.5)  # allow network fetch

        # Collect links
        links = browser.find_elements(
            By.XPATH,
            "//a[contains(@href, '/tournaments/') and not(contains(@href, '/archived'))]",
        )

        for link in links:
            href: str | None = link.get_attribute("href")  # type: ignore[no-untyped-call]
            if href and re.search(
                r"https://media.idchess.com/(en/)?tournaments/[a-zA-Z\d]+/.+", href
            ):
                collected_links.add(href)

        if len(collected_links) == previous_count:
            no_growth_cycles += 1
            print(f"No growth cycle {no_growth_cycles}")
        else:
            no_growth_cycles = 0
            print(f"Collected {len(collected_links)}")

        elapsed = time.time() - start_time
        print(f"Elapsed {elapsed // 60}:{elapsed % 60}")

        if no_growth_cycles >= MAX_NO_GROWTH:
            print("End of archived tournaments")
            break

    return list(collected_links)


def main() -> None:
    browser = webdriver.Chrome()

    tournament_links = collect_archived_tournaments(browser)
    print(f"Found {len(tournament_links)} tournaments")

    for idx, link in enumerate(tournament_links, start=1):
        try:
            print(f"({idx}) Downloading: {link}")
            scrap_tournament(link, browser)

            human_delay(MIN_TOURNAMENT_DELAY, MAX_TOURNAMENT_DELAY)

            if idx % COOLDOWN_EVERY == 0:
                print(f"Cooldown for {COOLDOWN_SECONDS}s")
                time.sleep(COOLDOWN_SECONDS)

        except Exception as e:
            print(f"Failed: {link} → {e}")
            human_delay(5, 10)

    input("Done. Press Enter to exit.")
    browser.quit()


if __name__ == "__main__":
    main()
