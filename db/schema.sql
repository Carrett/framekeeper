CREATE TABLE IF NOT EXISTS media_item (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    media_type          TEXT NOT NULL CHECK(media_type IN ('movie','episode')),
    path                TEXT NOT NULL UNIQUE,
    dir_path            TEXT NOT NULL,
    filename            TEXT NOT NULL,
    size_bytes          INTEGER NOT NULL,
    mtime_epoch         INTEGER NOT NULL,
    show_title_raw      TEXT,
    season              INTEGER,
    episode_start       INTEGER,
    episode_end         INTEGER,
    is_pack_folder      INTEGER DEFAULT 0,
    parsed_title        TEXT NOT NULL,
    parsed_year         INTEGER,
    quality_tags_json   TEXT,
    release_group       TEXT,
    first_seen_at       TEXT NOT NULL,
    last_seen_at        TEXT NOT NULL,
    missing             INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_media_item_type ON media_item(media_type);
CREATE INDEX IF NOT EXISTS idx_media_item_show_season ON media_item(show_title_raw, season);

CREATE TABLE IF NOT EXISTS tech_metadata (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    media_item_id           INTEGER NOT NULL UNIQUE REFERENCES media_item(id) ON DELETE CASCADE,
    cache_key               TEXT NOT NULL,
    probed_at               TEXT NOT NULL,
    duration_sec            REAL,
    container               TEXT,
    video_codec             TEXT,
    width                   INTEGER,
    height                  INTEGER,
    hdr_type                TEXT,
    bitrate_total           INTEGER,
    bitrate_video           INTEGER,
    audio_codec             TEXT,
    audio_channels_label    TEXT,
    audio_channels_count    INTEGER,
    languages_json          TEXT,
    probe_error             TEXT,
    raw_ffprobe_json        TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tech_cache_key ON tech_metadata(cache_key);

CREATE TABLE IF NOT EXISTS duplicate_group (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    media_type      TEXT NOT NULL CHECK(media_type IN ('movie','episode')),
    group_key       TEXT NOT NULL,
    display_title   TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    UNIQUE(media_type, group_key)
);

CREATE TABLE IF NOT EXISTS duplicate_group_member (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id                INTEGER NOT NULL REFERENCES duplicate_group(id) ON DELETE CASCADE,
    media_item_id           INTEGER NOT NULL REFERENCES media_item(id) ON DELETE CASCADE,
    quality_score           REAL,
    score_breakdown_json    TEXT,
    is_recommended_keep     INTEGER DEFAULT 0,
    UNIQUE(group_id, media_item_id)
);

CREATE TABLE IF NOT EXISTS trash_item (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    media_item_id   INTEGER REFERENCES media_item(id) ON DELETE SET NULL,
    original_path   TEXT NOT NULL,
    trash_path      TEXT NOT NULL,
    size_bytes      INTEGER NOT NULL,
    moved_at        TEXT NOT NULL,
    restored_at     TEXT,
    purged_at       TEXT,
    status          TEXT NOT NULL DEFAULT 'trashed'
);

CREATE TABLE IF NOT EXISTS scan_run (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    total_files     INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    new_files       INTEGER DEFAULT 0,
    updated_files   INTEGER DEFAULT 0,
    current_file    TEXT,
    error_message   TEXT
);
