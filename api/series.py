from collections import OrderedDict

from flask import Blueprint, jsonify, request

from db import db

bp = Blueprint("series_api", __name__, url_prefix="/api/series")


@bp.get("")
def series_tree():
    conn = db.get_connection()
    rows = conn.execute(
        """
        SELECT show_title_raw, season, COUNT(*) AS episode_count, SUM(size_bytes) AS total_size,
               COUNT(DISTINCT dir_path) AS release_count
        FROM media_item
        WHERE media_type = 'episode' AND missing = 0 AND show_title_raw IS NOT NULL
        GROUP BY show_title_raw, season
        ORDER BY show_title_raw, season
        """
    ).fetchall()

    shows = OrderedDict()
    for r in rows:
        show = r["show_title_raw"]
        if show not in shows:
            shows[show] = {"show": show, "total_size": 0, "seasons": []}
        shows[show]["total_size"] += r["total_size"] or 0
        shows[show]["seasons"].append(
            {
                "season": r["season"],
                "episode_count": r["episode_count"],
                "total_size": r["total_size"],
                "release_count": r["release_count"],
                "has_multiple_releases": r["release_count"] > 1,
            }
        )

    return jsonify(list(shows.values()))


@bp.get("/<show>/seasons/<season_key>")
def season_detail(show, season_key):
    if season_key == "unidentified":
        season_filter = "m.season IS NULL"
        params = (show,)
    else:
        try:
            season = int(season_key)
        except ValueError:
            return jsonify({"error": "temporada no válida"}), 400
        season_filter = "m.season = ?"
        params = (show, season)

    conn = db.get_connection()
    rows = conn.execute(
        f"""
        SELECT m.id, m.filename, m.dir_path, m.episode_start, m.episode_end, m.size_bytes,
               m.is_pack_folder,
               t.video_codec, t.width, t.height, t.hdr_type, t.audio_codec, t.audio_channels_label,
               t.container, t.bitrate_total, t.duration_sec, t.probe_error
        FROM media_item m
        LEFT JOIN tech_metadata t ON t.media_item_id = m.id
        WHERE m.media_type = 'episode' AND m.missing = 0 AND m.show_title_raw = ?
              AND {season_filter}
        ORDER BY m.dir_path, m.episode_start
        """,
        params,
    ).fetchall()
    return jsonify([dict(r) for r in rows])
