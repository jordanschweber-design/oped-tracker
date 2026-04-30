#!/usr/bin/env python3
"""
reliability.py — Prediction tracker & reliability rater for op-ed authors.

Pipeline:
  1. scrape_author_archive()  — pull all historical op-eds for an author
  2. extract_predictions()    — Claude reads each piece, extracts forward-looking claims
  3. check_outcomes()         — web-search each prediction to find what actually happened
  4. score_prediction()       — Claude rates the outcome vs. prediction (0–10)
  5. build_author_rating()    — aggregate into a per-author reliability profile
  6. save / load via SQLite   — everything is stored in oped_data.db
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ─── Config ───────────────────────────────────────────────────────────────────

DB_PATH    = "oped_data.db"
SERP_URL   = "https://serpapi.com/search"
DDG_URL    = "https://duckduckgo.com/html/"
HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def is_old_enough(pub_str: str, min_months: int = 6) -> bool:
    """Return True if article is at least min_months old (or date unknown)."""
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

# Import all site/author config from central config file
try:
    from sites_config import SITES, NOTABLE_AUTHORS, AUTHOR_ARCHIVE_URLS
except ImportError:
    # Fallback stub so the file can be imported alone (legacy)
    SITES = {}
    NOTABLE_AUTHORS = {}
    AUTHOR_ARCHIVE_URLS: dict[str, list[str]] = {
    "Paul Krugman":       ["https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml",
                           "https://www.nytimes.com/by/paul-krugman"],
    "Maureen Dowd":       ["https://www.nytimes.com/by/maureen-dowd"],
    "David Brooks":       ["https://www.nytimes.com/by/david-brooks"],
    "Gail Collins":       ["https://www.nytimes.com/by/gail-collins"],
    "Charles Blow":       ["https://www.nytimes.com/by/charles-m-blow"],
    "Ross Douthat":       ["https://www.nytimes.com/by/ross-douthat"],
    "Ezra Klein":         ["https://www.nytimes.com/by/ezra-klein"],
    "Michelle Goldberg":  ["https://www.nytimes.com/by/michelle-goldberg"],
    "Thomas Friedman":    ["https://www.nytimes.com/by/thomas-l-friedman"],
    "Bret Stephens":      ["https://www.nytimes.com/by/bret-stephens"],
    "Nicholas Kristof":   ["https://www.nytimes.com/by/nicholas-kristof"],
    "Frank Bruni":        ["https://www.nytimes.com/by/frank-bruni"],
    "George Monbiot":     ["https://www.theguardian.com/profile/georgemonbiot/rss",
                           "https://www.theguardian.com/profile/georgemonbiot"],
    "Polly Toynbee":      ["https://www.theguardian.com/profile/pollytoynbee/rss"],
    "Owen Jones":         ["https://www.theguardian.com/profile/owen-jones/rss"],
    "Simon Jenkins":      ["https://www.theguardian.com/profile/simonjenkins/rss"],
    "Gary Younge":        ["https://www.theguardian.com/profile/garyyounge/rss"],
    "Marina Hyde":        ["https://www.theguardian.com/profile/marinahyde/rss"],
    "Jonathan Freedland": ["https://www.theguardian.com/profile/jonathanfreedland/rss"],
    "Zoe Williams":       ["https://www.theguardian.com/profile/zoewilliams/rss"],
    "Hadley Freeman":     ["https://www.theguardian.com/profile/hadleyfreeman/rss"],
    "Nesrine Malik":      ["https://www.theguardian.com/profile/nesrine-malik/rss"],
    "Eugene Robinson":    ["https://www.washingtonpost.com/people/eugene-robinson/"],
    "George Will":        ["https://www.washingtonpost.com/people/george-f-will/"],
    "Jennifer Rubin":     ["https://www.washingtonpost.com/people/jennifer-rubin/"],
    "Dana Milbank":       ["https://www.washingtonpost.com/people/dana-milbank/"],
    "Kathleen Parker":    ["https://www.washingtonpost.com/people/kathleen-parker/"],
    "E.J. Dionne":        ["https://www.washingtonpost.com/people/e-j-dionne-jr/"],
    "Max Boot":           ["https://www.washingtonpost.com/people/max-boot/"],
    "David Ignatius":     ["https://www.washingtonpost.com/people/david-ignatius/"],
    "Megan McArdle":      ["https://www.washingtonpost.com/people/megan-mcardle/"],
    "Robert Kagan":       ["https://www.washingtonpost.com/people/robert-kagan/"],
    "David Frum":         ["https://www.theatlantic.com/author/david-frum/"],
    "Anne Applebaum":     ["https://www.theatlantic.com/author/anne-applebaum/"],
    "Adam Serwer":        ["https://www.theatlantic.com/author/adam-serwer/"],
    "Conor Friedersdorf": ["https://www.theatlantic.com/author/conor-friedersdorf/"],
    "Tom Nichols":        ["https://www.theatlantic.com/author/tom-nichols/"],
    "Caitlin Flanagan":   ["https://www.theatlantic.com/author/caitlin-flanagan/"],
    }  # end fallback stub

# ─── Database ─────────────────────────────────────────────────────────────────

def init_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            author      TEXT NOT NULL,
            title       TEXT,
            url         TEXT UNIQUE,
            published   TEXT,
            body        TEXT,
            scraped_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS predictions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id      INTEGER REFERENCES articles(id),
            author          TEXT NOT NULL,
            claim           TEXT NOT NULL,
            context         TEXT,
            predicted_year  TEXT,
            extracted_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS outcomes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id   INTEGER REFERENCES predictions(id),
            outcome_text    TEXT,
            sources         TEXT,
            verdict         TEXT CHECK(verdict IN ('correct','incorrect','partial','unverifiable','pending')),
            confidence      INTEGER,
            score           REAL,
            checked_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS ratings (
            author          TEXT PRIMARY KEY,
            total_checked   INTEGER DEFAULT 0,
            correct         INTEGER DEFAULT 0,
            partial         INTEGER DEFAULT 0,
            incorrect       INTEGER DEFAULT 0,
            unverifiable    INTEGER DEFAULT 0,
            avg_score       REAL DEFAULT 0,
            reliability_pct REAL DEFAULT 0,
            last_updated    TEXT
        );
    """)
    conn.commit()
    return conn


