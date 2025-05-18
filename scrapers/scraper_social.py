import re
import requests
import time
import csv
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

youtube_api_key = os.getenv("YOUTUBE_API_KEY")

URLS = {
    'Prawo i Sprawiedliwość': {
        'facebook': 'https://www.facebook.com/pisorgpl',
        'instagram': 'https://www.instagram.com/pisorgpl/',
        'twitter': 'https://twitter.com/PiS_org',
        'youtube': 'https://www.youtube.com/user/pisorgpl',
        'tiktok': 'https://www.tiktok.com/@pis_org'
    },
    'Koalicja Obywatelska': {
        'facebook': 'https://www.facebook.com/PlatformaObywatelska/',
        'instagram': 'https://www.instagram.com/platformaobywatelska/',
        'twitter': 'https://x.com/Platforma_org',
        'youtube': 'https://www.youtube.com/@PlatformaRP',
        'tiktok': 'https://www.tiktok.com/@platforma.obywatelska'
    },
    'Konfederacja': {
        'facebook': 'https://www.facebook.com/KONFEDERACJA2019',
        'instagram': 'https://www.instagram.com/konfederacja_/',
        'twitter': 'https://x.com/KONFEDERACJA_',
        'youtube': 'https://www.youtube.com/channel/UCn0TKgJb9EV6COKd8vlzJZQ',
        'tiktok': 'https://www.tiktok.com/@konfederacjawin'
    },
    'Razem': {
        'facebook': 'https://www.facebook.com/partiarazem',
        'instagram': 'https://www.instagram.com/partiarazem/',
        'twitter': 'https://x.com/partiarazem',
        'youtube': 'https://www.youtube.com/channel/UC0_HxMeYxDY-8-6NJ_umSVA',
        'tiktok': 'https://www.tiktok.com/@partiarazem'
    },
    'Nowa Lewica': {
        'facebook': 'https://www.facebook.com/NowaaLewica',
        'instagram': 'https://www.instagram.com/__lewica/',
        'twitter': 'https://x.com/__Lewica',
        'youtube': 'https://www.youtube.com/user/TVSLD',
        'tiktok': 'https://www.tiktok.com/@__lewica'
    },
}
def get_selenium_driver(wait=3):
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.implicitly_wait(wait)
    return driver

def get_soup(url, use_selenium=True, wait=3):
    if use_selenium:
        driver = get_selenium_driver(wait)
        driver.get(url)
        html = driver.page_source
        driver.quit()
    else:
        resp = requests.get(url)
        resp.raise_for_status()
        html = resp.text
    return BeautifulSoup(html, 'html.parser')

def parse_count(text: str) -> int:
    text = text.strip().lower().replace('\xa0', ' ')
    num = re.search(r'([\d\.,]+)', text).group(1).replace(',', '.')
    if 'mln' in text:
        return int(float(num) * 1_000_000)
    if 'tys' in text:
        return int(float(num) * 1_000)
    return int(num.replace('.', '').replace(' ', ''))

def get_channel_id_from_url(url):
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    if len(path_parts) == 0:
        return None
    if path_parts[0] == 'channel' and len(path_parts) > 1:
        return path_parts[1]
    elif path_parts[0] == 'user' and len(path_parts) > 1:
        username = path_parts[1]
        return get_channel_id_by_username(username)
    elif path_parts[0].startswith('@'):
        nickname = path_parts[0][1:]
        return get_channel_id_by_username(nickname)
    return None

def get_channel_id_by_username(username):
    url = f'https://www.googleapis.com/youtube/v3/channels?part=id&forUsername={username}&key={youtube_api_key}'
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    items = data.get('items', [])
    if items:
        return items[0]['id']
    return None

def scrape_facebook_followers(url):
    if not url:
        return None
    soup = get_soup(url)
    tag = soup.find('a', href=re.compile(r'/followers/'))
    if not tag:
        return None
    text = tag.get_text().strip().replace('\xa0', ' ')
    return parse_count(text)

def scrape_instagram_followers(url):
    if not url:
        return None
    username = url.rstrip('/').split('/')[-1]
    api = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'
    headers = {
        'User-Agent': 'Instagram 155.0.0.37.107',
        'Accept': 'application/json',
    }
    resp = requests.get(api, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    count = data['data']['user']['edge_followed_by']['count']
    return int(count)

def scrape_youtube_subscribers(url):
    if not url:
        return None
    channel_id = get_channel_id_from_url(url)
    if channel_id is None:
        return None
    api_url = f'https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={youtube_api_key}'
    resp = requests.get(api_url)
    resp.raise_for_status()
    data = resp.json()
    items = data.get('items', [])
    if not items:
        return None
    stats = items[0].get('statistics', {})
    subscriber_count = stats.get('subscriberCount')
    if subscriber_count is None:
        return None
    return int(subscriber_count)

def scrape_twitter_followers(url):
    if not url:
        return None
    driver = get_selenium_driver(wait=5)
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    container = soup.find('div', class_='css-175oi2r')
    if not container:
        return None
    link = container.find('a', href=re.compile(r'/verified_followers$'))
    if not link:
        return None
    number_span = link.find('span', class_='css-1jxf684')
    if not number_span:
        return None
    text = number_span.get_text(strip=True).lower()
    match = re.search(r'([\d\.,]+)', text)
    if not match:
        return None
    num_str = match.group(1).replace(',', '.')
    if 'tys' in text:
        return int(float(num_str) * 1_000)
    if 'mln' in text:
        return int(float(num_str) * 1_000_000)
    return int(float(num_str))

def scrape_tiktok_followers(url):
    if not url:
        return None
    driver = get_selenium_driver(wait=5)
    driver.get(url)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    strong = soup.find('strong', attrs={'data-e2e': 'followers-count'})
    if not strong:
        return None
    text = strong.get_text(strip=True).upper()
    match = re.match(r'([\d\.]+)([KM]?)', text)
    if not match:
        return None
    number = float(match.group(1))
    suffix = match.group(2)
    if suffix == 'K':
        number *= 1_000
    elif suffix == 'M':
        number *= 1_000_000
    return int(number)

def main():
    output_rows = []
    portals = ['facebook', 'instagram', 'twitter', 'youtube', 'tiktok']

    for party, links in URLS.items():
        for portal in portals:
            url = links.get(portal)
            try:
                if portal == 'facebook':
                    count = scrape_facebook_followers(url)
                elif portal == 'instagram':
                    count = scrape_instagram_followers(url)
                elif portal == 'twitter':
                    count = scrape_twitter_followers(url)
                elif portal == 'youtube':
                    count = scrape_youtube_subscribers(url)
                elif portal == 'tiktok':
                    count = scrape_tiktok_followers(url)
                else:
                    count = None
            except Exception as e:
                print(f"Błąd przy {party} {portal}: {e}")
                count = None
            
            output_rows.append({
                'Partia': party,
                'Portal': portal,
                'Followers': count if count is not None else 'Brak danych'
            })

    with open('data/socials/followers3.csv', 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Partia', 'Portal', 'Followers']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print("Zapisano dane do followers.csv")

if __name__ == '__main__':
    main()
