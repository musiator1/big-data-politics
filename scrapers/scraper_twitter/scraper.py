import json
import logging
import random
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TwitterPoliticalScraper:
    def __init__(self):
        # ========================= KONFIGURACJA KONTA =========================
        self.EMAIL = ""
        self.PASSWORD = ""
        self.USERNAME = ""

        # ======================= KONFIGURACJA SCRAPOWANIA ====================
        # Set this to scan a specific number of days ago (0 = yesterday, 1 = day before yesterday, etc.)
        self.DAYS_AGO = 0  # Change this to debug different days (0=yesterday, 1=2 days ago, etc.)
        self.MAX_TWEETS_PER_SEARCH = 50  # Increased limit
        self.MAX_SCROLL_ATTEMPTS = 10  # More scrolling attempts
        self.SCROLL_PAUSE_TIME = 3  # Longer pause between scrolls

        # ======================== PARTIE POLITYCZNE ==========================
        self.political_parties = [
            "PiS",
            "Prawo i Sprawiedliwość",
            "PO",
            "Platforma Obywatelska",
            "KO",
            "Koalicja Obywatelska",
            "Konfederacja",
            "Lewica",
            "PSL",
            "Polskie Stronnictwo Ludowe",
            "Polska 2050",
            "Trzecia Droga",
            "Razem",
        ]

        self.driver = None
        self.setup_logging()

    def setup_logging(self):
        """Konfiguracja logowania"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('twitter_political_scraper.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self, headless=True):
        """Konfiguracja przeglądarki Chrome z ustawieniami angielskimi"""
        chrome_options = Options()

        # Podstawowe ustawienia
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # JĘZYK ANGIELSKI - bardzo ważne!
        chrome_options.add_argument("--lang=en-US")
        chrome_options.add_experimental_option('prefs', {
            'intl.accept_languages': 'en-US,en',
            'profile.default_content_setting_values.notifications': 2
        })

        # User Agent
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Tryb headless (bez okna przeglądarki)
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")

        # Dodatkowe ustawienia dla stabilności
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        # Removed --disable-images to load all content

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        self.logger.info(f"Przeglądarka uruchomiona (headless: {headless})")

    def login_to_twitter(self):
        """Logowanie do Twittera z obsługą weryfikacji"""
        try:
            self.logger.info("Rozpoczynam logowanie do Twittera...")

            # Idź na stronę logowania z parametrem języka
            self.driver.get("https://twitter.com/i/flow/login?lang=en")
            time.sleep(5)

            # Sprawdź czy strona się załadowała poprawnie
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "input"))
                )
            except TimeoutException:
                self.logger.error("Nie udało się załadować strony logowania")
                return False

            # Wpisz email
            self.logger.info("Wprowadzam email...")
            try:
                email_input = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
                )
                email_input.clear()
                email_input.send_keys(self.EMAIL)
                email_input.send_keys(Keys.ENTER)
                time.sleep(3)
            except TimeoutException:
                self.logger.error("Nie znaleziono pola email")
                return False

            # Sprawdź czy jest dodatkowa weryfikacja (username)
            try:
                self.logger.info("Sprawdzam czy jest dodatkowa weryfikacja...")
                verification_input = WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]'))
                )
                self.logger.info("Wykryto weryfikację - wprowadzam username")
                verification_input.clear()
                verification_input.send_keys(self.USERNAME)
                verification_input.send_keys(Keys.ENTER)
                time.sleep(3)
            except TimeoutException:
                self.logger.info("Brak dodatkowej weryfikacji")

            # Wpisz hasło
            self.logger.info("Wprowadzam hasło...")
            try:
                password_input = WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
                )
                password_input.clear()
                password_input.send_keys(self.PASSWORD)
                password_input.send_keys(Keys.ENTER)
            except TimeoutException:
                self.logger.error("Nie znaleziono pola hasła")
                return False

            # Sprawdź czy logowanie się powiodło
            try:
                WebDriverWait(self.driver, 20).until(
                    EC.any_of(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, '[data-testid="SideNav_AccountSwitcher_Button"]')),
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="primaryColumn"]')),
                        EC.url_contains('/home')
                    )
                )
                self.logger.info("Logowanie zakończone sukcesem!")
                time.sleep(3)
                return True
            except TimeoutException:
                self.logger.error("Nie udało się potwierdzić logowania")
                return False

        except Exception as e:
            self.logger.error(f"Błąd podczas logowania: {str(e)}")
            return False

    def get_target_date(self):
        """Get the target date for scanning (yesterday - DAYS_AGO)"""
        target_date = datetime.now() - timedelta(days=1 + self.DAYS_AGO)
        return target_date

    def build_search_query(self, term):
        """Budowanie zapytania wyszukiwania z filtrami dla konkretnego dnia"""
        # Get target date
        target_date = self.get_target_date()
        next_date = target_date + timedelta(days=1)

        # Build query with exact date range
        query = f'"{term}" lang:pl since:{target_date.strftime("%Y-%m-%d")} until:{next_date.strftime("%Y-%m-%d")}'

        return query

    def search_and_scrape(self, search_term):
        """Wyszukiwanie i scrapowanie tweetów dla danego terminu z lepszym scrollowaniem"""
        tweets = []

        try:
            # Zbuduj zapytanie
            query = self.build_search_query(search_term)

            # Use Latest tab for more results
            search_url = f"https://twitter.com/search?q={query}&src=typed_query&f=live"

            self.logger.info(f"Wyszukuję: {search_term}")
            self.logger.info(f"Query: {query}")

            self.driver.get(search_url)
            time.sleep(5)

            # Sprawdź czy strona się załadowała poprawnie
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]')),
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="emptyState"]')),
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="primaryColumn"]'))
                    )
                )
            except TimeoutException:
                self.logger.warning(f"Timeout podczas ładowania wyników dla: {search_term}")
                return tweets

            # Sprawdź czy są jakieś wyniki
            if self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="emptyState"]'):
                self.logger.info(f"Brak wyników dla: {search_term}")
                return tweets

            # Enhanced scrolling with more aggressive collection
            last_height = 0
            no_new_tweets_count = 0
            scroll_attempts = 0

            while len(tweets) < self.MAX_TWEETS_PER_SEARCH and scroll_attempts < self.MAX_SCROLL_ATTEMPTS:
                # Collect all tweet elements on current view
                tweet_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweet"]')

                tweets_found_in_batch = 0
                for tweet_element in tweet_elements:
                    if len(tweets) >= self.MAX_TWEETS_PER_SEARCH:
                        break

                    tweet_data = self.extract_tweet_data(tweet_element, search_term)
                    if tweet_data and not self.is_duplicate(tweet_data, tweets):
                        tweets.append(tweet_data)
                        tweets_found_in_batch += 1
                        if len(tweets) % 50 == 0:  # Log every 50 tweets
                            self.logger.info(f"Zebrano {len(tweets)} tweetów dla {search_term}")

                # More aggressive scrolling
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(self.SCROLL_PAUSE_TIME)

                # Try additional scroll techniques
                if tweets_found_in_batch == 0:
                    # Try scrolling by smaller increments
                    for _ in range(3):
                        self.driver.execute_script("window.scrollBy(0, 1000);")
                        time.sleep(1)

                # Check if page height changed
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    no_new_tweets_count += 1
                    if no_new_tweets_count >= 3:
                        self.logger.info(f"Koniec wyników dla: {search_term}")
                        break
                else:
                    no_new_tweets_count = 0
                    last_height = new_height

                scroll_attempts += 1

            self.logger.info(f"Zebrano {len(tweets)} tweetów dla: {search_term}")

        except Exception as e:
            self.logger.error(f"Błąd podczas scrapowania {search_term}: {str(e)}")

        return tweets

    def extract_tweet_data(self, tweet_element, search_term):
        """Wyciągnij dane z elementu tweeta"""
        try:
            # Tekst tweeta
            try:
                text_element = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                text = text_element.text.strip()
            except NoSuchElementException:
                return None

            # Skip if text is empty or too short
            if not text or len(text) < 3:
                return None

            # Autor
            try:
                author_elements = tweet_element.find_elements(By.CSS_SELECTOR, '[data-testid="User-Name"] span')
                author = author_elements[0].text.strip() if author_elements else "Unknown"
            except:
                author = "Unknown"

            # Handle (@username)
            try:
                handle_element = tweet_element.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"] a')
                href = handle_element.get_attribute('href')
                handle = href.split('/')[-1] if href else "unknown"
            except:
                handle = "unknown"

            # Timestamp
            try:
                time_element = tweet_element.find_element(By.CSS_SELECTOR, 'time')
                timestamp = time_element.get_attribute('datetime')
            except:
                timestamp = datetime.now().isoformat()

            # Statystyki
            likes = retweets = replies = 0
            try:
                stat_buttons = tweet_element.find_elements(By.CSS_SELECTOR, '[role="group"] [role="button"]')
                for button in stat_buttons:
                    aria_label = button.get_attribute('aria-label') or ""
                    if 'like' in aria_label.lower():
                        likes = self.extract_number(aria_label)
                    elif 'repost' in aria_label.lower() or 'retweet' in aria_label.lower():
                        retweets = self.extract_number(aria_label)
                    elif 'repl' in aria_label.lower():
                        replies = self.extract_number(aria_label)
            except:
                pass

            # Link do tweeta
            try:
                time_link = tweet_element.find_element(By.CSS_SELECTOR, 'time').find_element(By.XPATH, '..')
                tweet_url = time_link.get_attribute('href')
            except:
                tweet_url = f"https://twitter.com/{handle}/status/unknown"

            return {
                'text': text,
                'author': author,
                'handle': handle,
                'timestamp': timestamp,
                'likes': likes,
                'retweets': retweets,
                'replies': replies,
                'tweet_url': tweet_url,
                'search_term': search_term,
                'scraped_at': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.debug(f"Błąd przy ekstraktowaniu tweeta: {str(e)}")
            return None

    def extract_number(self, text):
        """Wyciągnij liczbę z tekstu"""
        import re
        text = text.replace(',', '')
        numbers = re.findall(r'(\d+(?:\.\d+)?)\s*([KkMm]?)', text)
        if numbers:
            num, suffix = numbers[0]
            num = float(num)
            if suffix.lower() == 'k':
                num *= 1000
            elif suffix.lower() == 'm':
                num *= 1000000
            return int(num)
        return 0

    def is_duplicate(self, tweet_data, existing_tweets):
        """Sprawdź czy tweet już istnieje w liście"""
        for existing in existing_tweets:
            if (existing['text'] == tweet_data['text'] and
                    existing['handle'] == tweet_data['handle']):
                return True
        return False

    def save_to_json(self, tweets, target_date):
        """Zapisz tweety do pliku JSON z nazwą bazującą na dacie skanowania"""
        if not tweets:
            self.logger.warning("Brak tweetów do zapisania")
            return

        # Format filename as date being scanned
        filename = f"tweets_{target_date.strftime('%Y-%m-%d')}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Zapisano {len(tweets)} tweetów do: {filename}")

    def run_scraping(self, headless=True):
        """Główna funkcja scrapowania"""
        all_tweets = []
        target_date = self.get_target_date()

        try:
            # Uruchom przeglądarkę
            self.setup_driver(headless=headless)

            # Zaloguj się
            if not self.login_to_twitter():
                self.logger.error("Nie udało się zalogować!")
                return

            # Przygotuj wszystkie terminy do wyszukiwania
            all_search_terms = self.political_parties

            self.logger.info(
                f"Rozpoczynam scrapowanie {len(all_search_terms)} terminów dla daty: {target_date.strftime('%Y-%m-%d')}")

            # Scrapuj każdy termin
            for i, term in enumerate(all_search_terms, 1):
                self.logger.info(f"Progress: {i}/{len(all_search_terms)} - {term}")

                tweets = self.search_and_scrape(term)
                all_tweets.extend(tweets)

                # Przerwa między wyszukiwaniami
                if i < len(all_search_terms):
                    wait_time = random.uniform(4, 8)  # Longer delays to avoid rate limiting
                    self.logger.info(f"Czekam {wait_time:.1f}s przed następnym wyszukiwaniem...")
                    time.sleep(wait_time)

            # Usuń duplikaty
            unique_tweets = []
            seen = set()
            for tweet in all_tweets:
                identifier = f"{tweet['text']}_{tweet['handle']}"
                if identifier not in seen:
                    unique_tweets.append(tweet)
                    seen.add(identifier)

            # Zapisz wyniki
            if unique_tweets:
                self.save_to_json(unique_tweets, target_date)
                self.logger.info(
                    f"PODSUMOWANIE: Zebrano {len(unique_tweets)} unikalnych tweetów z dnia {target_date.strftime('%Y-%m-%d')}")

                # Log stats per search term
                term_stats = {}
                for tweet in unique_tweets:
                    term = tweet['search_term']
                    term_stats[term] = term_stats.get(term, 0) + 1

                self.logger.info("Statystyki per termin wyszukiwania:")
                for term, count in sorted(term_stats.items(), key=lambda x: x[1], reverse=True):
                    self.logger.info(f"  {term}: {count} tweetów")
            else:
                self.logger.warning("Nie znaleziono żadnych tweetów!")

        except Exception as e:
            self.logger.error(f"Błąd głównej funkcji: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("Przeglądarka zamknięta")


def main():
    """Główna funkcja"""
    scraper = TwitterPoliticalScraper()

    # =================== KONFIGURACJA URUCHOMIENIA ===================
    HEADLESS_MODE = False  # True = bez okna przeglądarki, False = z oknem

    target_date = scraper.get_target_date()

    print("Twitter Political Scraper")
    print("=" * 50)
    print(f"Konto: {scraper.EMAIL}")
    print(f"Data skanowania: {target_date.strftime('%Y-%m-%d')} ({scraper.DAYS_AGO} dni temu)")
    print(f"Max tweetów na wyszukiwanie: {scraper.MAX_TWEETS_PER_SEARCH}")
    print(f"Liczba terminów: {len(scraper.political_parties)}")
    print(f"Tryb headless: {HEADLESS_MODE}")
    print("=" * 50)

    # Uruchom scrapowanie
    scraper.run_scraping(headless=HEADLESS_MODE)


if __name__ == "__main__":
    main()
