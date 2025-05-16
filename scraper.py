import argparse
import platform
import subprocess
import os
import shutil
import json
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
URS_PATH = SCRIPT_DIR / 'URS'
URS_VENV_PYTHON = (
    URS_PATH / '.venv' / 'Scripts' / 'python.exe'
    if platform.system() == 'Windows'
    else URS_PATH / '.venv' / 'bin' / 'python'
)
SCRAPES_DIR = SCRIPT_DIR / 'scrapes'
DB_PATH = SCRIPT_DIR / 'reddit_data.db'


def clear_scrapes_folder(scrapes_root: Path):
    if scrapes_root.exists():
        for child in scrapes_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # cursor.executescript("""
    #     DROP TABLE IF EXISTS reddit_post_keywords;
    #     DROP TABLE IF EXISTS reddit_comment_keywords;
    #     DROP TABLE IF EXISTS reddit_post;
    #     DROP TABLE IF EXISTS reddit_comment;
    # """)

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reddit_post (
            id TEXT PRIMARY KEY,
            title TEXT,
            selftext TEXT,
            num_comments INT,
            author TEXT,
            created_utc REAL,
            subreddit TEXT,
            url TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reddit_comment (
            id TEXT PRIMARY KEY,
            comment TEXT,
            author TEXT,
            created_utc REAL,
            parent_post_id TEXT,
            subreddit TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reddit_post_keywords (
            post_id TEXT,
            keyword TEXT,
            PRIMARY KEY (post_id, keyword),
            FOREIGN KEY (post_id) REFERENCES reddit_post(id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reddit_comment_keywords (
            comment_id TEXT,
            keyword TEXT,
            PRIMARY KEY (comment_id, keyword),
            FOREIGN KEY (comment_id) REFERENCES reddit_comment(id)
        )
    ''')

    conn.commit()
    conn.close()


def run_reddit_scraper(subreddits, keywords):
    clear_scrapes_folder(SCRAPES_DIR)

    for subreddit in subreddits:
        for keyword in keywords:
            command = [
                str(URS_VENV_PYTHON), '-m', 'urs.Urs',
                '-r', subreddit,
                's', keyword
            ]

            print(f"[INFO] Running Reddit scraper: {' '.join(command)}")
            subprocess.run(
                command,
                cwd=URS_PATH,
                input='y\n',
                text=True
            )

    posts_to_scrape = []
    all_jsons = list(SCRAPES_DIR.rglob("*.json"))
    for json_file in all_jsons:
        if classify_urs_output(json_file) in ('subreddit_post',):
            posts_to_scrape.extend(insert_subreddit_posts(json_file, keywords))

    scraped = set()
    for post in posts_to_scrape:
        if post['id'] not in scraped:
            print(f"[INFO] Scraping comments for post: {post['id']}")
            scrape_comments_only(post['url'], post['num_comments'])
            scraped.add(post['id'])

    process_jsons(SCRAPES_DIR, keywords)



def scrape_comments_only(url: str, num_comments: int):
    command = [
        str(URS_VENV_PYTHON), '-m', 'urs.Urs',
        '-c', url, str(num_comments or 100)
    ]
    subprocess.run(command, cwd=URS_PATH)


def process_jsons(scrapes_root: Path, keywords):
    jsons = list(scrapes_root.rglob("*.json"))
    for json_file in jsons:
        kind = classify_urs_output(json_file)
        if kind == 'comment':
            insert_comments(json_file, keywords)


def classify_urs_output(json_path: Path):
    with open(json_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return 'unknown'

    if not data:
        return 'empty'

    if isinstance(data, dict) and 'data' in data:
        if isinstance(data['data'], list):
            if len(data['data']) > 0 and 'title' in data['data'][0] and 'selftext' in data['data'][0]:
                return 'subreddit_post'
            else:
                return 'empty_post_list'
        elif isinstance(data['data'], dict) and 'comments' in data['data']:
            return 'comment'

    return 'unknown'



def insert_subreddit_posts(json_path: Path, keywords):
    result_posts = []
    with sqlite3.connect(DB_PATH) as conn, open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        subreddit = json_data.get("scrape_settings", {}).get("subreddit", "")
        posts = json_data.get("data", [])
        for post in posts:
            post_id = post.get('id')
            url = f"https://www.reddit.com{post.get('permalink')}"
            num_comments = post.get('num_comments')
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO reddit_post (
                        id, title, selftext, num_comments, author, created_utc, subreddit, url
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post_id,
                    post.get('title'),
                    post.get('selftext'),
                    num_comments,
                    post.get('author'),
                    post.get('created_utc'),
                    subreddit,
                    url,
                ))

                matched_keywords = [
                    kw for kw in keywords
                    if kw.lower() in post.get('title', '').lower()
                    or kw.lower() in post.get('selftext', '').lower()
                ]
                for kw in matched_keywords:
                    conn.execute('''
                        INSERT OR IGNORE INTO reddit_post_keywords (post_id, keyword)
                        VALUES (?, ?)
                    ''', (post_id, kw))

                if matched_keywords:
                    result_posts.append({
                        'id': post_id,
                        'url': url,
                        'num_comments': num_comments
                    })

            except Exception as e:
                print(f"[ERROR] Failed to insert post {post_id}: {e}")
    return result_posts


def flatten_comments(comments, parent_post_id, subreddit):
    flat = []
    stack = list(comments)

    while stack:
        comment = stack.pop()
        flat.append({
            'id': comment.get('id'),
            'body': comment.get('body'),
            'author': comment.get('author'),
            'created_utc': comment.get('created_utc'),
            'parent_post_id': parent_post_id,
            'subreddit': subreddit
        })
        # Push replies to stack for processing
        stack.extend(comment.get('replies', []))
    return flat


def insert_comments(json_path: Path, keywords):
    with sqlite3.connect(DB_PATH) as conn, open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        comments = json_data.get("data", {}).get("comments", [])
        metadata = json_data.get("data", {}).get("submission_metadata", {})
        subreddit = metadata.get("subreddit", "")
        parent_post_id = json_data.get("scrape_settings", {}).get("url", "").split("/")[-3]

        flat_comments = flatten_comments(comments, parent_post_id, subreddit)

        for comment in flat_comments:
            try:
                conn.execute('''
                    INSERT OR IGNORE INTO reddit_comment (id, comment, author, created_utc, parent_post_id, subreddit)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    comment['id'],
                    comment['body'],
                    comment['author'],
                    comment['created_utc'],
                    comment['parent_post_id'],
                    comment['subreddit']
                ))

                matched_keywords = [
                    kw for kw in keywords if kw.lower() in (comment['body'] or '').lower()
                ]
                for kw in matched_keywords:
                    conn.execute('''
                        INSERT OR IGNORE INTO reddit_comment_keywords (comment_id, keyword)
                        VALUES (?, ?)
                    ''', (comment['id'], kw))

            except Exception as e:
                print(f"[ERROR] Failed to insert comment {comment['id']}: {e}")

    with sqlite3.connect(DB_PATH) as conn, open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        comments = json_data.get("data", {}).get("comments", [])
        subreddit = json_data.get("data", {}).get("submission_metadata", {}).get("subreddit", "")

        for comment in comments:
            link_id = comment.get("link_id", "")  # e.g., 't3_abc123'
            parent_id = comment.get("parent_id", "")
            if not link_id.startswith("t3_"):
                continue

            # Only include top-level comments (i.e., those replying directly to the post)
            if parent_id != link_id:
                continue

            parent_post_id = link_id[3:]  # Strip 't3_' prefix

            try:
                conn.execute('''
                    INSERT OR IGNORE INTO reddit_comment (id, comment, author, created_utc, parent_post_id, subreddit)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    comment.get('id'),
                    comment.get('body'),
                    comment.get('author'),
                    comment.get('created_utc'),
                    parent_post_id,
                    subreddit
                ))

                matched_keywords = [kw for kw in keywords if kw.lower() in comment.get('body', '').lower()]
                for kw in matched_keywords:
                    conn.execute('''
                        INSERT OR IGNORE INTO reddit_comment_keywords (comment_id, keyword)
                        VALUES (?, ?)
                    ''', (comment.get('id'), kw))

            except Exception as e:
                print(f"[ERROR] Failed to insert comment {comment.get('id')}: {e}")

    with sqlite3.connect(DB_PATH) as conn, open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        comments = json_data.get("data", {}).get("comments", [])
        metadata = json_data.get("data", {}).get("submission_metadata", {})
        subreddit = metadata.get("subreddit", "")
        submission_name = metadata.get("name", "")
        parent_post_id = submission_name[3:] if submission_name.startswith("t3_") else None

        for comment in comments:
            if comment.get("parent_id") != submission_name:
                continue  # Skip replies to comments

            try:
                conn.execute('''
                    INSERT OR IGNORE INTO reddit_comment (id, comment, author, created_utc, parent_post_id, subreddit)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    comment.get('id'),
                    comment.get('body'),
                    comment.get('author'),
                    comment.get('created_utc'),
                    parent_post_id,
                    subreddit
                ))

                matched_keywords = [kw for kw in keywords if kw.lower() in comment.get('body', '').lower()]
                for kw in matched_keywords:
                    conn.execute('''
                        INSERT OR IGNORE INTO reddit_comment_keywords (comment_id, keyword)
                        VALUES (?, ?)
                    ''', (comment.get('id'), kw))

            except Exception as e:
                print(f"[ERROR] Failed to insert comment {comment.get('id')}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Multi-platform scraper CLI.")
    subparsers = parser.add_subparsers(dest='platform', required=True)

    reddit_parser = subparsers.add_parser('reddit', help='Run Reddit scraper')
    reddit_parser.add_argument('-s', '--subreddits', nargs='+', required=True,
                           help="One or more subreddits to search")
    reddit_parser.add_argument('-k', '--keywords', nargs='+', required=True,
                           help="One or more keywords to search for")


    args = parser.parse_args()

    if args.platform == 'reddit':
        run_reddit_scraper(args.subreddits, args.keywords)


if __name__ == '__main__':
    load_dotenv()
    init_db()
    main()
