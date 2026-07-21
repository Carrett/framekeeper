import os
import shutil
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

import config
from db import db
from .localization import text

bp = Blueprint("trash_api", __name__, url_prefix="/api/trash")

PLEX_IGNORE_FILENAME = ".plexignore"
PLEX_IGNORE_CONTENT = "*\n"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _trash_root_for(path):
    if path.startswith(config.MOVIES_DIR):
        return os.path.join(config.MOVIES_DIR, config.TRASH_DIRNAME)
    return os.path.join(config.SERIES_DIR, config.TRASH_DIRNAME)


def ensure_plex_ignores():
    """Keep Plex from indexing recoverable files as library media."""
    for library_root in (config.MOVIES_DIR, config.SERIES_DIR):
        trash_root = os.path.join(library_root, config.TRASH_DIRNAME)
        if not os.path.isdir(trash_root):
            continue

        ignore_path = os.path.join(trash_root, PLEX_IGNORE_FILENAME)
        if os.path.exists(ignore_path):
            continue

        try:
            with open(ignore_path, "x", encoding="utf-8") as ignore_file:
                ignore_file.write(PLEX_IGNORE_CONTENT)
        except FileExistsError:
            pass
        except OSError:
            # Moving/restoring files should remain available even if the NAS
            # permissions do not allow creating Plex's optional ignore file.
            pass


def _ensure_trash_root(path):
    trash_root = _trash_root_for(path)
    os.makedirs(trash_root, exist_ok=True)
    ensure_plex_ignores()
    return trash_root


def _move_one_to_trash(conn, media_item_id):
    row = conn.execute("SELECT * FROM media_item WHERE id = ?", (media_item_id,)).fetchone()
    if not row:
        return {"id": media_item_id, "ok": False, "error": "no encontrado"}
    if not os.path.exists(row["path"]):
        return {"id": media_item_id, "ok": False, "error": "el archivo ya no existe en la NAS"}

    trash_root = _ensure_trash_root(row["path"])
    dest = os.path.join(trash_root, f"{media_item_id}_{row['filename']}")

    try:
        shutil.move(row["path"], dest)
    except OSError as exc:
        return {"id": media_item_id, "ok": False, "error": str(exc)}

    now = _now()
    conn.execute(
        """
        INSERT INTO trash_item (media_item_id, original_path, trash_path, size_bytes, moved_at, status)
        VALUES (?, ?, ?, ?, ?, 'trashed')
        """,
        (media_item_id, row["path"], dest, row["size_bytes"], now),
    )
    conn.execute("UPDATE media_item SET missing = 1 WHERE id = ?", (media_item_id,))
    return {"id": media_item_id, "ok": True}


@bp.post("/move")
def move():
    data = request.get_json(silent=True) or {}
    if not data.get("confirm"):
        return jsonify({"error": text("se requiere confirm=true", "confirm=true is required")}), 400
    ids = data.get("media_item_ids") or []
    if not ids:
        return jsonify({"error": text("media_item_ids vacío", "media_item_ids is empty")}), 400

    conn = db.get_connection()
    results = [_move_one_to_trash(conn, i) for i in ids]
    conn.commit()
    return jsonify(results)


@bp.post("/move-series")
def move_series():
    """Move all active episodes in a show or season to the trash."""
    data = request.get_json(silent=True) or {}
    if not data.get("confirm"):
        return jsonify({"error": text("se requiere confirm=true", "confirm=true is required")}), 400

    show = data.get("show")
    if not isinstance(show, str) or not show.strip():
        return jsonify({"error": text("show es obligatorio", "show is required")}), 400

    scope = data.get("scope")
    if scope not in {"show", "season"}:
        return jsonify({"error": text("scope debe ser 'show' o 'season'", "scope must be 'show' or 'season'")}), 400

    season = data.get("season")
    if scope == "season" and season is not None and (
        isinstance(season, bool) or not isinstance(season, int)
    ):
        return jsonify({"error": text("season debe ser un número entero o null", "season must be an integer or null")}), 400

    conn = db.get_connection()
    params = [show]
    season_filter = ""
    if scope == "season":
        if season is None:
            season_filter = " AND season IS NULL"
        else:
            season_filter = " AND season = ?"
            params.append(season)

    rows = conn.execute(
        f"""
        SELECT id
        FROM media_item
        WHERE media_type = 'episode' AND missing = 0 AND show_title_raw = ?{season_filter}
        ORDER BY id
        """,
        params,
    ).fetchall()
    if not rows:
        return jsonify({"error": text("no se encontraron episodios activos para esa selección", "no active episodes were found for that selection")}), 404

    results = [_move_one_to_trash(conn, row["id"]) for row in rows]
    conn.commit()
    moved = sum(1 for result in results if result["ok"])
    return jsonify(
        {
            "results": results,
            "selected": len(results),
            "moved": moved,
            "failed": len(results) - moved,
        }
    )


@bp.get("")
def list_trash():
    status = request.args.get("status", "trashed")
    conn = db.get_connection()
    rows = conn.execute(
        "SELECT * FROM trash_item WHERE status = ? ORDER BY moved_at DESC", (status,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.post("/restore")
def restore():
    data = request.get_json(silent=True) or {}
    if not data.get("confirm"):
        return jsonify({"error": text("se requiere confirm=true", "confirm=true is required")}), 400
    ids = data.get("trash_item_ids") or []

    conn = db.get_connection()
    results = []
    for trash_id in ids:
        row = conn.execute(
            "SELECT * FROM trash_item WHERE id = ? AND status = 'trashed'", (trash_id,)
        ).fetchone()
        if not row:
            results.append({"id": trash_id, "ok": False, "error": "no encontrado o ya restaurado"})
            continue
        try:
            os.makedirs(os.path.dirname(row["original_path"]), exist_ok=True)
            shutil.move(row["trash_path"], row["original_path"])
        except OSError as exc:
            results.append({"id": trash_id, "ok": False, "error": str(exc)})
            continue

        now = _now()
        conn.execute(
            "UPDATE trash_item SET status = 'restored', restored_at = ? WHERE id = ?", (now, trash_id)
        )
        if row["media_item_id"]:
            conn.execute("UPDATE media_item SET missing = 0 WHERE id = ?", (row["media_item_id"],))
        results.append({"id": trash_id, "ok": True})

    conn.commit()
    return jsonify(results)


@bp.post("/empty")
def empty():
    data = request.get_json(silent=True) or {}
    if not data.get("confirm"):
        return jsonify({"error": text("se requiere confirm=true", "confirm=true is required")}), 400

    conn = db.get_connection()
    if data.get("all"):
        rows = conn.execute("SELECT * FROM trash_item WHERE status = 'trashed'").fetchall()
    else:
        ids = data.get("trash_item_ids") or []
        if not ids:
            return jsonify({"error": text("trash_item_ids vacío (o usa all:true)", "trash_item_ids is empty (or use all:true)")}), 400
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"SELECT * FROM trash_item WHERE status = 'trashed' AND id IN ({placeholders})", ids
        ).fetchall()

    now = _now()
    results = []
    for row in rows:
        try:
            if os.path.exists(row["trash_path"]):
                os.remove(row["trash_path"])
        except OSError as exc:
            results.append({"id": row["id"], "ok": False, "error": str(exc)})
            continue
        conn.execute("UPDATE trash_item SET status = 'purged', purged_at = ? WHERE id = ?", (now, row["id"]))
        results.append({"id": row["id"], "ok": True})

    conn.commit()
    return jsonify(results)