# ─── Scraping ─────────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 20) -> Optional[str]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except requests.RequestException as e:
        print(f"    ⚠  {url}: {e}", file=sys.stderr)
        return None


def parse_rss_feed(xml: str, author: str) -> list[dict]:
    soup = BeautifulSoup(xml, "xml")
    items = soup.find_all("item") or soup.find_all("entry")
    out = []
    for it in items:
        def txt(tag): return tag.get_text(strip=True) if tag else ""
        title   = txt(it.find("title"))
        link    = txt(it.find("link"))
        pub     = txt(it.find("pubDate") or it.find("published"))
        desc    = txt(it.find("description") or it.find("summary"))
        creator = txt(it.find("dc:creator") or it.find("author"))
        if creator and author.split()[0].lower() not in creator.lower():
            continue
        if not is_old_enough(pub):
            continue
        # Fix NYT RSS URLs that incorrectly point to rss.nytimes.com
        if link and "rss.nytimes.com" in link:
            link = link.replace("rss.nytimes.com", "www.nytimes.com")
        out.append({"title": title, "url": link, "published": pub, "body": desc})
    return out


def parse_byline_page(html: str, base_url: str) -> list[dict]:
    """Generic byline/author page parser — extracts article links."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not text or len(text) < 15:
            continue
        # heuristic: skip nav/footer/social links
        if any(x in href for x in ["#", "twitter", "facebook", "mailto", "javascript"]):
            continue
        if href.startswith("/"):
            href = base_url.rstrip("/") + href
        links.append({"title": text, "url": href, "published": "", "body": ""})
    # deduplicate by URL
    seen, out = set(), []
    for l in links:
        if l["url"] not in seen:
            seen.add(l["url"])
            out.append(l)
    return out[:80]   # cap at 80 links per page


def fetch_article_body(url: str) -> str:
    # Fix any remaining rss.nytimes.com URLs
    if url and "rss.nytimes.com" in url:
        url = url.replace("rss.nytimes.com", "www.nytimes.com")
    html = fetch(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script","style","nav","header","footer","aside","figure","noscript"]):
        tag.decompose()
    text = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
    return text[:10000]


def scrape_author_archive(author: str, conn: sqlite3.Connection,
                          fetch_bodies: bool = True) -> int:
    """Scrape all available op-eds for an author. Returns count of new articles saved."""
    urls = AUTHOR_ARCHIVE_URLS.get(author, [])
    if not urls:
        print(f"  ✗  No archive URLs configured for {author}")
        return 0

    new_count = 0
    base_url  = urls[0].split("/")[0] + "//" + urls[0].split("/")[2]

    for url in urls:
        print(f"    Fetching archive: {url}")
        html = fetch(url)
        if not html:
            continue

        # choose parser
        if "rss" in url or html.strip().startswith("<?xml"):
            articles = parse_rss_feed(html, author)
        else:
            articles = parse_byline_page(html, base_url)

        for art in articles:
            # skip if already in DB
            exists = conn.execute(
                "SELECT id FROM articles WHERE url=?", (art["url"],)
            ).fetchone()
            if exists:
                continue

            body = art.get("body", "")
            if fetch_bodies and art["url"] and not body:
                print(f"      → body: {art['url'][:65]}…")
                body = fetch_article_body(art["url"])
                time.sleep(0.4)

            conn.execute(
                "INSERT OR IGNORE INTO articles (author,title,url,published,body,scraped_at) "
                "VALUES (?,?,?,?,?,?)",
                (author, art["title"], art["url"], art["published"],
                 body, datetime.now().isoformat())
            )
            new_count += 1

        conn.commit()
        time.sleep(0.5)

    print(f"    ✓  {author}: {new_count} new articles saved")
    return new_count


# ─── Claude helpers ───────────────────────────────────────────────────────────

def claude(prompt: str, system: str = "", max_tokens: int = 2000) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    messages = [{"role": "user", "content": prompt}]
    body: dict = {
        "model":      "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "messages":   messages,
    }
    if system:
        body["system"] = system

    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json=body,
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["content"][0]["text"]


def safe_json(text: str) -> list | dict:
    """Strip markdown fences then parse JSON."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text.strip())
    return json.loads(text)


