import argparse
import os
from datetime import datetime, timedelta

import pandas as pd
from pytrends.request import TrendReq


def parse_args():
    parser = argparse.ArgumentParser(
        description='Google Trends scraper: pobiera dane dla 10 topiców, dla każdego dnia z zakresu, z ostatnich 30 dni.')
    parser.add_argument(
        '--start-date', '-s', required=True,
        help='Data początkowa w formacie YYYY-MM-DD')
    parser.add_argument(
        '--end-date', '-e', required=True,
        help='Data końcowa w formacie YYYY-MM-DD')
    parser.add_argument(
        '--out-dir', '-o', required=True,
        help='Katalog do zapisu plików CSV')
    return parser.parse_args()


def fetch_day_data(pytrends, topics_group, start_date, end_date):
    timeframe = f"{start_date} {end_date}"
    pytrends.build_payload(topics_group, timeframe=timeframe)
    df = pytrends.interest_over_time()
    if 'isPartial' in df.columns:
        df = df.drop(columns=['isPartial'])
    return df


def save_csv(df, out_dir, date_str):
    if not os.path.isdir(out_dir):
        raise NotADirectoryError(f"Katalog '{out_dir}' nie istnieje.")
    filename = f"google_trends__{date_str}.csv"
    path = os.path.join(out_dir, filename)
    df.to_csv(path, index=True)
    print(f"✔ Zapisano: {path}")


def main():
    args = parse_args()

    topics_all = [
        # Partie
        '/m/02kzyq', '/g/11fkmzf02z', '/g/11h022twt1', '/g/11bw4vk537', '/g/11bc68wty8',
        # Osoby
        '/g/11b5v50sld', '/g/1ym_l538q', '/g/11flvyzg2p', '/g/11bwgw5n02', '/g/11fnyvwz79',
    ]

    mapping = {
        # Partie
        '/m/02kzyq': 'Prawo i Sprawiedliwość',
        '/g/11fkmzf02z': 'Koalicja Obywatelska',
        '/g/11h022twt1': 'Konfederacja',
        '/g/11bw4vk537': 'Razem',
        '/g/11bc68wty8': 'Nowa Lewica',
        # Osoby
        '/g/11b5v50sld': 'Karol Nawrocki',
        '/g/1ym_l538q': 'Rafał Trzaskowski',
        '/g/11flvyzg2p': 'Sławomir Mentzen',
        '/g/11bwgw5n02': 'Adrian Zandberg',
        '/g/11fnyvwz79': 'Magdalena Biejat',
    }

    groups = [topics_all[:5], topics_all[5:]]

    start_date = datetime.fromisoformat(args.start_date)
    end_date = datetime.fromisoformat(args.end_date)

    pytrends = TrendReq(hl='pl-PL', tz=60)

    current = start_date
    while current <= end_date:
        target_day_str = current.strftime('%Y-%m-%d')
        range_start = (current - timedelta(days=30)).strftime('%Y-%m-%d')
        range_end = target_day_str

        print(f"Pobieranie zakresu: {range_start} → {range_end} (szukam {target_day_str})")

        dfs = []
        for group in groups:
            try:
                df_part = fetch_day_data(pytrends, group, range_start, range_end)
                dfs.append(df_part)
            except Exception as e:
                print(f"❌ Błąd dla grupy {group}: {e}")

        if dfs:
            df = pd.concat(dfs, axis=1)
            df = df.rename(columns=mapping)

            # Wybierz tylko wiersz z interesującym dniem
            df_day = df[df.index.strftime('%Y-%m-%d') == target_day_str]
            if df_day.empty:
                print(f"⚠ Brak danych dla {target_day_str} w zwróconym zakresie.")
            else:
                save_csv(df_day, args.out_dir, target_day_str)
        else:
            print(f"⚠ Brak danych dla {target_day_str} - brak poprawnych grup danych.")

        current += timedelta(days=1)


if __name__ == '__main__':
    main()
