import os
import re
import time

from selenium import webdriver
from selenium.webdriver.common.by import By

from parser import lichess_download, scrap_livechess


def main():
    download_directory = os.path.expanduser("~/Pobrane")
    if not os.path.exists(download_directory):
        os.makedirs(download_directory)
    browser = webdriver.Chrome()
    countries = [
        "POL",
        # "ALB",
        # "ALG",
        # "AND",
        # "ANG",
        # "ARG",
        # "ARM",
        # "ARU",
        # "AUS",
        # "AUT",
        # "AZE",
        # "BAH",
        # "BRN",
        # "BAN",
        # "BAR",
        # "BLR",
        # "BEL",
        # "BIH",
        # "BIZ",
        # "BOL",
        # "BOT",
        # "BRA",
        # "IVB",
        # "BRU",
        # "BUL",
        # "BUR",
        # "BDI",
        # "CAM",
        # "CMR",
        # "CAN",
        # "CAF",
        # "CHI",
        # "CHN",
        # "TPE",
        # "COL",
        # "COM",
        # "CGO",
        # "CRC",
        # "CRO",
        # "CUB",
        # "CYP",
        # "CZE",
        # "DEN",
        # "DOM",
        # "ECU",
        # "EGY",
        # "ESA",
        # "ENG",
        # "EST",
        # "ETH",
        # "FAI",
        # "FID",
        # "FIJ",
        # "FIN",
        # "MKD",
        # "FRA",
        # "GAB",
        # "GAM",
        # "GBR",
        # "GEO",
        # "GER",
        # "GHA",
        # "GRE",
        # "GUM",
        # "GUA",
        # "GCI",
        # "GUY",
        # "HAI",
        # "HON",
        # "HKG",
        # "HUN",
        # "ISL",
        # "IND",
        # "INA",
        # "IRI",
        # "IRQ",
        # "IRL",
        # "ISR",
        # "ITA",
        # "IOM",
        # "CIV",
        # "JAM",
        # "JPN",
        # "JCI",
        # "JOR",
        # "KAZ",
        # "KEN",
        # "KGZ",
        # "KOS",
        # "KUW",
        # "LAO",
        # "LAT",
        # "LIB",
        # "LES",
        # "LBA",
        # "LIE",
        # "LTU",
        # "LUX",
        # "MAC",
        # "MAD",
        # "MAW",
        # "MAS",
        # "MDV",
        # "MLI",
        # "MLT",
        # "MTN",
        # "MRI",
        # "MEX",
        # "MDA",
        # "MNC",
        # "MGL",
        # "MNE",
        # "MAR",
        # "MOZ",
        # "MYA",
        # "NAM",
        # "NEP",
        # "NED",
        # "AHO",
        # "NZL",
        # "NCA",
        # "NGR",
        # "NOR",
        # "OMA",
        # "PAK",
        # "PLW",
        # "PLE",
        # "PAN",
        # "PNG",
        # "PAR",
        # "PER",
        # "PHI",
        # "POR",
        # "PUR",
        # "QAT",
        # "ROU",
        # "RUS",
        # "RWA",
        # "SMR",
        # "STP",
        # "KSA",
        # "SCO",
        # "SEN",
        # "SRB",
        # "SEY",
        # "SLE",
        # "SIN",
        # "SGP",
        # "SVK",
        # "SLO",
        # "SOL",
        # "SOM",
        # "SSD",
        # "RSA",
        # "KOR",
        # "ESP",
        # "SRI",
        # "SUD",
        # "SUR",
        # "SWZ",
        # "SWE",
        # "SUI",
        # "SYR",
        # "TJK",
        # "TAN",
        # "THA",
        # "TLS",
        # "TOG",
        # "TTO",
        # "TUN",
        # "TUR",
        # "TKM",
        # "UGA",
        # "UKR",
        # "UAE",
        # "USA",
        # "URU",
        # "ISV",
        # "UZB",
        # "VEN",
        # "VIE",
        # "WLS",
        # "YEM",
        # "ZAM",
        # "ZIM",
        # "CFR",
        # "FQE"

    ]

    with open("chessmanager.pgn","w") as output:
        for country in countries:
            try:
                browser.get(f"https://www.chessmanager.com/pl/tournaments/finished?country={country}")

                last_elem = browser.find_element(By.CSS_SELECTOR,
                                                 "body > div.pusher > div.ui.stackable.grid.container > "
                                                 "div.twelve.wide.column > div.ui.centered.pagination.menu > a:nth-child(8)")
                try:
                    last_elem_value = int(last_elem.text)
                except ValueError:
                    last_elem_value = 1

                for i in range(last_elem_value):
                    browser.get(
                        f"https://www.chessmanager.com/pl/tournaments/finished?country={country}&city=&city_radius=0&offset={i * 50}")
                    tournaments = [link.get_attribute("href") for link in browser.find_elements(By.TAG_NAME, "a")
                                   if re.match(r"https://www\.chessmanager\.com/[\w-]*/tournaments/\d+",
                                               link.get_attribute("href"))]
                    for tournament in tournaments:
                        browser.get(tournament)
                        try:
                            lichess_links = [link.get_attribute("href") for link in browser.find_elements(By.TAG_NAME, "a")
                                             if "lichess.org/broadcast/" in link.get_attribute("href")]
                            livechess_links = [link.get_attribute("href") for link in
                                               browser.find_elements(By.TAG_NAME, "a")
                                               if "view.livechesscloud.com" in link.get_attribute("href")]
                            for lichess_link in lichess_links:
                                print("lichess: " + lichess_link)
                                lichess_download(lichess_link, browser)

                            for livechess_link in livechess_links:
                                    print("livechess: " + livechess_link)
                                    output.write(scrap_livechess(livechess_link))
                        except TypeError:
                            pass
            except:
                pass
        while check_for_crdownload_files(download_directory):
            print("Waiting for downloads to complete...")
            time.sleep(10)
        try:
            input("chessmanager czeka na kliknięcie klawisza")
        except:
            pass
    browser.quit()


def check_for_crdownload_files(folder_path):
    crdownload_files = [f for f in os.listdir(folder_path) if f.endswith('.crdownload')]
    return len(crdownload_files) > 0


if __name__ == '__main__':
    main()
