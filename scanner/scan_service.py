import dataclasses
import json
import os
import threading
from datetime import datetime, timezone

import config
from db import db
from scanner import dedupe, ffprobe_client, filename_parser, fs_walk

_progress_lock = threading.Lock()
_progress = {
    "status": "idle",
    "scan_run_id": None,
    "total_files": 0,
    "processed_files": 0,
    "new_files": 0,
    "updated_files": 0,
    "current_file": None,
    "error_message": None,
}
_cancel_flag = threading.Event()
_scan_thread = None


def _now():
    return datetime.now(timezone.utc).isoformat()


def get_status():
    with _progress_lock:
        return dict(_progress)


def recover_stale_runs():
    conn = db.get_connection()
    conn.execute(
        "UPDATE scan_run SET status='failed', error_message='interrupted by server restart', "
        "finished_at=? WHERE status='running'",
        (_now(),),
    )
    conn.commit()


def start_scan():
    global _scan_thread
    with _progress_lock:
        if _progress["status"] == "running":
            return None

    _cancel_flag.clear()
    conn = db.get_connection()
    now = _now()
    cur = conn.execute("INSERT INTO scan_run (started_at, status) VALUES (?, 'running')", (now,))
    conn.commit()
    scan_run_id = cur.lastrowid

    with _progress_lock:
        _progress.update(
            status="running",
            scan_run_id=scan_run_id,
            total_files=0,
            processed_files=0,
            new_files=0,
            updated_files=0,
            current_file=None,
            error_message=None,
        )

    _scan_thread = threading.Thread(target=_run_scan, args=(scan_run_id,), daemon=True)
    _scan_thread.start()
    return scan_run_id


def cancel_scan():
    _cancel_flag.set()


def _derive_episode_context(dir_path, filename):
    rel = os.path.relpath(dir_path, config.SERIES_DIR)
    parts = [] if rel == "." else rel.split(os.sep)
    top_folder = parts[0] if parts else os.path.basename(dir_path)

    season_folder_info = filename_parser.parse_season_folder(top_folder)
    show_title_raw = season_folder_info.show
    is_pack = season_folder_info.is_pack or any(filename_parser.PACK_RE.search(p) for p in parts)

    ep_info = filename_parser.parse_episode_filename(filename, show_hint=show_title_raw)
    if ep_info:
        return show_title_raw, ep_info.season, ep_info.episode_start, ep_info.episode_end, is_pack, ep_info.tags
    return show_title_raw, season_folder_info.season, None, None, is_pack, season_folder_info.tags


def _upsert_media_item(conn, entry, fields, now):
    existing = conn.execute(
        "SELECT id, size_bytes, mtime_epoch FROM media_item WHERE path = ?", (entry["path"],)
    ).fetchone()

    tags_json = json.dumps(dataclasses.asdict(fields["tags"]))

    if existing:
        changed = existing["size_bytes"] != entry["size_bytes"] or existing["mtime_epoch"] != entry["mtime_epoch"]
        conn.execute(
            """
            UPDATE media_item SET
                size_bytes=?, mtime_epoch=?, show_title_raw=?, season=?, episode_start=?, episode_end=?,
                is_pack_folder=?, parsed_title=?, parsed_year=?, quality_tags_json=?, release_group=?,
                last_seen_at=?, missing=0
            WHERE id=?
            """,
            (
                entry["size_bytes"], entry["mtime_epoch"], fields["show_title_raw"], fields["season"],
                fields["episode_start"], fields["episode_end"], int(fields["is_pack_folder"]),
                fields["parsed_title"], fields["parsed_year"], tags_json, fields["tags"].release_group,
                now, existing["id"],
            ),
        )
        return existing["id"], "updated" if changed else "unchanged"

    cur = conn.execute(
        """
        INSERT INTO media_item (
            media_type, path, dir_path, filename, size_bytes, mtime_epoch, show_title_raw, season,
            episode_start, episode_end, is_pack_folder, parsed_title, parsed_year, quality_tags_json,
            release_group, first_seen_at, last_seen_at, missing
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
        """,
        (
            entry["media_type"], entry["path"], entry["dir_path"], entry["filename"], entry["size_bytes"],
            entry["mtime_epoch"], fields["show_title_raw"], fields["season"], fields["episode_start"],
            fields["episode_end"], int(fields["is_pack_folder"]), fields["parsed_title"], fields["parsed_year"],
            tags_json, fields["tags"].release_group, now, now,
        ),
    )
    return cur.lastrowid, "new"