# ─── Prediction extraction ────────────────────────────────────────────────────

EXTRACT_SYSTEM = """You are a prediction-extraction engine. Given an op-ed article, 
extract every forward-looking claim or prediction the author makes about future events, 
policies, or outcomes. Only extract genuine predictions (not rhetorical questions or 
pure opinions with no verifiable outcome).

Return a JSON array. Each element:
{
  "claim": "concise 1-sentence statement of the prediction",
  "context": "1-2 sentence quote/paraphrase showing where this appears",
  "predicted_year": "year or period the author implies the outcome will occur, or 'unspecified'"
}

If there are no predictions, return [].
Return ONLY the JSON array, no prose."""


def extract_predictions(article_id: int, title: str, body: str,
                        author: str, conn: sqlite3.Connection) -> int:
    # Use body if available, fall back to title-only analysis
    text = body.strip() if body and len(body.strip()) > 50 else ""
    if not text and not title:
        return 0

    # skip if already extracted
    existing = conn.execute(
        "SELECT COUNT(*) FROM predictions WHERE article_id=?", (article_id,)
    ).fetchone()[0]
    if existing:
        return 0

    if text:
        prompt = f"Article title: {title}\n\nArticle text:\n{text[:6000]}"
    else:
        prompt = (
            f"Article title: {title}\n\n"
            f"(Only the title is available — infer any predictions implied by the title alone. "
            f"If the title contains no clear prediction, return [].)"
        )
    try:
        raw  = claude(prompt, system=EXTRACT_SYSTEM)
        data = safe_json(raw)
    except Exception as e:
        print(f"      ⚠  extract error for article {article_id}: {e}", file=sys.stderr)
        return 0

    count = 0
    for p in (data if isinstance(data, list) else []):
        claim = p.get("claim", "").strip()
        if not claim:
            continue
        conn.execute(
            "INSERT INTO predictions (article_id,author,claim,context,predicted_year,extracted_at) "
            "VALUES (?,?,?,?,?,?)",
            (article_id, author, claim, p.get("context",""),
             p.get("predicted_year","unspecified"), datetime.now().isoformat())
        )
        count += 1

    conn.commit()
    return count


