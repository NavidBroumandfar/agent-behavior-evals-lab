"""Trace writing utilities for evaluator runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reporting_utils import atomic_write_text


def write_jsonl(records: list[dict[str, Any]], output_path: str | Path) -> None:
    """Write records as UTF-8 JSONL, creating parent directories as needed.

    The write is atomic: a reader concurrent with a regenerating quality gate
    never sees a half-written trace. Writing line by line into the destination
    was what let a reader observe a truncated final record and fail with
    `Unterminated string`. See `reporting_utils.atomic_write_text`.
    """

    path = Path(output_path)
    content = "".join(f"{json.dumps(record, ensure_ascii=False)}\n" for record in records)
    atomic_write_text(content, path)
