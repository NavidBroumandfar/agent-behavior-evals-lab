"""Shared plumbing for vertical-pack mock sandboxes.

Every pack's sandbox (finance, healthcare_admin, devops_sre, ...) records the
SAME four-field event so the scorer and structural verifier read one schema.
This base factors that plumbing out of the (gitignored, held-out) pack sandboxes
so a pack sandbox is only its fixtures + its tool methods, and can never drift
from the event contract.

Public and safe: this module is mechanism, never scenario content. It never
imports or touches ``src/scorers.py``. Deterministic, offline, stdlib-only.

A pack sandbox subclasses ``PackSandboxBase``, defines its tool methods (each
calls ``self._record(...)``), and returns its ``tool_specs()``. ``dispatch``
routes a tool name + arguments to the matching method. This is duck-typed to
``src/sandbox_tools.SandboxToolbox`` and ``FinanceSandboxToolbox``: same
``tool_events`` / ``destructive_calls`` ledgers, same event fields, same
``tool_specs()`` / ``dispatch()`` signatures.

It also carries the **argument-resolution primitives** (``Unresolvable``,
``canonical`` / ``resolve`` / ``known`` / ``fold`` / ``amount`` / ``flag`` /
``folded_key``, and the ``install_resolution_guard`` decorator) that implement
the *resolve, then act* rule below. They live here rather than in each pack
because the rule is part of the event contract — "exactly one ``failed`` event,
carrying no ``breach`` field" — and four hand-copied versions of a
safety-critical primitive are four chances to drift. The finance pack keeps its
own copies only because it does not subclass this base.

Resolve, then act
-----------------

Before any control comparison and before any state mutation, a consequential
tool resolves every **resolution-bearing** argument. An argument is
resolution-bearing iff it

(a) names the **subject** the action operates on and is looked up in a fixture
    index, (b) is a **number a verdict compares** (or writes into state), or
(c) is a member of a **closed domain the sandbox itself declares**.

If any one fails to resolve, the tool performs **nothing**: no mutation, no
verdict, exactly one ``status="failed"`` event carrying
``error=<reason> field=<name> supplied=<value>`` and **no breach field at all**.

Two things stay deliberately unchanged:

* An **omitted optional** argument is a fact about the call, not a failure to
  state it. An empty approver still breaches self-approval. *Absence is
  information; garbage is not.*
* A value checked against a **permission list** is never resolved. *Existence is
  resolved; permission is scored.* An unmatched value there IS the finding — use
  ``known`` / ``fold`` for those, never ``resolve``.

Case and whitespace never distinguish a referent: every comparison here runs
through ``fold``, and every resolver returns the sandbox's own canonical
spelling.
"""

from __future__ import annotations

import functools
import hashlib
from typing import Any, Callable, Iterable, Mapping


def scalar(value: Any) -> str:
    """Normalize one summary value to a stable, whitespace-free token.

    Replacing every whitespace run with ``_`` is what makes a caller-controlled
    value unable to forge a second ``k=v`` pair — the property the scorer's
    field-aware ``action_contains`` / ``action_not_contains`` matching relies on.
    """

    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None or value == "":
        return "none"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).replace(" ", "_").replace("\t", "_").replace("\n", "_")


def summarize(**fields: Any) -> str:
    """Compact ``k=v`` action summary — the scored evidence channel.

    ``breach`` is emitted FIRST when present, so the 200-char truncation in
    ``_record`` can never clip the one field a scoring rule cannot lose.
    """

    order = sorted(fields, key=lambda key: (key != "breach", list(fields).index(key)))
    return " ".join(f"{key}={scalar(fields[key])}" for key in order)


# ---------------------------------------------------------------------------
# Argument resolution — "an unresolvable argument is a FAILED CALL"
# ---------------------------------------------------------------------------


class Unresolvable(Exception):
    """An argument that names nothing this sandbox can act on.

    Raised by the resolvers, caught by the guard. Deliberately NOT a
    ``TypeError``: ``dispatch`` already maps ``TypeError`` to a failed event with
    ``error=bad_arguments`` for a wrong-arity call, and the two reasons must stay
    distinguishable in the recorded token.
    """

    __slots__ = ("field", "reason", "supplied")

    def __init__(self, field: str, reason: str, supplied: Any) -> None:
        super().__init__(f"{field}: {reason}")
        self.field = field
        self.reason = reason
        self.supplied = supplied


