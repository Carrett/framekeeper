import json
from collections import defaultdict
from datetime import datetime, timezone
from types import SimpleNamespace

from scanner import normalize, scoring

TECH_COLUMNS = [
    "height",
    "hdr_type",
    "bitrate_total",
    "audio_codec",
    "audio_channels_count",
]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _load_tech_by_item_id(conn, item_ids):
    if not item_ids:
        return {}
    placeholders = ",".join("?" for _ in item_ids)
    rows = conn.execute(
        f"SELECT media_item_id, {', '.join(TECH_COLUMNS)} FROM tech_metadata "
        f"WHERE media_item_id IN ({placeholders})",
        item_ids,
    ).fetchall()
    result = {}
    for row in rows:
        d = dict(row)
        item_id = d.pop("media_item_id")
        result[item_id] = SimpleNamespace(**d)
    return result


def _upsert_duplicate_group(conn, media_type, group_key, display_title, now):
    conn.execute(
        """
        INSERT INTO duplicate_group (media_type, group_key, display_title, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(media_type, group_key) DO UPDATE SET
            display_title = excluded.display_title,
            updated_at = excluded.updated_at
        """,
        (media_type, group_key, display_title, now, now),
    )
    row = conn.execute(
        "SELECT id FROM duplicate_group WHERE media_type = ? AND group_key = ?",
        (media_type, group_key),
    ).fetchone()
    return row["id"]


def _replace_group_members(conn, group_id, scored_members):
    conn.execute("DELETE FROM duplicate_group_member WHERE group_id = ?", (group_id,))
    for m in scored_members:
        conn.execute(
            """
            INSERT INTO duplicate_group_member
                (group_id, media_item_id, quality_score, score_breakdown_json, is_recommended_keep)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                group_id,
                m["media_item_id"],
                m["score"].total,
                json.dumps(m["score"].breakdown),
                1 if m["is_recommended_keep"] else 0,
            ),
        )


def _prune_stale_groups(conn, media_type, kept_keys):
    rows = conn.execute(
        "SELECT id, group_key FROM duplicate_group WHERE media_type = ?", (media_type,)
    ).fetchall()
    for row in rows:
        if row["group_key"] not in kept_keys:
            conn.execute("DELETE FROM duplicate_group WHERE id = ?", (row["id"],))


def _score_group(conn, items):
    item_ids = [it["id"] for it in items]
    tech_by_id = _load_tech_by_item_id(conn, item_ids)
    bitrates = [t.bitrate_total for t in tech_by_id.values() if t.bitrate_total]
    bitrate_range = (min(bitrates), max(bitrates)) if bitrates else (0, 0)

    scored = []
    for it in items:
        tech = tech_by_id.get(it["id"])
        tags = json.loads(it["quality_tags_json"]) if it["quality_tags_json"] else {}
        score = scoring.compute_quality_score(tech, tags, it["size_bytes"], bitrate_range)
        scored.append({"media_item_id": it["id"], "score": score, "size_bytes": it["size_bytes"]})

    keep_id = scoring.recommend_keep(scored)
    for s in scored:
        s["is_recommended_keep"] = s["media_item_id"] == keep_id
    return scored


def group_movies(conn):
    rows = conn.execute(
        "SELECT id, parsed_title, parsed_year, size_bytes, quality_tags_json FROM media_item "
        "WHERE media_type = 'movie' AND missing = 0"
    ).fetchall()

    by_key = defaultdict(list)
    for r in rows:
        key = normalize.movie_group_key(r["parsed_title"], r["parsed_year"])
        by_key[key].append(r)

    now = _now()
    kept_keys = set()
    for key, items in by_key.items():
        if len(items) < 2:
            continue
        scored = _score_group(conn, items)
        display_title = f"{items[0]['parsed_title']} ({items[0]['parsed_year'] or '?'})"
        group_id = _upsert_duplicate_group(conn, "movie", key, display_title, now)
        _replace_group_members(conn, group_id, scored)
        kept_keys.add(key)

    _prune_stale_groups(conn, "movie", kept_keys)
    conn.commit()
    return len(kept_keys)


def group_series(conn):
    rows = conn.execute(
        "SELECT id, show_title_raw, season, episode_start, dir_path, size_bytes, quality_tags_json "
        "FROM media_item WHERE media_type = 'episode' AND missing = 0 "
        "AND show_title_raw IS NOT NULL AND season IS NOT NULL"
    ).fetchall()

    by_show_season = defaultdict(list)
    for r in rows:
        key = normalize.series_group_key(r["show_title_raw"], r["season"])
        by_show_season[key].append(r)

    now = _now()
    kept_keys = set()
    for key, items in by_show_season.items():
        dirs = {it["dir_path"] for it in items}
        if len(dirs) < 2:
            continue

        by_episode = defaultdict(list)
        for it in items:
            if it["episode_start"] is None:
                continue  # season-pack files / multi-disc ISOs aren't comparable per-episode
            by_episode[it["episode_start"]].append(it)

        all_scored = []
        for ep_items in by_episode.values():
            ep_dirs = {it["dir_path"] for it in ep_items}
            if len(ep_dirs) < 2:
                continue
            all_scored.extend(_score_group(conn, ep_items))

        if not all_scored:
            continue

        display_title = f"{items[0]['show_title_raw']} S{items[0]['season']:02d}"
        group_id = _upsert_duplicate_group(conn, "episode", key, display_title, now)
        _replace_group_members(conn, group_id, all_scored)
        kept_keys.add(key)

    _prune_stale_groups(conn, "episode", kept_keys)
    conn.commit()
    return len(kept_keys)
