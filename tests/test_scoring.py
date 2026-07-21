import unittest
from types import SimpleNamespace

from scanner import scoring


def tech(height=None, hdr_type=None, bitrate_total=None, audio_codec=None, audio_channels_count=None):
    return SimpleNamespace(
        height=height,
        hdr_type=hdr_type,
        bitrate_total=bitrate_total,
        audio_codec=audio_codec,
        audio_channels_count=audio_channels_count,
    )


class TestScoring(unittest.TestCase):
    def test_uhd_remux_beats_webdl_1080p(self):
        uhd = scoring.compute_quality_score(
            tech(height=2160, hdr_type="DV", bitrate_total=70_000_000, audio_codec="TrueHD", audio_channels_count=8),
            {"source": "UHDREMUX", "hdr_tag": "DV", "audio_codecs": ["TRUEHD ATMOS"]},
            size_bytes=60_000_000_000,
            group_bitrate_min_max=(10_000_000, 70_000_000),
        )
        webdl = scoring.compute_quality_score(
            tech(height=1080, hdr_type="SDR", bitrate_total=10_000_000, audio_codec="DD+", audio_channels_count=6),
            {"source": "WEBDL", "hdr_tag": None, "audio_codecs": ["DDP"]},
            size_bytes=8_000_000_000,
            group_bitrate_min_max=(10_000_000, 70_000_000),
        )
        self.assertGreater(uhd.total, webdl.total)

    def test_recommend_keep_picks_highest_score(self):
        members = [
            {"media_item_id": 1, "score": scoring.QualityScore(total=90.0), "size_bytes": 50_000_000_000},
            {"media_item_id": 2, "score": scoring.QualityScore(total=60.0), "size_bytes": 60_000_000_000},
        ]
        self.assertEqual(scoring.recommend_keep(members), 1)

    def test_recommend_keep_tiebreaks_on_size(self):
        members = [
            {"media_item_id": 1, "score": scoring.QualityScore(total=80.0), "size_bytes": 40_000_000_000},
            {"media_item_id": 2, "score": scoring.QualityScore(total=80.5), "size_bytes": 55_000_000_000},
        ]
        self.assertEqual(scoring.recommend_keep(members), 2)

    def test_no_tech_falls_back_to_name_tags(self):
        result = scoring.compute_quality_score(
            None,
            {"source": "BDREMUX", "resolution_tag": "1080p", "hdr_tag": None, "audio_codecs": ["DTS-HD MA"]},
            size_bytes=20_000_000_000,
            group_bitrate_min_max=(0, 0),
        )
        self.assertGreater(result.total, 0)


if __name__ == "__main__":
    unittest.main()
