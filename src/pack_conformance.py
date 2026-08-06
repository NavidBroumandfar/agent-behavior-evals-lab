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
from typing import Any, NamedTuple

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

# A manifest frozen before sandbox pinning existed cannot be distinguished from a
# tampered one by hashes alone — so it is reported as UNPINNED, never as drift.
# Visible (the gate prints it), non-fatal (every already-frozen pack stays green).
SANDBOX_UNPINNED_NOTICE = (
    "sandbox is NOT pinned by this manifest (frozen before sandbox pinning existed) — "
    "re-freeze to pin the module that emits the breach tokens the scorer reads"
)

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


def _file_sha256(path: Path) -> str:
    """sha256 of a file's raw bytes — the one hashing convention this module uses."""

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _corpus_file_sha256(corpus_path: Path) -> str:
    """sha256 of the raw ``cases.jsonl`` bytes — the finance pack's convention.

    Hashing the file as written (not a re-serialization) is unambiguous and
    matches the already-frozen finance manifest, so one freeze convention holds
    across every pack.
    """

    return _file_sha256(corpus_path)


def _resolve_sandbox_path(pack_dir: Path, sandbox_filename: str | None = None) -> Path | None:
    """The pack's sandbox module, or ``None`` when the pack ships no sandbox.

    Some packs are driven by ``--tools`` instead of a module, so absence is a
    legitimate state and must be recorded as such rather than guessed at. When no
    filename is given, the registry is authoritative and the ``*sandbox_tools.py``
    glob (the convention ``main()`` already uses) is the fallback.
    """

    if sandbox_filename:
        candidate = pack_dir / sandbox_filename
        return candidate if candidate.is_file() else None
    registered = REGISTERED_PACKS.get(pack_dir.name)
    if registered:
        candidate = pack_dir / registered["sandbox"]
        if candidate.is_file():
            return candidate
    matches = sorted(pack_dir.glob("*sandbox_tools.py"))
    return matches[0] if matches else None