# ─── Outcome checking ─────────────────────────────────────────────────────────

OUTCOME_SYSTEM = """You are a prediction fact-checker. A journalist made a prediction in an op-ed.
Using your web search tool, search for what actually happened regarding this prediction.
Then return a JSON object with your verdict.

Return ONLY a JSON object, no prose, no markdown fences:
{
  "outcome_text": "1-3 sentence description of what actually happened",
  "verdict": "correct" or "incorrect" or "partial" or "unverifiable" or "pending",
  "confidence": integer 0-100,
  "score": float 0.0-10.0 (10=fully correct, 5=partial, 0=fully wrong, -1=unverifiable/pending),
  "sources": ["url1", "url2"]
}"""


def check_prediction_outcome(pred_id: int, claim: str, author: str,
                              article_date: str, conn: sqlite3.Connection) -> bool:
    """Use Claude with web_search tool to verify a prediction outcome."""
    existing = conn.execute(
        "SELECT id FROM outcomes WHERE prediction_id=?", (pred_id,)
    ).fetchone()
    if existing:
        return False

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return False

    prompt = (
        f"A journalist ({author}) made this prediction in an op-ed "
        f"(published: {article_date or 'unknown'}):\n"
        f"\"{claim}\"\n\n"
        f"Search the web to find out what actually happened. "
        f"Then return your verdict as a JSON object."
    )

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         api_key,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-sonnet-4-6",
                "max_tokens": 1500,
                "system":     OUTCOME_SYSTEM,
                "tools": [{"type": "web_search_20250305", "name": "web_search"}],
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()

        # Extract text from response (may include tool_use blocks)
        text = ""
        sources = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
            elif block.get("type") == "tool_result":
                for sub in block.get("content", []):
                    if isinstance(sub, dict) and sub.get("type") == "text":
                        # extract URLs from search results if present
                        pass

        result = safe_json(text)

    except Exception as e:
        print(f"      ⚠  outcome error for pred {pred_id}: {e}", file=sys.stderr)
        return False

    conn.execute(
        "INSERT INTO outcomes "
        "(prediction_id,outcome_text,sources,verdict,confidence,score,checked_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            pred_id,
            result.get("outcome_text", ""),
            json.dumps(result.get("sources", [])),
            result.get("verdict", "unverifiable"),
            result.get("confidence", 0),
            result.get("score", -1),
            datetime.now().isoformat(),
        )
    )
    conn.commit()
    return True


# ─── Reliability rating ───────────────────────────────────────────────────────

