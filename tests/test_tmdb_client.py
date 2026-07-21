import io
import json
import os
import sqlite3
import unittest
from unittest import mock

import tmdb_client


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class TestTmdbClient(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        schema_path = os.path.join(os.path.dirname(__file__), "..", "db", "schema.sql")
        with open(schema_path, encoding="utf-8") as schema_file:
            self.conn.executescript(schema_file.read())
        self.token_patch = mock.patch.object(
            tmdb_client.config, "TMDB_READ_ACCESS_TOKEN", "test-token"
        )
        self.token_patch.start()

    def tearDown(self):
        self.token_patch.stop()
        self.conn.close()

    def test_searches_for_exact_movie_and_caches_poster(self):
        payload = {
            "results": [
                {"id": 1, "title": "Blade Runner", "poster_path": "/wrong.jpg"},
                {
                    "id": 2,
                    "title": "Blade Runner 2049",
                    "original_title": "Blade Runner 2049",
                    "poster_path": "/poster.jpg",
                },
            ]
        }

        with mock.patch.object(
            tmdb_client,
            "urlopen",
            return_value=FakeResponse(json.dumps(payload).encode()),
        ) as urlopen_mock:
            first = tmdb_client.find_poster_path(
                self.conn, "movie", "Blade Runner 2049", 2017
            )
            second = tmdb_client.find_poster_path(
                self.conn, "movie", "Blade Runner 2049", 2017
            )

        self.assertEqual(first, "/poster.jpg")
        self.assertEqual(second, "/poster.jpg")
        urlopen_mock.assert_called_once()
        request = urlopen_mock.call_args.args[0]
        self.assertIn("primary_release_year=2017", request.full_url)
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")

    def test_does_not_accept_a_different_title(self):
        payload = {
            "results": [
                {"id": 1, "name": "A Different Show", "poster_path": "/wrong.jpg"}
            ]
        }
        with mock.patch.object(
            tmdb_client,
            "urlopen",
            return_value=FakeResponse(json.dumps(payload).encode()),
        ):
            result = tmdb_client.find_poster_path(self.conn, "tv", "Expected Show")

        self.assertIsNone(result)
        cached = self.conn.execute(
            "SELECT status FROM poster_cache WHERE media_type = 'tv'"
        ).fetchone()
        self.assertEqual(cached["status"], "not_found")

    def test_disabled_client_does_not_make_network_requests(self):
        with mock.patch.object(tmdb_client.config, "TMDB_READ_ACCESS_TOKEN", ""):
            with mock.patch.object(tmdb_client, "urlopen") as urlopen_mock:
                result = tmdb_client.find_poster_path(
                    self.conn, "movie", "Example", 2026
                )

        self.assertIsNone(result)
        urlopen_mock.assert_not_called()

    def test_builds_only_valid_poster_urls(self):
        self.assertEqual(
            tmdb_client.poster_url("/poster.jpg"),
            "https://image.tmdb.org/t/p/w342/poster.jpg",
        )
        self.assertIsNone(tmdb_client.poster_url("https://example.com/poster.jpg"))


if __name__ == "__main__":
    unittest.main()
