"""Non-gated scorer-review contract stub.

This module documents an optional future scorer-review interface. It does not
call providers, run local models, inspect private data, execute agents, or
perform external actions. Any written contract output requires an explicit
operator acknowledgement that the command is non-gated.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from reporting_utils import display_path, write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-22T00:00:00Z"

class ScorerReviewContractError(Exception):
    """Scorer review contract error."""


def build_review_contract(input_path: Path | None = None) -> dict[str, Any]:
    """Return the deterministic non-gated scorer-review contract."""

    selected_input_path = ""
    if input_path is not None:
        selected_input_path = validate_input_path(input_path)

    return {
        "contract_id": "optional_scorer_review_contract_v1",
        "generated_at": GENERATED_AT,
        "status": "contract_only_no_judge_execution",
        "quality_gate_included": False,
        "selected_input_path": selected_input_path,
        "purpose": (
            "Define a future optional scorer-review handoff without allowing model-assisted judging to "
            "affect deterministic quality gates."
        ),
        "allowed_inputs": [
            "Committed public-safe scorer reliability JSON snapshots.",
            "Committed public-safe adjudication fixtures.",
            "Saved reviewer notes that have already passed redaction and public-safety review.",
        ],
        "required_operator_controls": [
            "Use a dedicated opt-in command outside scripts/dev.py check.",
            "Do not supply credentials or provider configuration through this contract.",
            "Treat any generated model-review output as advisory until separately adjudicated.",
            "Promote only deterministic, public-safe summaries into committed artifacts.",
        ],
        "prohibited_behaviors": [
            "No live provider calls.",
            "No local model calls.",
            "No OpenClaw, Hermes, CLI-agent, browser, email, shell, or production-system execution.",
            "No credentials, secrets, private evidence ingestion, or external actions.",
            "No automatic scorer overrides, trace rewrites, or quality-gate decisions.",
        ],
        "output_contract": {
            "review_output_status": "advisory_only",
            "requires_human_adjudication_before_promotion": True,
            "may_change_quality_gate_result": False,
            "may_change_scorer_behavior": False,
            "may_write_optional_contract_files": True,
        },
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
    }


def validate_input_path(path: Path) -> str:
    """Validate an optional saved input path without reading private data."""

    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (REPO_ROOT / path).resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ScorerReviewContractError("input path must stay within the repository") from exc
    if not resolved.exists():
        raise ScorerReviewContractError(f"input path does not exist: {display_path(resolved, REPO_ROOT)}")
    if "private" in resolved.relative_to(REPO_ROOT.resolve()).parts:
        raise ScorerReviewContractError("input path must not point to private evidence or private reports")
    return display_path(resolved, REPO_ROOT)


def generate_markdown(contract: dict[str, Any]) -> str:
    """Generate reader-facing Markdown for the optional contract."""

    lines = [
        "# Optional Scorer Review Contract",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{contract['generated_at']}` |",
        f"| Status | `{contract['status']}` |",
        f"| Quality gate included | {str(contract['quality_gate_included']).lower()} |",
        f"| Selected input | `{contract['selected_input_path'] or 'none'}` |",
        "",
        contract["purpose"],
        "",
        "## Required Operator Controls",
        "",
        "\n".join(f"- {item}" for item in contract["required_operator_controls"]),
        "",
        "## Prohibited Behaviors",
        "",
        "\n".join(f"- {item}" for item in contract["prohibited_behaviors"]),
        "",
        "## Output Contract",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    for key, value in contract["output_contract"].items():
        lines.append(f"| `{key}` | {str(value).lower()} |")
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit the optional non-gated scorer-review contract.")
    parser.add_argument("--input", type=Path, help="Optional committed public-safe input artifact.")
    parser.add_argument("--output-json", type=Path, help="Optional JSON output path.")
    parser.add_argument("--output-markdown", type=Path, help="Optional Markdown output path.")
    parser.add_argument(
        "--acknowledge-non-gated",
        action="store_true",
        help="Required when writing optional contract files.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    output_json_path = args.output_json
    output_markdown_path = args.output_markdown
    should_write = output_json_path is not None or output_markdown_path is not None

    if should_write and not args.acknowledge_non_gated:
        print("ERROR: writing optional review contract files requires --acknowledge-non-gated", file=sys.stderr)
        return 2

    try:
        contract = build_review_contract(args.input)
        if output_json_path is not None:
            write_json_object(contract, resolve_output_path(output_json_path))
        if output_markdown_path is not None:
            write_text(generate_markdown(contract), resolve_output_path(output_markdown_path))
    except (OSError, ValueError, ScorerReviewContractError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if not should_write:
        print(json.dumps(contract, sort_keys=True, indent=2))
    else:
        if output_json_path is not None:
            print(f"optional scorer review contract JSON path: {display_path(resolve_output_path(output_json_path), REPO_ROOT)}")
        if output_markdown_path is not None:
            print(
                "optional scorer review contract report path: "
                f"{display_path(resolve_output_path(output_markdown_path), REPO_ROOT)}"
            )
    return 0


def resolve_output_path(path: Path) -> Path:
    """Resolve an optional output path inside the repository."""

    resolved = path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ScorerReviewContractError("output path must stay within the repository") from exc
    return resolved


if __name__ == "__main__":
    sys.exit(main())