def build_author_rating(author: str, conn: sqlite3.Connection) -> dict:
    rows = conn.execute("""
        SELECT o.verdict, o.score
        FROM outcomes o
        JOIN predictions p ON o.prediction_id = p.id
        WHERE p.author = ?
          AND o.verdict NOT IN ('pending','unverifiable')
    """, (author,)).fetchall()

    if not rows:
        return {"author": author, "total_checked": 0, "reliability_pct": 0.0}

    total     = len(rows)
    correct   = sum(1 for r in rows if r["verdict"] == "correct")
    partial   = sum(1 for r in rows if r["verdict"] == "partial")
    incorrect = sum(1 for r in rows if r["verdict"] == "incorrect")
    scores    = [r["score"] for r in rows if r["score"] is not None and r["score"] >= 0]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    # weighted reliability: correct=1, partial=0.5, incorrect=0
    reliability = round(((correct + 0.5 * partial) / total) * 100, 1) if total else 0.0

    rating = {
        "author":          author,
        "total_checked":   total,
        "correct":         correct,
        "partial":         partial,
        "incorrect":       incorrect,
        "avg_score":       avg_score,
        "reliability_pct": reliability,
        "last_updated":    datetime.now().isoformat(),
    }

    conn.execute("""
        INSERT OR REPLACE INTO ratings
        (author,total_checked,correct,partial,incorrect,avg_score,reliability_pct,last_updated)
        VALUES (:author,:total_checked,:correct,:partial,:incorrect,
                :avg_score,:reliability_pct,:last_updated)
    """, rating)
    conn.commit()
    return rating


def print_rating(r: dict) -> None:
    total = r.get("total_checked", 0)
    if not total:
        print(f"  {r['author']:<25}  no scored predictions yet")
        return
    bar_len = 30
    filled  = round(r["reliability_pct"] / 100 * bar_len)
    bar     = "█" * filled + "░" * (bar_len - filled)
    print(
        f"  {r['author']:<25}  {bar}  {r['reliability_pct']:5.1f}%  "
        f"({r.get('correct',0)}✓ {r.get('partial',0)}~ {r.get('incorrect',0)}✗ / {total})"
    )


# ─── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reliability",
        description="Scrape op-eds, extract predictions, check outcomes, rate authors.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands (use --run):
  scrape       Scrape historical op-eds for all (or --author) authors
  extract      Extract predictions from scraped articles
  check        Check prediction outcomes via web search + Claude
  rate         Compute & display reliability ratings
  full         Run entire pipeline end-to-end (scrape→extract→check→rate)
  report       Print a full prediction report for an author (requires --author)

