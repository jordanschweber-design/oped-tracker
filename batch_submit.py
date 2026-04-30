#!/usr/bin/env python3
"""
batch_submit.py — Submit all unchecked predictions to Anthropic's Batch API.

Usage:
  python3 batch_submit.py          # submits all unchecked predictions
  python3 batch_submit.py --dry-run  # shows what would be submitted without sending

The batch ID is saved to batch_id.txt so batch_collect.py can retrieve results.
Batches are processed within 24 hours at 50% of normal API cost.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import requests

DB_PATH = "oped_data.db"

OUTCOME_SYSTEM = """You are a prediction fact-checker. A journalist made a prediction in an op-ed.
Your job is to determine if the prediction came true AFTER it was written, using your knowledge.

CRITICAL RULES:
- The outcome must have occurred AFTER the article was published
- If the article date is unknown, use context clues in the prediction to estimate when it was written
- Only mark "correct" if you are confident the predicted event happened after publication
- Mark "pending" if the prediction is about something that hasn't happened yet as of early 2026
- Mark "unverifiable" if you don't have enough information to judge
- Be honest — if you're not sure, say unverifiable rather than guessing

Return ONLY a JSON object, no prose, no markdown fences:
{
  "outcome_text": "1-3 sentence description of what actually happened and when",
  "verdict": "correct" or "incorrect" or "partial" or "unverifiable" or "pending",
  "confidence": integer 0-100,
  "score": float 0.0-10.0 (10=fully correct, 5=partial, 0=fully wrong, -1=unverifiable/pending)
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


def main():
    dry_run = "--dry-run" in sys.argv

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key and not dry_run:
        print("❌ ANTHROPIC_API_KEY not set")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Fetch all unchecked predictions from articles older than 6 months
    preds = conn.execute("""
        SELECT p.id, p.claim, p.author, a.published
        FROM predictions p
        JOIN articles a ON p.article_id = a.id
        LEFT JOIN outcomes o ON o.prediction_id = p.id
        WHERE o.id IS NULL
        ORDER BY p.author, a.published DESC
    """).fetchall()

    # Filter to 6+ months old
    preds = [p for p in preds if is_old_enough(p["published"])]

    if not preds:
        print("✓ No unchecked predictions found.")
        conn.close()
        return

    print(f"\n  Preparing batch for {len(preds)} predictions...\n")

    # Build batch requests
    requests_list = []
    for pred in preds:
        prompt = (
            f"A journalist ({pred['author']}) made this prediction in an op-ed "
            f"(published: {pred['published'] or 'unknown'}):\n"
            f"\"{pred['claim']}\"\n\n"
            f"Based on your knowledge of world events, determine if this prediction came true."
        )
        requests_list.append({
            "custom_id": f"pred_{pred['id']}",
            "params": {
                "model": "claude-sonnet-4-6",
                "max_tokens": 500,
                "system": OUTCOME_SYSTEM,
                "messages": [{"role": "user", "content": prompt}]
            }
        })

    if dry_run:
        print(f"  DRY RUN — would submit {len(requests_list)} requests")
        print(f"  Sample: {requests_list[0]['custom_id']} — {preds[0]['claim'][:60]}...")
        conn.close()
        return

    # Submit to Anthropic Batch API
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
        print(f"❌ Batch submission failed: {resp.status_code} {resp.text}")
        conn.close()
        sys.exit(1)

    data = resp.json()
    batch_id = data["id"]
    status   = data["processing_status"]

    # Save batch ID for later retrieval
    with open("batch_id.txt", "w") as f:
        f.write(batch_id)

    print(f"\n  ✓ Batch submitted!")
    print(f"  Batch ID    : {batch_id}")
    print(f"  Status      : {status}")
    print(f"  Requests    : {len(requests_list)}")
    print(f"\n  Saved batch ID to batch_id.txt")
    print(f"  Processing usually completes within 1-24 hours.")
    print(f"\n  To collect results when ready, run:")
    print(f"    python3 batch_collect.py")
    print()

    conn.close()


if __name__ == "__main__":
    main()
