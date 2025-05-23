import praw
import csv
from dotenv import load_dotenv
import os

SAVE_DIRECTORY = "data/"
POSTS_TITLES = ["polityka", "polityk", "rząd", "sejm", "wybory", "Trzaskowski", "Nawrocki", "Mentzen", "Zandberg", "Biejat", "Prawo i     Sprawiedliwość", "Koalicja Obywatelska", "Konfederacja", "Razem", "Nowa Lewica"]
COMMENT_BATCH_SIZE = 100
LOG_EVERY_N_COMMENTS = 10

load_dotenv(dotenv_path="../.env")

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

total_comments = 0

with open(os.path.join(SAVE_DIRECTORY, 'reddit_comments.csv'), mode='w', encoding='utf-8', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["Tytuł posta", "Autor komentarza", "Komentarz"])

    subreddit = reddit.subreddit("Polska")

    for submission in subreddit.new(limit=COMMENT_BATCH_SIZE):
        if any(kw in submission.title.lower() for kw in POSTS_TITLES):
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list():
                writer.writerow([submission.title, comment.author, comment.body])
                total_comments += 1
                if total_comments % LOG_EVERY_N_COMMENTS == 0:
                    print(f"[INFO] Saved {total_comments} comments...")
                writer.writerow(["", "", "-----"])

print(f"[INFO] Process finished. Saved {total_comments} comments.")