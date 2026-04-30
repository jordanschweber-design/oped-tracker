"""
sites_config.py — Master config for all supported news outlets.

Drop this file in the same folder as scraper.py and reliability.py.
Both scripts import from it automatically.

Adding a new site:
  1. Add an entry to SITES (RSS preferred, HTML fallback)
  2. Add authors to NOTABLE_AUTHORS[site_key]
  3. Add archive URLs to AUTHOR_ARCHIVE_URLS[author_name]
"""

# ─── Site definitions ─────────────────────────────────────────────────────────

SITES: dict[str, dict] = {

    # ── Existing ──────────────────────────────────────────────────────────────
    "nyt_rss": {
        "name":        "New York Times",
        "group":       "US",
        "opinion_url": "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml",
        "type":        "rss",
    },
    "guardian_rss": {
        "name":        "The Guardian",
        "group":       "UK",
        "opinion_url": "https://www.theguardian.com/commentisfree/rss",
        "type":        "rss",
    },
    "wapo": {
        "name":        "Washington Post",
        "group":       "US",
        "opinion_url": "https://www.washingtonpost.com/opinions/",
        "base_url":    "https://www.washingtonpost.com",
        "article_selector": "div.story-headline",
        "title_selector":   "h3",
        "author_selector":  "span.author-name",
        "link_selector":    "a",
    },
    "atlantic": {
        "name":        "The Atlantic",
        "group":       "US",
        "opinion_url": "https://www.theatlantic.com/ideas/",
        "base_url":    "https://www.theatlantic.com",
        "article_selector": "article",
        "title_selector":   "h2",
        "author_selector":  "span.author",
        "link_selector":    "a",
    },

    # ── CNN ───────────────────────────────────────────────────────────────────
    "cnn_rss": {
        "name":        "CNN",
        "group":       "US",
        "opinion_url": "http://rss.cnn.com/rss/cnn_allpolitics.rss",
        "type":        "rss",
        # CNN removed its dedicated opinion RSS; politics feed is the closest proxy.
        # Authors are filtered per-author via byline pages below.
    },

    # ── Fox News ──────────────────────────────────────────────────────────────
    "fox_rss": {
        "name":        "Fox News",
        "group":       "US",
        "opinion_url": "https://moxie.foxnews.com/google-publisher/opinion.xml",
        "type":        "rss",
    },

    # ── BBC ───────────────────────────────────────────────────────────────────
    "bbc_rss": {
        "name":        "BBC News",
        "group":       "UK",
        # BBC doesn't have a standalone opinion RSS; Analysis & Comment is closest
        "opinion_url": "http://feeds.bbci.co.uk/news/rss.xml",
        "type":        "rss",
    },

    # ── NPR ───────────────────────────────────────────────────────────────────
    "npr_rss": {
        "name":        "NPR",
        "group":       "US",
        "opinion_url": "https://feeds.npr.org/1057/rss.xml",   # NPR Opinion
        "type":        "rss",
    },

    # ── Al Jazeera ────────────────────────────────────────────────────────────
    "aljazeera_rss": {
        "name":        "Al Jazeera",
        "group":       "Middle East",
        "opinion_url": "https://www.aljazeera.com/xml/rss/all.xml",
        "type":        "rss",
    },

    # ── Haaretz (English) ─────────────────────────────────────────────────────
    "haaretz_rss": {
        "name":        "Haaretz",
        "group":       "Israel",
        "opinion_url": "https://www.haaretz.com/srv/haaretz-latest-articles.xml",
        "type":        "rss",
    },

    # ── Jerusalem Post ────────────────────────────────────────────────────────
    "jpost_rss": {
        "name":        "Jerusalem Post",
        "group":       "Israel",
        "opinion_url": "https://rss.jpost.com/rss/rssfeedsopinion.aspx",
        "type":        "rss",
    },

    # ── Times of Israel ───────────────────────────────────────────────────────
    "toi_rss": {
        "name":        "Times of Israel",
        "group":       "Israel",
        "opinion_url": "https://www.timesofisrael.com/feed/",
        "type":        "rss",
    },

    # ── Reuters ───────────────────────────────────────────────────────────────
    "reuters_rss": {
        "name":        "Reuters",
        "group":       "International",
        "opinion_url": "https://feeds.reuters.com/reuters/topNews",
        "type":        "rss",
    },

    # ── The Economist ─────────────────────────────────────────────────────────
    "economist_rss": {
        "name":        "The Economist",
        "group":       "UK",
        "opinion_url": "https://www.economist.com/the-world-this-week/rss.xml",
        "type":        "rss",
    },

    # ── Financial Times ───────────────────────────────────────────────────────
    "ft_rss": {
        "name":        "Financial Times",
        "group":       "UK",
        "opinion_url": "https://www.ft.com/opinion?format=rss",
        "type":        "rss",
    },

    # ── Wall Street Journal ───────────────────────────────────────────────────
    "wsj_rss": {
        "name":        "Wall Street Journal",
        "group":       "US",
        "opinion_url": "https://feeds.a.dj.com/rss/RSSOpinion.xml",
        "type":        "rss",
    },

    # ── Politico ─────────────────────────────────────────────────────────────
    "politico_rss": {
        "name":        "Politico",
        "group":       "US",
        "opinion_url": "https://www.politico.com/rss/politicopicks.xml",
        "type":        "rss",
    },

    # ── The Hill ─────────────────────────────────────────────────────────────
    "hill_rss": {
        "name":        "The Hill",
        "group":       "US",
        "opinion_url": "https://thehill.com/opinion/feed/",
        "type":        "rss",
    },
}


