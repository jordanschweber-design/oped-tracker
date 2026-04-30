#!/usr/bin/env python3
"""
batch_collect_facts.py — Collect factual accuracy results and save to database.

Usage:
  python3 batch_collect_facts.py           # check status
  python3 batch_collect_facts.py --wait    # poll until done, then save
  python3 batch_collect_facts.py --id msgbatch_xxx
"""

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

import requests

DB_PATH  = "oped_data.db"
ID_FILE  = "fact_batch_id.txt"


def get_batch_id() -> str:
    if "--id" in sys.argv:
        return sys.argv[sys.argv.index("--id") + 1]
    if os.path.exists(ID_FILE):
        return open(ID_FILE).read().strip()
    print("❌ No batch ID. Run batch_submit_facts.py first.")
    sys.exit(1)


def safe_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return json.loads(text)


def check_status(batch_id: str, api_key: str) -> dict:
    r = requests.get(
        f"https://api.anthropic.com/v1/messages/batches/{batch_id}",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "anthropic-beta": "message-batches-2024-09-24"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def fetch_results(batch_id: str, api_key: str):
    r = requests.get(
        f"https://api.anthropic.com/v1/messages/batches/{batch_id}/results",
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                 "anthropic-beta": "message-batches-2024-09-24"},
        stream=True, timeout=120,
    )
    r.raise_for_status()
    for line in r.iter_lines():
        if line:
            yield json.loads(line)


def build_author_fact_ratings(conn: sqlite3.Connection):
    """Aggregate per-author factual accuracy ratings."""
    authors = [r[0] for r in conn.execute(
        "SELECT DISTINCT author FROM fact_checks"
    ).fetchall()]

    for author in authors:
        rows = conn.execute(
            "SELECT factual_score, verdict FROM fact_checks "
            "WHERE author=? AND verdict != 'unverifiable' AND factual_score >= 0",
            (author,)
        ).fetchall()
        if not rows:
            continue

        total       = len(rows)
        scores      = [r[0] for r in rows if r[0] is not None]
        avg_score   = round(sum(scores) / len(scores), 2) if scores else 0.0
        accurate    = sum(1 for r in rows if r[1] in ("accurate", "mostly_accurate"))
        mixed       = sum(1 for r in rows if r[1] == "mixed")
        inaccurate  = sum(1 for r in rows if r[1] in ("inaccurate", "mostly_inaccurate"))

        conn.execute("""
            INSERT OR REPLACE INTO author_fact_ratings
            (author, total_checked, avg_score, accurate_count, mixed_count, inaccurate_count, last_updated)
            VALUES (?,?,?,?,?,?,?)
        """, (author, total, avg_score, accurate, mixed, inaccurate, datetime.now().isoformat()))

    conn.commit()


def main():
    api_key  = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    batch_id = get_batch_id()
    wait     = "--wait" in sys.argv
    conn     = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Ensure tables exist
    conn.execute("""CREATE TABLE IF NOT EXISTS fact_checks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, article_id INTEGER,
        author TEXT, factual_score REAL, verdict TEXT, confidence INTEGER,
        key_claims TEXT, issues_found TEXT, summary TEXT, checked_at TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS author_fact_ratings (
        author TEXT PRIMARY KEY, total_checked INTEGER DEFAULT 0,
        avg_score REAL DEFAULT 0, accurate_count INTEGER DEFAULT 0,
        mixed_count INTEGER DEFAULT 0, inaccurate_count INTEGER DEFAULT 0,
        last_updated TEXT)""")
    conn.commit()

    print(f"\n  Checking batch: {batch_id}")

    while True:
        sd     = check_status(batch_id, api_key)
        status = sd["processing_status"]
        counts = sd.get("request_counts", {})
        print(f"  Status   : {status}")
        print(f"  Progress : {counts.get('succeeded',0)} succeeded / "
              f"{counts.get('errored',0)} errored / "
              f"{counts.get('processing',0)} processing")
        if status == "ended":
            break
        if not wait:
            print(f"\n  Still processing. Run with --wait to poll automatically.")
            conn.close()
            return
        print(f"  Waiting 60s...")
        time.sleep(60)

    print(f"\n  ✓ Done! Fetching results...")
    results = list(fetch_results(batch_id, api_key))
    print(f"  Retrieved {len(results)} results")

    saved = skipped = 0
    for result in results:
        custom_id = result.get("custom_id", "")
        if not custom_id.startswith("fact_"):
            continue
        article_id = int(custom_id.replace("fact_", ""))

        existing = conn.execute(
            "SELECT id FROM fact_checks WHERE article_id=?", (article_id,)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        if result.get("result", {}).get("type") != "succeeded":
            skipped += 1
            continue

        content = result["result"]["message"]["content"]
        text = "".join(b.get("text","") for b in content if b.get("type")=="text")

        try:
            data = safe_json(text)
        except Exception:
            skipped += 1
            continue

        author = conn.execute(
            "SELECT author FROM articles WHERE id=?", (article_id,)
        ).fetchone()
        author_name = author[0] if author else "Unknown"

        conn.execute("""
            INSERT INTO fact_checks
            (article_id, author, factual_score, verdict, confidence,
             key_claims, issues_found, summary, checked_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            article_id, author_name,
            data.get("factual_score", -1),
            data.get("verdict", "unverifiable"),
            data.get("confidence", 0),
            json.dumps(data.get("key_claims_checked", [])),
            data.get("issues_found", ""),
            data.get("summary", ""),
            datetime.now().isoformat(),
        ))
        saved += 1

    conn.commit()
    print(f"  Saved   : {saved}")
    print(f"  Skipped : {skipped}")

    build_author_fact_ratings(conn)

    rows = conn.execute(
        "SELECT author, avg_score, total_checked FROM author_fact_ratings "
        "WHERE total_checked >= 2 ORDER BY avg_score DESC"
    ).fetchall()
    if rows:
        print(f"\n  Factual Accuracy Ratings:")
        for r in rows:
            bar = "█" * round(r[1]) + "░" * (10 - round(r[1]))
            print(f"  {r[0]:<28} {bar}  {r[1]:.1f}/10  ({r[2]} articles)")

    conn.close()
    print(f"\n  ✓ Done! Restart server and refresh dashboard.\n")


if __name__ == "__main__":
    main()
