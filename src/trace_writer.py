"""Trace writing utilities for evaluator runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_jsonl(records: list[dict[str, Any]], output_path: str | Path) -> None:
    """Write records as UTF-8 JSONL, creating parent directories as needed."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, ensure_ascii=False))
            output_file.write("\n")
