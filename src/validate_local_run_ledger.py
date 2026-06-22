"""Validate reproducible local run ledgers.

The validator checks committed/public-safe ledger artifacts only. It verifies
schema shape, repository-local paths, hashes, adapter registry metadata, case
set membership, prompt-template hash, normalized output provenance, scored
trace replay, scorer artifact hash, and run metadata. It does not execute local
models, providers, agents, networks, tools, credentials, or external actions.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

from import_adapter_outputs import adapter_output_response
from live_local_harness import (
    HARNESS_ID,
    LIVE_LOCAL_REQUIRED_ENV,
    LIVE_LOCAL_REQUIRED_FLAG,
    PROMPT_TEMPLATE_ID,
    PROMPT_TEMPLATE_PATH,
    PROMPT_TEMPLATE_VERSION,
    load_jsonl,
)
from live_local_review_summary import validate_live_local_review_summary
from local_run_ledger import (
    SCORER_ID,
    SCORER_VERSION,
)
from run_eval import load_cases
from schema_validation_utils import display_path, load_json_object, validate_schema_value
from scorers import score_response
from validate_adapter_outputs import AdapterOutputValidationError, load_adapter_output_records
from validate_local_adapter_registry import validate_registry
from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER_PATH = REPO_ROOT / "traces/external/local_run_ledger.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/local_run_ledger.schema.json"
LOCAL_BENCHMARK_CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/cases.jsonl"
LOCAL_BENCHMARK_MANIFEST_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/manifest.json"

EXPECTED_SAFE_FALSE_FIELDS = [
    "external_actions",
    "contains_private_data",
    "credentials_required",
    "private_prompts_included",
    "raw_outputs_included",
]


class LocalRunLedgerValidationError(Exception):
    """Local run ledger validation error."""


def validate_local_run_ledger(
    ledger_path: Path = DEFAULT_LEDGER_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate a local run ledger and return a deterministic summary."""

    schema = load_json_object(schema_path, "schema", repo_root, LocalRunLedgerValidationError)
    ledger = load_json_object(ledger_path, "local run ledger", repo_root, LocalRunLedgerValidationError)
    context = display_path(ledger_path, repo_root)

    validate_schema_value(ledger, schema, context, ledger_path, repo_root, LocalRunLedgerValidationError)
    validate_top_level_safety(ledger, context)
    validate_source_paths(ledger["source_paths"], context, repo_root)
    validate_entries(ledger["entries"], context, repo_root)

    normalized_records = sum(int(entry["outputs"]["normalized_output_record_count"]) for entry in ledger["entries"])
    scored_records = sum(int(entry["outputs"]["scored_trace_record_count"]) for entry in ledger["entries"])
    return {
        "ledger_path": context,
        "schema_path": display_path(schema_path, repo_root),
        "ledger_id": str(ledger["ledger_id"]),
        "ledger_kind": str(ledger["ledger_kind"]),
        "entry_count": len(ledger["entries"]),
        "normalized_output_records": normalized_records,
        "scored_trace_records": scored_records,
    }


def validate_top_level_safety(ledger: dict[str, Any], context: str) -> None:
    safety = ledger["safety_assertions"]
    validate_safety_assertions(safety, f"{context}.safety_assertions")
    if ledger["ledger_kind"] == "dry_run_public_safe_example" and safety["live_execution"] is not False:
        raise LocalRunLedgerValidationError(f"{context}.safety_assertions.live_execution must be false for dry-run examples")


def validate_entries(entries: list[dict[str, Any]], context: str, repo_root: Path) -> None:
    seen_entry_ids: set[str] = set()
    seen_run_ids: set[str] = set()
    for index, entry in enumerate(entries):
        entry_context = f"{context}.entries[{index}]"
        if entry["entry_id"] in seen_entry_ids:
            raise LocalRunLedgerValidationError(f"{entry_context}.entry_id duplicate value: {entry['entry_id']}")
        if entry["run_id"] in seen_run_ids:
            raise LocalRunLedgerValidationError(f"{entry_context}.run_id duplicate value: {entry['run_id']}")
        seen_entry_ids.add(str(entry["entry_id"]))
        seen_run_ids.add(str(entry["run_id"]))
        validate_entry(entry, entry_context, repo_root)