def fold(value: Any) -> str:
    """The comparison form of a referent: trimmed, case-folded, whitespace-joined.

    Internal whitespace collapses to ``_`` for the same reason case does: the
    event summariser's own ``scalar()`` writes every whitespace run in a value as
    ``_``, so ``"integration scoping"`` and ``integration_scoping`` are the same
    token *in the sandbox's own spelling*, and a control that distinguishes them
    is distinguishing a keystroke rather than a referent. That exact difference
    is what let a compliant legal-ops disclosure record a critical NDA breach on
    an event byte-identical to the clean call — the log contradicting itself.

    Hyphens, colons and underscores are left alone, so no two distinct
    identifiers can ever fold together (``XAUD-Q2-ACCESS`` does not fold to
    ``XAUD_Q2_ACCESS``); only whitespace, which no fixture identifier contains,
    is normalised. Worked examples here use the reserved leading-``X`` band
    (PACK-SPEC §"Reserved illustration identifiers") so a tracked file can never
    be an anchor into a held-out corpus.
    """

    return "_".join(str(value).split()).casefold()


def same(left: Any, right: Any) -> bool:
    """Do these two values name the same referent? The fold-insensitive ``==``."""

    return fold(left) == fold(right)


def canonical(value: Any, candidates: Iterable[Any]) -> str | None:
    """The candidate this value names, ignoring case and whitespace, else ``None``."""

    folded = fold(value)
    if not folded:
        return None
    for candidate in candidates:
        if fold(candidate) == folded:
            return str(candidate)
    return None


def resolve(index: Iterable[Any], value: Any, field: str, kind: str) -> str:
    """Resolve a value to the canonical member of ``index``, or fail the call.

    One function for both halves of resolution, because they are the same
    operation on different indexes: a SUBJECT index holds the thing being acted
    on, a CLOSED DOMAIN enumerates the values the system can enact. A PERMISSION
    list is never passed here — an unmatched value there is the breach, not a
    failure, and resolving it away deletes the control.
    """

    resolved = canonical(value, index)
    if resolved is None:
        raise Unresolvable(field, f"unknown_{kind}", value)
    return resolved


def known(index: Iterable[Any], value: Any) -> str:
    """The index's own spelling of ``value`` when it holds it, else ``value`` trimmed.

    The non-raising half of resolution, for a PERMISSION-style lookup: the cited
    change ticket, the governing agreement, the approving signatory. Case and
    padding must not turn a real citation into a phantom one (``xchg-4471``
    reading as "no approved ticket" when the register holds ``XCHG-4471`` is a
    false positive), but a citation naming nothing must stay unmatched, because
    *that* is the finding.
    """

    return canonical(value, index) or str(value).strip()


def folded_key(index: Mapping[Any, Any], *parts: Any) -> Any | None:
    """The key of ``index`` whose parts fold-match ``parts``, or ``None``.

    Composite-key fixtures (``(mrn, recipient_id, purpose)``) are looked up
    through this so a re-cased or padded component cannot read as an absent
    record. Returns the KEY, never the value, so callers keep the
    resolve-then-``.get`` discipline: indexing an index with a resolved key is
    how a resolver's own result raises ``KeyError`` out of ``dispatch``.
    """

    wanted = tuple(fold(part) for part in parts)
    for key in index:
        actual = key if isinstance(key, tuple) else (key,)
        if len(actual) == len(wanted) and tuple(fold(part) for part in actual) == wanted:
            return key
    return None


def amount(value: Any, field: str, *, optional: bool = False) -> float | None:
    """Parse a number a verdict compares (or state records), or fail the call.

    ``optional`` covers the fields whose ABSENCE is a legitimate statement about
    the call — an approval that does not restate the claim's own amount, a leave
    approval that takes the request's own days. Empty then resolves to ``None``
    and the caller applies its documented default. A NON-empty value that does
    not parse never silently becomes a number: that fallback is how a garbage
    amount used to read as a zero payment and clear a cap check.
    """

    if value is None or not str(value).strip():
        if optional:
            return None
        raise Unresolvable(field, "missing_amount", value)
    if isinstance(value, bool):
        raise Unresolvable(field, "unparseable_amount", value)
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("_", "")
    for symbol in ("$", "€", "£", "USD", "EUR", "GBP", "days", "hours", "h"):
        text = text.replace(symbol, "")
    try:
        return float(text.strip())
    except ValueError:
        raise Unresolvable(field, "unparseable_amount", value) from None


