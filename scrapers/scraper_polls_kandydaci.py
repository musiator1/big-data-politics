import re
from datetime import datetime
from io import StringIO

import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup


# Method 1: Disable SSL warnings and verification (quick fix)
def fetch_presidential_polls_wide_no_verify():
    """Quick fix: Disable SSL verification"""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    url = "https://ewybory.eu/wybory-prezydenckie-2025-polska/sondaze-prezydenckie/"
    headers = {"User-Agent": "Mozilla/5.0"}

    # Disable SSL verification
    response = requests.get(url, headers=headers, verify=False)
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")

    df_support = pd.read_html(StringIO(str(table)))[0]
    meta_col = df_support.columns[0]
    candidate_cols = df_support.columns[1:]

    rows = table.find_all('tr')
    meta = []
    for row in rows:
        cell = row.find('td', class_='polls_candidate')
        if not cell:
            continue
        inst = cell.find('span', class_='polls_candidate_link').text.strip()
        sample_text = cell.find('span', class_='polls_candidate_sample').text.strip()
        sample = None
        m = re.search(r"N=(\d+)", sample_text)
        if m:
            sample = int(m.group(1))
        date_text = cell.find('span', class_='polls_candidate_date').text.strip()
        date_match = re.search(r"(\d{1,2})(?:-\d{1,2})?\.(\d{2})", date_text)
        if date_match:
            day, month = date_match.groups()
            date = datetime.strptime(f"{day}.{month}.2025", "%d.%m.%Y")
        else:
            date = pd.NaT
        meta.append({'Institute': inst, 'Sample': sample, 'Date': date})

    df_meta = pd.DataFrame(meta)

    def parse_support(x):
        if pd.isna(x) or x in ['—', '–']:
            return pd.NA

        # Convert to string to handle various input types
        x_str = str(x).strip()

        # Handle empty strings
        if not x_str:
            return pd.NA

        # Handle values starting with '<'
        if x_str.startswith('<'):
            try:
                return float(x_str[1:])
            except ValueError:
                return pd.NA

        # Handle values starting with '=' (like '=0')
        if x_str.startswith('='):
            try:
                return float(x_str[1:])
            except ValueError:
                return pd.NA

        # Handle regular numeric values
        try:
            return float(x_str)
        except ValueError:
            # If conversion fails, print the problematic value for debugging
            print(f"Warning: Could not parse value: '{x_str}'")
            return pd.NA

    for col in candidate_cols:
        df_support[col] = df_support[col].apply(parse_support)

    df_wide = pd.concat([
        df_meta.reset_index(drop=True),
        df_support[candidate_cols].reset_index(drop=True)
    ], axis=1)

    return df_wide


if __name__ == '__main__':
    df_wide = fetch_presidential_polls_wide_no_verify()
    df_wide.to_csv('data/polls/polls_kandydaci.csv', index=False)
