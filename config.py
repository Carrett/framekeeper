import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "config.json"), encoding="utf-8") as f:
    _cfg = json.load(f)

NAS_HOST = _cfg["nas"]["host"]
NAS_SHARE = _cfg["nas"]["share"]
MOUNT_POINT = _cfg["nas"]["mount_point"]
MOVIES_DIR = os.path.join(MOUNT_POINT, _cfg["nas"]["movies_dir"])
SERIES_DIR = os.path.join(MOUNT_POINT, _cfg["nas"]["series_dir"])
TRASH_DIRNAME = _cfg["nas"]["trash_dirname"]
CREDENTIALS_FILE = _cfg["nas"]["credentials_file"]
MOUNT_WRAPPER = _cfg["nas"]["mount_wrapper"]

DB_PATH = os.path.join(BASE_DIR, _cfg["db_path"])

SERVER_HOST = _cfg["server"]["host"]
SERVER_PORT = _cfg["server"]["port"]

SCORING_WEIGHTS = _cfg["scoring"]["weights"]
SCORING_TIE_EPSILON = _cfg["scoring"]["tie_epsilon"]
