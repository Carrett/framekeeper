import re
from dataclasses import dataclass, field

SOURCE_PATTERNS = [
    (re.compile(r"UHD\s*REMUX", re.I), "UHDREMUX"),
    (re.compile(r"BD\s*REMUX", re.I), "BDREMUX"),
    (re.compile(r"FULL\s*BLU\s*RAY", re.I), "BLURAY"),
    (re.compile(r"BLU\s*RAY|BDRIP", re.I), "BLURAY"),
    (re.compile(r"WEB[\-\s]?DL", re.I), "WEBDL"),
    (re.compile(r"WEBRIP", re.I), "WEBRIP"),
    (re.compile(r"\bAMZN\b|\bNF\b|\bRTVE\b|\bDCP\b|\bSHO\b|\bMA\b(?=\s*WEB)", re.I), "WEBDL"),
    (re.compile(r"\bHDTV\b", re.I), "HDTV"),
    (re.compile(r"DVDRIP", re.I), "DVDRIP"),
]

RESOLUTION_PATTERNS = [
    (re.compile(r"2160\s*p", re.I), "2160p"),
    (re.compile(r"1080\s*p", re.I), "1080p"),
    (re.compile(r"720\s*p", re.I), "720p"),
    (re.compile(r"480\s*p", re.I), "480p"),
    (re.compile(r"\b4K\b", re.I), "2160p"),
]

VIDEO_CODEC_PATTERNS = [
    (re.compile(r"HEVC|H\.?265|X265", re.I), "HEVC"),
    (re.compile(r"AVC|H\.?264|X264", re.I), "AVC"),
]

HDR_PATTERNS = [
    (re.compile(r"DV[\-\s]?HDR10\+", re.I), "DV-HDR10+"),
    (re.compile(r"DV[\-\s]?HDR10", re.I), "DV-HDR10"),
    (re.compile(r"\bDV\b|DOVI|DOLBY\s*VISION", re.I), "DV"),
    (re.compile(r"HDR10\+", re.I), "HDR10+"),
    (re.compile(r"HDR10", re.I), "HDR10"),
    (re.compile(r"\bHDR\b", re.I), "HDR10"),
]

AUDIO_CODEC_PATTERNS = [
    (re.compile(r"TRUE[\-\s]?HD\s*ATMOS|ATMOS", re.I), "TRUEHD ATMOS"),
    (re.compile(r"TRUE[\-\s]?HD", re.I), "TRUEHD"),
    (re.compile(r"DTS[\-\s]?X", re.I), "DTS-X"),
    (re.compile(r"DTS[\-\s]?HD\s*MA", re.I), "DTS-HD MA"),
    (re.compile(r"DTS[\-\s]?HD", re.I), "DTS-HD"),
    (re.compile(r"\bDTS\b", re.I), "DTS"),
    (re.compile(r"DD\+|DDP|DOLBY\s*DIGITAL\s*PLUS|EAC3", re.I), "DDP"),
    (re.compile(r"\bDD\b|\bAC3\b|DOLBY\s*DIGITAL(?!\s*PLUS)|DOLBY\s*DIGITAL\s*AUDIO", re.I), "DD"),
    (re.compile(r"\bAAC\b", re.I), "AAC"),
]

EDITION_PATTERNS = [
    (re.compile(r"\bPROPER\b", re.I), "PROPER"),
    (re.compile(r"\bREPACK\b", re.I), "REPACK"),
    (re.compile(r"\bEXTENDED\b", re.I), "EXTENDED"),
    (re.compile(r"\bUNRATED\b", re.I), "UNRATED"),
    (re.compile(r"\bREMASTERED\b", re.I), "REMASTERED"),
]

LANGUAGE_TOKENS = {
    "es": re.compile(r"\bESP\b|\bES\b|\bCAST\b|\bSPA\b", re.I),
    "en": re.compile(r"\bENG\b|\bEN\b|\bING\b", re.I),
}

CHANNELS_RE = re.compile(r"(\d\.\d)")
BRACKET_RE = re.compile(r"\[([^\]]*)\]")
PACK_RE = re.compile(r"\bPACK\b", re.I)
SEASON_RE = re.compile(r"\bS(\d{1,2})\b", re.I)
EPISODE_RE = re.compile(r"S(\d{1,2})E(\d{1,3})(?:E(\d{1,3}))?", re.I)
YEAR_RE = re.compile(r"\((\d{4})\)")


@dataclass
class QualityTags:
    source: str | None = None
    resolution_tag: str | None = None
    video_codec_tag: str | None = None
    hdr_tag: str | None = None
    edition_tags: list = field(default_factory=list)
    audio_codecs: list = field(default_factory=list)
    channels: list = field(default_factory=list)
    languages: list = field(default_factory=list)
    has_subs: bool = False
    release_group: str | None = None

    @property
    def best_audio_codec(self):
        return self.audio_codecs[0] if self.audio_codecs else None

    @property
    def best_channels(self):
        return self.channels[0] if self.channels else None


