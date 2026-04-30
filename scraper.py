#!/usr/bin/env python3
"""
Op-Ed Scraper — fetch opinion pieces from major news sites and analyze with Claude AI.
Leads by well-known major-site columnists / contributors.
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ─── Notable op-ed authors by site ───────────────────────────────────────────
# Import from central config; fallback to inline stub if not present.

try:
    from sites_config import SITES, NOTABLE_AUTHORS
except ImportError:
    NOTABLE_AUTHORS: dict[str, list[str]] = {
    "nyt_rss": [
        "Paul Krugman", "Maureen Dowd", "David Brooks", "Gail Collins",
        "Charles Blow", "Ross Douthat", "Ezra Klein", "Michelle Goldberg",
        "Frank Bruni", "Nicholas Kristof", "Thomas Friedman", "Bret Stephens",
    ],
    "guardian_rss": [
        "George Monbiot", "Polly Toynbee", "Owen Jones", "Simon Jenkins",
        "Gary Younge", "Marina Hyde", "Jonathan Freedland", "Zoe Williams",
        "Hadley Freeman", "Nesrine Malik",
    ],
    "wapo": [
        "Eugene Robinson", "George Will", "Jennifer Rubin", "Dana Milbank",
        "Kathleen Parker", "E.J. Dionne", "Max Boot", "David Ignatius",
        "Megan McArdle", "Robert Kagan",
    ],
    "atlantic": [
        "David Frum", "Anne Applebaum", "Adam Serwer", "Conor Friedersdorf",
        "Ibram X. Kendi", "Yair Rosenberg", "Tom Nichols", "Caitlin Flanagan",
    ],
    "nyt": [
        "Paul Krugman", "Maureen Dowd", "David Brooks", "Gail Collins",
        "Charles Blow", "Ross Douthat", "Ezra Klein", "Thomas Friedman",
    ],
    "guardian": [
        "George Monbiot", "Polly Toynbee", "Owen Jones", "Simon Jenkins",
        "Gary Younge", "Marina Hyde",
    ],
}  # end fallback stub

# ─── Site configurations (used when sites_config.py not present) ─────────────

try:
    from sites_config import SITES
except ImportError:
    SITES = {
    "nyt": {
        "name": "New York Times",
        "opinion_url": "https://www.nytimes.com/section/opinion",
        "base_url": "https://www.nytimes.com",
        "article_selector": "article",
        "title_selector": "h3",
        "author_selector": "p.css-1n7hynb",
        "link_selector": "a",
    },
    "wapo": {
        "name": "Washington Post",
        "opinion_url": "https://www.washingtonpost.com/opinions/",
        "base_url": "https://www.washingtonpost.com",
        "article_selector": "div.story-headline",
        "title_selector": "h3",
        "author_selector": "span.author-name",
        "link_selector": "a",
    },
    "guardian": {
        "name": "The Guardian",
        "opinion_url": "https://www.theguardian.com/uk/commentisfree",
        "base_url": "https://www.theguardian.com",
        "article_selector": "div.fc-item__content",
        "title_selector": "span.js-headline-text",
        "author_selector": "span.fc-item__byline",
        "link_selector": "a.fc-item__link",
    },
    "atlantic": {
        "name": "The Atlantic",
        "opinion_url": "https://www.theatlantic.com/ideas/",
        "base_url": "https://www.theatlantic.com",
        "article_selector": "article",
        "title_selector": "h2",
        "author_selector": "span.author",
        "link_selector": "a",
    },
    "nytimes_rss": {
        "name": "NYT Opinion (RSS)",
        "opinion_url": "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml",
        "type": "rss",
    },
    "guardian_rss": {
        "name": "Guardian Opinion (RSS)",
        "opinion_url": "https://www.theguardian.com/commentisfree/rss",
        "type": "rss",
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ─── Scraping helpers ─────────────────────────────────────────────────────────

def fetch_page(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch a URL and return HTML text, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  ⚠  Could not fetch {url}: {e}", file=sys.stderr)
        return None


def parse_rss(xml_text: str, keyword: str = "", author: str = "") -> list[dict]:
    """Parse RSS/Atom feed and return matching articles."""
    soup = BeautifulSoup(xml_text, "xml")
    items = soup.find_all("item") or soup.find_all("entry")
    results = []
    for item in items:
        def txt(tag): return tag.get_text(strip=True) if tag else ""
        title   = txt(item.find("title"))
        link    = txt(item.find("link"))
        desc    = txt(item.find("description") or item.find("summary"))
        pub     = txt(item.find("pubDate") or item.find("published"))
        creator = txt(item.find("dc:creator") or item.find("author"))

        if keyword and keyword.lower() not in (title + desc).lower():
            continue
        if author and author.lower() not in creator.lower():
            continue

        results.append({
            "title": title,
            "url": link,
            "author": creator,
            "snippet": desc[:300] + "…" if len(desc) > 300 else desc,
            "published": pub,
        })
    return results


def scrape_site(site_key: str, keyword: str = "", author: str = "",
                section_url: str = "") -> list[dict]:
    """Scrape one site and return a list of article dicts."""
    cfg = SITES.get(site_key)
    if not cfg:
        print(f"  ✗  Unknown site key: {site_key}", file=sys.stderr)
        return []

    url = section_url or cfg["opinion_url"]
    print(f"  → Fetching {cfg['name']} ({url})")

    html = fetch_page(url)
    if not html:
        return []

    # RSS path
    if cfg.get("type") == "rss":
        return parse_rss(html, keyword=keyword, author=author)

    # HTML path
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select(cfg["article_selector"]) or soup.find_all("article")
    results = []

    for art in articles[:30]:
        a_tag   = art.select_one(cfg["link_selector"]) or art.find("a")
        h_tag   = art.select_one(cfg["title_selector"]) or art.find(["h2", "h3", "h4"])
        by_tag  = art.select_one(cfg["author_selector"])

        title   = h_tag.get_text(strip=True)   if h_tag   else ""
        by_line = by_tag.get_text(strip=True)  if by_tag  else ""
        href    = a_tag["href"]                if a_tag and a_tag.get("href") else ""

        if not title:
            continue
        if keyword and keyword.lower() not in title.lower():
            continue
        if author and author.lower() not in by_line.lower():
            continue

        if href and href.startswith("/"):
            href = cfg["base_url"] + href

        results.append({
            "title":     title,
            "url":       href,
            "author":    by_line,
            "snippet":   "",
            "published": "",
        })

    return results


def scrape_by_authors(site_key: str, authors: list[str],
                      keyword: str = "", section_url: str = "") -> list[dict]:
    """Scrape a site filtered to a list of known authors."""
    results = []
    for author in authors:
        articles = scrape_site(site_key, keyword=keyword, author=author,
                               section_url=section_url)
        for a in articles:
            a.setdefault("author", author)
        results.extend(articles)
        time.sleep(0.2)
    return results


def scrape_all_by_notable_authors(site_keys: list[str], keyword: str = "",
                                  section_url: str = "") -> list[dict]:
    """
    Lead by major op-ed authors: for each site scan its known columnists first,
    collecting their latest pieces. Falls back to full-feed scrape for sites
    with no author list defined.
    """
    all_articles: list[dict] = []
    for site_key in site_keys:
        authors = NOTABLE_AUTHORS.get(site_key, [])
        if authors:
            site_name = SITES.get(site_key, {}).get("name", site_key)
            print(f"\n  ✦ {site_name} — scanning {len(authors)} notable authors")
            articles = scrape_by_authors(site_key, authors,
                                         keyword=keyword, section_url=section_url)
        else:
            articles = scrape_site(site_key, keyword=keyword,
                                   section_url=section_url)
        all_articles.extend(articles)
    return all_articles


def fetch_article_text(url: str) -> str:
    """Best-effort extraction of article body text."""
    html = fetch_page(url)
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    # Remove nav/header/footer/ads
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "figure"]):
        tag.decompose()
    paragraphs = soup.find_all("p")
    text = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
    return text[:8000]   # cap for API context window


# ─── Claude AI analysis ───────────────────────────────────────────────────────

def analyze_with_claude(articles: list[dict], mode: str = "summary") -> str:
    """Send articles to Claude and return the analysis."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return (
            "\n⚠  No ANTHROPIC_API_KEY found in environment.\n"
            "Export your key:  export ANTHROPIC_API_KEY=sk-ant-...\n"
        )

    if not articles:
        return "No articles to analyze."

    article_block = ""
    for i, a in enumerate(articles, 1):
        article_block += (
            f"\n--- Article {i} ---\n"
            f"Title:  {a['title']}\n"
            f"Author: {a.get('author', 'Unknown')}\n"
            f"URL:    {a.get('url', '')}\n"
        )
        if a.get("body"):
            article_block += f"Body:\n{a['body'][:3000]}\n"
        elif a.get("snippet"):
            article_block += f"Snippet: {a['snippet']}\n"

    prompts = {
        "summary":   f"Summarize each of the following op-ed pieces in 2-3 sentences, noting the author's main argument:\n{article_block}",
        "themes":    f"Identify the major recurring themes and viewpoints across these op-eds. Group by theme:\n{article_block}",
        "sentiment": f"Analyze the tone and sentiment of each op-ed (positive/negative/neutral) and explain briefly:\n{article_block}",
        "compare":   f"Compare and contrast the perspectives across these op-eds. Note agreements and disagreements:\n{article_block}",
    }
    prompt = prompts.get(mode, prompts["summary"])

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
                "max_tokens": 2048,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except requests.RequestException as e:
        return f"Claude API error: {e}"


