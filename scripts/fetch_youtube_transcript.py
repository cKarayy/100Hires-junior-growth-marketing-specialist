#!/usr/bin/env python3
"""Fetch a YouTube transcript and save it as markdown."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DEFAULT_OUTPUT = Path("research/youtube-transcripts/michelle-j-raymond.md")
TITLE_PLACEHOLDER = "TODO: Add video title"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a YouTube transcript and save it to markdown."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output markdown path (default: {DEFAULT_OUTPUT.as_posix()})",
    )
    parser.add_argument(
        "--title",
        default=TITLE_PLACEHOLDER,
        help="Video title to include in the markdown header",
    )
    return parser.parse_args()


def extract_video_id(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower().replace("www.", "")

    if host in {"youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if video_id:
                return video_id
        if parsed.path.startswith("/shorts/") or parsed.path.startswith("/embed/"):
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2:
                return parts[1]

    if host == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/")[0]
        if video_id:
            return video_id

    match = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[?&/]|$)", url)
    if match:
        return match.group(1)

    raise ValueError(f"Could not extract a YouTube video ID from: {url}")


def fetch_transcript(video_id: str) -> list[str]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependency: install requirements.txt to use this script."
        ) from exc

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
    except AttributeError:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=["en"])
        transcript = [
            {"text": item.text if hasattr(item, "text") else item["text"]}
            for item in fetched
        ]

    lines: list[str] = []
    for item in transcript:
        text = clean_text(item.get("text", ""))
        if text:
            lines.append(text)

    if not lines:
        raise RuntimeError("Transcript was fetched, but it did not contain any text.")

    return lines


def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def build_markdown(title: str, source_url: str, transcript_lines: list[str]) -> str:
    transcript_text = "\n".join(transcript_lines)
    return "\n".join(
        [
            f"# {title}",
            "",
            "## Metadata",
            f"- Source URL: {source_url}",
            "- Collection method: Transcript fetched with `youtube-transcript-api` via a local Python script.",
            "",
            "## Raw Transcript",
            "",
            transcript_text,
            "",
        ]
    )


def main() -> int:
    args = parse_args()

    try:
        video_id = extract_video_id(args.url)
        transcript_lines = fetch_transcript(video_id)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    markdown = build_markdown(args.title, args.url, transcript_lines)
    args.output.write_text(markdown, encoding="utf-8")

    print(f"Saved transcript to {args.output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
