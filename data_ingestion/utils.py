from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import requests


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    return logger


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def parse_ymd(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD.") from e


def read_sites_config(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Sites config not found: {p}")
    payload = json.loads(p.read_text(encoding="utf-8"))

    sites = payload.get("sites")
    if not isinstance(sites, list) or not sites:
        raise ValueError("sites.json must contain a non-empty 'sites' list.")

    normalized: list[dict[str, Any]] = []
    for item in sites:
        if isinstance(item, str):
            site_id = item.strip()
            if not site_id:
                continue
            normalized.append({"site_id": site_id})
            continue

        if not isinstance(item, dict) or "site_id" not in item:
            raise ValueError("Each site must be a string site_id or an object with 'site_id'.")
        site_id = str(item["site_id"]).strip()
        if not site_id:
            raise ValueError("site_id cannot be empty.")
        normalized.append({**item, "site_id": site_id})

    if not normalized:
        raise ValueError("No valid site_id entries found in sites.json.")
    return normalized


@dataclass(frozen=True)
class HttpConfig:
    timeout_s: float = 30.0
    max_retries: int = 3
    backoff_s: float = 1.0


def request_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    http: HttpConfig | None = None,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    http = http or HttpConfig()
    logger = logger or get_logger("http")

    last_err: Exception | None = None
    for attempt in range(1, http.max_retries + 1):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=http.timeout_s)
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
            return r.json()
        except Exception as e:
            last_err = e
            if attempt < http.max_retries:
                sleep_s = http.backoff_s * attempt
                logger.warning("Request failed (attempt %s/%s). Retrying in %.1fs. Error=%s", attempt, http.max_retries, sleep_s, e)
                time.sleep(sleep_s)
            else:
                break

    raise RuntimeError(f"Failed to fetch JSON from {url} after {http.max_retries} attempts.") from last_err


def chunked(items: Iterable[Any], size: int) -> Iterable[list[Any]]:
    buf: list[Any] = []
    for x in items:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

