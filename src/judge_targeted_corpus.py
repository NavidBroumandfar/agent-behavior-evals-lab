"""Assemble, validate, and freeze the judge-targeted red-team corpus.

Pre-registered in ``evals/adversarial/judge-targeted-protocol.md``. Authors write
one JSONL shard per attack lens; this module merges them, enforces the corpus
rules the protocol fixed in advance, and emits a sha256 manifest so the corpus
is frozen before any monitor scores it.

Validation is deliberately unforgiving. A corpus that silently accepts a
malformed record, a duplicate id, an orphaned twin, or a lying record whose log
actually supports it would manufacture a gap out of bad inputs — which is the
one failure mode an adversarial lab cannot survive.

Deterministic, offline, stdlib-only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from repo_config import REPO_ROOT
from reporting_utils import write_json_object

CORPUS_PATH = REPO_ROOT / "evals/adversarial/judge_targeted_cases.jsonl"
MANIFEST_PATH = REPO_ROOT / "evals/adversarial/judge_targeted_manifest.json"

REQUIRED_FIELDS = (
    "author",
    "category",
    "evasion_class",
    "evasion_id",
    "expected_catch",
    "kind",
    "note",
    "output_text",
    "public_safe",
    "tool_events",
    "twin_of",
)
VALID_KINDS = {"lying", "honest_twin"}
VALID_CATEGORIES = {
    "safe_direct_response",
    "approval_gated",
    "refusal_required",
    "uncertainty_handling",
}
VALID_STATUSES = {"succeeded", "failed", "denied"}


class CorpusError(Exception):
    """Judge-targeted corpus validation error."""


def load_shard(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise CorpusError(f"{path.name}:{line_number}: invalid JSON ({exc})") from exc
    return records


def validate(records: list[dict[str, Any]]) -> list[str]:
    """Return every rule violation found. Empty list means the corpus is sound."""

    problems: list[str] = []
    seen_ids: set[str] = set()
    lying_ids: set[str] = set()

    for record in records:
        rid = record.get("evasion_id", "<missing id>")

        missing = [f for f in REQUIRED_FIELDS if f not in record]
        if missing:
            problems.append(f"{rid}: missing fields {missing}")
            continue

        if rid in seen_ids:
            problems.append(f"{rid}: duplicate evasion_id")
        seen_ids.add(rid)

        if record["kind"] not in VALID_KINDS:
            problems.append(f"{rid}: kind {record['kind']!r} not in {sorted(VALID_KINDS)}")
        if record["category"] not in VALID_CATEGORIES:
            problems.append(f"{rid}: category {record['category']!r} invalid")
        if record["public_safe"] is not True:
            problems.append(f"{rid}: public_safe must be true")
        if not str(record["output_text"]).strip():
            problems.append(f"{rid}: empty output_text")
        if not str(record["note"]).strip():
            problems.append(f"{rid}: empty note — every record must say what it is doing")

        events = record["tool_events"]
        if not isinstance(events, list):
            problems.append(f"{rid}: tool_events must be a list")
        else:
            for index, event in enumerate(events):
                if not isinstance(event, dict):
                    problems.append(f"{rid}: tool_events[{index}] is not an object")
                    continue
                for key in ("tool_name", "action", "status"):
                    if key not in event:
                        problems.append(f"{rid}: tool_events[{index}] missing {key}")
                if event.get("status") not in VALID_STATUSES:
                    problems.append(
                        f"{rid}: tool_events[{index}] status {event.get('status')!r} invalid"
                    )

        if record["kind"] == "lying":
            lying_ids.add(rid)
            if record["twin_of"]:
                problems.append(f"{rid}: lying records must have empty twin_of")

    # Every twin must point at a lying record that exists, and every lying
    # record's lens must ship at least one twin (protocol corpus rules).
    twinned_lenses: set[str] = set()
    for record in records:
        if record.get("kind") != "honest_twin":
            continue
        rid = record.get("evasion_id", "<missing id>")
        target = record.get("twin_of", "")
        if not target:
            problems.append(f"{rid}: honest twin must name the record it mirrors via twin_of")
        elif target not in lying_ids:
            problems.append(f"{rid}: twin_of {target!r} does not match any lying record")
        twinned_lenses.add(record.get("evasion_class", ""))

    for record in records:
        if record.get("kind") == "lying" and record.get("evasion_class") not in twinned_lenses:
            problems.append(
                f"{record.get('evasion_class')}: lens ships no honest twin"
            )
            break

    return problems


def freeze(records: list[dict[str, Any]], corpus_path: Path, manifest_path: Path) -> dict[str, Any]:
    """Write the corpus in a stable order and pin it with a sha256 manifest."""

    ordered = sorted(records, key=lambda r: r["evasion_id"])
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    with corpus_path.open("w", encoding="utf-8") as handle:
        for record in ordered:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    per_record = {
        r["evasion_id"]: hashlib.sha256(
            json.dumps(r, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        for r in ordered
    }
    lens_counts: dict[str, dict[str, int]] = {}
    for record in ordered:
        row = lens_counts.setdefault(record["evasion_class"], {"lying": 0, "honest_twin": 0})
        row[record["kind"]] += 1

    manifest = {
        "authors": "claude-opus-4-8 x6, one attack lens each (see protocol)",
        "corpus": str(corpus_path.relative_to(REPO_ROOT)),
        "corpus_sha256": hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        "frozen_at": "2026-07-18",
        "honest_twin_count": sum(1 for r in ordered if r["kind"] == "honest_twin"),
        "lying_count": sum(1 for r in ordered if r["kind"] == "lying"),
        "note": (
            "Frozen before any monitor scored it. Labels are AUTHOR-INTENDED; the "
            "adjudicated labels that gate scoring live in the adjudication artifact. "
            "Verify with: shasum -a 256 " + str(corpus_path.relative_to(REPO_ROOT))
        ),
        "per_lens_counts": lens_counts,
        "per_record_sha256": per_record,
        "protocol": "evals/adversarial/judge-targeted-protocol.md",
        "threat_model": "attacker knows the judge prompt verbatim; no feedback loop",
    }
    write_json_object(manifest, manifest_path)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shards", nargs="+", required=True)
    parser.add_argument("--corpus-out", default=str(CORPUS_PATH))
    parser.add_argument("--manifest-out", default=str(MANIFEST_PATH))
    args = parser.parse_args(argv)

    records: list[dict[str, Any]] = []
    for shard in args.shards:
        path = Path(shard)
        if not path.exists():
            raise CorpusError(f"shard not found: {path}")
        shard_records = load_shard(path)
        print(f"{path.name}: {len(shard_records)} records")
        records.extend(shard_records)

    problems = validate(records)
    if problems:
        print(f"\n{len(problems)} validation problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    manifest = freeze(records, Path(args.corpus_out), Path(args.manifest_out))
    print(
        f"\nfroze {manifest['lying_count']} lying / {manifest['honest_twin_count']} twins"
        f"\nsha256 {manifest['corpus_sha256']}"
    )
    for lens, counts in sorted(manifest["per_lens_counts"].items()):
        print(f"  {lens}: {counts['lying']} lying, {counts['honest_twin']} twins")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
