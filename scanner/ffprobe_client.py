import json
import subprocess
from dataclasses import dataclass, field

FFPROBE_TIMEOUT = 30

VIDEO_CODEC_DISPLAY = {
    "h264": "AVC",
    "hevc": "HEVC",
    "av1": "AV1",
    "mpeg2video": "MPEG2",
    "vp9": "VP9",
}

AUDIO_CODEC_DISPLAY = {
    "truehd": "TrueHD",
    "dts": "DTS",
    "eac3": "DD+",
    "ac3": "DD",
    "aac": "AAC",
    "flac": "FLAC",
    "opus": "Opus",
    "mp3": "MP3",
    "pcm_s16le": "PCM",
    "pcm_s24le": "PCM",
}

AUDIO_CODEC_RANK = {
    "truehd": 5,
    "dts": 4,
    "eac3": 3,
    "ac3": 2,
    "aac": 1,
    "opus": 1,
    "flac": 3,
}

CHANNEL_LABELS = {1: "1.0", 2: "2.0", 3: "2.1", 6: "5.1", 7: "6.1", 8: "7.1"}


@dataclass
class TechMetadata:
    duration_sec: float | None = None
    container: str | None = None
    video_codec: str | None = None
    width: int | None = None
    height: int | None = None
    hdr_type: str | None = None
    bitrate_total: int | None = None
    bitrate_video: int | None = None
    audio_codec: str | None = None
    audio_channels_label: str | None = None
    audio_channels_count: int | None = None
    languages: list = field(default_factory=list)
    probe_error: str | None = None
    raw: dict | None = None


def _to_int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _detect_hdr(video_stream):
    if not video_stream:
        return "SDR"
    side_data = video_stream.get("side_data_list") or []
    for sd in side_data:
        if "dolby vision" in sd.get("side_data_type", "").lower() or "dovi" in sd.get("side_data_type", "").lower():
            return "DV"
    transfer = (video_stream.get("color_transfer") or "").lower()
    if transfer == "smpte2084":
        return "HDR10"
    if transfer == "arib-std-b67":
        return "HLG"
    return "SDR"


def _pick_best_audio_stream(audio_streams):
    if not audio_streams:
        return None

    def rank(stream):
        codec_rank = AUDIO_CODEC_RANK.get(stream.get("codec_name"), 0)
        channels = stream.get("channels") or 0
        bit_rate = _to_int(stream.get("bit_rate")) or 0
        return (codec_rank, channels, bit_rate)

    return max(audio_streams, key=rank)


def _channels_label(channels):
    if channels is None:
        return None
    return CHANNEL_LABELS.get(channels, f"{channels}ch")


def _collect_languages(streams):
    langs = []
    for s in streams:
        lang = (s.get("tags") or {}).get("language")
        if lang and lang not in ("und", "mis") and lang not in langs:
            langs.append(lang)
    return langs


def probe_file(path, timeout=FFPROBE_TIMEOUT):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return TechMetadata(probe_error="ffprobe timeout")
    except OSError as exc:
        return TechMetadata(probe_error=str(exc))

    if result.returncode != 0:
        return TechMetadata(probe_error=result.stderr.strip()[:500] or "ffprobe failed")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return TechMetadata(probe_error=f"invalid ffprobe json: {exc}")

    streams = data.get("streams", [])
    fmt = data.get("format", {})

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    best_audio = _pick_best_audio_stream(audio_streams)

    video_codec_name = video.get("codec_name") if video else None
    audio_codec_name = best_audio.get("codec_name") if best_audio else None

    bitrate_video = None
    if video:
        bitrate_video = _to_int(video.get("bit_rate")) or _to_int((video.get("tags") or {}).get("BPS-eng"))

    languages = _collect_languages(audio_streams) or _collect_languages(
        [s for s in streams if s.get("codec_type") == "subtitle"]
    )

    return TechMetadata(
        duration_sec=float(fmt["duration"]) if fmt.get("duration") else None,
        container=fmt.get("format_name"),
        video_codec=VIDEO_CODEC_DISPLAY.get(video_codec_name, video_codec_name),
        width=video.get("width") if video else None,
        height=video.get("height") if video else None,
        hdr_type=_detect_hdr(video),
        bitrate_total=_to_int(fmt.get("bit_rate")),
        bitrate_video=bitrate_video,
        audio_codec=AUDIO_CODEC_DISPLAY.get(audio_codec_name, audio_codec_name),
        audio_channels_label=_channels_label(best_audio.get("channels") if best_audio else None),
        audio_channels_count=best_audio.get("channels") if best_audio else None,
        languages=languages,
        raw=data,
    )
