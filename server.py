#!/usr/bin/env python3
"""
server.py — Local API server for the op-ed reliability dashboard.
Serves scraped data and ratings from oped_data.db to the browser dashboard.

Usage:
  python server.py              # starts on http://localhost:5000
  python server.py --port 8080
"""

import argparse
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

DB_PATH = "oped_data.db"

app = Flask(__name__)
CORS(app)

@app.get("/")
def index():
    from flask import send_from_directory
    import os
    return send_from_directory(os.getcwd(), "dashboard.html")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/ratings")
def ratings():
    """All author reliability ratings, sorted best→worst."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM ratings ORDER BY reliability_pct DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/authors")
def authors():
    """List of all authors with article + prediction counts."""
    conn = get_db()
    rows = conn.execute("""
        SELECT
            a.author,
            COUNT(DISTINCT a.id)          AS article_count,
            COUNT(DISTINCT p.id)          AS prediction_count,
            COUNT(DISTINCT o.id)          AS checked_count,
            r.reliability_pct,
            r.avg_score,
            r.correct,
            r.partial,
            r.incorrect,
            r.combined_score,
            r.confidence_level,
            r.topics,
            r.last_updated
        FROM articles a
        LEFT JOIN predictions p  ON p.author = a.author
        LEFT JOIN outcomes o     ON o.prediction_id = p.id
        LEFT JOIN ratings r      ON r.author = a.author
        GROUP BY a.author
        ORDER BY a.author
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/author/<path:author>")
def author_detail(author: str):
    """Full prediction+outcome history for one author."""
    conn = get_db()
    preds = conn.execute("""
        SELECT
            p.id, p.claim, p.predicted_year, p.context,
            a.title  AS article_title,
            a.url    AS article_url,
            a.published,
            o.verdict, o.score, o.confidence, o.outcome_text, o.sources, o.checked_at
        FROM predictions p
        JOIN articles a     ON p.article_id    = a.id
        LEFT JOIN outcomes o ON o.prediction_id = p.id
        WHERE p.author = ?
        ORDER BY a.published DESC
    """, (author,)).fetchall()

    rating = conn.execute(
        "SELECT * FROM ratings WHERE author=?", (author,)
    ).fetchone()
    fact_rating = conn.execute(
        "SELECT * FROM author_fact_ratings WHERE author=?", (author,)
    ).fetchone() if "author_fact_ratings" in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()] else None


    # Build per-theme article counts for this author
    theme_breakdown = []
    try:
        from sites_config import THEME_MAP
        conn2 = get_db()
        articles = conn2.execute(
            "SELECT title, body FROM articles WHERE author=?", (author,)
        ).fetchall()
        conn2.close()

        theme_counts = {}
        for art in articles:
            text = ((art["title"] or "") + " " + (art["body"] or "")).lower()
            # Assign each article to ONLY its best-matching theme (most keyword hits)
            best_theme = None
            best_hits = 0
            for theme, keywords in THEME_MAP.items():
                hits = sum(1 for kw in keywords if kw in text)
                if hits > best_hits:
                    best_hits = hits
                    best_theme = theme
            if best_theme and best_hits > 0:
                theme_counts[best_theme] = theme_counts.get(best_theme, 0) + 1

        total = len(articles)
        # Show only top 4 themes by article count
        top_themes = sorted(theme_counts.items(), key=lambda x: -x[1])[:4]
        for theme, count in top_themes:
            score_pct = round(count / total * 100) if total else 0
            theme_breakdown.append({
                "theme":    theme,
                "count":    count,
                "pct":      score_pct,
                "reliable": count >= 3,
            })
    except Exception:
        pass

    return jsonify({
        "author":          author,
        "rating":          dict(rating) if rating else {},
        "fact_rating":     dict(fact_rating) if fact_rating else {},
        "predictions":     [dict(p) for p in preds],
        "theme_breakdown": theme_breakdown,
    })



