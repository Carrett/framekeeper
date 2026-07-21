import re
import unicodedata

LEADING_ARTICLES = {"the", "el", "la", "los", "las", "a", "an", "un", "una"}


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _clean(s):
    s = _strip_accents(s.lower())
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_movie_title(raw_title):
    s = _clean(raw_title)
    tokens = s.split(" ") if s else []
    if tokens and tokens[0] in LEADING_ARTICLES:
        tokens = tokens[1:]
    return " ".join(tokens)


def movie_group_key(raw_title, year):
    return f"{normalize_movie_title(raw_title)}|{year if year else 'unknown'}"


def normalize_series_title(raw_show):
    return normalize_movie_title(raw_show)


def series_group_key(raw_show, season):
    season_part = f"S{season:02d}" if season is not None else "S??"
    return f"{normalize_series_title(raw_show)}|{season_part}"
