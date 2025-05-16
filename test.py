from pathlib import Path
import json

# Paths
BASE_DIR = Path(__file__).resolve().parent
POSTS_JSON = BASE_DIR / "scrapes/2025-05-10/subreddits/arbeitsleben-search-'Quereinstieg'.json"
COMMENTS_DIR = BASE_DIR / "scrapes/2025-05-10/comments"

expected_comments = {}
actual_comments = {}
missing_files = []

# Load expected num_comments from the posts JSON
with open(POSTS_JSON, "r", encoding="utf-8") as f:
    post_data = json.load(f)
    for post in post_data.get("data", []):
        post_id = post.get("id")
        expected_comments[post_id] = post.get("num_comments", 0)

# Recursively count all comments and replies
def count_all_comments(comments):
    count = 0
    for comment in comments:
        count += 1
        replies = comment.get("replies", [])
        if replies:
            count += count_all_comments(replies)
    return count

# Iterate over each comment file and count all nested comments
for file in COMMENTS_DIR.glob("*.json"):
    try:
        with open(file, "r", encoding="utf-8") as f:
            comment_data = json.load(f)
            comments = comment_data.get("data", {}).get("comments", [])
            total = count_all_comments(comments)

            # Extract post_id from link_id in any comment
            post_id = None
            for c in comments:
                link_id = c.get("link_id", "")
                if link_id.startswith("t3_"):
                    post_id = link_id[3:]
                    break

            if post_id:
                actual_comments[post_id] = total
    except Exception as e:
        print(f"[ERROR] Failed to process {file.name}: {e}")

# Print mismatches
print("\n=== MISMATCHES ===")
for post_id, expected in expected_comments.items():
    actual = actual_comments.get(post_id)
    if actual is None:
        print(f"[❌] Missing comment file for post {post_id} (expected {expected})")
        missing_files.append(post_id)
    elif actual != expected:
        print(f"[⚠️] Post {post_id}: expected {expected}, got {actual}")

# Print summary
print("\n=== SUMMARY ===")
print(f"Expected total comments: {sum(expected_comments.values())}")
print(f"Actual scraped comments: {sum(actual_comments.values())}")
print(f"Missing comment files:   {len(missing_files)}")
print(f"Incomplete scrapes:      {sum(1 for pid in expected_comments if pid in actual_comments and expected_comments[pid] != actual_comments[pid])}")