@app.get("/api/articles/<path:author>")
def author_articles(author: str):
    """All scraped articles for one author."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id,title,url,published,scraped_at FROM articles WHERE author=? "
        "ORDER BY published DESC",
        (author,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/leaderboard")
def leaderboard():
    """Top 10 and bottom 10 authors by reliability."""
    conn = get_db()
    rows = conn.execute("""
        SELECT author, combined_score, reliability_pct, total_checked, correct, incorrect, avg_score
        FROM ratings
        WHERE total_checked >= 5
        ORDER BY combined_score DESC
    """).fetchall()
    conn.close()
    data = [dict(r) for r in rows]
    # Filter to authors with 5+ checked, sort by combined score
    qualified = [d for d in data if d.get("total_checked", 0) >= 5]
    qualified_sorted = sorted(qualified, key=lambda x: x.get("combined_score") or x.get("reliability_pct") or 0, reverse=True)
    return jsonify({
        "top":    qualified_sorted[:10],
        "bottom": qualified_sorted[-10:][::-1] if len(qualified_sorted) > 10 else [],
    })


@app.get("/api/stats")
def stats():
    """Global counts for the dashboard header."""
    conn = get_db()
    def one(sql): return conn.execute(sql).fetchone()[0]
    data = {
        "total_articles":    one("SELECT COUNT(*) FROM articles"),
        "total_predictions": one("SELECT COUNT(*) FROM predictions"),
        "total_checked":     one("SELECT COUNT(*) FROM outcomes"),
        "total_authors":     one("SELECT COUNT(DISTINCT author) FROM articles"),
        "last_updated":      datetime.now().isoformat(),
    }
    conn.close()
    return jsonify(data)


@app.get("/api/predictions/recent")
def recent_predictions():
    """Most recently checked predictions across all authors."""
    limit = int(request.args.get("limit", 20))
    conn  = get_db()
    rows  = conn.execute("""
        SELECT p.author, p.claim, a.published, a.title AS article_title,
               o.verdict, o.score, o.outcome_text, o.checked_at
        FROM outcomes o
        JOIN predictions p ON o.prediction_id = p.id
        JOIN articles a    ON p.article_id     = a.id
        ORDER BY o.checked_at DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ─── Entry point ──────────────────────────────────────────────────────────────


@app.get("/api/outlet_ratings")
def outlet_ratings():
    """Per-outlet weighted reliability ratings."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM outlet_ratings ORDER BY avg_reliability DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/fact_ratings")
def fact_ratings():
    """Per-author factual accuracy ratings."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM author_fact_ratings ORDER BY avg_score DESC"
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.get("/api/author_fact/<path:author>")
def author_fact_detail(author: str):
    """Fact check history for one author."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT f.factual_score, f.verdict, f.confidence, f.summary,
                   f.issues_found, f.key_claims, f.checked_at,
                   a.title, a.published, a.url
            FROM fact_checks f
            JOIN articles a ON f.article_id = a.id
            WHERE f.author = ?
            ORDER BY a.published DESC
        """, (author,)).fetchall()
        rating = conn.execute(
            "SELECT * FROM author_fact_ratings WHERE author=?", (author,)
        ).fetchone()
    except Exception:
        rows = []
        rating = None
    conn.close()
    return jsonify({
        "author": author,
        "rating": dict(rating) if rating else {},
        "checks":  [dict(r) for r in rows],
    })


