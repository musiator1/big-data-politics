import praw
import csv
from dotenv import load_dotenv
import os
from datetime import datetime, timezone
from pathlib import Path

SAVE_DIRECTORY = "data_reddit/"
Path(SAVE_DIRECTORY).mkdir(parents=True, exist_ok=True)

SUBREDDITS = ["Polska", "PolskaPolityka"] 
COMMENT_LIMIT = 10000
COMMENTS_PER_FILE = 1000
POSTS_TITLES = ["sejm", "wybory", "Trzaskowski", "Nawrocki", "Mentzen", "Zandberg", "Biejat", "Tusk", "Kaczyński", "Braun", "Prawo i Sprawiedliwość", "Koalicja Obywatelska", "Konfederacja", "Razem", "Nowa Lewica"]
COMMENT_BATCH_SIZE = 100
LOG_EVERY_N_COMMENTS = 50

load_dotenv(dotenv_path="../.env")

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

def write_comments_to_file(subreddit_name, comments_batch, file_index):
    filename = f"{subreddit_name}_comments_{file_index}.csv"
    filepath = os.path.join(SAVE_DIRECTORY, filename)
    with open(filepath, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Post Title", "Comment Author", "Comment Date (UTC)", "Comment"])
        for row in comments_batch:
            writer.writerow(row)
    print(f"[INFO] Saved {len(comments_batch)} comments to {filename}")

def main():
    for subreddit_name in SUBREDDITS:
        print(f"[INFO] Processing subreddit: {subreddit_name}")
        subreddit = reddit.subreddit(subreddit_name)

        total_comments = 0
        file_index = 1
        comment_batch = []

        for submission in subreddit.new(limit=None):
            if any(kw in submission.title.lower() for kw in POSTS_TITLES):
                submission.comments.replace_more(limit=0)
                for comment in submission.comments.list():
                    comment_date = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
                    comment_batch.append([submission.title, str(comment.author), comment_date, comment.body])
                    total_comments += 1

                    if total_comments % LOG_EVERY_N_COMMENTS == 0:
                        print(f"[{subreddit_name}] Total comments saved: {total_comments}")

                    if len(comment_batch) >= COMMENTS_PER_FILE:
                        write_comments_to_file(subreddit_name, comment_batch, file_index)
                        comment_batch.clear()
                        file_index += 1

                    if total_comments >= COMMENT_LIMIT:
                        break

            if total_comments >= COMMENT_LIMIT:
                break

        if comment_batch:
            write_comments_to_file(subreddit_name, comment_batch, file_index)

    print(f"[INFO] Finished processing subreddit: {subreddit_name}. Total comments saved: {total_comments}\n")

if __name__ == "__main__":
    main()
