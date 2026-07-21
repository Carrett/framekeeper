from dataclasses import dataclass, field

import config

RESOLUTION_SCORE_TABLE = [
    (2000, 1.0),
    (1000, 0.72),
    (700, 0.5),
    (400, 0.25),
    (0, 0.15),
]

RESOLUTION_TAG_HEIGHT = {"2160p": 2160, "1080p": 1080, "720p": 720, "480p": 480}

SOURCE_SCORE = {
    "UHDREMUX": 1.0,
    "BDREMUX": 0.95,
    "BLURAY": 0.8,
    "WEBDL": 0.55,
    "WEBRIP": 0.5,
    "HDTV": 0.35,
    "DVDRIP": 0.2,
    None: 0.4,
}

HDR_SCORE = {
    "DV-HDR10+": 1.0,
    "DV-HDR10": 0.95,
    "DV": 0.9,
    "HDR10+": 0.85,
    "HDR10": 0.7,
    "HLG": 0.6,
    "SDR": 0.3,
    None: 0.3,
}

AUDIO_RANK = {
    "TRUEHD ATMOS": 1.0,
    "ATMOS": 1.0,
    "DTS-X": 0.98,
    "TRUEHD": 0.9,
    "DTS-HD MA": 0.88,
    "DTS-HD": 0.8,
    "FLAC": 0.7,
    "DD+": 0.6,
    "DDP": 0.6,
    "DTS": 0.55,
    "OPUS": 0.5,
    "PCM": 0.75,
    "DD": 0.4,
    "AC3": 0.4,
    "AAC": 0.3,
    None: 0.3,
}

DEFAULT_WEIGHTS = {"resolution": 35, "source": 25, "hdr": 15, "audio": 20, "bitrate": 5}


@dataclass
class QualityScore:
    total: float
    breakdown: dict = field(default_factory=dict)


def _lookup_resolution_score(height):
    if not height:
        return RESOLUTION_SCORE_TABLE[-1][1]
    for threshold, score in RESOLUTION_SCORE_TABLE:
        if height >= threshold:
            return score
    return RESOLUTION_SCORE_TABLE[-1][1]


def _height_from_tag(resolution_tag):
    return RESOLUTION_TAG_HEIGHT.get(resolution_tag)


def _audio_score(tech, name_tags):
    tech_codec = getattr(tech, "audio_codec", None) if tech else None
    name_codecs = (name_tags or {}).get("audio_codecs") or []
    base_codec = tech_codec.upper() if tech_codec else (name_codecs[0].upper() if name_codecs else None)
    rank = AUDIO_RANK.get(base_codec, AUDIO_RANK[None])
    if any("ATMOS" in c.upper() for c in name_codecs):
        rank = max(rank, AUDIO_RANK["ATMOS"])
    channels = (getattr(tech, "audio_channels_count", None) if tech else None) or 2
    bonus = min(0.15, max(0, channels - 2) * 0.03)
    return min(1.0, rank + bonus)


def _bitrate_score(bitrate_total, group_min, group_max):
    if not bitrate_total or not group_max or group_max <= group_min:
        return 0.5
    return max(0.0, min(1.0, (bitrate_total - group_min) / (group_max - group_min)))


def compute_quality_score(tech, name_tags, size_bytes, group_bitrate_min_max, weights=None):
    weights = weights or config.SCORING_WEIGHTS or DEFAULT_WEIGHTS
    name_tags = name_tags or {}

    height = (getattr(tech, "height", None) if tech else None) or _height_from_tag(name_tags.get("resolution_tag"))
    res_score = _lookup_resolution_score(height)

    source_score = SOURCE_SCORE.get(name_tags.get("source"), SOURCE_SCORE[None])

    hdr_key = name_tags.get("hdr_tag") or (getattr(tech, "hdr_type", None) if tech else None)
    hdr_score = HDR_SCORE.get(hdr_key, HDR_SCORE[None])

    audio_score = _audio_score(tech, name_tags)

    group_min, group_max = group_bitrate_min_max
    bitrate_total = getattr(tech, "bitrate_total", None) if tech else None
    bitrate_score = _bitrate_score(bitrate_total, group_min, group_max)

    total = (
        res_score * weights["resolution"]
        + source_score * weights["source"]
        + hdr_score * weights["hdr"]
        + audio_score * weights["audio"]
        + bitrate_score * weights["bitrate"]
    )
    breakdown = {
        "resolution": round(res_score * weights["resolution"], 2),
        "source": round(source_score * weights["source"], 2),
        "hdr": round(hdr_score * weights["hdr"], 2),
        "audio": round(audio_score * weights["audio"], 2),
        "bitrate": round(bitrate_score * weights["bitrate"], 2),
        "size_bytes": size_bytes,
    }
    return QualityScore(total=round(total, 1), breakdown=breakdown)


def recommend_keep(members):
    if not members:
        return None
    epsilon = config.SCORING_TIE_EPSILON
    ordered = sorted(members, key=lambda m: m["score"].total, reverse=True)
    top_score = ordered[0]["score"].total
    ties = [m for m in ordered if abs(m["score"].total - top_score) < epsilon]
    if len(ties) > 1:
        ties.sort(key=lambda m: m["size_bytes"], reverse=True)
        return ties[0]["media_item_id"]
    return ordered[0]["media_item_id"]
