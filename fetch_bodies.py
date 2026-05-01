#!/usr/bin/env python3
"""
fetch_bodies.py — Fetch full article bodies for authors with empty/short body text.

Strategy:
1. For paywalled sites (Haaretz, Al Jazeera, Jerusalem Post etc.) — try Wayback Machine
2. For NYT authors (Douthat, Klein) — try direct fetch with better headers
3. For Fox/CNN — try direct fetch

Usage:
  python3 fetch_bodies.py --author "Gideon Levy"    # one author
  python3 fetch_bodies.py --min-length 500          # all authors with bodies < 500 chars
  python3 fetch_bodies.py --dry-run                 # preview without fetching
"""

import argparse
import sqlite3
import sys
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

DB_PATH = "oped_data.db"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_wayback(url: str, timeout: int = 20) -> str:
    """Try to get a cached version from the Wayback Machine."""
    # First check if archive exists
    api_url = f"http://archive.org/wayback/available?url={quote(url)}"
    try:
        r = requests.get(api_url, headers=HEADERS, timeout=10)
        data = r.json()
        archived = data.get("archived_snapshots", {}).get("closest", {})
        if not archived.get("available"):
            return ""
        wayback_url = archived["url"]
        # Fetch the archived page
        r2 = requests.get(wayback_url, headers=HEADERS, timeout=timeout)
        r2.raise_for_status()
        return extract_text(r2.text)
    except Exception as e:
        return ""


def fetch_direct(url: str, timeout: int = 15) -> str:
    """Try direct fetch with realistic browser headers."""
    try:
        headers = {
            **HEADERS,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return extract_text(r.text)
    except Exception:
        return ""


def extract_text(html: str) -> str:
    """Extract main article text from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "figure", "noscript", "iframe", "ads"]):
        tag.decompose()
    paragraphs = soup.find_all("p")
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
    # Clean up whitespace
    text = " ".join(text.split())
    return text[:8000] if len(text) > 200 else ""


def get_articles_needing_bodies(conn: sqlite3.Connection,
                                 author: str = "",
                                 min_length: int = 500) -> list:
    """Get articles with body text shorter than min_length."""
    query = """
        SELECT id, author, title, url, published
        FROM articles
        WHERE url IS NOT NULL
          AND url != ''
          AND length(coalesce(body,'')) < ?
    """
    params = [min_length]
    if author:
        query += " AND author = ?"
        params.append(author)
    query += " ORDER BY author, published DESC"
    return conn.execute(query, params).fetchall()


def main():
    parser = argparse.ArgumentParser(description="Fetch article bodies from Wayback Machine")
    parser.add_argument("--author",     default="", help="Limit to one author")
    parser.add_argument("--min-length", type=int, default=500,
                        help="Fetch bodies shorter than this (default: 500)")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Show what would be fetched without doing it")
    parser.add_argument("--direct-only", action="store_true",
                        help="Only try direct fetch, skip Wayback Machine")
    parser.add_argument("--wayback-only", action="store_true",
                        help="Only try Wayback Machine, skip direct fetch")
    parser.add_argument("--db", default=DB_PATH)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    articles = get_articles_needing_bodies(conn, args.author, args.min_length)

    if not articles:
        print("✓ No articles need body fetching.")
        conn.close()
        return

    # Group by author for display
    by_author: dict[str, list] = {}
    for a in articles:
        by_author.setdefault(a["author"], []).append(a)

    print(f"\n  Articles needing bodies: {len(articles)} across {len(by_author)} authors\n")
    for author, arts in sorted(by_author.items()):
        print(f"  {author:<30} {len(arts)} articles")

    if args.dry_run:
        print("\n  DRY RUN — not fetching.")
        conn.close()
        return

    print(f"\n  Starting fetch...\n")
    updated = 0
    failed  = 0

    for art in articles:
        url = art["url"]
        if not url or url.startswith("https://news.google.com"):
            continue

        print(f"  [{art['author'][:20]:<20}] {art['title'][:50] if art['title'] else url[:50]}…")

        text = ""

        # Try direct first (faster, free)
        if not args.wayback_only:
            text = fetch_direct(url)
            if text:
                print(f"    ✓ direct ({len(text)} chars)")

        # Fall back to Wayback Machine
        if not text and not args.direct_only:
            print(f"    → trying Wayback Machine…")
            text = fetch_wayback(url)
            if text:
                print(f"    ✓ wayback ({len(text)} chars)")
            else:
                print(f"    ✗ not found")
                failed += 1
                time.sleep(0.3)
                continue

        if text:
            conn.execute(
                "UPDATE articles SET body=? WHERE id=?",
                (text, art["id"])
            )
            conn.commit()
            updated += 1

        time.sleep(0.5)  # polite delay

    print(f"\n  ✓ Updated: {updated}")
    print(f"  ✗ Failed:  {failed}")
    conn.close()


if __name__ == "__main__":
    main()
