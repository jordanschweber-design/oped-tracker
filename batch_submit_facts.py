#!/usr/bin/env python3
"""
batch_submit_facts.py — Submit articles for factual accuracy checking via Batch API.

For each author's articles, Claude checks:
  - Are specific facts and statistics cited accurately?
  - Are attributions correct (did the named person actually say/do that)?
  - Does the broader narrative hold up to scrutiny?

Usage:
  python3 batch_submit_facts.py              # submit all unscored articles
  python3 batch_submit_facts.py --dry-run    # preview without submitting
  python3 batch_submit_facts.py --author "Gideon Levy"  # one author only
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import requests

DB_PATH = "oped_data.db"

FACT_CHECK_SYSTEM = """You are a factual accuracy checker for opinion journalism.

IMPORTANT: Opinion pieces express views — your job is NOT to judge whether the author's 
opinions are correct. You ONLY flag objectively verifiable errors.

Score as "inaccurate" or "mostly_inaccurate" ONLY when:
- A specific statistic or number is clearly wrong (e.g. wrong GDP figure, wrong date)
- A quote is fabricated or significantly misrepresented  
- A named person is falsely credited with an action or statement
- A historical fact is plainly incorrect

Score as "accurate" or "mostly_accurate" when:
- The verifiable facts cited appear correct, even if you disagree with the conclusions
- There are no verifiable factual claims (pure opinion) — default to "accurate"

Score as "unverifiable" ONLY when the text is too short to assess (under 100 words).

Start from 10/10 and only deduct for clear objective errors. Do NOT deduct for:
- Opinions you disagree with
- Framing or emphasis choices
- Predictions that turned out wrong
- Contested interpretations of events

Return ONLY a JSON object, no prose, no markdown fences:
{
  "factual_score": float 0.0-10.0 (start at 10, deduct only for clear errors),
  "verdict": "accurate" or "mostly_accurate" or "mixed" or "mostly_inaccurate" or "inaccurate" or "unverifiable",
  "confidence": integer 0-100,
  "key_claims_checked": ["brief description of 1-3 main verifiable claims found"],
  "issues_found": "specific objective errors found, or empty string if none",
  "summary": "1-2 sentence assessment focusing only on factual accuracy"
}"""


def is_old_enough(pub_str: str, min_months: int = 6) -> bool:
    if not pub_str:
        return True
    try:
        dt = parsedate_to_datetime(pub_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        try:
            dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
        except Exception:
            return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=min_months * 30)
    return dt <= cutoff


def init_fact_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fact_checks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id      INTEGER REFERENCES articles(id),
            author          TEXT NOT NULL,
            factual_score   REAL,
            verdict         TEXT,
            confidence      INTEGER,
            key_claims      TEXT,
            issues_found    TEXT,
            summary         TEXT,
            checked_at      TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS author_fact_ratings (
            author          TEXT PRIMARY KEY,
            total_checked   INTEGER DEFAULT 0,
            avg_score       REAL DEFAULT 0,
            accurate_count  INTEGER DEFAULT 0,
            mixed_count     INTEGER DEFAULT 0,
            inaccurate_count INTEGER DEFAULT 0,
            last_updated    TEXT
        )
    """)
    conn.commit()


def main():
    dry_run    = "--dry-run" in sys.argv
    author_filter = ""
    if "--author" in sys.argv:
        idx = sys.argv.index("--author")
        author_filter = sys.argv[idx + 1]

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not dry_run:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_fact_table(conn)

    # Get articles that haven't been fact-checked yet, with body text
    query = """
        SELECT a.id, a.author, a.title, a.body, a.published, a.url
        FROM articles a
        LEFT JOIN fact_checks f ON f.article_id = a.id
        WHERE f.id IS NULL
          AND length(a.body) > 100
    """
    if author_filter:
        query += f" AND a.author = '{author_filter}'"

    articles = conn.execute(query).fetchall()
    articles = [a for a in articles if is_old_enough(a["published"])]

    if not articles:
        print("✓ No articles to fact-check.")
        conn.close()
        return

    print(f"\n  Preparing fact-check batch for {len(articles)} articles...\n")

    requests_list = []
    for art in articles:
        text = art["body"][:2000] if art["body"] else ""
        prompt = (
            f"Author: {art['author']}\n"
            f"Title: {art['title']}\n"
            f"Published: {art['published'] or 'unknown'}\n"
            f"URL: {art['url'] or ''}\n\n"
            f"Article text (may be a snippet):\n{text}\n\n"
            f"Please assess the factual accuracy of this piece."
        )
        requests_list.append({
            "custom_id": f"fact_{art['id']}",
            "params": {
                "model":      "claude-sonnet-4-6",
                "max_tokens": 600,
                "system":     FACT_CHECK_SYSTEM,
                "messages":   [{"role": "user", "content": prompt}]
            }
        })

    if dry_run:
        print(f"  DRY RUN — would submit {len(requests_list)} fact-check requests")
        authors = list({a["author"] for a in articles})
        print(f"  Authors covered: {', '.join(sorted(authors)[:8])}{'...' if len(authors) > 8 else ''}")
        conn.close()
        return

    print(f"  Submitting {len(requests_list)} requests to Anthropic Batch API...")
    resp = requests.post(
        "https://api.anthropic.com/v1/messages/batches",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta":    "message-batches-2024-09-24",
            "content-type":      "application/json",
        },
        json={"requests": requests_list},
        timeout=60,
    )

    if not resp.ok:
        print(f"❌ Batch submission failed: {resp.status_code} {resp.text[:200]}")
        conn.close()
        sys.exit(1)

    data     = resp.json()
    batch_id = data["id"]

    with open("fact_batch_id.txt", "w") as f:
        f.write(batch_id)

    print(f"\n  ✓ Fact-check batch submitted!")
    print(f"  Batch ID : {batch_id}")
    print(f"  Requests : {len(requests_list)}")
    print(f"\n  Saved to fact_batch_id.txt")
    print(f"  To collect results:\n    python3 batch_collect_facts.py --wait\n")
    conn.close()


if __name__ == "__main__":
    main()
