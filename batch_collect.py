#!/usr/bin/env python3
"""
batch_collect.py — Poll for batch results and save outcomes to the database.

Usage:
  python3 batch_collect.py           # checks status, saves results if ready
  python3 batch_collect.py --wait    # polls every 60s until done, then saves
  python3 batch_collect.py --id msgbatch_xxx  # use a specific batch ID

Run this after batch_submit.py. Results are saved to oped_data.db automatically.
"""

import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime

import requests

DB_PATH   = "oped_data.db"
ID_FILE   = "batch_id.txt"


def get_batch_id() -> str:
    if "--id" in sys.argv:
        idx = sys.argv.index("--id")
        return sys.argv[idx + 1]
    if os.path.exists(ID_FILE):
        return open(ID_FILE).read().strip()
    print("❌ No batch ID found. Run batch_submit.py first, or pass --id msgbatch_xxx")
    sys.exit(1)


def safe_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return json.loads(text)


def check_status(batch_id: str, api_key: str) -> dict:
    resp = requests.get(
        f"https://api.anthropic.com/v1/messages/batches/{batch_id}",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta":    "message-batches-2024-09-24",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_results(batch_id: str, api_key: str):
    """Stream results from the batch."""
    resp = requests.get(
        f"https://api.anthropic.com/v1/messages/batches/{batch_id}/results",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "anthropic-beta":    "message-batches-2024-09-24",
        },
        stream=True,
        timeout=120,
    )
    resp.raise_for_status()
    for line in resp.iter_lines():
        if line:
            yield json.loads(line)


def save_results(results, conn: sqlite3.Connection) -> tuple[int, int]:
    saved = 0
    skipped = 0

    for result in results:
        custom_id = result.get("custom_id", "")
        if not custom_id.startswith("pred_"):
            continue

        pred_id = int(custom_id.replace("pred_", ""))

        # Skip if already saved
        existing = conn.execute(
            "SELECT id FROM outcomes WHERE prediction_id=?", (pred_id,)
        ).fetchone()
        if existing:
            skipped += 1
            continue

        result_type = result.get("result", {}).get("type")
        if result_type != "succeeded":
            print(f"  ⚠  pred_{pred_id} failed: {result.get('result',{}).get('error','unknown')}")
            skipped += 1
            continue

        # Extract text from response
        content = result["result"]["message"]["content"]
        text = ""
        for block in content:
            if block.get("type") == "text":
                text += block.get("text", "")

        try:
            data = safe_json(text)
        except Exception as e:
            print(f"  ⚠  pred_{pred_id} parse error: {e}")
            skipped += 1
            continue

        conn.execute(
            "INSERT INTO outcomes "
            "(prediction_id,outcome_text,sources,verdict,confidence,score,checked_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (
                pred_id,
                data.get("outcome_text", ""),
                json.dumps([]),
                data.get("verdict", "unverifiable"),
                data.get("confidence", 0),
                data.get("score", -1),
                datetime.now().isoformat(),
            )
        )
        saved += 1

    conn.commit()
    return saved, skipped


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    batch_id = get_batch_id()
    wait     = "--wait" in sys.argv
    conn     = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print(f"\n  Checking batch: {batch_id}")

    while True:
        status_data = check_status(batch_id, api_key)
        status      = status_data["processing_status"]
        counts      = status_data.get("request_counts", {})

        print(f"  Status   : {status}")
        print(f"  Progress : {counts.get('succeeded',0)} succeeded / "
              f"{counts.get('errored',0)} errored / "
              f"{counts.get('processing',0)} processing / "
              f"{counts.get('canceled',0)} canceled")

        if status == "ended":
            break

        if not wait:
            print(f"\n  Batch is still processing.")
            print(f"  Run again later, or use --wait to poll automatically:")
            print(f"    python3 batch_collect.py --wait")
            conn.close()
            return

        print(f"  Waiting 60s before checking again...")
        time.sleep(60)

    # Results are ready
    print(f"\n  ✓ Batch complete! Fetching results...")
    results = list(fetch_results(batch_id, api_key))
    print(f"  Retrieved {len(results)} results")

    saved, skipped = save_results(results, conn)
    print(f"  Saved   : {saved} outcomes")
    print(f"  Skipped : {skipped} (already saved or failed)")

    # Update ratings
    from reliability import build_author_rating, init_db
    authors = [r[0] for r in conn.execute(
        "SELECT DISTINCT author FROM predictions"
    ).fetchall()]
    print(f"\n  Computing ratings for {len(authors)} authors...")
    for author in authors:
        r = build_author_rating(author, conn)
        if r.get("total_checked", 0) > 0:
            pct = r["reliability_pct"]
            total = r["total_checked"]
            print(f"  {author:<30} {pct:.1f}%  ({total} checked)")

    conn.close()
    print(f"\n  ✓ Done! Refresh your dashboard to see results.")
    print()


if __name__ == "__main__":
    main()