# ─── Notable opinion authors per site ────────────────────────────────────────

NOTABLE_AUTHORS: dict[str, list[str]] = {

    "nyt_rss": [
        "Paul Krugman", "Maureen Dowd", "David Brooks", "Gail Collins",
        "Charles Blow", "Ross Douthat", "Ezra Klein", "Michelle Goldberg",
        "Thomas Friedman", "Bret Stephens", "Nicholas Kristof", "Frank Bruni",
    ],
    "guardian_rss": [
        "George Monbiot", "Polly Toynbee", "Owen Jones", "Simon Jenkins",
        "Gary Younge", "Marina Hyde", "Jonathan Freedland", "Zoe Williams",
        "Hadley Freeman", "Nesrine Malik",
    ],
    "wapo": [
        "Eugene Robinson", "George Will", "Jennifer Rubin", "Dana Milbank",
        "Kathleen Parker", "E.J. Dionne", "Max Boot", "David Ignatius",
        "Megan McArdle", "Robert Kagan", "Fareed Zakaria",
    ],
    "atlantic": [
        "David Frum", "Anne Applebaum", "Adam Serwer", "Conor Friedersdorf",
        "Tom Nichols", "Caitlin Flanagan",
    ],
    "cnn_rss": [
        "Fareed Zakaria", "Van Jones", "S.E. Cupp", "Jill Filipovic",
        "Dean Obeidallah", "Roxanne Jones", "Bob Greene",
    ],
    "fox_rss": [
        "Tucker Carlson", "Laura Ingraham", "Victor Davis Hanson",
        "Newt Gingrich", "Karl Rove", "Ari Fleischer", "Jonathan Turley",
        "Mollie Hemingway", "Miranda Devine",
    ],
    "bbc_rss": [
        "Katty Kay", "Ros Atkins", "John Simpson", "Mark Mardell",
        "Lyse Doucet", "Jeremy Bowen",
    ],
    "npr_rss": [
        "Mara Liasson", "David Folkenflik", "Domenico Montanaro",
        "Mary Louise Kelly", "Ari Shapiro",
    ],
    "aljazeera_rss": [
        "Marwan Bishara", "Ali Younes", "Daoud Kuttab", "Ramzy Baroud",
        "Joseph Massad", "As'ad AbuKhalil", "Khaled Diab",
    ],
    "haaretz_rss": [
        "Gideon Levy", "Amira Hass", "Benny Morris", "Chemi Shalev",
        "Amos Harel", "Yossi Verter", "Anshel Pfeffer", "Bradley Burston",
    ],
    "jpost_rss": [
        "Caroline Glick", "Herb Keinon", "Gil Troy", "Douglas Bloomfield",
        "Ruthie Blum", "Seth Frantzman",
    ],
    "toi_rss": [
        "David Horovitz", "Haviv Rettig Gur", "Raphael Ahren",
        "Mitch Ginsburg", "Jacob Magid",
    ],
    "reuters_rss": [
        "John Lloyd", "Hugo Dixon",
    ],
    "economist_rss": [
        "Bagehot", "Lexington", "Charlemagne",   # pseudonym columns
    ],
    "wsj_rss": [
        "Peggy Noonan", "William Galston", "Kimberley Strassel",
        "Daniel Henninger", "Jason Riley", "Mary Anastasia O'Grady",
    ],
    "politico_rss": [
        "Roger Simon", "Jack Shafer", "Bill Scher",
    ],
    "hill_rss": [
        "Juan Williams", "Liz Peek", "Douglas MacKinnon", "Joe Concha",
    ],
    "ft_rss": [
        "Martin Wolf", "Gideon Rachman", "Janan Ganesh", "Edward Luce",
        "Gillian Tett", "Philip Stephens",
    ],
}


