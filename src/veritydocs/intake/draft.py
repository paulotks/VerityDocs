from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def new_draft() -> dict[str, Any]:
    ts = now_iso()
    return {
        "session_id": ts.replace(":", "").replace("-", ""),
        "status": "em_andamento",
        "started_at": ts,
        "updated_at": ts,
        "fields": {},
        "questions_asked": [],
        "confirmed": False,
    }


def save_draft(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_draft(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
