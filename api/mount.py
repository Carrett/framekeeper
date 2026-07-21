from dataclasses import asdict

from flask import Blueprint, jsonify

from mount import mount_manager

bp = Blueprint("mount_api", __name__, url_prefix="/api/mount")


@bp.get("/status")
def status():
    return jsonify(asdict(mount_manager.get_status()))


@bp.post("/retry")
def retry():
    return jsonify(asdict(mount_manager.ensure_mounted()))