# ─── Output helpers ───────────────────────────────────────────────────────────

def print_articles(articles: list[dict], verbose: bool = False,
                   group_by_author: bool = False) -> None:
    print(f"\n{'═'*60}")
    print(f"  Found {len(articles)} op-ed(s)")
    print(f"{'═'*60}")

    if group_by_author and articles:
        by_author: dict[str, list[dict]] = defaultdict(list)
        for a in articles:
            key = a.get("author") or "Unknown"
            by_author[key].append(a)

        for author, pieces in by_author.items():
            print(f"\n  ── {author} ({len(pieces)} piece{'s' if len(pieces)>1 else ''}) ──")
            for a in pieces:
                print(f"    • {a['title']}")
                if a.get("published"):
                    print(f"      Published : {a['published']}")
                if a.get("url"):
                    print(f"      URL       : {a['url']}")
                if verbose and a.get("snippet"):
                    print(f"      Snippet   : {a['snippet'][:200]}…")
        print()
    else:
        print()
        for i, a in enumerate(articles, 1):
            print(f"  [{i}] {a['title']}")
            if a.get("author"):
                print(f"       By: {a['author']}")
            if a.get("published"):
                print(f"       Published: {a['published']}")
            if a.get("url"):
                print(f"       URL: {a['url']}")
            if verbose and a.get("snippet"):
                print(f"       Snippet: {a['snippet'][:200]}…")
            print()


