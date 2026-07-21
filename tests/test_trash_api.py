import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from flask import Flask

from api import trash


class TestMoveSeriesToTrash(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.series_dir = os.path.join(self.temp_dir.name, "series")
        os.makedirs(self.series_dir)

        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
        with open(schema_path, encoding="utf-8") as schema_file:
            self.conn.executescript(schema_file.read())

        self.app = Flask(__name__)
        self.app.register_blueprint(trash.bp)
        self.client = self.app.test_client()

        self.patches = [
            mock.patch.object(trash.db, "get_connection", return_value=self.conn),
            mock.patch.object(trash.config, "SERIES_DIR", self.series_dir),
            mock.patch.object(trash.config, "MOVIES_DIR", os.path.join(self.temp_dir.name, "movies")),
            mock.patch.object(trash.config, "TRASH_DIRNAME", "#trash"),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.conn.close()
        self.temp_dir.cleanup()

    def add_episode(self, show, season, filename):
        season_dir = os.path.join(self.series_dir, show, f"Season {season}")
        os.makedirs(season_dir, exist_ok=True)
        path = os.path.join(season_dir, filename)
        with open(path, "wb") as episode_file:
            episode_file.write(b"video")

        cursor = self.conn.execute(
            """
            INSERT INTO media_item (
                media_type, path, dir_path, filename, size_bytes, mtime_epoch,
                show_title_raw, season, episode_start, episode_end, parsed_title,
                first_seen_at, last_seen_at
            ) VALUES ('episode', ?, ?, ?, 5, 1, ?, ?, 1, 1, ?, 'now', 'now')
            """,
            (path, season_dir, filename, show, season, show),
        )
        self.conn.commit()
        return cursor.lastrowid, path

    def test_moves_only_the_selected_season(self):
        season_one = [
            self.add_episode("Example Show", 1, "S01E01.mkv"),
            self.add_episode("Example Show", 1, "S01E02.mkv"),
        ]
        season_two_id, season_two_path = self.add_episode("Example Show", 2, "S02E01.mkv")
        other_id, other_path = self.add_episode("Other Show", 1, "S01E01.mkv")

        response = self.client.post(
            "/api/trash/move-series",
            json={"show": "Example Show", "scope": "season", "season": 1, "confirm": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["moved"], 2)
        for media_id, original_path in season_one:
            self.assertFalse(os.path.exists(original_path))
            missing = self.conn.execute(
                "SELECT missing FROM media_item WHERE id = ?", (media_id,)
            ).fetchone()["missing"]
            self.assertEqual(missing, 1)

        self.assertTrue(os.path.exists(season_two_path))
        self.assertTrue(os.path.exists(other_path))
        self.assertEqual(
            self.conn.execute("SELECT missing FROM media_item WHERE id = ?", (season_two_id,)).fetchone()[0],
            0,
        )
        self.assertEqual(
            self.conn.execute("SELECT missing FROM media_item WHERE id = ?", (other_id,)).fetchone()[0],
            0,
        )

        ignore_path = os.path.join(self.series_dir, "#trash", ".plexignore")
        with open(ignore_path, encoding="utf-8") as ignore_file:
            self.assertEqual(ignore_file.read(), "*\n")

    def test_adds_plex_ignore_to_an_existing_trash_directory(self):
        trash_dir = os.path.join(self.series_dir, "#trash")
        os.makedirs(trash_dir)
        trashed_episode = os.path.join(trash_dir, "old-S01E01.mkv")
        with open(trashed_episode, "wb") as episode_file:
            episode_file.write(b"video")

        trash.ensure_plex_ignores()

        with open(os.path.join(trash_dir, ".plexignore"), encoding="utf-8") as ignore_file:
            self.assertEqual(ignore_file.read(), "*\n")
        self.assertTrue(os.path.exists(trashed_episode))

    def test_does_not_overwrite_an_existing_plex_ignore(self):
        trash_dir = os.path.join(self.series_dir, "#trash")
        os.makedirs(trash_dir)
        ignore_path = os.path.join(trash_dir, ".plexignore")
        with open(ignore_path, "w", encoding="utf-8") as ignore_file:
            ignore_file.write("custom-rule\n")

        trash.ensure_plex_ignores()

        with open(ignore_path, encoding="utf-8") as ignore_file:
            self.assertEqual(ignore_file.read(), "custom-rule\n")

    def test_moves_the_remaining_complete_show(self):
        first_id, first_path = self.add_episode("Example Show", 1, "S01E01.mkv")
        second_id, second_path = self.add_episode("Example Show", 2, "S02E01.mkv")
        _, other_path = self.add_episode("Other Show", 1, "S01E01.mkv")

        response = self.client.post(
            "/api/trash/move-series",
            json={"show": "Example Show", "scope": "show", "confirm": True},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["moved"], 2)
        self.assertFalse(os.path.exists(first_path))
        self.assertFalse(os.path.exists(second_path))
        self.assertTrue(os.path.exists(other_path))
        missing_count = self.conn.execute(
            "SELECT COUNT(*) FROM media_item WHERE id IN (?, ?) AND missing = 1",
            (first_id, second_id),
        ).fetchone()[0]
        self.assertEqual(missing_count, 2)

    def test_null_season_scope_does_not_move_the_complete_show(self):
        unidentified_id, unidentified_path = self.add_episode(
            "Example Show", None, "special.mkv"
        )
        regular_id, regular_path = self.add_episode("Example Show", 1, "S01E01.mkv")

        response = self.client.post(
            "/api/trash/move-series",
            json={
                "show": "Example Show",
                "scope": "season",
                "season": None,
                "confirm": True,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["moved"], 1)
        self.assertFalse(os.path.exists(unidentified_path))
        self.assertTrue(os.path.exists(regular_path))
        self.assertEqual(
            self.conn.execute(
                "SELECT missing FROM media_item WHERE id = ?", (unidentified_id,)
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            self.conn.execute(
                "SELECT missing FROM media_item WHERE id = ?", (regular_id,)
            ).fetchone()[0],
            0,
        )

    def test_requires_explicit_confirmation(self):
        self.add_episode("Example Show", 1, "S01E01.mkv")

        response = self.client.post(
            "/api/trash/move-series",
            json={"show": "Example Show", "scope": "season", "season": 1},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("confirm", response.get_json()["error"])

    def test_error_language_follows_accept_language(self):
        english = self.client.post(
            "/api/trash/move",
            json={"media_item_ids": [1]},
            headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        spanish = self.client.post(
            "/api/trash/move",
            json={"media_item_ids": [1]},
            headers={"Accept-Language": "es-MX,es;q=0.9"},
        )

        self.assertEqual(english.get_json()["error"], "confirm=true is required")
        self.assertEqual(spanish.get_json()["error"], "se requiere confirm=true")


if __name__ == "__main__":
    unittest.main()
