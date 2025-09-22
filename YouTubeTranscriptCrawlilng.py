#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
yt_transcript.py

Two ways to get a YouTube transcript:
  A) Parse saved transcript HTML (your given structure with <ytd-transcript-segment-renderer>)
  B) Fetch via youtube-transcript-api (recommended when available)

Usage:
  # A) Parse from HTML file (your snippet)
  python yt_transcript.py --html path/to/transcript.html --out text

  # B) Fetch from video URL/ID directly into text line by line
  python yt_transcript.py --video https://www.youtube.com/watch?v=VIDEO_ID --out text --save
  python yt_transcript.py --video VIDEO_ID --out srt

  # C) Fetch from video URL/ID directly into paragraph mode
  python yt_transcript.py --video https://www.youtube.com/watch?v=VIDEO_ID --out text --paragraphs --keep-ts --gap 2.5 --save
  
  # D) Directly print out the text in terminal
  python yt_transcript.py --video https://www.youtube.com/watch?v=VIDEO_ID --out text
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def _die(msg: str, code: int = 1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def extract_from_html(html_text: str):
    """
    Extract segments from YouTube transcript HTML that looks like:
      <ytd-transcript-segment-renderer> ... <yt-formatted-string class="segment-text">...</yt-formatted-string>
    Returns: list of dicts: [{'timestamp': '2:15', 'text': '...'}, ...]
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        _die(
            "Missing dependency: beautifulsoup4. Install with: pip install beautifulsoup4 lxml"
        )

    # Use lxml if available (more forgiving), fallback to html.parser
    parser = "lxml"
    try:
        import lxml  # noqa: F401
    except Exception:
        parser = "html.parser"

    soup = BeautifulSoup(html_text, parser)

    segments = []
    for seg in soup.find_all("ytd-transcript-segment-renderer"):
        # timestamp
        ts_el = seg.select_one(".segment-timestamp")
        ts = ts_el.get_text(strip=True) if ts_el else None

        # text in yt-formatted-string with class 'segment-text'
        text_el = seg.select_one("yt-formatted-string.segment-text")
        if not text_el:
            # fallback: any yt-formatted-string inside the segment
            text_el = seg.find("yt-formatted-string")

        text = text_el.get_text(" ", strip=True) if text_el else ""

        if text or ts:
            segments.append({"timestamp": ts, "text": text})
    return segments


def _normalize_segments(raw):
    """
    Accepts many shapes:
      - [{'text': str, 'start': float, 'duration': float}, ...]
      - objects with .text/.start/.duration
      - tuples/lists like (start, duration, text)
    Returns: [{'timestamp': 'HH:MM:SS', 'text': str}, ...]
    """

    def sec_to_hms(sec: float):
        sec = int(round(float(sec)))
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    out = []
    for i in raw:
        # dict shape
        if isinstance(i, dict):
            start = float(i.get("start", 0.0))
            text = (i.get("text") or "").replace("\n", " ").strip()
        # object with attrs
        elif hasattr(i, "start") or hasattr(i, "text"):
            start = float(getattr(i, "start", 0.0))
            text = getattr(i, "text", "") or ""
            if not text and hasattr(i, "get_text"):
                text = i.get_text()
            text = text.replace("\n", " ").strip()
        # tuple/list (start, duration, text) or (start, text)
        elif isinstance(i, (list, tuple)):
            if len(i) >= 3:
                start, _, text = i[0], i[1], i[2]
            elif len(i) == 2:
                start, text = i
            else:
                continue
            start = float(start or 0.0)
            text = (text or "").replace("\n", " ").strip()
        else:
            continue

        out.append({"timestamp": sec_to_hms(start), "text": text})
    return out


def extract_from_video(video_id_or_url: str, languages=None):
    # Pull out the video ID if a URL was passed
    video_id = video_id_or_url
    m = re.search(r"(?:v=|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{6,})", video_id_or_url)
    if m:
        video_id = m.group(1)

    # language preference order
    languages = languages or ["zh-TW", "en", "en-US"]

    # unify time formatting
    def sec_to_hms(sec: float):
        sec = int(round(float(sec)))
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    # Try multiple API shapes
    try:
        from youtube_transcript_api import (
            YouTubeTranscriptApi,
            TranscriptsDisabled,
            NoTranscriptFound,
        )
    except Exception as e:
        raise SystemExit(f"Could not import youtube-transcript-api: {e}")

    # 1) Modern, simple path
    if hasattr(YouTubeTranscriptApi, "get_transcript"):
        try:
            raw = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            return _normalize_segments(raw)
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            raise SystemExit(str(e))
        except Exception as e:
            # fall through to other strategies
            pass

    # 2) Modern, advanced path
    if hasattr(YouTubeTranscriptApi, "list_transcripts"):
        try:
            tl = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = None
            try:
                transcript = tl.find_transcript(languages)
            except Exception:
                # try translating the first available transcript into the first preferred language
                for tr in tl:
                    try:
                        transcript = tr.translate(languages[0])
                        break
                    except Exception:
                        continue
            if transcript is None:
                raise NoTranscriptFound("No transcript in preferred languages.")
            raw = transcript.fetch()
            return _normalize_segments(raw)
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            raise SystemExit(str(e))
        except Exception:
            # fall through
            pass

        # 3) Your environment’s variant (methods are *instance* methods)
    try:
        api = YouTubeTranscriptApi()
        if hasattr(api, "fetch"):
            raw = api.fetch(video_id, languages=languages)
        elif hasattr(api, "list"):
            raw = api.list(video_id, languages=languages)
        else:
            raise RuntimeError("No usable fetch/list method on YouTubeTranscriptApi")

        return _normalize_segments(raw)
    except Exception as e:
        raise SystemExit(
            "Failed to fetch transcript. Your environment is using a nonstandard/old package. "
            f"Error: {e}\nTip: uninstall any 'youtube-transcript' or 'youtube_transcript' "
            "packages and install the official 'youtube-transcript-api'."
        )


def to_plain_text(segments):
    """Join as plain text (timestamp + text)."""
    lines = []
    for seg in segments:
        ts = seg.get("timestamp") or ""
        txt = seg.get("text") or ""
        if ts:
            lines.append(f"[{ts}] {txt}")
        else:
            lines.append(txt)
    return "\n".join(lines)


def _safe_name(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s)  # Windows-safe
    s = s.strip().strip(".") or "transcript"
    return s[:120]


def _ext_for(out_fmt: str) -> str:
    return {"text": ".txt", "json": ".json", "srt": ".srt"}[out_fmt]


def _video_id_of(s: str) -> str:
    m = re.search(r"(?:v=|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{6,})", s or "")
    return m.group(1) if m else (s or "video")


def to_srt(segments):
    """Very simple SRT (timestamps only as start; end is next start - 1s)."""

    def hms_to_secs(hms):
        parts = [int(p) for p in hms.split(":")]
        if len(parts) == 2:
            h, m, s = 0, parts[0], parts[1]
        else:
            h, m, s = parts
        return h * 3600 + m * 60 + s

    def secs_to_srt_time(sec):
        if isinstance(sec, str):
            # Try parse "M:SS" or "H:MM:SS"
            if ":" in sec:
                try:
                    sec = hms_to_secs(sec)
                except Exception:
                    sec = 0
            else:
                sec = 0
        ms = int((sec - int(sec)) * 1000) if isinstance(sec, float) else 0
        sec = int(sec)
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    # Convert any M:SS timestamps to H:MM:SS for math
    norm = []
    for seg in segments:
        ts = seg.get("timestamp") or "00:00:00"
        if ts.count(":") == 1:
            # M:SS -> 00:MM:SS
            m, s = ts.split(":")
            ts = f"00:{int(m):02d}:{int(s):02d}"
        norm.append({"timestamp": ts, "text": seg.get("text", "")})

    # Build SRT entries
    srt_lines = []
    for i, seg in enumerate(norm, start=1):
        start_sec = hms_to_secs(seg["timestamp"])
        # End time: next start - 1 second, or start + 2 seconds fallback
        if i < len(norm):
            next_start_sec = hms_to_secs(norm[i]["timestamp"])
            end_sec = max(start_sec + 1, next_start_sec - 1)
        else:
            end_sec = start_sec + 2

        srt_lines.append(str(i))
        srt_lines.append(
            f"{secs_to_srt_time(start_sec)} --> {secs_to_srt_time(end_sec)}"
        )
        srt_lines.append(seg["text"])
        srt_lines.append("")  # blank line
    return "\n".join(srt_lines)


END_PUNCT = "。！？!?…"


def _ts_to_secs(ts: str) -> float:
    """'M:SS' or 'HH:MM:SS' -> seconds; returns -1 if missing/invalid."""
    if not ts:
        return -1
    ts = ts.strip().strip("[]")
    parts = ts.split(":")
    try:
        if len(parts) == 2:
            m, s = int(parts[0]), int(parts[1])
            return m * 60 + s
        elif len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            return h * 3600 + m * 60 + s
    except Exception:
        return -1
    return -1


def _clean_piece(text: str) -> str:
    # collapse whitespace and stray line breaks from captions
    t = text.replace("\n", " ").replace("\r", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


def segments_to_paragraphs(
    segments,
    gap_threshold: float = 2.0,
    max_chars: int = 220,
    end_punct: str = END_PUNCT,
    keep_timestamps: bool = False,
):
    """
    Merge caption lines into paragraphs based on time gaps and punctuation.
    Returns a list[str] paragraphs (optionally prefixed with [HH:MM:SS]).
    """
    paras = []
    buf = []
    para_start_ts = None
    prev_secs = None

    for seg in segments:
        ts = seg.get("timestamp") or ""
        secs = _ts_to_secs(ts)
        piece = _clean_piece(seg.get("text") or "")
        if not piece:
            continue

        # Decide if we should break BEFORE adding this piece
        should_break = False

        # time-gap break
        if prev_secs is not None and secs >= 0 and prev_secs >= 0:
            if secs - prev_secs > gap_threshold:
                should_break = True

        # soft length break (avoid monster paragraphs)
        if not should_break and buf and sum(len(x) for x in buf) >= max_chars:
            should_break = True

        # finalize previous paragraph
        if should_break and buf:
            para_text = "".join(buf).strip()
            if keep_timestamps and para_start_ts:
                paras.append(f"[{para_start_ts}] {para_text}")
            else:
                paras.append(para_text)
            buf = []
            para_start_ts = None

        # start a new paragraph if buffer is empty
        if not buf:
            para_start_ts = ts if secs >= 0 else None

        # append this piece; add a joiner space if last char isn't punctuation or space
        if buf:
            # if previous chunk doesn’t end with punctuation, add a space
            if not any(buf[-1].endswith(p) for p in (end_punct + "，,。．.、;；:：")):
                buf.append(" ")
        buf.append(piece)

        prev_secs = secs

        # If this piece itself ends the sentence strongly and we already have some length, flush
        if piece and piece[-1] in end_punct and sum(len(x) for x in buf) >= 30:
            para_text = "".join(buf).strip()
            if keep_timestamps and para_start_ts:
                paras.append(f"[{para_start_ts}] {para_text}")
            else:
                paras.append(para_text)
            buf = []
            para_start_ts = None

    # flush remaining
    if buf:
        para_text = "".join(buf).strip()
        if keep_timestamps and para_start_ts:
            paras.append(f"[{para_start_ts}] {para_text}")
        else:
            paras.append(para_text)

    return paras


def to_paragraph_text(segments, **kwargs):
    """Return paragraphs separated by blank lines."""
    paras = segments_to_paragraphs(segments, **kwargs)
    return "\n\n".join(paras)


def _video_id_of(s: str) -> str:
    if not s:
        return "video"
    m = re.search(r"(?:v=|/shorts/|/live/|/embed/)([A-Za-z0-9_-]{6,})", s)
    return m.group(1) if m else s


def _safe_name(s: str) -> str:
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s).strip().strip(".")
    return (s or "transcript")[:120]


def _ext_for(out_fmt: str) -> str:
    return {"text": ".txt", "json": ".json", "srt": ".srt"}[out_fmt]


def _auto_save_path(args, out_fmt: str) -> Path:
    if args.video:
        vid = _safe_name(_video_id_of(args.video))
        base = (
            f"transcript_paras_{vid}"
            if args.paragraphs and out_fmt == "text"
            else f"transcript_{vid}"
        )
    else:
        # html mode – derive from the input file name
        base = _safe_name(Path(args.html).stem)
        if args.paragraphs and out_fmt == "text":
            base = f"{base}_paras"
    return Path(os.getcwd()) / f"{base}{_ext_for(out_fmt)}"


def main():
    ap = argparse.ArgumentParser(
        description="Extract YouTube transcript text from HTML or fetch via API."
    )
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--html", help="Path to saved transcript HTML page")
    g.add_argument("--video", help="YouTube video URL or ID")
    ap.add_argument(
        "--out", choices=["text", "json", "srt"], default="text", help="Output format"
    )
    ap.add_argument(
        "--save",
        nargs="?",  # value is optional
        const=True,  # present with no value → True
        default=None,  # absent → None
        help="Save output to a file. If no path is provided, an auto name is used.",
    )
    ap.add_argument(
        "--paragraphs", action="store_true", help="Merge lines into paragraphs."
    )
    ap.add_argument(
        "--keep-ts",
        action="store_true",
        help="Prefix each paragraph with its first timestamp.",
    )
    ap.add_argument(
        "--gap",
        type=float,
        default=2.0,
        help="Gap (seconds) that triggers a new paragraph. Default 2.0",
    )
    ap.add_argument(
        "--max-chars",
        type=int,
        default=220,
        help="Approx max characters per paragraph before a soft break.",
    )
    args = ap.parse_args()

    # Extract
    if args.html:
        html_path = Path(args.html)
        if not html_path.exists():
            _die(f"HTML file not found: {html_path}")
        html_text = html_path.read_text(encoding="utf-8", errors="ignore")
        segments = extract_from_html(html_text)
    else:
        segments = extract_from_video(args.video)

    # Serialize
    if args.out == "text":
        if args.paragraphs:
            out_text = to_paragraph_text(
                segments,
                gap_threshold=getattr(args, "gap", 2.0),
                max_chars=getattr(args, "max_chars", 220),
                keep_timestamps=getattr(args, "keep_ts", False),
            )
        else:
            out_text = to_plain_text(segments)
    elif args.out == "json":
        out_text = json.dumps(segments, ensure_ascii=False, indent=2)
    else:
        out_text = to_srt(segments)

    # Save / print
    if args.save is None:
        # no --save provided → print to stdout
        print(out_text)
    else:
        # --save provided
        out_path = (
            _auto_save_path(args, args.out) if args.save is True else Path(args.save)
        )
        out_path.write_text(out_text, encoding="utf-8")
        print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
