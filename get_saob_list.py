#!/usr/bin/env python3

# Code from https://gist.github.com/salgo60/73dc99d71fcdeb75e4d69bd73b71acf9
# based on https://github.com/Torbacka/wordlist/blob/master/client.py
from datetime import datetime
import requests
from bs4 import BeautifulSoup

data = {
    'action': 'myprefix_scrollist',
    'unik': '0',
    'dir': 'ned',
    'dict': 'saob'
}
headers = {
    'User-Agent': 'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0'
}
date = datetime.today().strftime("%Y-%m-%d")
print(date)
file = open(f"saob_{date}.csv", "a")


def main():
    for i in range(1, 20000):
        if i % 10 == 0:
            print(i)
        response = requests.post('https://svenska.se/wp-admin/admin-ajax.php', data=data, headers=headers)
        unik = parse_response(response)
        if unik == -1:
            break
        data['unik'] = unik


# Parse the html response from svenska.se
def parse_response(response):
    soup = BeautifulSoup(response.text, features="html.parser")
    links = soup.findAll("a", class_='slank')
    if len(links) == 0:
        return -1
    for link in links[1:]:
        gather_information(link)
    div = soup.findAll("div", class_='pilned')
    return div[0].a['unik']


def gather_information(link):
    span = link.findAll('span')
    file.write(span[0].getText().strip() +
               "," + span[1].getText().strip() +
               "," + span[2].getText().strip() +
               "," + span[3].getText().strip() +
               "," + link['href'].strip() + "\n")


if __name__ == '__main__':
    main()
