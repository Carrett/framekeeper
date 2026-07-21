import unittest

from scanner import filename_parser as fp


class TestParseMovieFilename(unittest.TestCase):
    def test_bdremux_with_dual_audio(self):
        name = "101 dálmatas (1961) [BDRemux AVC 1080p Esp Dolby Digital Audio 5.1 - Eng DTS-HD MA 5.1 - Subs].mkv"
        info = fp.parse_movie_filename(name)
        self.assertEqual(info.title, "101 dálmatas")
        self.assertEqual(info.year, 1961)
        self.assertEqual(info.tags.source, "BDREMUX")
        self.assertEqual(info.tags.resolution_tag, "1080p")
        self.assertEqual(info.tags.video_codec_tag, "AVC")
        self.assertIn("DD", info.tags.audio_codecs)
        self.assertIn("DTS-HD MA", info.tags.audio_codecs)
        self.assertTrue(info.tags.has_subs)

    def test_uhdremux_proper_with_release_group(self):
        name = "1917 (2019) [PROPER][UHDRemux 2160p HEVC DV-HDR10+ ES DD+ 7.1 - TrueHD Atmos 7.1 Subs][HDO].mkv"
        info = fp.parse_movie_filename(name)
        self.assertEqual(info.title, "1917")
        self.assertEqual(info.year, 2019)
        self.assertEqual(info.tags.source, "UHDREMUX")
        self.assertEqual(info.tags.resolution_tag, "2160p")
        self.assertEqual(info.tags.hdr_tag, "DV-HDR10+")
        self.assertIn("PROPER", info.tags.edition_tags)
        self.assertIn("TRUEHD ATMOS", info.tags.audio_codecs)
        self.assertEqual(info.tags.release_group, "HDO")

    def test_no_year_no_brackets_fallback(self):
        name = "Avatar 2 4Kwebrip2160.atomohd.ninja.mkv"
        info = fp.parse_movie_filename(name)
        self.assertTrue(info.title.startswith("Avatar 2"))
        self.assertIsNone(info.year)

    def test_dot_separated_quality_with_year(self):
        name = "Agente X. Última Misión (2024).2160p.UHDREMUX.DV.HDR.ESP DD 5.1.ING DTS HD 5.1.HEVC-EmlHDTeam.mkv"
        info = fp.parse_movie_filename(name)
        self.assertEqual(info.year, 2024)
        self.assertEqual(info.tags.source, "UHDREMUX")
        self.assertEqual(info.tags.resolution_tag, "2160p")
        self.assertEqual(info.tags.video_codec_tag, "HEVC")


class TestParseSeasonFolder(unittest.TestCase):
    def test_arcane_custom_bluray_release(self):
        name = "Arcane (2021) S01 [Custom UHD FullBluRay 2160p HEVC DV-HDR10 ES DD+ 5.1 Subs][HDO]"
        info = fp.parse_season_folder(name)
        self.assertEqual(info.show, "Arcane")
        self.assertEqual(info.year, 2021)
        self.assertEqual(info.season, 1)
        self.assertEqual(info.tags.resolution_tag, "2160p")
        self.assertEqual(info.tags.hdr_tag, "DV-HDR10")

    def test_arcane_pack_webdl_release(self):
        name = "Arcane (2021) S01 [PACK] [NF WEBDL 1080p AVC ES-EN DD+ 5.1 Subs][HDO]"
        info = fp.parse_season_folder(name)
        self.assertEqual(info.show, "Arcane")
        self.assertEqual(info.season, 1)
        self.assertTrue(info.is_pack)
        self.assertEqual(info.tags.resolution_tag, "1080p")

    def test_dexter_pack(self):
        name = "Dexter (2006) S01 [PACK][AMZN WEB-DL 1080p AVC ES DD+ 2.0 - EN DD+ 5.1 Subs][HDO]"
        info = fp.parse_season_folder(name)
        self.assertEqual(info.show, "Dexter")
        self.assertEqual(info.season, 1)
        self.assertTrue(info.is_pack)

    def test_black_mirror_top_level_season(self):
        name = "Black Mirror S01 [WEB-DL NF 1080p EAC3 5.1 esp eng Subs][HDOlimpo]"
        info = fp.parse_season_folder(name)
        self.assertEqual(info.show, "Black Mirror")
        self.assertEqual(info.season, 1)

    def test_black_mirror_with_year(self):
        name = "Black Mirror (2011) S04 [PACK][NF WEB-DL 2160p HEVC HDR10 ES DD 5.1][HDO]"
        info = fp.parse_season_folder(name)
        self.assertEqual(info.show, "Black Mirror")
        self.assertEqual(info.year, 2011)
        self.assertEqual(info.season, 4)


class TestParseEpisodeFilename(unittest.TestCase):
    def test_dexter_episode(self):
        name = "Dexter S01E01 [AMZN WEB-DL 1080p AVC ES DD+ 2.0 - EN DD+ 5.1 Subs][HDO].mkv"
        info = fp.parse_episode_filename(name)
        self.assertEqual(info.show, "Dexter")
        self.assertEqual(info.season, 1)
        self.assertEqual(info.episode_start, 1)
        self.assertEqual(info.episode_end, 1)

    def test_black_mirror_episode_with_title(self):
        name = "Black Mirror S01E01 El himno nacional [WEB-DL NF 1080p EAC3 5.1 esp eng Subs][HDOlimpo].mkv"
        info = fp.parse_episode_filename(name, show_hint="Black Mirror")
        self.assertEqual(info.show, "Black Mirror")
        self.assertEqual(info.season, 1)
        self.assertEqual(info.episode_start, 1)

    def test_fallout_episode_no_season_folder(self):
        name = "Fallout S02E01 [AMZN WEB-DL 2160p HEVC DV-HDR10+ ES DD+ 5.1][HDO].mkv"
        info = fp.parse_episode_filename(name)
        self.assertEqual(info.show, "Fallout")
        self.assertEqual(info.season, 2)
        self.assertEqual(info.episode_start, 1)

    def test_double_episode_range(self):
        name = "Show S01E01E02 [WEB-DL 1080p].mkv"
        info = fp.parse_episode_filename(name)
        self.assertEqual(info.episode_start, 1)
        self.assertEqual(info.episode_end, 2)


if __name__ == "__main__":
    unittest.main()
