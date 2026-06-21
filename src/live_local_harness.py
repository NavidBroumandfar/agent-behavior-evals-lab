"""Opt-in local text-only model harness for public-safe benchmark cases.

This M57 harness can run Ollama or local OpenAI-compatible text-only models
against the frozen local_public_v1 corpus. Live execution is blocked unless the
caller provides both --live-local and AGENT_EVALS_ENABLE_LIVE_LOCAL. Tests use
fake clients only; the deterministic quality gate validates plans and schemas,
not local model execution.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trace_writer import write_jsonl
from validate_local_adapter_registry import DEFAULT_REGISTRY_PATH, validate_registry


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_BENCHMARK_MANIFEST_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/manifest.json"
PROMPT_TEMPLATE_PATH = REPO_ROOT / "targets/prompts/local_text_only_v1.md"
HARNESS_ID = "live_local_text_only_harness"
HARNESS_VERSION = "0.1.0"
PROMPT_TEMPLATE_ID = "local_text_only_v1"
PROMPT_TEMPLATE_VERSION = "0.1.0"
LIVE_LOCAL_REQUIRED_FLAG = "--live-local"
LIVE_LOCAL_REQUIRED_ENV = "AGENT_EVALS_ENABLE_LIVE_LOCAL"
DEFAULT_SPLIT = "smoke"
DEFAULT_ADAPTER_ID = "ollama_text_only"
SUPPORTED_SPLITS = ["smoke", "standard", "extended"]
SUPPORTED_LIVE_ADAPTER_IDS = {
    "ollama_text_only",
    "local_openai_compatible_text_only",
}
TRUTHY_ENV_VALUES = {"1", "true", "yes", "on"}

SYSTEM_PROMPT = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8").strip()


class LiveLocalHarnessError(Exception):
    """Live-local harness error with public-safe context."""


def build_run_plan(
    *,
    adapter_id: str,
    model: str,
    split: str,
    output_path: Path,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    metadata_output_path: Path | None = None,
    normalized_output_path: Path | None = None,
    scored_trace_path: Path | None = None,
    endpoint: str | None = None,
    run_id: str | None = None,
    created_at: str | None = None,
    timeout_seconds: int | None = None,
    max_attempts: int = 1,
    max_failures: int = 1,
    max_cases: int | None = None,
    mode: str = "plan_only",
    live_local_flag_present: bool = False,
    live_local_env_present: bool = False,
) -> dict[str, Any]:
    """Build a public-safe local run plan without contacting a model endpoint."""

    if split not in SUPPORTED_SPLITS:
        raise LiveLocalHarnessError(f"split must be one of: {', '.join(SUPPORTED_SPLITS)}")
    if not model.strip():
        raise LiveLocalHarnessError("model must not be empty")
    if mode not in {"plan_only", "live_local"}:
        raise LiveLocalHarnessError("mode must be plan_only or live_local")
    if max_attempts < 1:
        raise LiveLocalHarnessError("max_attempts must be at least 1")
    if max_failures < 1:
        raise LiveLocalHarnessError("max_failures must be at least 1")
    if max_cases is not None and max_cases < 1:
        raise LiveLocalHarnessError("max_cases must be at least 1 when provided")

    validate_raw_output_path(output_path)
    metadata_output_path = metadata_output_path or derive_metadata_output_path(output_path)
    validate_metadata_output_path(metadata_output_path)
    normalized_output_path = normalized_output_path or default_normalized_output_path(output_path)
    scored_trace_path = scored_trace_path or default_scored_trace_path(output_path)

    registry = load_registry(registry_path)
    adapter = adapter_from_registry(registry, adapter_id)
    parameters = dict(adapter["default_parameters"])
    if timeout_seconds is not None:
        if timeout_seconds < 1:
            raise LiveLocalHarnessError("timeout_seconds must be positive")
        parameters["timeout_seconds"] = timeout_seconds

    endpoint_value = endpoint or str(adapter["endpoint_template"])
    validate_loopback_endpoint(endpoint_value)

    manifest, cases = load_local_public_cases(registry)
    selected_cases = [case for case in cases if split in case["benchmark_splits"]]
    if max_cases is not None:
        selected_cases = selected_cases[:max_cases]
    if not selected_cases:
        raise LiveLocalHarnessError(f"no cases selected for split {split!r}")

    run_id = run_id or default_run_id(adapter_id, split)
    created_at = created_at or utc_now()

    return {
        "run_id": run_id,
        "created_at": created_at,
        "mode": mode,
        "harness_id": HARNESS_ID,
        "harness_version": HARNESS_VERSION,
        "adapter": {
            "adapter_id": adapter["adapter_id"],
            "adapter_class": adapter["adapter_class"],
            "adapter_version": adapter["adapter_version"],
            "runtime": adapter["runtime"],
            "endpoint_class": adapter["endpoint_class"],
            "endpoint": endpoint_value,
            "model": model,
            "parameters": parameters,
        },
        "case_set": {
            "case_set_id": manifest["case_set_id"],
            "case_set_version": manifest["version"],
            "benchmark_split": split,
            "case_count": len(selected_cases),
            "case_ids": [case["case_id"] for case in selected_cases],
            "case_path": registry["case_set"]["case_path"],
            "manifest_path": registry["case_set"]["manifest_path"],
        },
        "prompt_template": {
            "template_id": PROMPT_TEMPLATE_ID,
            "template_version": PROMPT_TEMPLATE_VERSION,
            "template_path": display_path(PROMPT_TEMPLATE_PATH),
            "tools_enabled": False,
            "system_prompt_summary": "Final text only; tools and external actions disabled.",
        },
        "outputs": {
            "raw_output_path": display_path(output_path),
            "run_metadata_path": display_path(metadata_output_path),
            "normalized_output_path": display_path(normalized_output_path),
            "scored_trace_path": display_path(scored_trace_path),
            "raw_outputs_committable": False,
            "normalized_outputs_require_review": True,
        },
        "execution_controls": {
            "live_local_required_flag": LIVE_LOCAL_REQUIRED_FLAG,
            "live_local_required_env": LIVE_LOCAL_REQUIRED_ENV,
            "live_local_flag_present": live_local_flag_present,
            "live_local_env_present": live_local_env_present,
            "quality_gate_execution_allowed": False,
            "dry_run_plan_in_quality_gate": mode == "plan_only",
            "tools_enabled": False,
            "external_actions_allowed": False,
            "credentials_required": False,
            "shell_or_file_actions_as_system_under_test": False,
            "model_availability_check_required": True,
            "timeout_seconds": int(parameters["timeout_seconds"]),
            "max_attempts": max_attempts,
            "max_failures": max_failures,
        },
        "run_status_policy": {
            "partial_runs_allowed": True,
            "failed_cases_marked": True,
            "ranking_exclusion_for_partial_or_failed": True,
        },
        "safety_assertions": {
            "public_safe": True,
            "live_execution": mode == "live_local",
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
    }


def run_live_local_plan(
    plan: dict[str, Any],
    *,
    env: dict[str, str] | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    """Execute an opt-in live-local plan and write ignored local raw outputs."""

    require_live_local_enabled(plan, env if env is not None else os.environ)
    cases = load_cases_for_plan(plan)
    client = client or client_for_plan(plan)
    raw_output_path = repo_path(plan["outputs"]["raw_output_path"])
    metadata_output_path = repo_path(plan["outputs"]["run_metadata_path"])

    records: list[dict[str, Any]] = []
    failure_count = 0
    skipped_case_ids: list[str] = []
    availability_error = ""

    try:
        client.check_model_available()
    except Exception as exc:  # pragma: no cover - exercised with fake clients.
        availability_error = sanitize_error(exc)
        failure_count = len(cases)
        skipped_case_ids = [case["case_id"] for case in cases]

    if not availability_error:
        for index, case in enumerate(cases, start=1):
            result = generate_with_retries(plan, client, case)
            if result["run_status"] != "succeeded":
                failure_count += 1
            records.append(raw_record_from_result(plan, case, index, result))

            if failure_count >= int(plan["execution_controls"]["max_failures"]):
                skipped_case_ids = [remaining["case_id"] for remaining in cases[index:]]
                break

    write_jsonl(records, raw_output_path)
    run_metadata = run_metadata_from_results(plan, records, skipped_case_ids, availability_error)
    write_json_object(run_metadata, metadata_output_path)

    return {
        "run_id": plan["run_id"],
        "run_status": run_metadata["run_status"],
        "raw_output_path": display_path(raw_output_path),
        "run_metadata_path": display_path(metadata_output_path),
        "records_written": len(records),
        "succeeded": run_metadata["results"]["succeeded"],
        "failed": run_metadata["results"]["failed"],
        "skipped": run_metadata["results"]["skipped"],
    }


def generate_with_retries(plan: dict[str, Any], client: Any, case: dict[str, Any]) -> dict[str, Any]:
    """Generate one response with the configured retry policy."""

    max_attempts = int(plan["execution_controls"]["max_attempts"])
    timeout_seconds = int(plan["execution_controls"]["timeout_seconds"])
    last_error = ""

    for attempt in range(1, max_attempts + 1):
        try:
            output_text = str(client.generate(case, timeout_seconds=timeout_seconds)).strip()
            if not output_text:
                raise LiveLocalHarnessError("model returned empty output")
            return {
                "run_status": "succeeded",
                "output_text": output_text,
                "attempt_count": attempt,
                "failure_reason": "",
            }
        except Exception as exc:  # pragma: no cover - fake tests cover behavior.
            last_error = sanitize_error(exc)

    return {
        "run_status": "failed",
        "output_text": "NO_OUTPUT_CAPTURED: local model generation failed before final text was captured.",
        "attempt_count": max_attempts,
        "failure_reason": last_error,
    }


def raw_record_from_result(
    plan: dict[str, Any],
    case: dict[str, Any],
    index: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Build one local raw record for human review."""

    adapter = plan["adapter"]
    run_status = result["run_status"]
    metadata = {
        "harness_id": plan["harness_id"],
        "harness_version": plan["harness_version"],
        "adapter_id": adapter["adapter_id"],
        "runtime": adapter["runtime"],
        "endpoint_class": adapter["endpoint_class"],
        "model": adapter["model"],
        "parameters": adapter["parameters"],
        "case_set_id": plan["case_set"]["case_set_id"],
        "case_set_version": plan["case_set"]["case_set_version"],
        "benchmark_split": plan["case_set"]["benchmark_split"],
        "prompt_template_id": plan["prompt_template"]["template_id"],
        "prompt_template_version": plan["prompt_template"]["template_version"],
        "tools_enabled": False,
        "external_actions_allowed": False,
        "credentials_required": False,
        "quality_gate_execution": False,
        "attempt_count": result["attempt_count"],
        "run_status": run_status,
        "ranking_excluded": run_status != "succeeded",
    }
    if result["failure_reason"]:
        metadata["failure_reason"] = result["failure_reason"]

    return {
        "raw_record_id": f"{plan['run_id']}-RAW-{index:03d}",
        "run_id": plan["run_id"],
        "case_id": case["case_id"],
        "target_profile": "text_only_adapter_candidate",
        "adapter_name": adapter["adapter_id"],
        "adapter_version": adapter["adapter_version"],
        "collected_at": plan["created_at"],
        "output_text": result["output_text"],
        "review_status": "pending_review",
        "provenance": {
            "public_safe": False,
            "live_execution": True,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "review_required": True,
        "source_label": f"{adapter['adapter_id']}:{adapter['model']}",
        "notes": "M57 live-local text-only raw output; review and sanitize before promotion.",
        "metadata": metadata,
    }


def run_metadata_from_results(
    plan: dict[str, Any],
    records: list[dict[str, Any]],
    skipped_case_ids: list[str],
    availability_error: str,
) -> dict[str, Any]:
    """Summarize a local run without including private logs."""

    succeeded = sum(1 for record in records if record["metadata"]["run_status"] == "succeeded")
    failed_records = sum(1 for record in records if record["metadata"]["run_status"] != "succeeded")
    failed = failed_records + len(skipped_case_ids)
    skipped = len(skipped_case_ids)
    if availability_error:
        run_status = "failed"
    elif failed or skipped:
        run_status = "partial"
    else:
        run_status = "succeeded"

    metadata = dict(plan)
    metadata["mode"] = "live_local"
    metadata["completed_at"] = utc_now()
    metadata["run_status"] = run_status
    metadata["ranking_excluded"] = run_status != "succeeded"
    metadata["results"] = {
        "planned_cases": plan["case_set"]["case_count"],
        "attempted": len(records),
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "skipped_case_ids": skipped_case_ids,
        "availability_error": availability_error,
    }
    return metadata


class JsonHttpClient:
    """Small JSON HTTP client for loopback-only local model servers."""

    def get_json(self, url: str, timeout_seconds: int) -> dict[str, Any]:
        request = urllib.request.Request(url, method="GET")
        return self._request_json(request, timeout_seconds)

    def post_json(self, url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._request_json(request, timeout_seconds)

    def _request_json(self, request: urllib.request.Request, timeout_seconds: int) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                text = response.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise LiveLocalHarnessError(f"local endpoint request failed: {exc.reason}") from exc

        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LiveLocalHarnessError("local endpoint returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise LiveLocalHarnessError("local endpoint JSON response must be an object")
        return value


class OllamaTextOnlyClient:
    """Loopback Ollama /api/chat client."""

    def __init__(self, plan: dict[str, Any], http_client: JsonHttpClient | None = None):
        self.plan = plan
        self.http_client = http_client or JsonHttpClient()
        self.endpoint = str(plan["adapter"]["endpoint"])
        self.model = str(plan["adapter"]["model"])
        self.parameters = plan["adapter"]["parameters"]

    def check_model_available(self) -> None:
        tags_url = self.endpoint.split("/api/", 1)[0] + "/api/tags"
        value = self.http_client.get_json(tags_url, int(self.parameters["timeout_seconds"]))
        models = value.get("models", [])
        names = {str(model.get("name", "")) for model in models if isinstance(model, dict)}
        if self.model not in names:
            raise LiveLocalHarnessError(f"model {self.model!r} was not reported by Ollama /api/tags")

    def generate(self, case: dict[str, Any], *, timeout_seconds: int) -> str:
        payload = {
            "model": self.model,
            "messages": prompt_messages(case),
            "stream": False,
            "options": {
                "temperature": self.parameters["temperature"],
                "num_predict": self.parameters["max_output_tokens"],
                "num_ctx": self.parameters["context_window_tokens"],
            },
        }
        value = self.http_client.post_json(self.endpoint, payload, timeout_seconds)
        message = value.get("message", {})
        if not isinstance(message, dict):
            raise LiveLocalHarnessError("Ollama response missing message object")
        content = message.get("content", "")
        if not isinstance(content, str):
            raise LiveLocalHarnessError("Ollama response message.content must be a string")
        return content


class LocalOpenAICompatibleTextOnlyClient:
    """Loopback OpenAI-compatible /v1/chat/completions client."""

    def __init__(self, plan: dict[str, Any], http_client: JsonHttpClient | None = None):
        self.plan = plan
        self.http_client = http_client or JsonHttpClient()
        self.endpoint = str(plan["adapter"]["endpoint"])
        self.model = str(plan["adapter"]["model"])
        self.parameters = plan["adapter"]["parameters"]

    def check_model_available(self) -> None:
        models_url = openai_compatible_models_url(self.endpoint)
        value = self.http_client.get_json(models_url, int(self.parameters["timeout_seconds"]))
        models = value.get("data", [])
        ids = {str(model.get("id", "")) for model in models if isinstance(model, dict)}
        if self.model not in ids:
            raise LiveLocalHarnessError(f"model {self.model!r} was not reported by the local /v1/models endpoint")

    def generate(self, case: dict[str, Any], *, timeout_seconds: int) -> str:
        payload = {
            "model": self.model,
            "messages": prompt_messages(case),
            "temperature": self.parameters["temperature"],
            "max_tokens": self.parameters["max_output_tokens"],
        }
        value = self.http_client.post_json(self.endpoint, payload, timeout_seconds)
        choices = value.get("choices", [])
        if not choices or not isinstance(choices[0], dict):
            raise LiveLocalHarnessError("OpenAI-compatible response missing choices[0]")
        message = choices[0].get("message", {})
        if not isinstance(message, dict):
            raise LiveLocalHarnessError("OpenAI-compatible response missing message object")
        content = message.get("content", "")
        if not isinstance(content, str):
            raise LiveLocalHarnessError("OpenAI-compatible response message.content must be a string")
        return content


def client_for_plan(plan: dict[str, Any]) -> Any:
    endpoint_class = str(plan["adapter"]["endpoint_class"])
    if endpoint_class == "local_ollama_http":
        return OllamaTextOnlyClient(plan)
    if endpoint_class == "local_openai_compatible_http":
        return LocalOpenAICompatibleTextOnlyClient(plan)
    raise LiveLocalHarnessError(f"unsupported endpoint_class for live-local run: {endpoint_class}")


def require_live_local_enabled(plan: dict[str, Any], env: dict[str, str]) -> None:
    controls = plan["execution_controls"]
    if plan["mode"] != "live_local":
        raise LiveLocalHarnessError("live-local execution requires a plan with mode=live_local")
    if controls["live_local_flag_present"] is not True:
        raise LiveLocalHarnessError(f"live-local execution requires {LIVE_LOCAL_REQUIRED_FLAG}")
    if controls["live_local_env_present"] is not True:
        raise LiveLocalHarnessError(f"live-local execution requires {LIVE_LOCAL_REQUIRED_ENV}")
    if not env_value_enabled(env.get(LIVE_LOCAL_REQUIRED_ENV, "")):
        raise LiveLocalHarnessError(f"{LIVE_LOCAL_REQUIRED_ENV} must be set to a truthy value")


def load_registry(registry_path: Path) -> dict[str, Any]:
    validate_registry(registry_path)
    return load_json_object(registry_path)


def adapter_from_registry(registry: dict[str, Any], adapter_id: str) -> dict[str, Any]:
    if adapter_id not in SUPPORTED_LIVE_ADAPTER_IDS:
        supported = ", ".join(sorted(SUPPORTED_LIVE_ADAPTER_IDS))
        raise LiveLocalHarnessError(f"adapter_id must be a live-local adapter: {supported}")
    for adapter in registry["adapters"]:
        if adapter["adapter_id"] == adapter_id:
            if adapter["live_local_required"] is not True:
                raise LiveLocalHarnessError(f"{adapter_id} is not marked live_local_required")
            return adapter
    raise LiveLocalHarnessError(f"adapter_id not found in local adapter registry: {adapter_id}")


def load_local_public_cases(registry: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_path = repo_path(registry["case_set"]["manifest_path"])
    case_path = repo_path(registry["case_set"]["case_path"])
    manifest = load_json_object(manifest_path)
    cases = load_jsonl(case_path)
    return manifest, cases


def load_cases_for_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    case_path = repo_path(plan["case_set"]["case_path"])
    case_ids = set(str(case_id) for case_id in plan["case_set"]["case_ids"])
    cases = [case for case in load_jsonl(case_path) if str(case["case_id"]) in case_ids]
    if len(cases) != len(case_ids):
        raise LiveLocalHarnessError("case_path does not contain every planned case_id")
    return cases


def prompt_messages(case: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": str(case["user_prompt"])},
    ]


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LiveLocalHarnessError(f"{display_path(path)} contains invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise LiveLocalHarnessError(f"{display_path(path)} must contain a JSON object")
    return value


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise LiveLocalHarnessError(
                    f"{display_path(path)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise LiveLocalHarnessError(f"{display_path(path)}:{line_number}: record must be an object")
            records.append(value)
    if not records:
        raise LiveLocalHarnessError(f"{display_path(path)} contains no records")
    return records


def write_json_object(value: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def validate_raw_output_path(path: Path) -> None:
    if not path.name.endswith(".local.jsonl"):
        raise LiveLocalHarnessError("raw output path must end with .local.jsonl")
    resolved = path.resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return
    try:
        resolved.relative_to((REPO_ROOT / "traces/raw").resolve())
    except ValueError as exc:
        raise LiveLocalHarnessError("raw output path inside the repository must stay under traces/raw") from exc


def validate_metadata_output_path(path: Path) -> None:
    if not path.name.endswith(".local.json"):
        raise LiveLocalHarnessError("run metadata path must end with .local.json")
    resolved = path.resolve()
    try:
        resolved.relative_to(REPO_ROOT.resolve())
    except ValueError:
        return
    try:
        resolved.relative_to((REPO_ROOT / "traces/raw").resolve())
    except ValueError as exc:
        raise LiveLocalHarnessError("run metadata path inside the repository must stay under traces/raw") from exc


def validate_loopback_endpoint(endpoint: str) -> None:
    if not (endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost")):
        raise LiveLocalHarnessError("live-local endpoint must use a loopback http URL")


def derive_metadata_output_path(output_path: Path) -> Path:
    name = output_path.name
    if name.endswith(".local.jsonl"):
        return output_path.with_name(name[: -len(".local.jsonl")] + ".metadata.local.json")
    return output_path.with_suffix(".metadata.local.json")


def default_normalized_output_path(output_path: Path) -> Path:
    stem = output_path.name[: -len(".local.jsonl")] if output_path.name.endswith(".local.jsonl") else output_path.stem
    return REPO_ROOT / "traces/external" / f"{stem}.reviewed.jsonl"


def default_scored_trace_path(output_path: Path) -> Path:
    stem = output_path.name[: -len(".local.jsonl")] if output_path.name.endswith(".local.jsonl") else output_path.stem
    return REPO_ROOT / "traces/scored" / f"{stem}.local.jsonl"


def default_run_id(adapter_id: str, split: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"m57_{adapter_id}_{split}_{timestamp}"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def env_value_enabled(value: str) -> bool:
    return value.strip().lower() in TRUTHY_ENV_VALUES


def openai_compatible_models_url(endpoint: str) -> str:
    if endpoint.endswith("/chat/completions"):
        return endpoint[: -len("/chat/completions")] + "/models"
    return endpoint.rstrip("/") + "/models"


def sanitize_error(exc: Exception) -> str:
    text = str(exc).replace("\n", " ").strip()
    if len(text) > 200:
        text = text[:197] + "..."
    return f"{exc.__class__.__name__}: {text}" if text else exc.__class__.__name__


def repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)
