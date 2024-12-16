from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup


def main():
    url = "https://live.chessbase.com/en/History"
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        links = [
            a['href']
            for a in soup.find_all('a', href=True)
            if "Games?" in a['href']
        ]

        print("Extracted links:")
        with open("chessbase.pgn",'w') as output:
            for link in links:
                tournament_link = f"https://live.chessbase.com{link}"
                print(tournament_link)
                parsed_url = urlparse(tournament_link)

                query_params = parse_qs(parsed_url.query)
                pgn_url = f"https://liveserver.chessbase.com:6009/pgn/{query_params['id'][0]}/0/0/all.pgn"
                res = requests.get(pgn_url)
                output.write(res.text)
    else:
        print(f"Failed to fetch the page. Status code: {response.status_code}")


if __name__ == '__main__':
    main()
