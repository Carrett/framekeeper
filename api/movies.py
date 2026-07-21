import json

from flask import Blueprint, jsonify, request

from db import db

bp = Blueprint("movies_api", __name__, url_prefix="/api/movies")

SORT_COLUMNS = {
    "size": "m.size_bytes",
    "name": "m.parsed_title",
    "quality": "COALESCE(dgm.quality_score, 0)",
    "date": "m.mtime_epoch",
}

LIST_FIELDS = """
    m.id, m.filename, m.path, m.dir_path, m.size_bytes, m.parsed_title, m.parsed_year,
    m.mtime_epoch, m.release_group,
    t.video_codec, t.width, t.height, t.hdr_type, t.audio_codec, t.audio_channels_label,
    t.container, t.bitrate_total, t.duration_sec, t.languages_json, t.probe_error,
    dgm.quality_score, dgm.is_recommended_keep, dgm.group_id
"""

JOINS = """
    FROM media_item m
    LEFT JOIN tech_metadata t ON t.media_item_id = m.id
    LEFT JOIN duplicate_group_member dgm ON dgm.media_item_id = m.id
    WHERE m.media_type = 'movie' AND m.missing = 0
"""


def _row_to_dict(row):
    d = dict(row)
    d["languages"] = json.loads(d.pop("languages_json")) if d.get("languages_json") else []
    return d


@bp.get("")
def list_movies():
    sort = request.args.get("sort", "name")
    order = request.args.get("order", "asc")
    column = SORT_COLUMNS.get(sort, SORT_COLUMNS["name"])
    order_sql = "DESC" if order == "desc" else "ASC"

    conn = db.get_connection()
    rows = conn.execute(f"SELECT {LIST_FIELDS} {JOINS} ORDER BY {column} {order_sql}").fetchall()
    return jsonify([_row_to_dict(r) for r in rows])


@bp.get("/<int:item_id>")
def movie_detail(item_id):
    conn = db.get_connection()
    row = conn.execute(f"SELECT {LIST_FIELDS} {JOINS} AND m.id = ?", (item_id,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404

    result = _row_to_dict(row)
    raw = conn.execute(
        "SELECT raw_ffprobe_json FROM tech_metadata WHERE media_item_id = ?", (item_id,)
    ).fetchone()
    result["raw_ffprobe"] = json.loads(raw["raw_ffprobe_json"]) if raw and raw["raw_ffprobe_json"] else None
    return jsonify(result)