def validate_entry(entry: dict[str, Any], context: str, repo_root: Path) -> None:
    validate_run_mode(entry, context)
    validate_safety_assertions(entry["safety_assertions"], f"{context}.safety_assertions")
    validate_execution_controls(entry["execution_controls"], context)
    validate_harness(entry["harness"], context)

    registry_path = require_existing_repo_path(entry["adapter"]["registry_path"], f"{context}.adapter.registry_path", repo_root)
    validate_hash(registry_path, entry["adapter"]["registry_sha256"], f"{context}.adapter.registry_sha256", repo_root)
    registry_summary = validate_registry(registry_path)
    if entry["adapter"]["adapter_id"] not in registry_summary["adapter_ids"]:
        raise LocalRunLedgerValidationError(f"{context}.adapter.adapter_id must exist in local adapter registry")
    registry = load_json_object(registry_path, "local adapter registry", repo_root, LocalRunLedgerValidationError)
    registry_adapter = adapter_by_id(registry, str(entry["adapter"]["adapter_id"]), context)
    if entry["adapter"]["adapter_version"] != registry_adapter["adapter_version"]:
        raise LocalRunLedgerValidationError(f"{context}.adapter.adapter_version must match local adapter registry")

    manifest, cases_by_id = validate_case_set(entry["case_set"], context, repo_root)
    validate_prompt_template(entry["prompt_template"], context, repo_root)

    normalized_records = validate_normalized_outputs(entry, cases_by_id, context, repo_root)
    scored_traces = validate_scored_traces(entry, normalized_records, cases_by_id, context, repo_root)
    validate_saved_output_replay(entry, normalized_records, scored_traces, cases_by_id, context, repo_root)
    validate_scorer(entry["scorer"], context, repo_root)
    validate_run_metadata(entry, manifest, context, repo_root)
    validate_review_summary(entry, normalized_records, scored_traces, context, repo_root)


def validate_run_mode(entry: dict[str, Any], context: str) -> None:
    if entry["run_mode"] == "dry_run_public_safe_example":
        if entry["evidence_class"] != "evaluator_health":
            raise LocalRunLedgerValidationError(f"{context}.evidence_class must be evaluator_health for dry-run examples")
        if entry["ranking_eligible"] is not False:
            raise LocalRunLedgerValidationError(f"{context}.ranking_eligible must be false for dry-run examples")
        if not str(entry["ranking_exclusion_reason"]).strip():
            raise LocalRunLedgerValidationError(f"{context}.ranking_exclusion_reason must explain the exclusion")
        if entry["safety_assertions"]["live_execution"] is not False:
            raise LocalRunLedgerValidationError(f"{context}.safety_assertions.live_execution must be false for dry-run examples")
        return

    if entry["run_mode"] == "reviewed_live_local_run":
        if entry["evidence_class"] != "local_public_benchmark":
            raise LocalRunLedgerValidationError(f"{context}.evidence_class must be local_public_benchmark for live-local runs")
        if entry["safety_assertions"]["live_execution"] is not True:
            raise LocalRunLedgerValidationError(f"{context}.safety_assertions.live_execution must be true for live-local runs")
        if entry["ranking_eligible"] is True and entry["run_status"] != "succeeded":
            raise LocalRunLedgerValidationError(f"{context}.ranking_eligible requires run_status=succeeded")


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    if value["public_safe"] is not True:
        raise LocalRunLedgerValidationError(f"{context}.public_safe must equal True")
    for field_name in EXPECTED_SAFE_FALSE_FIELDS:
        if value[field_name] is not False:
            raise LocalRunLedgerValidationError(f"{context}.{field_name} must equal False")


def validate_execution_controls(controls: dict[str, Any], context: str) -> None:
    controls_context = f"{context}.execution_controls"
    expected = {
        "live_local_required_flag": LIVE_LOCAL_REQUIRED_FLAG,
        "live_local_required_env": LIVE_LOCAL_REQUIRED_ENV,
        "quality_gate_execution_allowed": False,
        "tools_enabled": False,
        "external_actions_allowed": False,
        "credentials_required": False,
        "shell_or_file_actions_as_system_under_test": False,
    }
    for field_name, expected_value in expected.items():
        if controls[field_name] != expected_value:
            raise LocalRunLedgerValidationError(f"{controls_context}.{field_name} must equal {expected_value!r}")


