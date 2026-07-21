import os

import config

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".m4v", ".ts", ".iso", ".img"}


def _iter_video_files(root):
    if not os.path.isdir(root):
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != config.TRASH_DIRNAME]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in VIDEO_EXTENSIONS:
                continue
            full_path = os.path.join(dirpath, fn)
            try:
                st = os.stat(full_path)
            except OSError:
                continue
            yield {
                "path": full_path,
                "dir_path": dirpath,
                "filename": fn,
                "size_bytes": st.st_size,
                "mtime_epoch": int(st.st_mtime),
            }


def walk_movies(movies_dir=None):
    movies_dir = movies_dir or config.MOVIES_DIR
    for entry in _iter_video_files(movies_dir):
        entry["media_type"] = "movie"
        yield entry


def walk_series(series_dir=None):
    series_dir = series_dir or config.SERIES_DIR
    for entry in _iter_video_files(series_dir):
        entry["media_type"] = "episode"
        yield entry
