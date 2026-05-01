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

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)   # allow dashboard (file://) to call localhost

@app.get("/")
def index():
    return app.send_static_file("dashboard.html")


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

    conn.close()

    return jsonify({
        "author":       author,
        "rating":       dict(rating) if rating else {},
        "fact_rating":  dict(fact_rating) if fact_rating else {},
        "predictions":  [dict(p) for p in preds],
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
        SELECT author, reliability_pct, total_checked, correct, incorrect, avg_score
        FROM ratings
        WHERE total_checked >= 3
        ORDER BY reliability_pct DESC
    """).fetchall()
    conn.close()
    data = [dict(r) for r in rows]
    return jsonify({
        "top":    data[:10],
        "bottom": data[-10:][::-1],
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
