import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import config
from scanner import normalize

API_BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w342"
REQUEST_TIMEOUT_SECONDS = 8


def is_enabled():
    return bool(config.TMDB_READ_ACCESS_TOKEN.strip())


def _now():
    return datetime.now(timezone.utc).isoformat()


def _normalized_title(title):
    return normalize.normalize_movie_title(title)


def _cache_key(media_type, title, year):
    year_part = str(year) if media_type == "movie" and year else "unknown"
    return f"{media_type}:{_normalized_title(title)}:{year_part}"


def _candidate_title(candidate, media_type):
    if media_type == "movie":
        return candidate.get("title") or candidate.get("original_title")
    return candidate.get("name") or candidate.get("original_name")


def _find_exact_match(results, media_type, title):
    expected = _normalized_title(title)
    for candidate in results:
        names = (
            (candidate.get("title"), candidate.get("original_title"))
            if media_type == "movie"
            else (candidate.get("name"), candidate.get("original_name"))
        )
        if any(name and _normalized_title(name) == expected for name in names):
            return candidate
    return None


def _search(media_type, title, year):
    params = {
        "query": title,
        "include_adult": "false",
        "language": config.TMDB_LANGUAGE,
        "page": 1,
    }
    if media_type == "movie" and year:
        params["primary_release_year"] = year

    url = f"{API_BASE_URL}/search/{media_type}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {config.TMDB_READ_ACCESS_TOKEN.strip()}",
            "User-Agent": "Framekeeper/0.1",
        },
    )
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        payload = json.load(response)
    return _find_exact_match(payload.get("results", []), media_type, title)


def find_poster_path(conn, media_type, title, year=None):
    if media_type not in {"movie", "tv"} or not title or not is_enabled():
        return None

    key = _cache_key(media_type, title, year)
    cached = conn.execute(
        "SELECT poster_path FROM poster_cache WHERE cache_key = ?", (key,)
    ).fetchone()
    if cached is not None:
        return cached["poster_path"]

    try:
        match = _search(media_type, title, year)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError):
        # Retry temporary TMDB failures later instead of caching them forever.
        return None

    poster_path = match.get("poster_path") if match else None
    status = "found" if poster_path else "not_found"
    conn.execute(
        """
        INSERT INTO poster_cache (
            cache_key, media_type, title, year, tmdb_id, matched_title,
            poster_path, fetched_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(cache_key) DO UPDATE SET
            tmdb_id=excluded.tmdb_id,
            matched_title=excluded.matched_title,
            poster_path=excluded.poster_path,
            fetched_at=excluded.fetched_at,
            status=excluded.status
        """,
        (
            key,
            media_type,
            title,
            year,
            match.get("id") if match else None,
            _candidate_title(match, media_type) if match else None,
            poster_path,
            _now(),
            status,
        ),
    )
    conn.commit()
    return poster_path


def poster_url(poster_path):
    if not poster_path or not poster_path.startswith("/"):
        return None
    return f"{IMAGE_BASE_URL}{poster_path}"
