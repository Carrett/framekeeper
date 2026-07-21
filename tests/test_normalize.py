import unittest

from scanner import normalize as norm


class TestNormalize(unittest.TestCase):
    def test_movie_title_accents_and_case(self):
        self.assertEqual(norm.normalize_movie_title("101 dálmatas"), "101 dalmatas")

    def test_movie_group_key_same_title_year(self):
        key1 = norm.movie_group_key("Agárralo Como Puedas", 1988)
        key2 = norm.movie_group_key("agarralo como puedas", 1988)
        self.assertEqual(key1, key2)

    def test_movie_group_key_leading_article_stripped(self):
        key_the = norm.movie_group_key("The Matrix", 1999)
        key_plain = norm.movie_group_key("Matrix", 1999)
        self.assertEqual(key_the, key_plain)

    def test_arcane_two_releases_same_group(self):
        key1 = norm.series_group_key("Arcane", 1)
        key2 = norm.series_group_key("arcane", 1)
        self.assertEqual(key1, key2)

    def test_black_mirror_different_folders_same_show(self):
        show_a = norm.normalize_series_title("Black Mirror")
        show_b = norm.normalize_series_title("Black Mirror")
        self.assertEqual(show_a, show_b)
        key_s01 = norm.series_group_key("Black Mirror", 1)
        key_s04 = norm.series_group_key("Black Mirror", 4)
        self.assertNotEqual(key_s01, key_s04)

    def test_different_seasons_do_not_collide(self):
        self.assertNotEqual(
            norm.series_group_key("Dexter", 1),
            norm.series_group_key("Dexter", 2),
        )


if __name__ == "__main__":
    unittest.main()