def save_results(articles: list[dict], analysis: str, output_file: str) -> None:
    payload = {
        "scraped_at": datetime.now().isoformat(),
        "article_count": len(articles),
        "articles": articles,
        "analysis": analysis,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Results saved to: {output_file}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scraper",
        description="Scrape op-eds from major news sites and analyze with Claude AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: lead by major authors across NYT + Guardian (author-grouped output)
  python scraper.py --analyze summary

  # Keyword filter across notable authors
  python scraper.py --keyword "climate" --analyze themes

  # Specific sites
  python scraper.py --sites nyt_rss wapo --analyze compare

  # Target one author
  python scraper.py --author "Paul Krugman" --analyze summary

  # Disable author-lead mode (scrape full feed instead)
  python scraper.py --no-author-lead --analyze summary

  # Custom section URL
  python scraper.py --url https://www.nytimes.com/section/opinion

  # Save output
  python scraper.py --keyword "AI" --analyze summary --output results.json

  # List notable authors per site
  python scraper.py --list-authors

Available sites:  nyt  wapo  guardian  atlantic  nyt_rss  guardian_rss
Analysis modes:   summary  themes  sentiment  compare
        """,
    )
    p.add_argument("--sites",    nargs="+", default=["nyt_rss", "guardian_rss"],
                   metavar="SITE", help="Site keys to scrape (default: nyt_rss guardian_rss)")
    p.add_argument("--keyword",  default="", metavar="WORD",
                   help="Filter articles by keyword")
    p.add_argument("--author",   default="", metavar="NAME",
                   help="Override: filter to one specific author name")
    p.add_argument("--no-author-lead", action="store_true",
                   help="Disable author-first mode; scrape the full feed instead")
    p.add_argument("--url",      default="", metavar="URL",
                   help="Scrape a specific section URL instead of the default opinion page")
    p.add_argument("--analyze",  default="", metavar="MODE",
                   choices=["summary", "themes", "sentiment", "compare"],
                   help="Send results to Claude for AI analysis")
    p.add_argument("--fetch-body", action="store_true",
                   help="Fetch full article body text (slower, uses more API tokens)")
    p.add_argument("--output",   default="", metavar="FILE",
                   help="Save results + analysis to a JSON file")
    p.add_argument("--verbose",  action="store_true",
                   help="Print article snippets in the terminal")
    p.add_argument("--list-sites", action="store_true",
                   help="List all supported site keys and exit")
    p.add_argument("--list-authors", action="store_true",
                   help="List notable authors tracked per site and exit")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_sites:
        print("\nSupported sites:\n")
        for key, cfg in SITES.items():
            print(f"  {key:<15} {cfg['name']}")
        print()
        sys.exit(0)

    if args.list_authors:
        print("\nNotable op-ed authors tracked per site:\n")
        for site_key, authors in NOTABLE_AUTHORS.items():
            site_name = SITES.get(site_key, {}).get("name", site_key)
            print(f"  {site_name} ({site_key})")
            for a in authors:
                print(f"    • {a}")
            print()
        sys.exit(0)

    # Determine mode
    author_lead = not args.no_author_lead and not args.author

    print(f"\n{'─'*60}")
    print("  Op-Ed Scraper")
    print(f"{'─'*60}")
    print(f"  Mode    : {'Author-lead (major columnists)' if author_lead else 'Full feed'}")
    if args.keyword:  print(f"  Keyword : {args.keyword}")
    if args.author:   print(f"  Author  : {args.author}")
    if args.url:      print(f"  URL     : {args.url}")
    print(f"  Sites   : {', '.join(args.sites)}")
    print(f"{'─'*60}")

    all_articles: list[dict] = []

    if author_lead:
        # Lead by notable authors — grouped output
        all_articles = scrape_all_by_notable_authors(
            args.sites, keyword=args.keyword, section_url=args.url
        )
    else:
        # Full feed or single-author filter
        for site_key in args.sites:
            articles = scrape_site(
                site_key,
                keyword=args.keyword,
                author=args.author,
                section_url=args.url,
            )
            all_articles.extend(articles)

    if args.fetch_body:
        for a in all_articles:
            if a.get("url"):
                print(f"    Fetching body: {a['url'][:70]}…")
                a["body"] = fetch_article_text(a["url"])
                time.sleep(0.5)

    print_articles(all_articles, verbose=args.verbose, group_by_author=author_lead)

    analysis = ""
    if args.analyze:
        print(f"\n{'─'*60}")
        print(f"  Claude analysis  ({args.analyze})")
        print(f"{'─'*60}\n")
        analysis = analyze_with_claude(all_articles, mode=args.analyze)
        print(analysis)

    if args.output:
        save_results(all_articles, analysis, args.output)


if __name__ == "__main__":
    main()
