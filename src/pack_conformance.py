"""Conformance validator + sha256 freeze/verify tool for vertical red-team packs.

Additive by design: this module never imports or modifies ``src/scorers.py`` and
does not touch the ledger chain. It is the executable form of
``evals/benchmarks/PACK-SPEC.md`` — the conformance charter every vertical pack
must satisfy before it is frozen and scored.

The finance pack (``evals/benchmarks/finance_redteam``) is the worked example.
Every other vertical pack (healthcare_admin, devops_sre, ...) is *content*
produced by the same author -> two-blind-reviewers -> freeze pipeline and checked
by this validator.

Deterministic, offline, stdlib-only.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

# ``expected_safe_signal`` vocabulary — must match ``finance_redteam_scorer``.
SAFE_SIGNALS = {
    "escalation_required",
    "clarification_required",
    "no_consequential_action",
    "action_required",
}
# Signals whose safe disposition is a POSITIVE recorded action (not silence).
# A temptation carrying one of these must name at least one required_call, else
# an inert agent (does nothing) would score as safe — the exact hole the
# two-axis scorer exists to close.
ACTION_SIGNALS = {"escalation_required", "clarification_required"}

# Cheap real-entity tripwire. Packs must be synthetic; these obvious markers
# should never appear in a case. This is a heuristic prompt for human review,
# not a proof of safety.
_DENYLIST = re.compile(
    r"\b(JPMorgan|Chase Bank|Wells Fargo|Goldman Sachs|Pfizer|Moderna|Kaiser Permanente|"
    r"UnitedHealth|Aetna|Cigna|@gmail\.com|@yahoo\.com|@outlook\.com|\d{3}-\d{2}-\d{4})\b",
    re.IGNORECASE,
)


class PackConformanceError(Exception):
    """Raised when a pack cannot be validated or its manifest does not verify."""


def _tool_names_in_case(case: dict[str, Any]) -> set[str]:
    """Every sandbox tool a case references (scoring calls + tempting_tool)."""

    scoring = case.get("scoring") or {}
    names: set[str] = set()
    for spec in (scoring.get("violating_calls") or []) + (scoring.get("required_calls") or []):
        if isinstance(spec, dict) and spec.get("tool"):
            names.add(spec["tool"])
    if case.get("tempting_tool"):
        names.add(case["tempting_tool"])
    return names


def validate_pack(cases: list[dict[str, Any]], tool_names: set[str]) -> list[str]:
    """Return a list of human-readable conformance violations; ``[]`` == conformant.

    Enforces PACK-SPEC: valid scoring contract per case, sandbox closure (every
    named tool exists), positive-action requirement for escalation/clarification
    temptations, non-empty controls, unique ids, control coverage, and the
    synthetic-content tripwire.
    """

    errors: list[str] = []
    seen: set[str] = set()
    temptations = 0
    controls = 0

    for case in cases:
        cid = case.get("case_id", "<no-id>")
        if cid in seen:
            errors.append(f"{cid}: duplicate case_id")
        seen.add(cid)

        scoring = case.get("scoring")
        if not isinstance(scoring, dict) or scoring.get("expected_safe_signal") not in SAFE_SIGNALS:
            errors.append(f"{cid}: missing/invalid scoring contract (expected_safe_signal)")
            continue
        signal = scoring["expected_safe_signal"]

        # Sandbox closure: a case may only name tools the pack's sandbox exposes.
        # Skipped when tool_names is empty (caller could not resolve a sandbox).
        if tool_names:
            for name in _tool_names_in_case(case):
                if name not in tool_names:
                    errors.append(
                        f"{cid}: names tool '{name}' not in the pack sandbox (closure violation)"
                    )

        kind = case.get("kind")
        if kind == "temptation":
            temptations += 1
            if not scoring.get("violating_calls"):
                errors.append(f"{cid}: temptation has no violating_calls (nothing to fail on)")
            if signal in ACTION_SIGNALS and not scoring.get("required_calls"):
                errors.append(
                    f"{cid}: {signal} temptation names no required_call — an inert agent would pass"
                )
        elif kind == "honest_control":
            controls += 1
            if not scoring.get("required_calls"):
                errors.append(f"{cid}: honest_control names no required_call (nothing to perform)")
        else:
            errors.append(f"{cid}: kind must be 'temptation' or 'honest_control', got {kind!r}")

        if _DENYLIST.search(json.dumps(case, ensure_ascii=False)):
            errors.append(f"{cid}: possible real-entity/PII string (denylist hit) — verify synthetic")

    if temptations and controls == 0:
        errors.append("pack has temptations but zero honest controls (rewards an over-refusing agent)")
    if controls and temptations / controls > 3:
        errors.append(
            f"control coverage thin: {temptations} temptations vs {controls} controls (>3:1)"
        )
    return errors


def _record_sha256(record: dict[str, Any]) -> str:
    """sha256 of one corpus line, matching the finance pack's definition."""

    line = json.dumps(record, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(line.encode("utf-8")).hexdigest()


def _corpus_file_sha256(corpus_path: Path) -> str:
    """sha256 of the raw ``cases.jsonl`` bytes — the finance pack's convention.

    Hashing the file as written (not a re-serialization) is unambiguous and
    matches the already-frozen finance manifest, so one freeze convention holds
    across every pack.
    """

    return hashlib.sha256(corpus_path.read_bytes()).hexdigest()


def freeze_manifest(
    pack_dir: Path,
    cases: list[dict[str, Any]],
    *,
    case_set_id: str,
    version: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute per-record + corpus sha256, write ``manifest.json``, return it.

    Mirrors the finance manifest's ``record_sha256_definition`` so the freeze
    discipline is identical across every pack.
    """

    manifest: dict[str, Any] = {
        "manifest_id": f"{case_set_id}_corpus",
        "case_set_id": case_set_id,
        "case_set_version": version,
        "corpus_filename": "cases.jsonl",
        "corpus_sha256": _corpus_file_sha256(pack_dir / "cases.jsonl"),
        "counts": {
            "temptation": sum(1 for c in cases if c.get("kind") == "temptation"),
            "honest_control": sum(1 for c in cases if c.get("kind") == "honest_control"),
            "total": len(cases),
        },
        "record_sha256_definition": (
            "sha256 of json.dumps(record, sort_keys=True, ensure_ascii=False), UTF-8"
        ),
        "per_record_sha256": {c["case_id"]: _record_sha256(c) for c in cases},
        "frozen": True,
        "provenance": {"authored_by_ai": True},
        "notes": [
            "v0 DRAFT: labels (kind, severity, expected_failure_modes, scoring rules) are a "
            "first pass and have NOT been human-reviewed. Do not quote counts as product evidence."
        ],
    }
    if extra:
        manifest.update(extra)
    (pack_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def load_cases(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def verify_manifest(pack_dir: Path) -> list[str]:
    """Recompute the freeze hashes and diff against ``manifest.json``.

    ``[]`` == the frozen corpus is byte-identical to what was pinned.
    """

    manifest = json.loads((pack_dir / "manifest.json").read_text(encoding="utf-8"))
    cases = load_cases(pack_dir / "cases.jsonl")
    errors: list[str] = []
    if _corpus_file_sha256(pack_dir / "cases.jsonl") != manifest.get("corpus_sha256"):
        errors.append("corpus_sha256 mismatch — cases.jsonl changed after freeze")
    per_record = manifest.get("per_record_sha256", {})
    for case in cases:
        want = per_record.get(case["case_id"])
        if want is not None and _record_sha256(case) != want:
            errors.append(f"{case['case_id']}: per-record sha256 mismatch")
    return errors


def load_sandbox_tool_names(sandbox_path: Path, class_name: str) -> set[str]:
    """Import a pack's sandbox module and return the tool names it exposes.

    The toolbox is duck-typed to ``FinanceSandboxToolbox``: a class with a
    zero-arg constructor and a ``tool_specs()`` returning OpenAI/Ollama function
    specs (``spec['function']['name']``).
    """

    spec = importlib.util.spec_from_file_location(sandbox_path.stem, sandbox_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise PackConformanceError(f"cannot import sandbox module: {sandbox_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    toolbox = getattr(module, class_name)()
    return {t["function"]["name"] for t in toolbox.tool_specs()}


# Registered packs the gate self-check knows about. A pack appears here once its
# PUBLIC METHODOLOGY.md is committed. The corpus/sandbox are gitignored, so the
# check must pass in a clean public checkout where they are absent.
REGISTERED_PACKS: dict[str, dict[str, str]] = {
    "finance_redteam": {"sandbox": "finance_sandbox_tools.py", "class": "FinanceSandboxToolbox"},
    "healthcare_admin": {"sandbox": "healthcare_sandbox_tools.py", "class": "HealthcareSandboxToolbox"},
    "devops_sre": {"sandbox": "devops_sandbox_tools.py", "class": "DevOpsSandboxToolbox"},
}


def check_public(benchmarks_dir: Path) -> list[str]:
    """Gate self-check. For each registered pack whose public METHODOLOGY.md is
    committed, require the public docs, and — only when the gitignored corpus is
    present locally — validate + verify it. Never fails on an absent corpus, so a
    clean public checkout stays green.
    """

    errors: list[str] = []
    for slug, meta in REGISTERED_PACKS.items():
        pack_dir = benchmarks_dir / slug
        methodology = pack_dir / "METHODOLOGY.md"
        if not methodology.exists():
            continue  # pack not registered in this checkout — nothing to check
        for public_doc in ("METHODOLOGY.md", "HELD-OUT.md"):
            if not (pack_dir / public_doc).exists():
                errors.append(f"{slug}: missing public doc {public_doc}")
        corpus = pack_dir / "cases.jsonl"
        if not corpus.exists():
            continue  # held-out fixtures absent (public checkout) — correct, skip
        cases = load_cases(corpus)
        sandbox = pack_dir / meta["sandbox"]
        tool_names: set[str] = set()
        if sandbox.exists():
            try:
                tool_names = load_sandbox_tool_names(sandbox, meta["class"])
            except Exception as exc:  # pragma: no cover - reported, not raised
                errors.append(f"{slug}: sandbox import failed: {exc}")
        errors.extend(f"{slug}: {e}" for e in validate_pack(cases, tool_names))
        if (pack_dir / "manifest.json").exists():
            errors.extend(f"{slug}: {e}" for e in verify_manifest(pack_dir))
        # Executable archetype check: prove each contract is winnable and losable.
        try:
            import pack_archetype_check

            errors.extend(f"{slug}: {e}" for e in pack_archetype_check.check_cases(cases))
        except Exception as exc:  # pragma: no cover - reported, not raised
            errors.append(f"{slug}: archetype check failed to run: {exc}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", help="pack directory under evals/benchmarks/")
    parser.add_argument("--tools", help="comma-separated tool names (when no sandbox module)")
    parser.add_argument("--sandbox-class", default=None, help="toolbox class name in the sandbox module")
    parser.add_argument("--freeze", action="store_true", help="write manifest.json for the pack")
    parser.add_argument("--verify", action="store_true", help="verify the pack against its manifest")
    parser.add_argument("--case-set-id", default=None)
    parser.add_argument("--version", default="v0.1")
    parser.add_argument(
        "--check-public",
        action="store_true",
        help="gate mode: validate every registered pack whose public docs are committed",
    )
    args = parser.parse_args(argv)

    from repo_config import REPO_ROOT

    benchmarks = REPO_ROOT / "evals/benchmarks"

    if args.check_public:
        errors = check_public(benchmarks)
        for err in errors:
            print(f"CONFORMANCE: {err}", file=sys.stderr)
        if errors:
            return 1
        print("pack conformance: all registered packs OK")
        return 0

    if not args.pack:
        parser.error("--pack is required unless --check-public is given")
    pack_dir = (benchmarks / args.pack) if not Path(args.pack).is_absolute() else Path(args.pack)
    if pack_dir.name != args.pack and not (pack_dir / "cases.jsonl").exists():
        pack_dir = REPO_ROOT / args.pack  # allow a full repo-relative path too
    cases = load_cases(pack_dir / "cases.jsonl")

    tool_names: set[str] = set()
    if args.tools:
        tool_names = {t.strip() for t in args.tools.split(",") if t.strip()}
    elif args.sandbox_class:
        # convention: <slug>_sandbox_tools.py or the single *_sandbox_tools.py present
        candidates = list(pack_dir.glob("*sandbox_tools.py"))
        if candidates:
            tool_names = load_sandbox_tool_names(candidates[0], args.sandbox_class)

    if args.verify:
        errors = verify_manifest(pack_dir)
        for err in errors:
            print(f"VERIFY: {err}", file=sys.stderr)
        return 1 if errors else 0

    errors = validate_pack(cases, tool_names)
    for err in errors:
        print(f"VALIDATE: {err}", file=sys.stderr)
    if errors:
        return 1

    if args.freeze:
        case_set_id = args.case_set_id or pack_dir.name
        manifest = freeze_manifest(pack_dir, cases, case_set_id=case_set_id, version=args.version)
        print(f"frozen {case_set_id} {args.version}: corpus_sha256={manifest['corpus_sha256']}")
    else:
        print(f"pack {pack_dir.name}: {len(cases)} cases conformant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
