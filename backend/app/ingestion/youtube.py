import subprocess
from pathlib import Path

from app.core.config import settings


class YoutubeDownloadError(RuntimeError):
    """Raised when YouTube metadata extraction or media download fails."""


def download_youtube_video(url: str, video_id: str, resolution: int = 720) -> tuple[Path, str]:
    target_dir = settings.storage_path / "videos"
    output_template = str(target_dir / f"{video_id}.%(ext)s")
    try:
        info = subprocess.run(
            [
                "yt-dlp",
                "--print",
                "after_move:title",
                "--no-playlist",
                "--no-warnings",
                "--merge-output-format",
                "mp4",
                "-f",
                f"bestvideo[height<={resolution}][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<={resolution}]",
                "-o",
                output_template,
                url,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise YoutubeDownloadError("YouTube downloader is not installed") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip().splitlines()
        message = detail[-1] if detail else "YouTube download failed"
        raise YoutubeDownloadError(message[:500]) from exc
    title = info.stdout.splitlines()[0].strip() if info.stdout.strip() else "YouTube Video"
    matches = sorted(
        path
        for path in target_dir.glob(f"{video_id}.*")
        if path.is_file() and not path.name.endswith((".part", ".ytdl"))
    )
    media = next((path for path in matches if path.suffix.lower() in settings.allowed_video_extensions), None)
    if not media:
        raise YoutubeDownloadError("Downloaded media file was not found")
    return media, title
