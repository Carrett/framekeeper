import os

from flask import Flask

import config
from api import register_blueprints
from db import db
from mount import mount_manager
from scanner import scan_service

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def create_app():
    app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

    db.init_db()
    scan_service.recover_stale_runs()
    mount_manager.ensure_mounted()

    register_blueprints(app)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, threaded=True, debug=False)