Examples:
  python reliability.py --run scrape --author "Paul Krugman"
  python reliability.py --run extract --author "George Monbiot"
  python reliability.py --run check --author "David Brooks" --limit 20
  python reliability.py --run rate
  python reliability.py --run full --author "Ezra Klein"
  python reliability.py --run report --author "Paul Krugman"
        """
    )
    p.add_argument("--run",    required=True,
                   choices=["scrape","extract","check","rate","full","report"],
                   help="Pipeline stage to run")
    p.add_argument("--author", default="",
                   help="Limit to one author (default: all configured authors)")
    p.add_argument("--limit",  type=int, default=0,
                   help="Max predictions to check per author (0=all)")
    p.add_argument("--no-bodies", action="store_true",
                   help="Skip fetching full article bodies during scrape")
    p.add_argument("--db",     default=DB_PATH,
                   help=f"SQLite database path (default: {DB_PATH})")
    return p


def run_scrape(authors: list[str], conn: sqlite3.Connection,
               fetch_bodies: bool = True) -> None:
    print(f"\n{'─'*60}\n  SCRAPE  ({len(authors)} authors)\n{'─'*60}")
    for author in authors:
        print(f"\n  ► {author}")
        scrape_author_archive(author, conn, fetch_bodies=fetch_bodies)


def run_extract(authors: list[str], conn: sqlite3.Connection) -> None:
    print(f"\n{'─'*60}\n  EXTRACT PREDICTIONS  ({len(authors)} authors)\n{'─'*60}")
    for author in authors:
        articles = conn.execute(
            "SELECT id,title,body FROM articles WHERE author=?",
            (author,)
        ).fetchall()
        print(f"\n  ► {author}  ({len(articles)} articles)")
        total = 0
        for art in articles:
            n = extract_predictions(art["id"], art["title"], art["body"], author, conn)
            if n:
                print(f"      {art['title'][:60]:<60}  +{n} predictions")
                total += n
            time.sleep(0.3)
        print(f"    → {total} new predictions extracted")


def run_check(authors: list[str], conn: sqlite3.Connection, limit: int = 0) -> None:
    print(f"\n{'─'*60}\n  CHECK OUTCOMES  ({len(authors)} authors)\n{'─'*60}")
    for author in authors:
        # Only check predictions from articles older than 6 months
        from datetime import timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y-%m-%d")
        preds = conn.execute("""
            SELECT p.id, p.claim, p.author, a.published
            FROM predictions p
            JOIN articles a ON p.article_id = a.id
            LEFT JOIN outcomes o ON o.prediction_id = p.id
            WHERE p.author = ? AND o.id IS NULL
            ORDER BY a.published DESC
        """, (author,)).fetchall()
        # Filter by date in Python since SQLite date comparison is tricky with mixed formats
        preds = [p for p in preds if is_old_enough(p["published"])]

        if limit:
            preds = preds[:limit]

        print(f"\n  ► {author}  ({len(preds)} unchecked)")
        for pred in preds:
            print(f"      Checking: {pred['claim'][:70]}…")
            success = check_prediction_outcome(
                pred["id"], pred["claim"], pred["author"], pred["published"], conn
            )
            if not success:
                print(f"      ⏳ rate limited, waiting 60s...")
                time.sleep(60.0)  # back off on failure
            else:
                time.sleep(8.0)   # polite delay between checks


def run_rate(authors: list[str], conn: sqlite3.Connection) -> None:
    print(f"\n{'═'*60}")
    print(f"  RELIABILITY RATINGS")
    print(f"{'═'*60}\n")
    ratings = []
    for author in authors:
        r = build_author_rating(author, conn)
        ratings.append(r)
    ratings.sort(key=lambda x: x["reliability_pct"], reverse=True)
    for r in ratings:
        print_rating(r)
    print()


def run_report(author: str, conn: sqlite3.Connection) -> None:
    print(f"\n{'═'*60}")
    print(f"  PREDICTION REPORT: {author}")
    print(f"{'═'*60}\n")

    rows = conn.execute("""
        SELECT p.claim, p.predicted_year, a.title, a.published,
               o.verdict, o.score, o.outcome_text, o.confidence
        FROM predictions p
        JOIN articles a    ON p.article_id    = a.id
        LEFT JOIN outcomes o ON o.prediction_id = p.id
        WHERE p.author = ?
        ORDER BY a.published DESC
    """, (author,)).fetchall()

    if not rows:
        print(f"  No predictions found for {author}.")
        return

    for r in rows:
        verdict_icon = {"correct":"✓","partial":"~","incorrect":"✗",
                        "pending":"⏳","unverifiable":"?"}.get(r["verdict"] or "pending","·")
        print(f"  {verdict_icon}  [{r['published'] or '?':>10}]  {r['claim'][:80]}")
        if r["outcome_text"]:
            print(f"       → {r['outcome_text'][:100]}")
        print()


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()
    conn   = init_db(args.db)

    all_authors = list(AUTHOR_ARCHIVE_URLS.keys())
    authors     = [args.author] if args.author else all_authors

    if args.run == "scrape":
        run_scrape(authors, conn, fetch_bodies=not args.no_bodies)
    elif args.run == "extract":
        run_extract(authors, conn)
    elif args.run == "check":
        run_check(authors, conn, limit=args.limit)
    elif args.run == "rate":
        run_rate(authors, conn)
    elif args.run == "full":
        run_scrape(authors, conn, fetch_bodies=not args.no_bodies)
        run_extract(authors, conn)
        run_check(authors, conn, limit=args.limit)
        run_rate(authors, conn)
    elif args.run == "report":
        if not args.author:
            print("--author required for report mode", file=sys.stderr)
            sys.exit(1)
        run_report(args.author, conn)

    conn.close()


if __name__ == "__main__":
    main()
