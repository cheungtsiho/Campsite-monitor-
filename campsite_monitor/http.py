"""Tiny stdlib HTTP helper with retries, so the project has no dependencies."""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from typing import Any

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36 campsite-monitor"
)


class HttpError(RuntimeError):
    pass


def request_json(
    url: str,
    *,
    method: str = "GET",
    body: Any | None = None,
    headers: dict[str, str] | None = None,
    retries: int = 3,
    timeout: float = 30.0,
) -> Any:
    """Fetch ``url`` and decode JSON, retrying on 429/5xx and network errors."""
    data = None
    all_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
        all_headers["Content-Type"] = "application/json"
    all_headers.update(headers or {})

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, method=method, headers=all_headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode() or "null")
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504):
                raise HttpError(f"{method} {url} -> HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
        if attempt < retries:
            time.sleep((2**attempt) + random.random())
    raise HttpError(f"{method} {url} failed after {retries + 1} attempts: {last_error}")
