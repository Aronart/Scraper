import sqlite3
import pandas as pd
from pathlib import Path

# Paths
DB_PATH = Path(__file__).resolve().parent / "reddit_data.db"
OUTPUT_CSV = Path(__file__).resolve().parent / "db_output_all.csv"

# SQL query (equivalent to the view)
QUERY = """
SELECT 
    'post' AS source,
    p.id AS id,
    p.title AS title,
    p.selftext AS content,
    p.subreddit,
    p.created_utc,
    pk.keyword
FROM reddit_post p
LEFT JOIN reddit_post_keywords pk ON p.id = pk.post_id

UNION ALL

SELECT 
    'comment' AS source,
    c.id AS id,
    NULL AS title,
    c.comment AS content,
    c.subreddit,
    c.created_utc,
    ck.keyword
FROM reddit_comment c
LEFT JOIN reddit_comment_keywords ck ON c.id = ck.comment_id;
"""

# Connect and query
conn = sqlite3.connect(DB_PATH)
df = pd.read_sql_query(QUERY, conn)

# Save to CSV
df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
print(f"[INFO] Exported {len(df)} rows to {OUTPUT_CSV}")

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 0)
pd.set_option('display.max_colwidth', None)

print(df.head(20))