@app.get("/api/outlet_detail/<path:outlet>")
def outlet_detail(outlet: str):
    """Full breakdown for one outlet: authors, scores, aggregated topics."""
    try:
        from sites_config import NOTABLE_AUTHORS, SITES
        # Find authors for this outlet
        author_list = []
        for site_key, authors in NOTABLE_AUTHORS.items():
            if SITES.get(site_key, {}).get("name") == outlet:
                author_list = authors
                break
    except ImportError:
        author_list = []

    conn = get_db()

    # Get ratings for all authors at this outlet
    author_data = []
    all_topics: dict[str, int] = {}

    for author in author_list:
        rating = conn.execute(
            "SELECT * FROM ratings WHERE author=?", (author,)
        ).fetchone()

        # Aggregate topics across all authors
        if rating and rating["topics"]:
            for topic in rating["topics"].split(", "):
                topic = topic.strip()
                if topic:
                    all_topics[topic] = all_topics.get(topic, 0) + 1

        author_data.append({
            "author":          author,
            "combined_score":  dict(rating)["combined_score"] if rating else None,
            "reliability_pct": dict(rating)["reliability_pct"] if rating else None,
            "confidence_level": dict(rating)["confidence_level"] if rating else "low",
            "total_checked":   dict(rating)["total_checked"] if rating else 0,
            "topics":          dict(rating)["topics"] if rating else "",
        })

    # Map raw keywords to broad themes for outlet
    try:
        from sites_config import get_author_themes, THEME_MAP
        outlet_theme_hits: dict[str, int] = {}
        for kw, cnt in all_topics.items():
            for theme, words in THEME_MAP.items():
                if any(w in kw or kw in w for w in words):
                    outlet_theme_hits[theme] = outlet_theme_hits.get(theme, 0) + cnt
        top_topics = sorted(outlet_theme_hits.items(), key=lambda x: x[1], reverse=True)[:6]
    except Exception:
        top_topics = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)[:6]

    # Outlet overall rating
    outlet_rating = conn.execute(
        "SELECT * FROM outlet_ratings WHERE outlet=?", (outlet,)
    ).fetchone()

    conn.close()
    return jsonify({
        "outlet":        outlet,
        "rating":        dict(outlet_rating) if outlet_rating else {},
        "authors":       author_data,
        "top_topics":    [{"topic": t, "count": c} for t, c in top_topics],
    })


@app.get("/api/author_themes")
def all_author_themes():
    """Return theme breakdown for all authors at once — used for sidebar filtering."""
    try:
        from sites_config import THEME_MAP
    except ImportError:
        return jsonify({})

    conn = get_db()
    authors = conn.execute("SELECT DISTINCT author FROM articles").fetchall()
    result = {}

    for row in authors:
        author = row[0]
        articles = conn.execute(
            "SELECT title, body FROM articles WHERE author=?", (author,)
        ).fetchall()

        theme_counts: dict[str, int] = {}
        for art in articles:
            text = ((art["title"] or "") + " " + (art["body"] or "")).lower()
            best_theme, best_hits = None, 0
            for theme, keywords in THEME_MAP.items():
                hits = sum(1 for kw in keywords if kw in text)
                if hits > best_hits:
                    best_hits, best_theme = hits, theme
            if best_theme:
                theme_counts[best_theme] = theme_counts.get(best_theme, 0) + 1

        total = len(articles)
        result[author] = [
            {"theme": t, "count": c, "pct": round(c/total*100) if total else 0, "reliable": c >= 3}
            for t, c in sorted(theme_counts.items(), key=lambda x: -x[1])[:4]
        ]

    conn.close()
    return jsonify(result)


@app.get("/api/theme_keywords")
def theme_keywords():
    """Return keyword lists per theme for client-side prediction filtering."""
    try:
        from sites_config import THEME_MAP
        return jsonify({theme: kws for theme, kws in THEME_MAP.items()})
    except Exception:
        return jsonify({})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Op-ed reliability dashboard API server")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--db",   default=DB_PATH)
    args = parser.parse_args()

    DB_PATH = args.db
    if not Path(DB_PATH).exists():
        print(f"⚠  Database not found at {DB_PATH}.")
        print("   Run: python reliability.py --run scrape first.")

    print(f"\n  Op-Ed Reliability API")
    print(f"  Running on http://localhost:{args.port}")
    print(f"  Database: {DB_PATH}\n")
    app.run(port=args.port, debug=False)
