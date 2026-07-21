from flask import Blueprint, jsonify

from mount import mount_manager
from scanner import scan_service
from .localization import text

bp = Blueprint("scan_api", __name__, url_prefix="/api/scan")


@bp.post("/start")
def start():
    if not mount_manager.is_mounted():
        return jsonify({"error": text("La NAS no está montada", "The NAS is not mounted")}), 409
    scan_run_id = scan_service.start_scan()
    if scan_run_id is None:
        return jsonify({"error": text("Ya hay un escaneo en curso", "A scan is already running")}), 409
    return jsonify({"scan_run_id": scan_run_id, "status": "running"})


@bp.get("/status")
def status():
    return jsonify(scan_service.get_status())


@bp.post("/cancel")
def cancel():
    scan_service.cancel_scan()
    return jsonify({"status": "cancelling"})
