from app.utils.time import seconds_to_timestamp, youtube_timestamp_url


def test_seconds_to_timestamp():
    assert seconds_to_timestamp(497) == "08:17"


def test_youtube_timestamp_url():
    url = youtube_timestamp_url("https://www.youtube.com/watch?v=ABC123", 497)
    assert url == "https://www.youtube.com/watch?v=ABC123&t=497s"

