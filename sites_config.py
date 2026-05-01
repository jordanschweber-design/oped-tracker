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

    # ── Haaretz (English) — via Google News aggregation ──────────────────────
    "haaretz_rss": {
        "name":        "Haaretz",
        "group":       "Israel",
        "opinion_url": "https://news.google.com/rss/search?q=site:haaretz.com+opinion&hl=en-US&gl=US&ceid=US:en",
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
        "opinion_url": "https://www.timesofisrael.com/blogs/feed/",
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
    # Al Jazeera via Google News — filters by author name
    "Marwan Bishara":     ["https://news.google.com/rss/search?q=site:aljazeera.com+%22Marwan+Bishara%22&hl=en-US&gl=US&ceid=US:en"],
    "Daoud Kuttab":       ["https://news.google.com/rss/search?q=site:aljazeera.com+%22Daoud+Kuttab%22&hl=en-US&gl=US&ceid=US:en"],
    "Ramzy Baroud":       ["https://news.google.com/rss/search?q=site:aljazeera.com+%22Ramzy+Baroud%22&hl=en-US&gl=US&ceid=US:en"],
    "Khaled Diab":        ["https://news.google.com/rss/search?q=site:aljazeera.com+%22Khaled+Diab%22&hl=en-US&gl=US&ceid=US:en"],

    # Haaretz
    # Haaretz via Google News — filters by author name in title/description
    "Gideon Levy":        ["https://news.google.com/rss/search?q=site:haaretz.com+%22Gideon+Levy%22&hl=en-US&gl=US&ceid=US:en"],
    "Amira Hass":         ["https://news.google.com/rss/search?q=site:haaretz.com+%22Amira+Hass%22&hl=en-US&gl=US&ceid=US:en"],
    "Chemi Shalev":       ["https://news.google.com/rss/search?q=site:haaretz.com+%22Chemi+Shalev%22&hl=en-US&gl=US&ceid=US:en"],
    "Anshel Pfeffer":     ["https://news.google.com/rss/search?q=site:haaretz.com+%22Anshel+Pfeffer%22&hl=en-US&gl=US&ceid=US:en"],
    "Bradley Burston":    ["https://news.google.com/rss/search?q=site:haaretz.com+%22Bradley+Burston%22&hl=en-US&gl=US&ceid=US:en"],

    # Jerusalem Post
    "Caroline Glick":     ["https://news.google.com/rss/search?q=site:jpost.com+%22Caroline+Glick%22&hl=en-US&gl=US&ceid=US:en"],
    "Gil Troy":           ["https://news.google.com/rss/search?q=site:jpost.com+%22Gil+Troy%22&hl=en-US&gl=US&ceid=US:en"],
    "Seth Frantzman":     ["https://news.google.com/rss/search?q=site:jpost.com+%22Seth+Frantzman%22&hl=en-US&gl=US&ceid=US:en"],
    "Ruthie Blum":        ["https://news.google.com/rss/search?q=site:jpost.com+%22Ruthie+Blum%22&hl=en-US&gl=US&ceid=US:en"],

    # Times of Israel
    "David Horovitz":     ["https://news.google.com/rss/search?q=site:timesofisrael.com+%22David+Horovitz%22&hl=en-US&gl=US&ceid=US:en"],
    "Haviv Rettig Gur":   ["https://news.google.com/rss/search?q=site:timesofisrael.com+%22Haviv+Rettig+Gur%22&hl=en-US&gl=US&ceid=US:en"],

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


# ─── Topic theme map ──────────────────────────────────────────────────────────
# Maps broad themes to lists of keywords. Used to bucket raw article keywords
# into meaningful categories for display on the dashboard.

THEME_MAP: dict[str, list[str]] = {
    "Middle East": [
        "iran","israel","gaza","palestine","palestinian","palestinians","hamas",
        "hezbollah","jerusalem","lebanon","netanyahu","hormuz","israeli","arab",
        "jordan","egypt","saudi","yemen","syria","iraq","occupied","intifada"
    ],
    "US Politics": [
        "trump","biden","democrat","democratic","republican","congress","senate",
        "election","maga","white","house","hegseth","harris","obama","constitution",
        "impeach","midterm","doge","musk","elon","tariff","tariffs","administration"
    ],
    "Global Economics": [
        "economy","trade","gdp","inflation","recession","market","dollar","interest",
        "rate","fed","fiscal","debt","deficit","imf","supply","chain","globalization",
        "growth","employment","wages","bank","financial","currency"
    ],
    "Democracy & Authoritarianism": [
        "democracy","autocracy","authoritarian","illiberal","orban","populism",
        "freedom","rights","fascism","dictatorship","disinformation","propaganda",
        "censorship","liberties","rule","law","institutions","checks","balances"
    ],
    "Climate & Environment": [
        "climate","environment","carbon","emissions","energy","fossil","renewable",
        "green","solar","oil","gas","pollution","warming","paris","epa","nature"
    ],
    "Technology & AI": [
        "tech","technology","intelligence","silicon","google","apple","facebook",
        "meta","amazon","data","privacy","surveillance","social","media","algorithm",
        "digital","software","hardware","startup","innovation"
    ],
    "UK & European Politics": [
        "britain","uk","brexit","starmer","labour","tory","conservative","parliament",
        "europe","nato","france","germany","macron","sunak","keir","brussels"
    ],
    "Race & Social Justice": [
        "race","racism","racial","black","diversity","dei","inequality","justice",
        "discrimination","civil","affirmative","police","protest","equity"
    ],
    "China & Asia": [
        "china","chinese","beijing","taiwan","hong","kong","asia","japan","korea",
        "pacific","tiktok","huawei","decoupling","indo"
    ],
    "Russia & Ukraine": [
        "russia","ukraine","putin","zelensky","moscow","kyiv","sanctions","crimea",
        "donbas","russian","ukrainian","nato","volodymyr"
    ],
    "Immigration": [
        "immigration","immigrant","migrants","border","deportation","asylum","refugee",
        "visa","undocumented","daca","dreamers","illegal"
    ],
    "Media & Culture": [
        "media","journalism","press","culture","art","film","book","writer","speech",
        "cancel","woke","college","university","education","academia"
    ],
}


def get_author_themes(topics_str: str) -> list[str]:
    """Convert raw topic keywords to broad theme buckets."""
    if not topics_str:
        return []
    keywords = [t.strip().lower() for t in topics_str.split(",")]
    theme_hits: dict[str, int] = {}
    for kw in keywords:
        for theme, words in THEME_MAP.items():
            if any(w in kw or kw in w for w in words):
                theme_hits[theme] = theme_hits.get(theme, 0) + 1
    # Return themes sorted by how many keywords matched, top 3
    return [t for t, _ in sorted(theme_hits.items(), key=lambda x: x[1], reverse=True)][:3]


# ─── Broad theme definitions ──────────────────────────────────────────────────

THEME_MAP: dict[str, list[str]] = {
    "US Politics":          ["trump","biden","democrats","republicans","congress","election",
                             "senate","maga","presidency","partisan","vote","midterm","campaign",
                             "gop","liberal","conservative","white house","political"],
    "Foreign Policy":       ["iran","ukraine","china","russia","nato","diplomacy","nuclear",
                             "war","britain","europe","starmer","labour","brexit","eu","sanctions",
                             "treaty","foreign","international","global","macron","germany",
                             "france","japan","india","korea","taiwan"],
    "Economy":              ["trade","tariffs","inflation","gdp","jobs","recession","markets",
                             "fiscal","economy","economic","deficit","debt","tax","growth",
                             "wages","unemployment","reserve","interest","dollar","budget",
                             "spending","wealth","inequality","poverty","business"],
    "Middle East":          ["israel","gaza","palestinians","jerusalem","hamas","west bank",
                             "arab","netanyahu","idf","hezbollah","lebanon","syria","iraq",
                             "saudi","qatar","dubai","hormuz","occupation","ceasefire"],
    "Climate & Environment":["climate","energy","oil","emissions","environment","carbon",
                             "fossil","renewable","solar","wind","green","warming","paris",
                             "pollution","sustainability"],
    "Technology & AI":      ["tech","silicon","artificial","data","surveillance","social media",
                             "algorithm","privacy","facebook","google","twitter","tiktok",
                             "openai","automation","robots","cyber","digital","platform"],
    "Media & Culture":      ["journalism","media","culture","books","film","arts","news",
                             "press","television","hollywood","entertainment","podcast",
                             "speech","disinformation","propaganda","narrative"],
    "Health & Science":     ["health","covid","vaccines","medical","pandemic","disease",
                             "science","research","mental","opioid","cancer","hospital",
                             "drug","pharmaceutical"],
}


def get_author_themes(topics_text: str) -> list[str]:
    """Map raw keyword topics to broad theme names."""
    if not topics_text:
        return []
    text = topics_text.lower()
    matched = []
    for theme, keywords in THEME_MAP.items():
        if any(kw in text for kw in keywords):
            matched.append(theme)
    return matched
