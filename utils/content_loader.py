from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = BASE_DIR / "content"


def _read_json(filename: str) -> Any:
    path = CONTENT_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@lru_cache(maxsize=1)
def get_stages() -> list[dict[str, Any]]:
    return _read_json("stages.json")


@lru_cache(maxsize=1)
def get_guides() -> dict[str, Any]:
    return _read_json("guide_steps.json")


@lru_cache(maxsize=1)
def get_programs() -> list[dict[str, Any]]:
    return _read_json("programs.json")


@lru_cache(maxsize=1)
def get_faqs() -> list[dict[str, Any]]:
    return _read_json("faq.json")
