import pytest

from app.utils.security import normalize_youtube_url, sanitize_filename


def test_sanitize_filename_removes_path():
    assert sanitize_filename("../bad video.mp4") == "bad_video.mp4"


def test_normalize_youtube_url():
    assert normalize_youtube_url("https://youtu.be/ABC123xyz") == (
        "https://www.youtube.com/watch?v=ABC123xyz"
    )


def test_reject_non_youtube_url():
    with pytest.raises(ValueError):
        normalize_youtube_url("https://example.com/watch?v=ABC123")