def freeze_manifest(
    pack_dir: Path,
    cases: list[dict[str, Any]],
    *,
    case_set_id: str,
    version: str,
    sandbox_filename: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute per-record + corpus + sandbox sha256, write ``manifest.json``, return it.

    Mirrors the finance manifest's ``record_sha256_definition`` so the freeze
    discipline is identical across every pack.

    The sandbox is pinned alongside the corpus because the sandbox is what emits
    the breach tokens the scorer reads: a manifest that pins only ``cases.jsonl``
    lets two runs against the same frozen corpus score differently. When the pack
    ships no sandbox module both fields are recorded as ``null`` — explicitly
    "no sandbox", which is a different claim from an older manifest's silence.
    """

    sandbox = _resolve_sandbox_path(pack_dir, sandbox_filename)
    manifest: dict[str, Any] = {
        "manifest_id": f"{case_set_id}_corpus",
        "case_set_id": case_set_id,
        "case_set_version": version,
        "corpus_filename": "cases.jsonl",
        "corpus_sha256": _corpus_file_sha256(pack_dir / "cases.jsonl"),
        "sandbox_filename": sandbox.name if sandbox is not None else None,
        "sandbox_sha256": _file_sha256(sandbox) if sandbox is not None else None,
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


def verify_sandbox_pin(
    pack_dir: Path,
    manifest: dict[str, Any],
    *,
    notices: list[str] | None = None,
) -> list[str]:
    """Verify the pinned sandbox hash. ``[]`` == pinned-and-unchanged, or unpinned.

    Three states, kept deliberately distinct because conflating them would either
    break every already-frozen pack or hide real drift:

    - **key absent** — a manifest frozen before sandbox pinning existed. It never
      made a claim about the sandbox, so there is nothing to contradict: reported
      as an UNPINNED notice, never as an error. Absence is read with ``in``, not
      ``get()``, so it cannot be confused with an explicit ``null``.
    - **key present and ``null``** — the pack was frozen with no sandbox module
      (it is driven by ``--tools``). A module appearing later IS drift: the thing
      that emits breach tokens changed after the freeze.
    - **key present with a hash** — recompute and diff, like the corpus.
    """

    if "sandbox_sha256" not in manifest:
        if notices is not None:
            notices.append(SANDBOX_UNPINNED_NOTICE)
        return []

    pinned = manifest["sandbox_sha256"]
    filename = manifest.get("sandbox_filename")
    if pinned is None:
        found = _resolve_sandbox_path(pack_dir)
        if found is not None:
            return [
                f"sandbox_sha256 mismatch — manifest pins no sandbox, but {found.name} "
                "is present now (the breach-token emitter changed after freeze)"
            ]
        return []

    if not filename:
        return ["sandbox_sha256 pinned without a sandbox_filename — manifest is inconsistent"]
    sandbox = pack_dir / filename
    if not sandbox.is_file():
        return [f"sandbox module {filename} is pinned by the manifest but missing"]
    if _file_sha256(sandbox) != pinned:
        return [f"sandbox_sha256 mismatch — {filename} changed after freeze"]
    return []


def verify_manifest(pack_dir: Path, *, notices: list[str] | None = None) -> list[str]:
    """Recompute the freeze hashes and diff against ``manifest.json``.

    ``[]`` == the frozen corpus (and, when pinned, the sandbox) is byte-identical
    to what was pinned. Pass ``notices`` to also collect non-fatal observations —
    currently only "this manifest does not pin the sandbox at all".
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
    errors.extend(verify_sandbox_pin(pack_dir, manifest, notices=notices))
    return errors


def import_sandbox_module(sandbox_path: Path) -> Any:
    """Import a pack's sandbox module from its path (no package install needed)."""

    spec = importlib.util.spec_from_file_location(sandbox_path.stem, sandbox_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise PackConformanceError(f"cannot import sandbox module: {sandbox_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def toolbox_class_name(module: Any) -> str | None:
    """The toolbox class a sandbox module defines, or ``None`` when it defines none.

    Needed because an **unregistered** pack has no registry entry naming its
    class, and refusing to check it for want of that one string is how a pack
    comes to sit on disk unchecked. Only classes *defined in this module* count,
    so the imported ``PackSandboxBase`` every pack sandbox inherits from can
    never be mistaken for the pack's own toolbox. Definition order decides ties,
    with a ``*Toolbox`` name preferred, so the answer is deterministic.
    """

    defined = [
        (name, obj)
        for name, obj in vars(module).items()
        if isinstance(obj, type)
        and getattr(obj, "__module__", None) == module.__name__
        and callable(getattr(obj, "tool_specs", None))
    ]
    if not defined:
        return None
    for name, _obj in defined:
        if name.endswith("Toolbox"):
            return name
    return defined[0][0]


def load_sandbox_tool_names(sandbox_path: Path, class_name: str | None = None) -> set[str]:
    """Import a pack's sandbox module and return the tool names it exposes.

    The toolbox is duck-typed to ``FinanceSandboxToolbox``: a class with a
    zero-arg constructor and a ``tool_specs()`` returning OpenAI/Ollama function
    specs (``spec['function']['name']``). ``class_name`` may be omitted, in which
    case the module's own toolbox class is discovered — the unregistered-pack path.
    """

    module = import_sandbox_module(sandbox_path)
    resolved = class_name or toolbox_class_name(module)
    if not resolved:
        raise PackConformanceError(f"{sandbox_path.name} defines no toolbox class")
    toolbox = getattr(module, resolved)()
    return {t["function"]["name"] for t in toolbox.tool_specs()}


# ---------------------------------------------------------------------------
# The registry, its lifecycle states, and discovery of what is NOT in it
# ---------------------------------------------------------------------------

# Lifecycle states a registered pack can be in. Added 2026-08-06, after a review
# found ``legal_ops`` and ``hr_payroll`` sitting on disk with an authored corpus
# and a working sandbox while EVERY gate check discovered its work from the
# registry — so the gate validated neither pack, and said nothing about it.
#
# The binary registered/not-registered is what created that hole: registering was
# treated as a freeze-time act (each pack's METHODOLOGY said so in as many words),
# so the only way to be checked was to make a claim the pack could not yet make.
# An author facing that choice picks "unchecked", every time. A lifecycle state
# separates the two claims: ``candidate`` says "check me", ``frozen`` says "and I
# am pinned".
STATUS_CANDIDATE = "candidate"  # corpus authored, in review, NOT pinned — check it anyway
STATUS_FROZEN = "frozen"  # pinned by a manifest; verify the pin too
STATUS_UNREGISTERED = "unregistered"  # found on disk, in no registry entry — synthesized

# Registered packs the gate self-check knows about. A pack appears here as soon as
# it has held-out content worth checking, with the state it is actually in — NOT
# only once it freezes. The corpus/sandbox are gitignored, so every check must
# still pass in a clean public checkout where they are absent.
REGISTERED_PACKS: dict[str, dict[str, str]] = {
    "finance_redteam": {
        "sandbox": "finance_sandbox_tools.py",
        "class": "FinanceSandboxToolbox",
        "status": STATUS_FROZEN,
    },
    "healthcare_admin": {
        "sandbox": "healthcare_sandbox_tools.py",
        "class": "HealthcareSandboxToolbox",
        "status": STATUS_FROZEN,
    },
    "devops_sre": {
        "sandbox": "devops_sandbox_tools.py",
        "class": "DevOpsSandboxToolbox",
        "status": STATUS_FROZEN,
    },
    "legal_ops": {
        "sandbox": "legal_sandbox_tools.py",
        "class": "LegalSandboxToolbox",
        "status": STATUS_CANDIDATE,
    },
    "hr_payroll": {
        "sandbox": "hr_sandbox_tools.py",
        "class": "HRPayrollSandboxToolbox",
        "status": STATUS_CANDIDATE,
    },
}

# What makes a directory under evals/benchmarks/ a PACK rather than a plain
# corpus. ``local_public_v1/v2/v3`` ship a ``cases.jsonl`` too, in a completely
# different schema, so "has cases" is not the test — a published pack charter or
# a pack sandbox module is.
PACK_MARKERS = ("METHODOLOGY.md",)
SANDBOX_GLOB = "*sandbox_tools.py"
# Files that are held out per pack (gitignored). Their presence is what turns "a
# pack directory exists" into "there is something here the gate can check".
HELD_OUT_FILES = ("cases.jsonl", "manifest.json")

UNREGISTERED_PACK_NOTICE = (
    "PRESENT BUT UNREGISTERED — held-out content is on disk ({content}) and this pack is in no "
    "REGISTERED_PACKS entry. It is being checked opportunistically as an unregistered candidate, "
    "but nothing else in the repo knows it exists: add it to src/pack_conformance.py:REGISTERED_PACKS "
    f"with status={STATUS_CANDIDATE!r} (registration is NOT a freeze-time act)"
)


class PackEntry(NamedTuple):
    """One pack the gate will look at, registered or merely found on disk."""

    slug: str
    sandbox: str  # sandbox module filename; "" when the pack ships none
    cls: str  # toolbox class name; "" when it must be discovered from the module
    status: str

    @property
    def registered(self) -> bool:
        return self.status != STATUS_UNREGISTERED

    @property
    def frozen(self) -> bool:
        return self.status == STATUS_FROZEN


def held_out_content(pack_dir: Path) -> list[str]:
    """Held-out filenames present in this pack directory, sorted.

    Empty means "public docs only" — the normal state of a clean public checkout,
    and the state that must stay silent.
    """

    found = [name for name in HELD_OUT_FILES if (pack_dir / name).is_file()]
    found.extend(path.name for path in pack_dir.glob(SANDBOX_GLOB))
    return sorted(set(found))


def is_pack_dir(pack_dir: Path) -> bool:
    """Does this directory claim to be a vertical red-team pack?

    Either it publishes a pack charter, or it ships a pack sandbox module. The
    second arm matters: a pack whose author has not written the public docs yet
    is exactly the case the gate must still see.
    """

    if any((pack_dir / marker).is_file() for marker in PACK_MARKERS):
        return True
    return any(pack_dir.glob(SANDBOX_GLOB))


def entry_sandbox_path(pack_dir: Path, entry: PackEntry) -> Path | None:
    """The sandbox module for an entry: the registry's filename, else the glob."""

    if entry.sandbox:
        candidate = pack_dir / entry.sandbox
        return candidate if candidate.is_file() else None
    matches = sorted(pack_dir.glob(SANDBOX_GLOB))
    return matches[0] if matches else None


def discover_packs(benchmarks_dir: Path) -> list[PackEntry]:
    """Every pack the gate should look at: the registry FIRST, then the disk.

    Registry-only traversal is what let two packs accumulate a corpus and a
    sandbox without a single check ever running against them. So the registry is
    no longer the enumeration — it is the *annotation*. A pack directory holding
    held-out content but named in no entry is still returned, tagged
    ``STATUS_UNREGISTERED``, so the caller can report it by name and check what
    is checkable without one.

    A registered slug with neither public docs nor held-out content is skipped:
    the pack does not exist in this checkout. A pack directory with public docs
    and *nothing else* is returned too, so its doc contract is still checked, but
    it carries no content and therefore stays silent — that is a clean public
    checkout, and it must not go noisy.
    """

    entries: list[PackEntry] = []
    seen: set[str] = set()
    for slug, meta in REGISTERED_PACKS.items():
        seen.add(slug)
        pack_dir = benchmarks_dir / slug
        if not is_pack_dir(pack_dir) and not held_out_content(pack_dir):
            continue  # pack not in this checkout — nothing to check
        entries.append(
            PackEntry(slug, meta.get("sandbox", ""), meta.get("class", ""), meta.get("status", STATUS_FROZEN))
        )
    if not benchmarks_dir.is_dir():
        return entries
    for pack_dir in sorted(p for p in benchmarks_dir.iterdir() if p.is_dir()):
        if pack_dir.name in seen or not is_pack_dir(pack_dir):
            continue
        content = held_out_content(pack_dir)
        if not content:
            continue  # a published charter with nothing held out — normal, silent
        sandbox = next(iter(sorted(pack_dir.glob(SANDBOX_GLOB))), None)
        entries.append(
            PackEntry(pack_dir.name, sandbox.name if sandbox is not None else "", "", STATUS_UNREGISTERED)
        )
    return entries


def unregistered_packs(benchmarks_dir: Path) -> list[str]:
    """Slugs found on disk with held-out content and no registry entry."""

    return [e.slug for e in discover_packs(benchmarks_dir) if not e.registered]


def packs_with_corpus(benchmarks_dir: Path) -> list[PackEntry]:
    """Discovered packs whose held-out ``cases.jsonl`` is actually present.

    The shared traversal for every check that needs a corpus, and the number a
    summary line must report: "0 findings" over 5 packs and "0 findings" over
    none are different results, and a check that cannot tell you which is the
    instrument this whole discovery pass exists to stop shipping.
    """

    return [e for e in discover_packs(benchmarks_dir) if (benchmarks_dir / e.slug / "cases.jsonl").is_file()]


def check_public(benchmarks_dir: Path, *, notices: list[str] | None = None) -> list[str]:
    """Gate self-check over every pack ``discover_packs`` can see — registered or not.

    For each pack present in this checkout, require the public docs, and — only
    when the gitignored corpus is present locally — validate + verify it. Never
    fails on an absent corpus, so a clean public checkout stays green *and quiet*.

    Two things are deliberately kept on different channels:

    - **A pack being unregistered is a NOTICE.** It is a bookkeeping fact about
      the registry, and failing the blocking gate on the mere existence of a
      work-in-progress pack directory would teach authors to keep their pack
      somewhere the gate cannot see — reopening the hole this closes. But the
      notice names the pack, says the content is on disk, and says what to do.
    - **What the checks find in that pack is an ERROR**, exactly as for a
      registered pack. A duplicate case_id or a closure violation is a defect
      whether or not anyone remembered to add a registry line, and a check that
      runs is worth more than a warning that scrolls past.

    Pass ``notices`` to collect the non-fatal, slug-prefixed observations (an
    unregistered pack; a manifest predating sandbox pinning). They are kept out of
    the returned error list so neither can fail the gate.
    """

    errors: list[str] = []
    for entry in discover_packs(benchmarks_dir):
        slug = entry.slug
        pack_dir = benchmarks_dir / slug
        content = held_out_content(pack_dir)
        if not entry.registered and notices is not None:
            notices.append(f"{slug}: " + UNREGISTERED_PACK_NOTICE.format(content=", ".join(content)))
        for public_doc in ("METHODOLOGY.md", "HELD-OUT.md"):
            if not (pack_dir / public_doc).exists():
                errors.append(f"{slug}: missing public doc {public_doc}")
        corpus = pack_dir / "cases.jsonl"
        if not corpus.exists():
            continue  # held-out fixtures absent (public checkout) — correct, skip
        try:
            cases = load_cases(corpus)
        except Exception as exc:  # reported, not raised — corruption must not mask itself
            errors.append(f"{slug}: cases.jsonl unreadable (corrupt/truncated?): {exc}")
            continue
        sandbox = entry_sandbox_path(pack_dir, entry)
        tool_names: set[str] = set()
        if sandbox is not None:
            try:
                tool_names = load_sandbox_tool_names(sandbox, entry.cls or None)
            except Exception as exc:  # pragma: no cover - reported, not raised
                errors.append(f"{slug}: sandbox import failed: {exc}")
        errors.extend(f"{slug}: {e}" for e in validate_pack(cases, tool_names))
        if (pack_dir / "manifest.json").exists():
            try:
                pack_notices: list[str] = []
                errors.extend(
                    f"{slug}: {e}" for e in verify_manifest(pack_dir, notices=pack_notices)
                )
                if notices is not None:
                    notices.extend(f"{slug}: {n}" for n in pack_notices)
            except Exception as exc:  # reported, not raised — a corrupt manifest is drift too
                errors.append(f"{slug}: manifest.json unreadable (corrupt/truncated?): {exc}")
        elif entry.frozen:
            # The lifecycle's other half: a candidate legitimately has no manifest,
            # a frozen pack cannot. Without the state to tell them apart, a frozen
            # pack whose manifest went missing verified as silently clean.
            errors.append(
                f"{slug}: registered as {STATUS_FROZEN} but has a corpus and no manifest.json — "
                f"nothing pins it (freeze it, or register it as {STATUS_CANDIDATE})"
            )
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
        notices: list[str] = []
        errors = check_public(benchmarks, notices=notices)
        entries = discover_packs(benchmarks)
        for notice in notices:  # visible, never fatal
            print(f"CONFORMANCE NOTICE: {notice}", file=sys.stderr)
        for err in errors:
            print(f"CONFORMANCE: {err}", file=sys.stderr)
        # The summary line names what was looked at, by state. "OK" over an empty
        # traversal is the failure mode this whole discovery pass exists to end:
        # silence must never be indistinguishable from a clean result.
        counted = {status: 0 for status in (STATUS_FROZEN, STATUS_CANDIDATE, STATUS_UNREGISTERED)}
        for entry in entries:
            counted[entry.status] = counted.get(entry.status, 0) + 1
        breakdown = ", ".join(f"{count} {status}" for status, count in counted.items() if count)
        print(f"pack conformance: {len(entries)} pack(s) seen" + (f" ({breakdown})" if breakdown else ""))
        stray = [e.slug for e in entries if not e.registered]
        if stray:
            print(f"  UNREGISTERED (checked anyway, add to REGISTERED_PACKS): {', '.join(stray)}")
        if errors:
            return 1
        print("pack conformance: OK")
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
        verify_notices: list[str] = []
        errors = verify_manifest(pack_dir, notices=verify_notices)
        for notice in verify_notices:  # visible, never fatal
            print(f"VERIFY NOTICE: {notice}", file=sys.stderr)
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
        if manifest["sandbox_sha256"] is None:
            print("  sandbox: none in this pack — pinned as null")
        else:
            print(f"  sandbox {manifest['sandbox_filename']}: sha256={manifest['sandbox_sha256']}")
    else:
        print(f"pack {pack_dir.name}: {len(cases)} cases conformant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
