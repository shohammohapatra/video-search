from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def seconds_to_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def youtube_timestamp_url(url: str | None, seconds: float) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["t"] = [f"{int(max(0, seconds))}s"]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))

