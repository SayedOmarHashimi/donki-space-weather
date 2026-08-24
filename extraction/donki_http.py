"""Shared HTTP helper for the DONKI extractors.

NASA's DONKI endpoints occasionally return transient errors (503 Service
Unavailable, gateway timeouts, rate limits) or drop connections. A single
blip used to abort the whole daily refresh. `get_json` retries those
transient failures with exponential backoff so a momentary NASA outage no
longer fails the pipeline, while genuine client errors (bad key, bad params)
still surface immediately.
"""
import time

import requests

# Transient, server-side/rate-limit statuses worth retrying. Everything else
# (400/401/403/404 …) points at a real problem and is raised right away.
RETRY_STATUSES = {429, 500, 502, 503, 504}


class TransientAPIError(Exception):
    """Raised when a request keeps failing on a transient error after all retries."""


def get_json(url, params, *, timeout=30, retries=5, backoff=2.0, session=None):
    """GET ``url`` and return parsed JSON, retrying transient failures.

    Retries connection errors, timeouts, and ``RETRY_STATUSES`` responses with
    exponential backoff (``backoff``, ``backoff*2``, ``backoff*4`` …), honoring
    a ``Retry-After`` header when the server sends one. Non-transient HTTP
    errors raise immediately via ``raise_for_status``. If every attempt fails
    on a transient error, raises :class:`TransientAPIError`.
    """
    sess = session or requests
    last_exc = None
    reason = "unknown error"

    for attempt in range(1, retries + 1):
        resp = None
        try:
            resp = sess.get(url, params=params, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            reason = type(exc).__name__
        else:
            if resp.status_code not in RETRY_STATUSES:
                resp.raise_for_status()   # non-transient 4xx -> raise now
                return resp.json()
            reason = f"HTTP {resp.status_code} {resp.reason}"
            last_exc = requests.HTTPError(reason, response=resp)

        if attempt == retries:
            break

        delay = backoff * (2 ** (attempt - 1))
        if resp is not None:                      # honor Retry-After on 429/503 etc.
            retry_after = resp.headers.get("Retry-After", "")
            if retry_after.isdigit():
                delay = max(delay, int(retry_after))
        print(f"[retry] {url} failed ({reason}); "
              f"attempt {attempt}/{retries}, retrying in {delay:.0f}s")
        time.sleep(delay)

    raise TransientAPIError(
        f"{url} still failing after {retries} attempts: {reason}"
    ) from last_exc
