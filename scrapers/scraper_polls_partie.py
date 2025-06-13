import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
import os
import re
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def parse_poll_row(text):
    # Publikator
    publikator_match = re.match(r'^(.*?)\s*N=', text)
    publikator = publikator_match.group(1).strip() if publikator_match else None

    # Liczność próby
    liczba_match = re.search(r'N=(\d+)', text)
    liczba = int(liczba_match.group(1)) if liczba_match else None

    # Data (ostatni dzień badania)
    date_match = re.search(r'Termin:\s*([\d\-.]+)', text)
    data_str = date_match.group(1) if date_match else None

    data = None
    if data_str:
        # jeśli zakres dat np. "12-13.05"
        if '-' in data_str:
            last = data_str.split('-')[-1]
        else:
            last = data_str
        try:
            dzien, miesiac = map(int, last.split('.'))
            data = pd.Timestamp(year=2025, month=miesiac, day=dzien)
        except:
            pass

    return publikator, liczba, data

def scrape_poll_data(url: str, output_file: str):
    print(f"Pobieranie danych z: {url}")

    # Add headers and disable SSL verification
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')
    target_div = soup.find("div", id="2025")
    if not target_div:
        print("Nie znaleziono diva o id=2025.")
        return

    tables = pd.read_html(StringIO(str(target_div)))
    if not tables:
        print("Nie znaleziono żadnych tabel.")
        return

    df = tables[0]
    first_col = df.columns[0]
    df.rename(columns={first_col: "Opis"}, inplace=True)

    # Parsowanie: publikator, liczność, data
    df[["Publikator", "Liczność", "Data"]] = df["Opis"].apply(
        lambda x: pd.Series(parse_poll_row(str(x)))
    )

    df.drop(columns=["Opis"], inplace=True)

    # Przeniesienie kolumn
    fixed_cols = ["Data", "Publikator", "Liczność"]
    party_cols = [col for col in df.columns if col not in fixed_cols]
    df = df[fixed_cols + party_cols]

    # Czyszczenie wartości partyjnych
    for col in party_cols:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace("%", "", regex=False)
            .str.strip()
            .replace("—", None)
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[df["Data"].notnull()]
    df.sort_values("Data", ascending=False, inplace=True)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"Zapisano {len(df)} wierszy do: {output_file}")

if __name__ == "__main__":
    URL = "https://ewybory.eu/sondaze/"
    OUTPUT = "./data/polls/polls_data.csv"  # Fixed typo: pools -> polls
    scrape_poll_data(URL, OUTPUT)