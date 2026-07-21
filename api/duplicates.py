import json

from flask import Blueprint, jsonify, request

from db import db

bp = Blueprint("duplicates_api", __name__, url_prefix="/api/duplicates")


@bp.get("")
def list_groups():
    media_type = "episode" if request.args.get("type") == "series" else "movie"
    conn = db.get_connection()
    groups = conn.execute(
        "SELECT * FROM duplicate_group WHERE media_type = ? ORDER BY display_title", (media_type,)
    ).fetchall()

    result = []
    for g in groups:
        members = conn.execute(
            """
            SELECT dgm.is_recommended_keep, m.size_bytes
            FROM duplicate_group_member dgm
            JOIN media_item m ON m.id = dgm.media_item_id
            WHERE dgm.group_id = ?
            """,
            (g["id"],),
        ).fetchall()
        total_size = sum(m["size_bytes"] for m in members)
        keep_size = sum(m["size_bytes"] for m in members if m["is_recommended_keep"])
        result.append(
            {
                **dict(g),
                "member_count": len(members),
                "total_size": total_size,
                "wasted_size": total_size - keep_size,
            }
        )
    return jsonify(result)


@bp.get("/<int:group_id>")
def group_detail(group_id):
    conn = db.get_connection()
    group = conn.execute("SELECT * FROM duplicate_group WHERE id = ?", (group_id,)).fetchone()
    if not group:
        return jsonify({"error": "not found"}), 404

    members = conn.execute(
        """
        SELECT dgm.quality_score, dgm.score_breakdown_json, dgm.is_recommended_keep,
               m.id AS media_item_id, m.path, m.filename, m.dir_path, m.size_bytes,
               m.season, m.episode_start, m.episode_end,
               t.video_codec, t.width, t.height, t.hdr_type, t.audio_codec, t.audio_channels_label,
               t.container, t.bitrate_total, t.duration_sec, t.languages_json, t.probe_error
        FROM duplicate_group_member dgm
        JOIN media_item m ON m.id = dgm.media_item_id
        LEFT JOIN tech_metadata t ON t.media_item_id = m.id
        WHERE dgm.group_id = ?
        ORDER BY m.episode_start, dgm.quality_score DESC
        """,
        (group_id,),
    ).fetchall()

    member_list = []
    for m in members:
        d = dict(m)
        d["score_breakdown"] = json.loads(d.pop("score_breakdown_json")) if d.get("score_breakdown_json") else {}
        d["languages"] = json.loads(d.pop("languages_json")) if d.get("languages_json") else []
        member_list.append(d)

    return jsonify({"group": dict(group), "members": member_list})
