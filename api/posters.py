from flask import Blueprint, jsonify, redirect, request

import tmdb_client
from db import db
from .localization import text

bp = Blueprint("posters_api", __name__, url_prefix="/api/posters")


def _redirect_to_poster(media_type, title, year=None):
    poster_path = tmdb_client.find_poster_path(
        db.get_connection(), media_type, title, year
    )
    url = tmdb_client.poster_url(poster_path)
    if not url:
        return jsonify({"error": text("carátula no encontrada", "poster not found")}), 404

    response = redirect(url, code=302)
    response.headers["Cache-Control"] = "private, max-age=86400"
    return response


@bp.get("/movie/<int:item_id>")
def movie_poster(item_id):
    row = db.get_connection().execute(
        """
        SELECT parsed_title, parsed_year
        FROM media_item
        WHERE id = ? AND media_type = 'movie' AND missing = 0
        """,
        (item_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": text("película no encontrada", "movie not found")}), 404
    return _redirect_to_poster("movie", row["parsed_title"], row["parsed_year"])


@bp.get("/tv")
def tv_poster():
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"error": text("title es obligatorio", "title is required")}), 400
    return _redirect_to_poster("tv", title)
