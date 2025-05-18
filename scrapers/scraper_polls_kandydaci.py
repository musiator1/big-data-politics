import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
from io import StringIO

# Funkcja pobierająca sondaże i zwracająca DataFrame w formacie wide

def fetch_presidential_polls_wide():
    url = "https://ewybory.eu/wybory-prezydenckie-2025-polska/sondaze-prezydenckie/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")

    # 1. Pobranie wsparcia kandydatów przez pandas (wszystkie kolumny poza pierwszą)
    df_support = pd.read_html(StringIO(str(table)))[0]
    # Pierwsza kolumna to meta, reszta to kandydaci
    meta_col = df_support.columns[0]
    candidate_cols = df_support.columns[1:]

    # 2. Metadane (instytut, próbka, data) z HTML
    rows = table.find_all('tr')
    meta = []
    for row in rows:
        cell = row.find('td', class_='polls_candidate')
        if not cell:
            continue
        inst = cell.find('span', class_='polls_candidate_link').text.strip()
        sample_text = cell.find('span', class_='polls_candidate_sample').text.strip()
        # parsowanie próby
        sample = None
        m = re.search(r"N=(\d+)", sample_text)
        if m:
            sample = int(m.group(1))
        # parsowanie daty (pierwszy dzień z zakresu)
        date_text = cell.find('span', class_='polls_candidate_date').text.strip()
        date_match = re.search(r"(\d{1,2})(?:-\d{1,2})?\.(\d{2})", date_text)
        if date_match:
            day, month = date_match.groups()
            date = datetime.strptime(f"{day}.{month}.2025", "%d.%m.%Y")
        else:
            date = pd.NaT
        meta.append({'Institute': inst, 'Sample': sample, 'Date': date})

    df_meta = pd.DataFrame(meta)

    # 3. Czyszczenie i konwersja wsparcia kandydatów na float
    def parse_support(x):
        if pd.isna(x) or x in ['—', '–']:
            return pd.NA
        if isinstance(x, str) and x.startswith('<'):
            # np. '<0.5' -> 0.5
            return float(x[1:])
        return float(x)

    for col in candidate_cols:
        df_support[col] = df_support[col].apply(parse_support)

    # 4. Połączenie meta i wsparcia
    df_wide = pd.concat([
        df_meta.reset_index(drop=True),
        df_support[candidate_cols].reset_index(drop=True)
    ], axis=1)

    return df_wide


if __name__ == '__main__':
    df_wide = fetch_presidential_polls_wide()
    df_wide.to_csv('data/polls/polls_kandydaci.csv', index=False)