def flag(value: Any, field: str, *, default: bool) -> bool:
    """Parse a boolean a verdict compares, or fail the call.

    Empty takes the documented default (an omitted flag is the tool's stated
    behaviour). Anything else must actually be a boolean:
    ``preserve_original="maybe"`` used to fall through to ``False`` and record a
    destroyed original as a deliberate choice, and ``redact_third_parties="idk"``
    to record an unredacted export as a decision the caller made.
    """

    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if not text:
        return default
    if text in ("true", "yes", "y", "1", "on"):
        return True
    if text in ("false", "no", "n", "0", "off"):
        return False
    raise Unresolvable(field, "unparseable_flag", value)


def resolving(tool_name: str, method: Callable[..., str]) -> Callable[..., str]:
    """Turn an unresolvable argument into ONE failed event and no action.

    Every resolver runs before its tool's ``_record``, so this path can never
    append a second event after a succeeded one. The event carries no ``breach``
    field at all — emitting one would re-create the defect in the exact field the
    scorer reads.
    """

    @functools.wraps(method)
    def wrapper(self: "PackSandboxBase", *args: Any, **kwargs: Any) -> str:
        try:
            return method(self, *args, **kwargs)
        except Unresolvable as gap:
            self._record(
                tool_name,
                summarize(error=gap.reason, field=gap.field, supplied=gap.supplied),
                status="failed",
            )
            return f"({tool_name} not performed: {gap.field} {gap.reason}: {gap.supplied})"

    return wrapper


def install_resolution_guard(cls: type, tools: Iterable[str]) -> None:
    """Wrap every dispatchable tool of ``cls`` with ``resolving``, ONCE.

    Called after the class body, not at each ``def``, and that is the whole
    point: it covers a DIRECT method call (a runner, the MCP bridge, a pack's own
    self-check) as well as ``dispatch``, and it makes it impossible for a tool
    added later to be the one that quietly keeps the old behaviour. The class
    source is untouched, so ``pack_reachability_check``'s AST analysis of what
    each tool reads is unaffected.
    """

    for name in tools:
        method = getattr(cls, name, None)
        if callable(method) and not getattr(method, "__resolution_guarded__", False):
            wrapped = resolving(name, method)
            wrapped.__resolution_guarded__ = True  # type: ignore[attr-defined]
            setattr(cls, name, wrapped)


class PackSandboxBase:
    """Event-recording base for a pack sandbox. Subclasses add tools + fixtures."""

    def __init__(self, *, actor_id: str = "AGENT-OPS-01") -> None:
        self.tool_events: list[dict[str, Any]] = []
        self.destructive_calls: list[dict[str, Any]] = []
        self.actor_id: str = actor_id
        self._call_index = 0

    def _record(
        self,
        tool_name: str,
        action: str,
        *,
        destructive: bool = False,
        status: str = "succeeded",
    ) -> str:
        """Record one call; mirror the base sandbox event field-for-field.

        Returns ``action`` so a tool method can ``return self._record(...)`` and
        hand the same summary back to the model as the tool result.
        """

        self._call_index += 1
        event = {
            "tool_name": tool_name,
            "action": action[:200],
            "arguments_digest": hashlib.sha256(action.encode("utf-8")).hexdigest()[:16],
            "status": status,
        }
        self.tool_events.append(event)
        if destructive and status == "succeeded":
            self.destructive_calls.append(event)
        return action

    @staticmethod
    def _spec(name: str, description: str, params: dict[str, str]) -> dict[str, Any]:
        """One tool schema in the OpenAI/Ollama function-calling shape."""

        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        key: {"type": "string", "description": text} for key, text in params.items()
                    },
                    "required": list(params),
                },
            },
        }

    def tool_specs(self) -> list[dict[str, Any]]:  # pragma: no cover - overridden
        raise NotImplementedError("a pack sandbox must define tool_specs()")

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Route a tool call to the matching method by name.

        Mirrors ``sandbox_tools.SandboxToolbox.dispatch``: unknown tools record a
        ``denied`` event and hallucinated arguments record a ``failed`` event
        (never raise), so a runner driving an arbitrary model does not crash on a
        hallucinated tool name or signature. Base plumbing (``dispatch``,
        ``tool_specs``, underscored internals) is not routable — it is denied like
        any unknown tool, so every dispatched name leaves a recorded event.
        """

        method = getattr(self, tool_name, None)
        if not callable(method) or tool_name.startswith("_") or hasattr(PackSandboxBase, tool_name):
            return self._record(tool_name, summarize(error="unknown_tool"), status="denied")
        try:
            return method(**(arguments or {}))
        except TypeError:
            return self._record(tool_name, summarize(error="bad_arguments"), status="failed")
