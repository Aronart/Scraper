import sqlite3
import pandas as pd
from pathlib import Path

# Paths
DB_PATH = Path(__file__).resolve().parent / "reddit_data.db"
OUTPUT_CSV = Path(__file__).resolve().parent / "db_output_all.csv"

# SQL query (equivalent to the view)
QUERY = """
WITH unified AS (
    SELECT 
        'post' AS source,
        p.id AS id,
        p.title AS title,
        p.selftext AS content,
        p.subreddit AS subreddit,
        p.created_utc AS created_utc,
        GROUP_CONCAT(pk.keyword, ', ') AS keywords
    FROM reddit_post p
    LEFT JOIN reddit_post_keywords pk ON p.id = pk.post_id
    GROUP BY p.id

    UNION ALL

    SELECT 
        'comment' AS source,
        c.id AS id,
        NULL AS title,
        c.comment AS content,
        c.subreddit AS subreddit,
        c.created_utc AS created_utc,
        GROUP_CONCAT(ck.keyword, ', ') AS keywords
    FROM reddit_comment c
    LEFT JOIN reddit_comment_keywords ck ON c.id = ck.comment_id
    GROUP BY c.id
)

SELECT * FROM unified
WHERE content IS NOT NULL
GROUP BY content
ORDER BY created_utc DESC;
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