# ─── Author archive URLs ──────────────────────────────────────────────────────
# Maps each author to their byline/profile page(s) for deep historical scraping.

AUTHOR_ARCHIVE_URLS: dict[str, list[str]] = {

    # NYT
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

    # Guardian
    "George Monbiot":     ["https://www.theguardian.com/profile/georgemonbiot/rss"],
    "Polly Toynbee":      ["https://www.theguardian.com/profile/pollytoynbee/rss"],
    "Owen Jones":         ["https://www.theguardian.com/profile/owen-jones/rss"],
    "Simon Jenkins":      ["https://www.theguardian.com/profile/simonjenkins/rss"],
    "Gary Younge":        ["https://www.theguardian.com/profile/garyyounge/rss"],
    "Marina Hyde":        ["https://www.theguardian.com/profile/marinahyde/rss"],
    "Jonathan Freedland": ["https://www.theguardian.com/profile/jonathanfreedland/rss"],
    "Zoe Williams":       ["https://www.theguardian.com/profile/zoewilliams/rss"],
    "Hadley Freeman":     ["https://www.theguardian.com/profile/hadleyfreeman/rss"],
    "Nesrine Malik":      ["https://www.theguardian.com/profile/nesrine-malik/rss"],

    # WaPo
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
    "Fareed Zakaria":     ["https://www.washingtonpost.com/people/fareed-zakaria/",
                           "https://fareedzakaria.com/columns"],

    # Atlantic
    "David Frum":         ["https://www.theatlantic.com/author/david-frum/"],
    "Anne Applebaum":     ["https://www.theatlantic.com/author/anne-applebaum/"],
    "Adam Serwer":        ["https://www.theatlantic.com/author/adam-serwer/"],
    "Conor Friedersdorf": ["https://www.theatlantic.com/author/conor-friedersdorf/"],
    "Tom Nichols":        ["https://www.theatlantic.com/author/tom-nichols/"],
    "Caitlin Flanagan":   ["https://www.theatlantic.com/author/caitlin-flanagan/"],

    # CNN — no per-author archive pages; use full opinion RSS and filter
    "Van Jones":          ["http://rss.cnn.com/rss/cnn_allpolitics.rss"],
    "S.E. Cupp":          ["http://rss.cnn.com/rss/cnn_allpolitics.rss"],
    "Jill Filipovic":     ["http://rss.cnn.com/rss/cnn_allpolitics.rss"],
    "Dean Obeidallah":    ["http://rss.cnn.com/rss/cnn_allpolitics.rss"],
    "Roxanne Jones":      ["http://rss.cnn.com/rss/cnn_allpolitics.rss"],

    # Fox
    "Victor Davis Hanson":["https://moxie.foxnews.com/google-publisher/opinion.xml"],
    "Newt Gingrich":      ["https://moxie.foxnews.com/google-publisher/opinion.xml"],
    "Karl Rove":          ["https://moxie.foxnews.com/google-publisher/opinion.xml"],
    "Ari Fleischer":      ["https://moxie.foxnews.com/google-publisher/opinion.xml"],
    "Jonathan Turley":    ["https://moxie.foxnews.com/google-publisher/opinion.xml"],
    "Mollie Hemingway":   ["https://moxie.foxnews.com/google-publisher/opinion.xml"],
    "Miranda Devine":     ["https://moxie.foxnews.com/google-publisher/opinion.xml"],

    # BBC — no per-author RSS; filter from main feed
    "Katty Kay":          ["http://feeds.bbci.co.uk/news/rss.xml"],
    "John Simpson":       ["http://feeds.bbci.co.uk/news/rss.xml"],
    "Mark Mardell":       ["http://feeds.bbci.co.uk/news/rss.xml"],
    "Lyse Doucet":        ["http://feeds.bbci.co.uk/news/rss.xml"],
    "Jeremy Bowen":       ["http://feeds.bbci.co.uk/news/rss.xml"],

    # NPR
    "Mara Liasson":       ["https://feeds.npr.org/1057/rss.xml"],
    "Domenico Montanaro": ["https://feeds.npr.org/1057/rss.xml"],

    # Al Jazeera
    # Al Jazeera uses numeric IDs in author URLs — fall back to main RSS feed filtered by name
    "Marwan Bishara":     ["https://www.aljazeera.com/xml/rss/all.xml"],
    "Daoud Kuttab":       ["https://www.aljazeera.com/xml/rss/all.xml"],
    "Ramzy Baroud":       ["https://www.aljazeera.com/xml/rss/all.xml"],
    "Khaled Diab":        ["https://www.aljazeera.com/xml/rss/all.xml"],

    # Haaretz
    # Haaretz writer pages require login — use RSS feed filtered by name
    "Gideon Levy":        ["https://www.haaretz.com/srv/haaretz-latest-articles.xml"],
    "Amira Hass":         ["https://www.haaretz.com/srv/haaretz-latest-articles.xml"],
    "Chemi Shalev":       ["https://www.haaretz.com/srv/haaretz-latest-articles.xml"],
    "Anshel Pfeffer":     ["https://www.haaretz.com/srv/haaretz-latest-articles.xml"],
    "Bradley Burston":    ["https://www.haaretz.com/srv/haaretz-latest-articles.xml"],

    # Jerusalem Post
    "Caroline Glick":     ["https://rss.jpost.com/rss/rssfeedsopinion.aspx"],
    "Gil Troy":           ["https://rss.jpost.com/rss/rssfeedsopinion.aspx"],
    "Seth Frantzman":     ["https://rss.jpost.com/rss/rssfeedsopinion.aspx"],
    "Ruthie Blum":        ["https://rss.jpost.com/rss/rssfeedsopinion.aspx"],

    # Times of Israel
    # Times of Israel — use main feed filtered by name
    "David Horovitz":     ["https://www.timesofisrael.com/feed/"],
    "Haviv Rettig Gur":   ["https://www.timesofisrael.com/feed/"],

    # WSJ
    "Peggy Noonan":       ["https://feeds.a.dj.com/rss/RSSOpinion.xml"],
    "Kimberley Strassel": ["https://feeds.a.dj.com/rss/RSSOpinion.xml"],
    "Daniel Henninger":   ["https://feeds.a.dj.com/rss/RSSOpinion.xml"],
    "Jason Riley":        ["https://feeds.a.dj.com/rss/RSSOpinion.xml"],
    "William Galston":    ["https://feeds.a.dj.com/rss/RSSOpinion.xml"],
    "Mary Anastasia O'Grady": ["https://feeds.a.dj.com/rss/RSSOpinion.xml"],

    # FT
    "Martin Wolf":        ["https://www.ft.com/martin-wolf"],
    "Gideon Rachman":     ["https://www.ft.com/gideon-rachman"],
    "Janan Ganesh":       ["https://www.ft.com/janan-ganesh"],
    "Edward Luce":        ["https://www.ft.com/edward-luce"],
    "Gillian Tett":       ["https://www.ft.com/gillian-tett"],

    # Hill
    "Juan Williams":      ["https://thehill.com/opinion/feed/"],
    "Liz Peek":           ["https://thehill.com/opinion/feed/"],
    "Joe Concha":         ["https://thehill.com/opinion/feed/"],
}


# ─── Site label map for dashboard ────────────────────────────────────────────
# Maps author name → short site label used for colour-coding in the UI

def get_author_site(author: str) -> str:
    for site_key, authors in NOTABLE_AUTHORS.items():
        if author in authors:
            site_cfg = SITES.get(site_key, {})
            return site_cfg.get("name", site_key)
    return "Other"


SITE_GROUPS: dict[str, list[str]] = {}
for _sk, _cfg in SITES.items():
    _group = _cfg.get("group", "Other")
    SITE_GROUPS.setdefault(_group, []).append(_sk)