@dataclass
class MovieNameInfo:
    title: str
    year: int | None
    tags: QualityTags


@dataclass
class SeasonFolderInfo:
    show: str
    year: int | None
    season: int
    is_pack: bool
    tags: QualityTags


@dataclass
class EpisodeNameInfo:
    show: str | None
    season: int
    episode_start: int
    episode_end: int
    tags: QualityTags


def _first_match(patterns, text):
    for pattern, value in patterns:
        if pattern.search(text):
            return value
    return None


def _all_matches(patterns, text):
    found = []
    for pattern, value in patterns:
        if pattern.search(text) and value not in found:
            found.append(value)
    return found


def extract_release_group(text):
    blocks = BRACKET_RE.findall(text)
    if not blocks:
        tail = re.search(r"-([A-Za-z][A-Za-z0-9]{2,14})$", text.strip())
        return tail.group(1) if tail else None
    last = blocks[-1].strip()
    if len(last) <= 20 and not _first_match(SOURCE_PATTERNS + RESOLUTION_PATTERNS, last):
        return last
    return None


def extract_quality_tags(text):
    tags = QualityTags()
    tags.source = _first_match(SOURCE_PATTERNS, text)
    tags.resolution_tag = _first_match(RESOLUTION_PATTERNS, text)
    tags.video_codec_tag = _first_match(VIDEO_CODEC_PATTERNS, text)
    tags.hdr_tag = _first_match(HDR_PATTERNS, text)
    tags.edition_tags = _all_matches(EDITION_PATTERNS, text)
    tags.audio_codecs = _all_matches(AUDIO_CODEC_PATTERNS, text)
    tags.channels = CHANNELS_RE.findall(text)
    tags.languages = [lang for lang, pattern in LANGUAGE_TOKENS.items() if pattern.search(text)]
    tags.has_subs = bool(re.search(r"\bSUBS?\b", text, re.I))
    tags.release_group = extract_release_group(text)
    return tags


def _strip_extension(filename):
    return re.sub(r"\.(mkv|mp4|avi|m4v|ts)$", "", filename, flags=re.I)


def parse_movie_filename(filename):
    name = _strip_extension(filename)
    m = re.match(r"^(?P<title>.+?)\s*\((?P<year>\d{4})\)\s*(?P<rest>.*)$", name)
    if m:
        title = m.group("title").strip(" .-")
        year = int(m.group("year"))
        tags = extract_quality_tags(m.group("rest"))
        return MovieNameInfo(title=title, year=year, tags=tags)

    cut_idx = len(name)
    bracket_idx = name.find("[")
    if bracket_idx != -1:
        cut_idx = min(cut_idx, bracket_idx)
    for pattern, _ in SOURCE_PATTERNS + RESOLUTION_PATTERNS:
        tag_match = pattern.search(name)
        if tag_match:
            cut_idx = min(cut_idx, tag_match.start())
    title_raw = name[:cut_idx]
    title = re.sub(r"[\._]+", " ", title_raw).strip(" .-")
    tags = extract_quality_tags(name[cut_idx:] or name)
    return MovieNameInfo(title=title or name, year=None, tags=tags)


def parse_season_folder(folder_name):
    season_match = SEASON_RE.search(folder_name)
    season = int(season_match.group(1)) if season_match else None
    year_match = YEAR_RE.search(folder_name)
    year = int(year_match.group(1)) if year_match else None

    if season_match:
        show = folder_name[: season_match.start()]
    elif year_match:
        show = folder_name[: year_match.start()]
    else:
        show = folder_name
    show = re.sub(r"\(\d{4}\)", "", show)
    show = re.sub(r"[\._]+", " ", show).strip(" .-()")

    is_pack = bool(PACK_RE.search(folder_name))
    tags = extract_quality_tags(folder_name)
    return SeasonFolderInfo(show=show, year=year, season=season, is_pack=is_pack, tags=tags)


def parse_episode_filename(filename, show_hint=None):
    name = _strip_extension(filename)
    ep_match = EPISODE_RE.search(name)
    if not ep_match:
        return None

    season = int(ep_match.group(1))
    ep_start = int(ep_match.group(2))
    ep_end = int(ep_match.group(3)) if ep_match.group(3) else ep_start

    if show_hint:
        show = show_hint
    else:
        show_raw = name[: ep_match.start()]
        show = re.sub(r"[\._]+", " ", show_raw).strip(" .-")

    tags = extract_quality_tags(name[ep_match.end():])
    return EpisodeNameInfo(show=show or None, season=season, episode_start=ep_start, episode_end=ep_end, tags=tags)