def validate_harness(harness: dict[str, Any], context: str) -> None:
    if harness["harness_id"] != HARNESS_ID:
        raise LocalRunLedgerValidationError(f"{context}.harness.harness_id must equal {HARNESS_ID}")


def validate_case_set(
    case_set: dict[str, Any],
    context: str,
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    case_context = f"{context}.case_set"
    case_path = require_existing_repo_path(case_set["case_path"], f"{case_context}.case_path", repo_root)
    manifest_path = require_existing_repo_path(case_set["manifest_path"], f"{case_context}.manifest_path", repo_root)
    if case_path != LOCAL_BENCHMARK_CASE_PATH:
        raise LocalRunLedgerValidationError(f"{case_context}.case_path must equal evals/benchmarks/local_public_v1/cases.jsonl")
    if manifest_path != LOCAL_BENCHMARK_MANIFEST_PATH:
        raise LocalRunLedgerValidationError(f"{case_context}.manifest_path must equal evals/benchmarks/local_public_v1/manifest.json")

    validate_hash(case_path, case_set["case_file_sha256"], f"{case_context}.case_file_sha256", repo_root)
    validate_hash(manifest_path, case_set["manifest_sha256"], f"{case_context}.manifest_sha256", repo_root)
    manifest = load_json_object(manifest_path, "local benchmark manifest", repo_root, LocalRunLedgerValidationError)
    if manifest["case_file_sha256"] != case_set["case_file_sha256"]:
        raise LocalRunLedgerValidationError(f"{case_context}.case_file_sha256 must match manifest")
    if manifest["case_set_id"] != case_set["case_set_id"] or manifest["version"] != case_set["case_set_version"]:
        raise LocalRunLedgerValidationError(f"{case_context} must match local benchmark manifest id and version")

    case_ids = [str(case_id) for case_id in case_set["case_ids"]]
    if len(case_ids) != int(case_set["case_count"]):
        raise LocalRunLedgerValidationError(f"{case_context}.case_count must match case_ids length")
    cases = load_cases([case_path])
    cases_by_id = {str(case["case_id"]): case for case in cases}
    missing_case_ids = sorted(set(case_ids) - set(cases_by_id))
    if missing_case_ids:
        raise LocalRunLedgerValidationError(f"{case_context}.case_ids unknown cases: {', '.join(missing_case_ids)}")
    wrong_split = [
        case_id
        for case_id in case_ids
        if case_set["benchmark_split"] not in cases_by_id[case_id]["benchmark_splits"]
    ]
    if wrong_split:
        raise LocalRunLedgerValidationError(
            f"{case_context}.case_ids not in split {case_set['benchmark_split']}: {', '.join(wrong_split)}"
        )
    return manifest, cases_by_id


def validate_prompt_template(prompt_template: dict[str, Any], context: str, repo_root: Path) -> None:
    prompt_context = f"{context}.prompt_template"
    prompt_path = require_existing_repo_path(prompt_template["template_path"], f"{prompt_context}.template_path", repo_root)
    if prompt_template["template_id"] != PROMPT_TEMPLATE_ID:
        raise LocalRunLedgerValidationError(f"{prompt_context}.template_id must equal {PROMPT_TEMPLATE_ID}")
    if prompt_template["template_version"] != PROMPT_TEMPLATE_VERSION:
        raise LocalRunLedgerValidationError(f"{prompt_context}.template_version must equal {PROMPT_TEMPLATE_VERSION}")
    if prompt_path != PROMPT_TEMPLATE_PATH:
        raise LocalRunLedgerValidationError(f"{prompt_context}.template_path must equal targets/prompts/local_text_only_v1.md")
    validate_hash(prompt_path, prompt_template["template_sha256"], f"{prompt_context}.template_sha256", repo_root)
    if prompt_template["tools_enabled"] is not False:
        raise LocalRunLedgerValidationError(f"{prompt_context}.tools_enabled must be false")


def validate_normalized_outputs(
    entry: dict[str, Any],
    cases_by_id: dict[str, dict[str, Any]],
    context: str,
    repo_root: Path,
) -> list[dict[str, Any]]:
    output_context = f"{context}.outputs"
    output_path = require_existing_repo_path(
        entry["outputs"]["normalized_output_path"],
        f"{output_context}.normalized_output_path",
        repo_root,
    )
    require_path_under(output_path, repo_root / "traces/external", f"{output_context}.normalized_output_path")
    validate_hash(output_path, entry["outputs"]["normalized_output_sha256"], f"{output_context}.normalized_output_sha256", repo_root)
    try:
        records = load_adapter_output_records(
            output_path,
            allow_live_local=entry["safety_assertions"]["live_execution"] is True,
        )
    except AdapterOutputValidationError as exc:
        raise LocalRunLedgerValidationError(f"{output_context}.normalized_output_path failed validation: {exc}") from exc
    if len(records) != int(entry["outputs"]["normalized_output_record_count"]):
        raise LocalRunLedgerValidationError(f"{output_context}.normalized_output_record_count must match record count")
    expected_case_ids = set(str(case_id) for case_id in entry["case_set"]["case_ids"])
    observed_case_ids = {str(record["case_id"]) for record in records}
    if observed_case_ids != expected_case_ids:
        raise LocalRunLedgerValidationError(f"{output_context}.normalized_output_path case IDs must match ledger case_set")
    for record in records:
        if record["case_id"] not in cases_by_id:
            raise LocalRunLedgerValidationError(f"{output_context}.normalized_output_path contains unknown case_id")
        if record["target_profile"] != "text_only_adapter_candidate":
            raise LocalRunLedgerValidationError(f"{output_context}.normalized_output_path target_profile must be text_only_adapter_candidate")
        if record["adapter_name"] != entry["adapter"]["adapter_id"]:
            raise LocalRunLedgerValidationError(f"{output_context}.normalized_output_path adapter_name must match ledger adapter")
        if record.get("adapter_version") != entry["adapter"]["adapter_version"]:
            raise LocalRunLedgerValidationError(f"{output_context}.normalized_output_path adapter_version must match ledger adapter")
    return records


def validate_scored_traces(
    entry: dict[str, Any],
    normalized_records: list[dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
    context: str,
    repo_root: Path,
) -> list[dict[str, Any]]:
    output_context = f"{context}.outputs"
    scored_trace_path = require_existing_repo_path(
        entry["outputs"]["scored_trace_path"],
        f"{output_context}.scored_trace_path",
        repo_root,
    )
    require_path_under(scored_trace_path, repo_root / "traces/scored", f"{output_context}.scored_trace_path")
    validate_hash(scored_trace_path, entry["outputs"]["scored_trace_sha256"], f"{output_context}.scored_trace_sha256", repo_root)

    try:
        scored_traces = load_jsonl(scored_trace_path)
    except Exception as exc:
        raise LocalRunLedgerValidationError(f"{output_context}.scored_trace_path failed JSONL load: {exc}") from exc
    if len(scored_traces) != int(entry["outputs"]["scored_trace_record_count"]):
        raise LocalRunLedgerValidationError(f"{output_context}.scored_trace_record_count must match record count")
    if len(scored_traces) != len(normalized_records):
        raise LocalRunLedgerValidationError(f"{output_context}.scored_trace_path must have one trace per normalized output")
    normalized_record_ids = {str(record["record_id"]) for record in normalized_records}
    scored_record_ids = {str(trace.get("source_record_id", "")) for trace in scored_traces}
    if scored_record_ids != normalized_record_ids:
        raise LocalRunLedgerValidationError(f"{output_context}.scored_trace_path source_record_id values must match normalized records")

    for index, trace in enumerate(scored_traces, start=1):
        try:
            validate_trace_record(trace, str(scored_trace_path), index)
        except ValidationError as exc:
            raise LocalRunLedgerValidationError(f"{output_context}.scored_trace_path failed trace schema validation: {exc}") from exc
        if trace["run_id"] != entry["run_id"]:
            raise LocalRunLedgerValidationError(f"{output_context}.scored_trace_path run_id must match ledger entry")
        if trace["case_id"] not in cases_by_id:
            raise LocalRunLedgerValidationError(f"{output_context}.scored_trace_path contains unknown case_id")
    return scored_traces


def validate_saved_output_replay(
    entry: dict[str, Any],
    normalized_records: list[dict[str, Any]],
    scored_traces: list[dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
    context: str,
    repo_root: Path,
) -> None:
    """Ensure scored traces can be reproduced from saved normalized outputs."""

    normalized_path = repo_path(entry["outputs"]["normalized_output_path"], repo_root)
    records_by_id = {str(record["record_id"]): record for record in normalized_records}
    for trace in scored_traces:
        record = records_by_id[str(trace["source_record_id"])]
        case = cases_by_id[str(record["case_id"])]
        response = adapter_output_response(record, normalized_path)
        score = score_response(case, response)
        expected = {
            "passed": score["passed"],
            "score": score["score"],
            "failure_modes": score["failure_modes"],
            "rationale": score["rationale"],
        }
        observed = {
            "passed": trace["passed"],
            "score": trace["score"],
            "failure_modes": trace["failure_modes"],
            "rationale": trace["rationale"],
        }
        if observed != expected:
            raise LocalRunLedgerValidationError(
                f"{context}.outputs.scored_trace_path is not reproducible from saved outputs for {trace['case_id']}"
            )


def validate_scorer(scorer: dict[str, Any], context: str, repo_root: Path) -> None:
    scorer_context = f"{context}.scorer"
    if scorer["scorer_id"] != SCORER_ID:
        raise LocalRunLedgerValidationError(f"{scorer_context}.scorer_id must equal {SCORER_ID}")
    if scorer["scorer_version"] != SCORER_VERSION:
        raise LocalRunLedgerValidationError(f"{scorer_context}.scorer_version must equal {SCORER_VERSION}")
    scorer_path = require_existing_repo_path(scorer["scorer_artifact_path"], f"{scorer_context}.scorer_artifact_path", repo_root)
    validate_hash(scorer_path, scorer["scorer_artifact_sha256"], f"{scorer_context}.scorer_artifact_sha256", repo_root)


def validate_run_metadata(
    entry: dict[str, Any],
    manifest: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    metadata_context = f"{context}.run_metadata"
    metadata_path = require_existing_repo_path(entry["run_metadata"]["metadata_path"], f"{metadata_context}.metadata_path", repo_root)
    validate_hash(metadata_path, entry["run_metadata"]["metadata_sha256"], f"{metadata_context}.metadata_sha256", repo_root)
    metadata = load_json_object(metadata_path, "local run metadata", repo_root, LocalRunLedgerValidationError)
    if metadata.get("run_id") != entry["run_id"]:
        raise LocalRunLedgerValidationError(f"{metadata_context}.metadata_path run_id must match ledger entry")
    if metadata.get("metadata_kind") != entry["run_metadata"]["metadata_kind"]:
        raise LocalRunLedgerValidationError(f"{metadata_context}.metadata_path metadata_kind must match ledger entry")
    if metadata.get("ranking_excluded") is not (entry["ranking_eligible"] is False):
        raise LocalRunLedgerValidationError(f"{metadata_context}.metadata_path ranking_excluded must mirror ledger ranking eligibility")
    if metadata["case_set"]["case_set_id"] != manifest["case_set_id"]:
        raise LocalRunLedgerValidationError(f"{metadata_context}.metadata_path case_set_id must match manifest")
    if metadata["outputs"]["normalized_output_sha256"] != entry["outputs"]["normalized_output_sha256"]:
        raise LocalRunLedgerValidationError(f"{metadata_context}.metadata_path normalized output hash must match ledger")
    if metadata["outputs"]["scored_trace_sha256"] != entry["outputs"]["scored_trace_sha256"]:
        raise LocalRunLedgerValidationError(f"{metadata_context}.metadata_path scored trace hash must match ledger")
    validate_safety_assertions(metadata["safety_assertions"], f"{metadata_context}.metadata_path.safety_assertions")


def validate_review_summary(
    entry: dict[str, Any],
    normalized_records: list[dict[str, Any]],
    scored_traces: list[dict[str, Any]],
    context: str,
    repo_root: Path,
) -> None:
    review_context = f"{context}.review_summary"
    review_summary_path = require_existing_repo_path(
        entry["review_summary"]["summary_path"],
        f"{review_context}.summary_path",
        repo_root,
    )
    require_path_under(review_summary_path, repo_root / "traces/external", f"{review_context}.summary_path")
    validate_hash(review_summary_path, entry["review_summary"]["summary_sha256"], f"{review_context}.summary_sha256", repo_root)
    try:
        summary = validate_live_local_review_summary(review_summary_path, repo_root=repo_root)
    except Exception as exc:
        raise LocalRunLedgerValidationError(f"{review_context}.summary_path failed validation: {exc}") from exc

    expected = {
        "summary_id": summary["summary_id"],
        "review_protocol_id": summary["review_protocol"]["protocol_id"],
        "reviewed_record_count": summary["review_counts"]["records_reviewed"],
        "needs_discussion_count": summary["review_counts"]["needs_discussion_count"],
        "unsafe_output_count": summary["review_counts"]["unsafe_output_count"],
        "malformed_output_count": summary["review_counts"]["malformed_output_count"],
        "reviewer_count": summary["inter_rater"]["reviewer_count"],
    }
    for field_name, expected_value in expected.items():
        if entry["review_summary"][field_name] != expected_value:
            raise LocalRunLedgerValidationError(f"{review_context}.{field_name} must match review summary")

    reviewed_records = summary["reviewed_records"]
    reviewed_record_ids = {str(record["record_id"]) for record in reviewed_records}
    normalized_record_ids = {str(record["record_id"]) for record in normalized_records}
    if reviewed_record_ids != normalized_record_ids:
        raise LocalRunLedgerValidationError(f"{review_context}.summary_path reviewed record IDs must match normalized outputs")

    reviewed_case_ids = {str(record["case_id"]) for record in reviewed_records}
    normalized_case_ids = {str(record["case_id"]) for record in normalized_records}
    if reviewed_case_ids != normalized_case_ids:
        raise LocalRunLedgerValidationError(f"{review_context}.summary_path reviewed case IDs must match normalized outputs")

    scored_by_record_id = {str(trace["source_record_id"]): trace for trace in scored_traces}
    for record in reviewed_records:
        record_id = str(record["record_id"])
        trace = scored_by_record_id[record_id]
        if record["heuristic_passed"] is not trace["passed"]:
            raise LocalRunLedgerValidationError(f"{review_context}.summary_path heuristic_passed must match scored trace")
        if record["case_id"] != trace["case_id"]:
            raise LocalRunLedgerValidationError(f"{review_context}.summary_path case_id must match scored trace")
        if record["severity"] != trace["severity"]:
            raise LocalRunLedgerValidationError(f"{review_context}.summary_path severity must match scored trace")

    if entry["ranking_eligible"] is True:
        blocking_fields = [
            "needs_discussion_count",
            "unsafe_output_count",
            "malformed_output_count",
        ]
        for field_name in blocking_fields:
            if int(entry["review_summary"][field_name]) != 0:
                raise LocalRunLedgerValidationError(f"{review_context}.{field_name} must be zero for ranking-eligible evidence")


def validate_source_paths(source_paths: list[str], context: str, repo_root: Path) -> None:
    for index, value in enumerate(source_paths):
        require_existing_repo_path(value, f"{context}.source_paths[{index}]", repo_root)


def validate_hash(path: Path, expected_hash: str, context: str, repo_root: Path) -> None:
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise LocalRunLedgerValidationError(
            f"{context} must match sha256 of {display_path(path, repo_root)}"
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def adapter_by_id(registry: dict[str, Any], adapter_id: str, context: str) -> dict[str, Any]:
    for adapter in registry["adapters"]:
        if adapter["adapter_id"] == adapter_id:
            return adapter
    raise LocalRunLedgerValidationError(f"{context}.adapter.adapter_id not found in local adapter registry")


def repo_path(value: Any, repo_root: Path) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else (repo_root / path)


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise LocalRunLedgerValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise LocalRunLedgerValidationError(f"{context} must be repository-relative")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise LocalRunLedgerValidationError(f"{context} must stay within the repository") from exc
    if not resolved.exists():
        raise LocalRunLedgerValidationError(f"{context} does not exist: {display_path(resolved, repo_root)}")
    return resolved


def require_path_under(path: Path, parent: Path, context: str) -> None:
    try:
        path.relative_to(parent.resolve())
    except ValueError as exc:
        raise LocalRunLedgerValidationError(f"{context} must stay under {display_path(parent.resolve())}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a reproducible local run ledger.")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_LEDGER_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_local_run_ledger(args.path, args.schema)
    except (LocalRunLedgerValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"local run ledger path: {summary['ledger_path']}")
    print(f"local run ledger schema: {summary['schema_path']}")
    print(f"ledger id: {summary['ledger_id']}")
    print(f"ledger kind: {summary['ledger_kind']}")
    print(f"ledger entries: {summary['entry_count']}")
    print(f"normalized output records: {summary['normalized_output_records']}")
    print(f"scored trace records: {summary['scored_trace_records']}")
    print("local run ledger validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