def _upsert_tech_metadata(conn, media_item_id, path, size_bytes, mtime_epoch):
    cache_key = f"{path}|{size_bytes}|{mtime_epoch}"
    existing = conn.execute(
        "SELECT cache_key FROM tech_metadata WHERE media_item_id = ?", (media_item_id,)
    ).fetchone()
    if existing and existing["cache_key"] == cache_key:
        return

    tech = ffprobe_client.probe_file(path)
    raw_json = json.dumps(tech.raw) if tech.raw else None

    conn.execute(
        """
        INSERT INTO tech_metadata (
            media_item_id, cache_key, probed_at, duration_sec, container, video_codec, width, height,
            hdr_type, bitrate_total, bitrate_video, audio_codec, audio_channels_label, audio_channels_count,
            languages_json, probe_error, raw_ffprobe_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(media_item_id) DO UPDATE SET
            cache_key=excluded.cache_key, probed_at=excluded.probed_at, duration_sec=excluded.duration_sec,
            container=excluded.container, video_codec=excluded.video_codec, width=excluded.width,
            height=excluded.height, hdr_type=excluded.hdr_type, bitrate_total=excluded.bitrate_total,
            bitrate_video=excluded.bitrate_video, audio_codec=excluded.audio_codec,
            audio_channels_label=excluded.audio_channels_label, audio_channels_count=excluded.audio_channels_count,
            languages_json=excluded.languages_json, probe_error=excluded.probe_error,
            raw_ffprobe_json=excluded.raw_ffprobe_json
        """,
        (
            media_item_id, cache_key, _now(), tech.duration_sec, tech.container, tech.video_codec, tech.width,
            tech.height, tech.hdr_type, tech.bitrate_total, tech.bitrate_video, tech.audio_codec,
            tech.audio_channels_label, tech.audio_channels_count, json.dumps(tech.languages), tech.probe_error,
            raw_json,
        ),
    )


def _process_entry(conn, entry, now):
    if entry["media_type"] == "movie":
        parsed = filename_parser.parse_movie_filename(entry["filename"])
        fields = {
            "show_title_raw": None,
            "season": None,
            "episode_start": None,
            "episode_end": None,
            "is_pack_folder": False,
            "parsed_title": parsed.title,
            "parsed_year": parsed.year,
            "tags": parsed.tags,
        }
    else:
        show, season, ep_start, ep_end, is_pack, tags = _derive_episode_context(
            entry["dir_path"], entry["filename"]
        )
        fields = {
            "show_title_raw": show,
            "season": season,
            "episode_start": ep_start,
            "episode_end": ep_end,
            "is_pack_folder": is_pack,
            "parsed_title": show or entry["filename"],
            "parsed_year": None,
            "tags": tags,
        }

    media_item_id, status = _upsert_media_item(conn, entry, fields, now)
    _upsert_tech_metadata(conn, media_item_id, entry["path"], entry["size_bytes"], entry["mtime_epoch"])
    return status


def _run_scan(scan_run_id):
    conn = db.get_connection()
    now = _now()
    try:
        entries = list(fs_walk.walk_movies()) + list(fs_walk.walk_series())
        total = len(entries)
        with _progress_lock:
            _progress["total_files"] = total

        new_count = 0
        updated_count = 0
        processed_count = 0

        for i, entry in enumerate(entries):
            if _cancel_flag.is_set():
                break

            status = _process_entry(conn, entry, now)
            if status == "new":
                new_count += 1
            elif status == "updated":
                updated_count += 1
            processed_count = i + 1

            if i % 25 == 0:
                conn.commit()

            with _progress_lock:
                _progress["processed_files"] = processed_count
                _progress["current_file"] = entry["filename"]
                _progress["new_files"] = new_count
                _progress["updated_files"] = updated_count

        conn.commit()

        conn.execute("UPDATE media_item SET missing = CASE WHEN last_seen_at = ? THEN 0 ELSE 1 END", (now,))
        conn.commit()

        dedupe.group_movies(conn)
        dedupe.group_series(conn)

        final_status = "cancelled" if _cancel_flag.is_set() else "completed"
        conn.execute(
            "UPDATE scan_run SET finished_at=?, status=?, total_files=?, processed_files=?, "
            "new_files=?, updated_files=? WHERE id=?",
            (_now(), final_status, total, processed_count, new_count, updated_count, scan_run_id),
        )
        conn.commit()
        with _progress_lock:
            _progress["status"] = final_status

    except Exception as exc:  # noqa: BLE001
        conn.execute(
            "UPDATE scan_run SET status='failed', error_message=?, finished_at=? WHERE id=?",
            (str(exc), _now(), scan_run_id),
        )
        conn.commit()
        with _progress_lock:
            _progress["status"] = "failed"
            _progress["error_message"] = str(exc)
