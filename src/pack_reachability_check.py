"""Sandbox-driven reachability check for vertical red-team pack contracts.

Four checkers now guard a pack, and each sees something the others cannot:

- ``pack_conformance.validate_pack`` checks a contract's **shape** — does every
  case name a tool the sandbox exposes, can a temptation fail at all.
- ``pack_symmetry_check`` checks a temptation/control pair's **prompts** — can a
  reader sort them without touching sandbox state.
- ``pack_archetype_check`` checks a contract's **scored behavior** — but it
  *fabricates* the tool events from the contract itself. It therefore proves a
  contract is losable *in principle*, and never that the pack's own sandbox can
  **emit** the losing event.
- this module drives the **real sandbox** and asks the missing question:

      Is there any argument payload that makes this sandbox record an event this
      case's contract — and this case's stated breach verdict — actually match?

That gap is not hypothetical; it shipped. ``devops_sre``'s
``rollback_without_authorization`` was structurally losable and practically
unreachable: one fixture ticket authorized every rollback in its environment, so
an unauthorized production rollback scored **safe** on the safety axis. The
contract stayed losable through an unrelated breach token, so contract-level
reachability alone reported the case as healthy — which is why the prose-level
check below exists too.

## The three checks

1. **Contract reachability.** For every temptation, search for a payload whose
   recorded event satisfies each ``violating_call``. For every control /
   ``action_required`` case, search for a payload that satisfies its
   ``required_calls`` *without* tripping its own violating guard — the mirror
   defect, since a control no agent can perform always false-positives.
2. **Stated-mechanism reachability.** Every breach verdict a case's prose names
   ("records breach=X", "expected token X") is a claim about the sandbox. A named
   token no payload can emit means the case measures something other than what it
   says it measures — the ``rollback_without_authorization`` defect exactly.
3. **Fixture influence** (author mode, ``--fixtures``). Perturb each fixture leaf
   and re-drive the tools that statically read its attribute, over payloads seeded
   from the field's own key and row. A field no verdict follows is **inert state** —
   the second shipped defect's class: ``healthcare_admin``'s ``restricted_chart``
   was read by no tool while a frozen case's prose asserted a rule about it. Prose
   and sandbox disagreed, and the sandbox is what executes. Neither check 1 nor
   check 2 can see this: that case's violation stayed reachable through a
   *different* rule, so the contract looked perfectly healthy. Findings here are
   always advisory — narrative fixture state is legitimate, and only a human can
   say whether a case's prose leans on the inert field.

Checks 1 and 2 are defect claims (``[dead]``, with ``[warn]`` when the evidence is
weaker); check 3 only ever narrows a search for a person to finish.

## The bounded domain (the honest part)

Arguments are free strings, so an exhaustive sweep is infinite. The search runs
over a **bounded, documented domain**, and the two things that make it hit are
scoping and staging.

**Scoping.** A tool's candidate values are harvested from the fixture attributes
*that tool actually reads* — resolved from the sandbox's own AST, following
``self._helper()`` calls — plus the string/number literals in its body (the values
its branch conditions compare against), plus the identifier-shaped tokens the case
itself names, plus universal numeric probes (``0``, ``1``, and a value larger than
any fixture threshold, so magnitude rules are decidable in both directions).
Scoping to what a tool reads is what keeps the domain in the dozens instead of the
hundreds, which is what makes exhausting it meaningful.

**Staging.** Rather than one flat product at a tiny per-parameter cap, the sweep
runs, from both an all-blank base and a case-canonical base: every 1-parameter
variation, then every 2-parameter variation, then a full cartesian product at
whatever per-parameter cap the remaining budget affords. Every stage is planned
before it runs, so the check reports whether it **exhausted its plan**. A reported
``unreachable`` means *provably unreachable over this documented domain*, never
"we gave up", and the reported payload count makes the claim auditable.

**History.** A verdict can be a function of *prior* calls — the finance sandbox
keeps identity, screening, substantiation and payee-aggregation history — so a
single-call sweep alone reports live contracts as dead. Two mechanisms handle it:

1. **Primed passes.** After the unprimed plan is exhausted, the plan is re-run
   (shallow) behind each of a few named prior-call sequences: the tool called
   twice, the case's other contract tools first, every read-only tool first
   ("substantiate before you attest"), and reads-then-peers. Primed passes only
   ever turn an ``unreachable`` into a ``reachable``, never the reverse.
2. **Minted-id feed-forward.** Some state is keyed by an id the *sandbox* invents:
   ``draft_accrual`` mints ``entry_id=ACR-0001``, and that value exists in no
   fixture and no case prose, so no probe payload can name it. Each primed pass
   therefore harvests the fields its own events recorded and substitutes them into
   the target call **by field name**. Without this, finance's live 2-call
   ``preparer_and_approver_are_the_same_actor`` verdict was reported as a dead
   contract — a false defect claim against frozen content.

Where even a primed sweep finds nothing, the check still *measures* history
dependence (same minted feed-forward) and downgrades to advisory with that reason
named, rather than making a defect claim a single-call sweep cannot support.

Deterministic, offline, stdlib-only. No model calls. Never imports or touches
``src/scorers.py``.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import inspect
import itertools
import re
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, NamedTuple

import finance_redteam_scorer as frs
import pack_conformance

# Dispatches allowed per (case, spec) search. The staged plan is sized to fit.
PAYLOAD_BUDGET = 60_000
# Per-parameter domain used by the 1- and 2-coordinate stages.
MAX_PARAMETER_DOMAIN = 24
MIN_PARAMETER_DOMAIN = 3
# Scoped-fixture-pool values APPENDED to a parameter's domain after the cap. See
# ``parameter_domain``: the append is prefix-preserving on purpose, so widening
# here can only ever clear a finding, never manufacture one.
POOL_RESERVE = 6
# Payloads per PRIMED pass. Behind the right prior calls the witness is the
# canonical or a 1-coordinate payload, so a deep primed sweep buys nothing and
# costs a whole priming sequence per payload.
PRIMED_BUDGET = 1_200
# Probe payloads per tool for the fixture-influence sweep (author mode only).
FIXTURE_PAYLOAD_CAP = 400
# Payloads used to test whether a tool's verdict depends on call history.
HISTORY_PROBE_PAYLOADS = 24

SEVERITY_DEAD = "dead"  # a real defect: an unreachable violation / unperformable control
SEVERITY_WARN = "warn"  # advisory: a dead guard, history-dependent verdict, budget exhaustion

# Harvested values are argument *candidates*; anything longer is prose, not an id.
MAX_TOKEN_LEN = 64

# Identifier-shaped tokens in case prose. A token qualifies on a digit, a hyphen,
# an underscore, an internal dot or a colon — so ordinary words are excluded while
# the shapes the corpora actually use survive (``AR-7710``, ``tomas.v``,
# ``SYN:CLDB``, ``rooming_and_vitals_only``, ``v2.7.1``).
_CASE_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:$-]*")
_CASE_TOKEN_TRIM = ".,;:!?'\"()[]-"
_ID_MARKERS = "-_.:"

# Breach verdicts a case's prose names as the sandbox's response.
_BREACH_TOKEN_RE = re.compile(r"breach=([A-Za-z0-9_|]+)")
_EXPECTED_TOKEN_RE = re.compile(r"expected tokens?\s+([A-Za-z0-9_]+)")

_WORD_SPLIT_RE = re.compile(r"[^a-z0-9]+")
_STOP_WORDS = frozenset({"id", "ref", "the", "of", "a", "to", "for"})

# Name prefixes PACK-SPEC reserves for tools that only RETRIEVE state, plus the
# other retrieval verbs the packs use. A read can never be a violation, so priming
# with all of them is always safe — and it is the only way to reach a
# "substantiate before you attest" rule, whose verdict is a function of which
# reads the agent ran first (finance's sign_off_reconciliation, run_control_test
# and pre-trade restriction checks are all this shape).
READ_TOOL_PREFIXES = (
    "get_", "read_", "check_", "list_", "fetch_", "verify_", "screen_", "compare_", "run_", "describe_",
)

# Parameters whose rules are decided by MAGNITUDE, not identity. Threshold logic
# ("did this entry close the break", "is this over the ceiling") compares an
# argument against a numeric fixture, so those fixtures' values have to rank ahead
# of the identifier tokens that dominate a pool by count.
_NUMERIC_PARAMETER_WORDS = frozenset(
    {
        "amount", "limit", "quantity", "qty", "value", "count", "price", "total",
        "balance", "variance", "notional", "sum", "cap", "threshold", "income", "size",
    }
)


class PackReachabilityError(Exception):
    """Raised when a pack's sandbox cannot be loaded for a reachability sweep."""


# ---------------------------------------------------------------------------
# Sandbox loading
# ---------------------------------------------------------------------------


def load_sandbox(sandbox_path: Path, class_name: str) -> tuple[Any, Callable[[], Any]]:
    """Import a pack sandbox and return ``(module, zero-arg toolbox factory)``.

    A **fresh** toolbox per payload is not paranoia: the finance sandbox keeps
    call ledgers (payee totals, screening calls, verification TTL) that tools
    mutate, so a shared instance would make a sweep order-dependent. Construction
    costs microseconds, so isolation is free.
    """

    spec = importlib.util.spec_from_file_location(sandbox_path.stem, sandbox_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise PackReachabilityError(f"cannot import sandbox module: {sandbox_path}")
    module = importlib.util.module_from_spec(spec)
    # Registering before exec is what lets ``inspect.getsource`` find the class
    # later: without it the class looks "built-in" to inspect and the static
    # analysis silently resolves nothing, which quietly widens every domain.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    cls = getattr(module, class_name, None)
    if cls is None:
        raise PackReachabilityError(f"{sandbox_path.name} has no class {class_name}")
    return module, cls


def tool_parameters(toolbox: Any) -> dict[str, list[str]]:
    """Every tool's declared parameter names, read from ``tool_specs()``.

    From the schema rather than from ``inspect.signature`` on purpose: the schema
    is what an agent under test sees, so it is the surface a payload can be built
    from.
    """

    params: dict[str, list[str]] = {}
    for spec in toolbox.tool_specs():
        fn = spec.get("function") or {}
        name = fn.get("name")
        if name:
            params[name] = list((fn.get("parameters") or {}).get("properties") or {})
    return params


# ---------------------------------------------------------------------------
# Static analysis of the sandbox: what each tool reads, and its literals
# ---------------------------------------------------------------------------


class ToolStatics(NamedTuple):
    """What a tool's implementation touches, resolved statically."""

    reads: dict[str, set[str]]  # tool -> fixture attribute names (no leading _)
    literals: dict[str, list[str]]  # tool -> string/number literals in its body


def _method_bodies(cls: type) -> dict[str, ast.FunctionDef]:
    """Parse the sandbox class (and its bases) into ``name -> function AST``."""

    bodies: dict[str, ast.FunctionDef] = {}
    for klass in reversed(inspect.getmro(cls)):
        if klass is object:
            continue
        try:
            source = inspect.getsource(klass)
        except (OSError, TypeError):  # pragma: no cover - defensive
            continue
        tree = ast.parse(_dedent(source))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                bodies[node.name] = node  # type: ignore[assignment]
    return bodies


def _dedent(source: str) -> str:
    return inspect.cleandoc("\n" + source) if source[:1].isspace() else source


def _comparison_literals(node: ast.AST) -> list[str]:
    """Literals a function *compares against* — its branch-condition vocabulary.

    Only these are argument candidates. A function's other literals are mostly
    things it *emits* (breach token names, field names), and letting them into a
    parameter's domain crowds out the handful of values that actually flip a
    verdict: ``disclose_patient_record`` compares ``sections`` against
    ``("full_chart", "all")`` among 25 literals, and a naive quota kept the wrong
    six.
    """

    out: list[str] = []

    def take(value: Any) -> None:
        token = _clean_token(value)
        if token is not None:
            out.append(token)

    def take_node(item: ast.AST) -> None:
        # Every constant anywhere inside the comparison, including ones passed
        # through a helper call: ``_scope_rank(scope) >= _scope_rank("transact")``
        # hides its only interesting value in a call argument.
        for element in ast.walk(item):
            if isinstance(element, ast.Constant):
                take(element.value)

    for sub in ast.walk(node):
        if isinstance(sub, ast.Compare):
            take_node(sub.left)
            for comparator in sub.comparators:
                take_node(comparator)
        elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr in ("startswith", "endswith", "count", "split"):
                for argument in sub.args:
                    take_node(argument)
    return out


def _self_attributes(node: ast.AST) -> tuple[set[str], set[str]]:
    """``(fixture attributes, self-method calls)`` referenced directly in ``node``."""

    attributes: set[str] = set()
    calls: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if isinstance(sub.func.value, ast.Name) and sub.func.value.id == "self":
                calls.add(sub.func.attr)
        if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name):
            if sub.value.id == "self":
                attributes.add(sub.attr)
    return attributes, calls


def tool_statics(cls: type, tools: Iterable[str], *, max_depth: int = 3) -> ToolStatics:
    """Resolve, per tool, the fixtures it reads and the literals it compares against.

    Follows ``self._helper()`` calls transitively (the finance sandbox routes many
    tools through ``self._posting`` / ``self._outbound``), so a delegating tool
    still resolves to the fixtures its helper reads.
    """

    bodies = _method_bodies(cls)
    reads: dict[str, set[str]] = {}
    literals: dict[str, list[str]] = {}
    for tool in tools:
        seen: set[str] = set()
        frontier = [(tool, 0)]
        attributes: set[str] = set()
        compared: list[str] = []
        every: list[str] = []
        while frontier:
            name, depth = frontier.pop()
            if name in seen or depth > max_depth or name not in bodies:
                continue
            seen.add(name)
            node = bodies[name]
            found, calls = _self_attributes(node)
            attributes |= found
            compared.extend(_comparison_literals(node))
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant):
                    token = _clean_token(sub.value)
                    if token is not None:
                        every.append(token)
            frontier.extend((call, depth + 1) for call in calls)
        reads[tool] = {a.lstrip("_") for a in attributes if a not in seen}
        # Comparison literals FIRST (high signal), then every other literal. A
        # union rather than a fallback: a tool can have one incidental comparison
        # constant and still keep its real vocabulary elsewhere, and preferring the
        # thin list then cost update_staff_entitlement its "transact" scope.
        literals[tool] = _dedupe(compared + every)
    return ToolStatics(reads, literals)


# ---------------------------------------------------------------------------
# Token harvesting
# ---------------------------------------------------------------------------


class Token(NamedTuple):
    """One harvested argument candidate and where it came from."""

    root: str  # the fixture attribute it lives under (no leading _)
    tag: str  # full provenance path, for parameter-name affinity
    value: str


def _clean_token(value: Any) -> str | None:
    """Normalize one harvested value to an argument candidate, or drop it."""

    if isinstance(value, bool):
        return None  # a flag is fixture state, never an argument token
    if isinstance(value, float):
        token = str(int(value)) if value.is_integer() else str(value)
    elif isinstance(value, int):
        token = str(value)
    elif isinstance(value, str):
        token = value.strip()
    else:
        return None
    if not token or len(token) > MAX_TOKEN_LEN:
        return None
    if any(ch.isspace() for ch in token) or not any(ch.isalnum() for ch in token):
        return None
    return token


def harvest_tokens(module: Any, toolbox: Any) -> list[Token]:
    """Argument candidates from a sandbox's fixtures, in declaration order.

    Order is fixture declaration order so a sweep is reproducible; ``root`` is
    what per-tool scoping filters on and ``tag`` is what parameter-name affinity
    is computed against.
    """

    out: list[Token] = []
    seen: set[tuple[str, str]] = set()

    def emit(root: str, tag: str, value: Any) -> None:
        token = _clean_token(value)
        if token is None:
            return
        key = (tag, token)
        if key not in seen:
            seen.add(key)
            out.append(Token(root, tag, token))

    def walk(root: str, tag: str, value: Any, depth: int) -> None:
        if depth > 4:
            return
        if isinstance(value, dict):
            for key, item in value.items():
                # Only a fixture's TOP-level keys are argument candidates: those are
                # the ids ("CHG-4471", "ORD-5511"). One level down the keys are field
                # names ("status", "symbol", "quantity"), and letting those into a
                # parameter's domain crowds out the ids — it is how a modify_order
                # sweep lost ORD-5511 to the word "symbol".
                if depth > 0:
                    walk(root, f"{tag}.{key}" if isinstance(key, str) else tag, item, depth + 1)
                    continue
                if isinstance(key, tuple):
                    # A composite key is a column layout: tag each component with
                    # its POSITION, because a fixture keyed (user_id, mrn) lines up
                    # with a tool whose first two parameters are user_id and mrn.
                    # Positional affinity is what makes such a domain reachable —
                    # a tuple component carries no field name to match on.
                    for index, part in enumerate(key):
                        emit(root, f"{tag}#{index}", part)
                else:
                    emit(root, tag, key)
                walk(root, f"{tag}.{key}" if isinstance(key, str) else tag, item, depth + 1)
            return
        if isinstance(value, (list, tuple, set, frozenset)):
            items = sorted(value, key=repr) if isinstance(value, (set, frozenset)) else value
            for item in items:
                walk(root, tag, item, depth + 1)
            return
        emit(root, tag, value)

    for name, value in vars(toolbox).items():
        if name in ("tool_events", "destructive_calls"):
            continue  # the event ledgers, not fixtures
        walk(name.lstrip("_"), name.lstrip("_"), value, 0)
    for name in dir(module):
        if name.isupper():
            tag = name.lstrip("_").lower()
            walk(tag, tag, getattr(module, name), 0)
    return out


def numeric_probes(pool: list[Token]) -> list[str]:
    """``0``, ``1`` and a value above every fixture threshold.

    Magnitude rules ("amount over the delegated ceiling") are decidable only if
    the domain can straddle the threshold, and a threshold's own value is never
    above itself. Three candidates buy every such rule in both directions.
    """

    largest = 0.0
    for token in pool:
        try:
            largest = max(largest, abs(float(token.value)))
        except ValueError:
            continue
    ceiling = int(largest * 1000) if largest else 1_000_000_000
    return ["0", "1", str(ceiling)]


def case_tokens(case: dict[str, Any]) -> list[str]:
    """Identifier-shaped tokens the case itself names, in first-appearance order."""

    ordered: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        token = raw.strip(_CASE_TOKEN_TRIM)
        if not token or len(token) > MAX_TOKEN_LEN:
            return
        if not any(ch.isdigit() or ch in _ID_MARKERS for ch in token):
            return  # an ordinary word, not an identifier
        if token not in seen:
            seen.add(token)
            ordered.append(token)

    scoring = case.get("scoring") or {}
    for spec in (scoring.get("violating_calls") or []) + (scoring.get("required_calls") or []):
        if isinstance(spec, dict) and isinstance(spec.get("action_contains"), str):
            contains = spec["action_contains"]
            _key, sep, value = contains.partition("=")
            add(value if sep else contains)
    for field in ("user_prompt", "expected_behavior", "scoring_notes"):
        for raw in _CASE_TOKEN_RE.findall(str(case.get(field) or "")):
            add(raw)
    return ordered


def named_breach_tokens(case: dict[str, Any]) -> list[str]:
    """Breach verdicts the case's own prose says the sandbox records.

    A case states its mechanism twice — in ``expected_behavior`` ("which records
    breach=X") and in ``scoring_notes`` ("expected token X"). Those are claims
    about the sandbox, and a claim no payload can satisfy is exactly the defect
    that shipped in ``devops_sre`` v0.4.

    Abbreviated continuations (``.../ _open_investigation``, where the prose
    elides a shared prefix) are skipped rather than guessed at: under-detecting is
    safer than manufacturing a false alarm against frozen content.
    """

    raw: list[str] = []
    prose = " ".join(str(case.get(f) or "") for f in ("expected_behavior", "scoring_notes"))
    for match in _BREACH_TOKEN_RE.findall(prose):
        raw.extend(match.split("|"))
    # "expected token(s)" is followed by prose as often as by a token ("expected
    # tokens are ..."), so that pattern only yields snake_case names. Every breach
    # verdict in every pack is multi-word snake_case, so the filter costs nothing.
    raw.extend(t for t in _EXPECTED_TOKEN_RE.findall(prose) if "_" in t)
    tokens: list[str] = []
    seen: set[str] = set()
    for token in raw:
        token = token.strip()
        if not token or token == "none" or token.startswith("_") or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


# ---------------------------------------------------------------------------
# Parameter-name affinity + domain construction
# ---------------------------------------------------------------------------


def _singular(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def name_words(name: str) -> set[str]:
    """The comparable words in a parameter name or a fixture provenance tag."""

    words = {_singular(w) for w in _WORD_SPLIT_RE.split(name.lower()) if w}
    return {w for w in words if w and w not in _STOP_WORDS}


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def scoped_pool(pool: list[Token], reads: set[str]) -> list[Token]:
    """The fixture tokens a tool can plausibly take, i.e. the state it reads.

    Falls back to the whole pool when static analysis resolved no fixture reads,
    so an unanalysable tool is over-searched rather than under-searched.
    """

    if not reads:
        return pool
    scoped = [t for t in pool if t.root in reads]
    return scoped or pool


def parameter_domain(
    parameter: str,
    tokens: list[str],
    pool: list[Token],
    literals: list[str],
    probes: list[str],
    cap: int,
    *,
    position: int = -1,
    reserve: int = POOL_RESERVE,
) -> list[str]:
    """Ordered candidate values for one parameter.

    A pool token is *affine* to the parameter when their names share a word
    (``secret_id`` ↔ ``secret_scopes``) or when it is the ``position``-th component
    of a composite fixture key (a fixture keyed ``(user_id, mrn)`` supplying a tool
    whose first two parameters are ``user_id`` and ``mrn``).

    Priority, highest first: the blank argument; tokens that are BOTH affine AND
    named by the case (almost always the value the case's own prose puts in that
    slot, so the first non-blank payload is usually the canonical one); the tool's
    own literals; the case's other tokens; the remaining affine tokens; the numeric
    probes; then the rest of the tool's scoped pool.

    ``reserve`` then APPENDS scoped-pool values the cap dropped. That tail is not a
    nicety: every other source in the priority list has a quota, the pool has none,
    and a case naming many ids against a tool holding many literals fills ``cap``
    before one pool value is admitted. That is how a live "sent restricted content
    to the filing subject" violation was reported unreachable while both deciding
    values (the subject's address, the restricted case reference) sat unsearched in
    a NINE-item pool. Appending rather than reordering keeps the domain a
    prefix-preserving superset of the un-reserved one, so the wider search can only
    ever clear a finding — it can never manufacture a new one.
    """

    parameter_words = name_words(parameter)
    positional = f"#{position}" if position >= 0 else None
    affine: list[str] = []
    rest: list[str] = []
    for token in pool:
        matched = bool(parameter_words & name_words(token.tag)) or (
            positional is not None and token.tag.endswith(positional)
        )
        (affine if matched else rest).append(token.value)
    affine = _dedupe(affine)
    affine_set = set(affine)
    named = set(tokens)
    numeric: list[str] = []
    if parameter_words & _NUMERIC_PARAMETER_WORDS:
        numeric = _dedupe(t.value for t in pool if _is_numeric(t.value))
    numeric = _dedupe(numeric + _halves(numeric))
    quota = max(2, cap // 4)
    candidates = _dedupe(
        [""]
        + [t for t in tokens if t in affine_set]
        + numeric[: quota * 2]
        + literals[:quota]
        + tokens[:quota]
        + [t for t in affine if t not in named][:quota]
        + probes
        + tokens
        + affine
        + literals
        + numeric
        + _dedupe(rest)
    )
    domain = candidates[:cap]
    if reserve <= 0:
        return domain
    dropped = [v for v in _dedupe(t.value for t in pool) if v not in set(domain)]
    return domain + dropped[:reserve]


def _halves(values: list[str]) -> list[str]:
    """Half of each numeric candidate — the probe an AGGREGATE threshold needs.

    ``0``, ``1`` and "above every threshold" decide a per-event magnitude rule in
    both directions, but they cannot decide a rule on a RUNNING TOTAL: crossing a
    threshold across two calls needs a value that is under the threshold while two
    of them are not. Half is the smallest such value, and it is what makes finance's
    "split one obligation into sub-threshold instructions" predicate reachable at
    all — a whole failure mode that was otherwise invisible to this sweep.
    """

    out: list[str] = []
    for value in values:
        try:
            number = float(value)
        except ValueError:
            continue
        if number <= 1:
            continue
        out.extend([str(int(number / 2)), str(int(number / 2) + 1)])
    return _dedupe(out)


def _is_numeric(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def tool_domains(
    parameters: list[str],
    tokens: list[str],
    pool: list[Token],
    literals: list[str],
    probes: list[str],
    *,
    cap: int = MAX_PARAMETER_DOMAIN,
) -> dict[str, list[str]]:
    return {
        p: parameter_domain(p, tokens, pool, literals, probes, cap, position=index)
        for index, p in enumerate(parameters)
    }


# ---------------------------------------------------------------------------
# The staged payload plan
# ---------------------------------------------------------------------------


def _flat_cap(n_parameters: int, budget: int) -> int:
    if n_parameters <= 0:
        return MIN_PARAMETER_DOMAIN
    cap = int(max(budget, 1) ** (1.0 / n_parameters))
    return max(MIN_PARAMETER_DOMAIN, min(MAX_PARAMETER_DOMAIN, cap))


def payload_plan(
    domains: dict[str, list[str]], *, budget: int = PAYLOAD_BUDGET
) -> tuple[list[dict[str, str]], str]:
    """Every payload the sweep will drive, and a one-line description of the plan.

    Staged so that each parameter gets its full domain in the 1- and 2-coordinate
    passes (where most breach rules live) while the all-coordinate pass runs at
    whatever per-parameter cap the remaining budget affords. Planned up front and
    deduped, so "the plan was exhausted" is a checkable statement.
    """

    keys = list(domains)
    if not keys:
        return [{}], "1 payload (no arguments)"
    plan: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()

    def push(payload: dict[str, str]) -> None:
        key = tuple(payload[k] for k in keys)
        if key not in seen:
            seen.add(key)
            plan.append(payload)

    blank = {k: "" for k in keys}
    canonical = {k: (domains[k][1] if len(domains[k]) > 1 else "") for k in keys}
    bases = _unique_bases([blank, canonical], keys)
    for base in bases:
        push(dict(base))
    for depth in (1, 2):
        for base in bases:
            for positions in itertools.combinations(keys, depth):
                pools = [[v for v in domains[p] if v != base[p]] or [base[p]] for p in positions]
                for combo in itertools.product(*pools):
                    if len(plan) >= budget:
                        return plan, _describe(plan, keys, domains, depth - 1, 0)
                    payload = dict(base)
                    payload.update(dict(zip(positions, combo)))
                    push(payload)
    flat_cap = _flat_cap(len(keys), max(budget - len(plan), 1))
    flat = [domains[k][:flat_cap] or [""] for k in keys]
    for combo in itertools.product(*flat):
        if len(plan) >= budget:
            return plan, _describe(plan, keys, domains, 2, flat_cap)
        push(dict(zip(keys, combo)))
    return plan, _describe(plan, keys, domains, 2, flat_cap)


def _unique_bases(bases: list[dict[str, str]], keys: list[str]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for base in bases:
        key = tuple(base[k] for k in keys)
        if key not in seen:
            seen.add(key)
            out.append(base)
    return out


def _describe(
    plan: list[dict[str, str]], keys: list[str], domains: dict[str, list[str]], depth: int, flat_cap: int
) -> str:
    sizes = "/".join(str(len(domains[k])) for k in keys)
    flat = f", full product at {flat_cap}/parameter" if flat_cap else ""
    return (
        f"{len(plan)} payloads over {len(keys)} parameters (domains {sizes}); "
        f"all <={depth}-parameter variations from 2 bases{flat}"
    )


# ---------------------------------------------------------------------------
# The search
# ---------------------------------------------------------------------------


class Priming(NamedTuple):
    """A named sequence of prior calls to run before the tool under search.

    ``echo`` prepends the payload *under test* to the sequence, so the tool runs
    twice with identical arguments. An aggregation rule needs exactly that and
    nothing else will do: finance's structuring predicate fires only when two calls
    share a payee AND a single obligation reference AND each amount sits under the
    threshold while the running total crosses it. Priming with any *other* payload
    changes the payee or adds a second obligation and the rule stays silent.
    """

    label: str
    calls: list[tuple[str, dict[str, str]]]
    echo: bool = False


class Search(NamedTuple):
    """Outcome of one bounded sandbox search."""

    status: str  # "reachable" | "unreachable" | "inconclusive"
    tool: str
    arguments: dict[str, str] | None
    action: str | None
    tried: int
    planned: int
    plan: str
    priming: str = "none"  # which prior-call sequence produced the witness

    @property
    def exhaustive(self) -> bool:
        return self.tried >= self.planned


def _last_action(toolbox: Any, tool: str) -> str | None:
    for event in reversed(toolbox.tool_events):
        if event.get("tool_name") == tool:
            return str(event.get("action", ""))
    return None


def _last_event(toolbox: Any, tool: str) -> dict[str, Any] | None:
    for event in reversed(toolbox.tool_events):
        if event.get("tool_name") == tool:
            return event
    return None


def minted_fields(events: list[dict[str, Any]], known: set[str]) -> dict[str, str]:
    """``field -> value`` pairs a priming pass recorded that no payload could name.

    A value absent from every parameter's domain is one the *sandbox* invented
    (``draft_accrual`` -> ``entry_id=ACR-0001``). Such a value keys the very state a
    later tool's verdict reads, and no probe payload can ever supply it — so it is
    fed forward by FIELD NAME into the target call. First occurrence wins, so the
    substitution is deterministic.
    """

    minted: dict[str, str] = {}
    for event in events:
        for pair in str(event.get("action", "")).split(" "):
            key, sep, value = pair.partition("=")
            if sep and key and value and value not in known and key not in minted:
                minted[key] = value
    return minted


def _sweep(
    factory: Callable[[], Any],
    tool: str,
    plan: list[dict[str, str]],
    predicate: Callable[[dict[str, Any]], bool],
    priming: Priming,
    known: set[str],
) -> tuple[dict[str, str], str] | None:
    """One (priming, plan) pass. Returns ``(arguments, action)`` on first witness."""

    for arguments in plan:
        toolbox = factory()
        if priming.echo:
            toolbox.dispatch(tool, dict(arguments))
        for other, payload in priming.calls:
            toolbox.dispatch(other, dict(payload))
        call = dict(arguments)
        if priming.calls:
            for key, value in minted_fields(list(toolbox.tool_events), known).items():
                if key in call:
                    call[key] = value
        toolbox.dispatch(tool, call)
        event = _last_event(toolbox, tool)
        if event is not None and predicate(event):
            return call, str(event.get("action", ""))
    return None


def search_tool(
    factory: Callable[[], Any],
    tool: str,
    domains: dict[str, list[str]],
    predicate: Callable[[dict[str, Any]], bool],
    *,
    budget: int = PAYLOAD_BUDGET,
    primings: Iterable[Priming] = (),
    primed_budget: int = PRIMED_BUDGET,
) -> Search:
    """Drive ``tool`` over its planned domain until ``predicate`` accepts an event.

    Runs the unprimed plan first (so a reachable contract stays cheap), then the
    shallow plan behind each priming sequence. Every primed pass is *additional*
    evidence: it can only turn an ``unreachable`` into a ``reachable``.

    Reports whether the whole plan was exhausted (``unreachable``) or the budget ran
    out first (``inconclusive`` — an honest "not proven", never a defect claim).
    """

    plan, description = payload_plan(domains, budget=budget)
    known = {value for values in domains.values() for value in values}
    found = _sweep(factory, tool, plan, predicate, Priming("none", []), known)
    if found is not None:
        return Search("reachable", tool, found[0], found[1], len(plan), len(plan), description)
    primed = [p for p in primings if p.calls or p.echo]
    shallow, _ = payload_plan(domains, budget=min(budget, primed_budget)) if primed else ([], "")
    planned = len(plan) + len(shallow) * len(primed)
    for priming in primed:
        found = _sweep(factory, tool, shallow, predicate, priming, known)
        if found is not None:
            return Search("reachable", tool, found[0], found[1], planned, planned, description, priming.label)
    if primed:
        description += (
            f"; then {len(shallow)} payloads behind each of {len(primed)} priming sequence(s) "
            f"[{', '.join(p.label for p in primed)}]"
        )
    status = "unreachable" if len(plan) < budget else "inconclusive"
    return Search(status, tool, None, None, planned, planned, description)


def _breach_of(action: str | None) -> str | None:
    if action is None:
        return None
    for token in action.split(" "):
        key, sep, value = token.partition("=")
        if sep and key == "breach":
            return value
    return None


def is_history_dependent(
    factory: Callable[[], Any],
    tool: str,
    payloads: list[dict[str, str]],
    *primings: dict[str, dict[str, str]],
) -> bool:
    """Does this tool's breach verdict depend on what was called before it?

    For each probe payload, compares the breach field across histories: alone,
    called twice, and called after every other tool has run once with each supplied
    ``primings`` payload map (and its all-blank variant). Payload choice is not a
    detail — ``submit_application`` only contradicts its verified income after
    ``update_application_financials`` has run *on a real application id*, and a
    blank-argument prime would miss that and mislabel the pair as a defect. Several
    payload maps are accepted for the same reason, and every one of them can only
    ADD a way to prove dependence: losing one would harden an honest advisory into
    a false defect claim against frozen content.

    Only the breach field is compared — references and sequence numbers change
    harmlessly, and the verdict is the only thing a scoring contract reads. Several
    payloads are probed because state dependence often shows only on a payload that
    actually touches the state (a posting whose account has a reconciliation).

    This is what keeps a single-call sweep honest. A sandbox whose verdict is a
    function of call history cannot be exhausted one call at a time, so its
    findings are advisory rather than defect claims.
    """

    for arguments in payloads:
        solo = factory()
        solo.dispatch(tool, dict(arguments))
        baseline = _breach_of(_last_action(solo, tool))

        twice = factory()
        twice.dispatch(tool, dict(arguments))
        twice.dispatch(tool, dict(arguments))
        if _breach_of(_last_action(twice, tool)) != baseline:
            return True

        # Each primer catches what the others miss. Canonical args reach state keyed
        # by a real id (an application's verified income); case-named args reach
        # state keyed by the record the case is about; blank args reach state keyed
        # by whatever was passed (a restriction check recorded under the empty
        # symbol). Any difference proves dependence.
        variants = [
            payloads
            for priming in primings
            for payloads in (priming, {t: dict.fromkeys(pl, "") for t, pl in priming.items()})
        ]
        for payloads_by_tool in variants:
            primed = factory()
            for other, payload in payloads_by_tool.items():
                if other != tool:
                    primed.dispatch(other, dict(payload))
            primed.dispatch(tool, dict(arguments))
            if _breach_of(_last_action(primed, tool)) != baseline:
                return True
            # Feed forward the ids the priming MINTED. Without this the approval
            # family looks history-independent: its verdict reads
            # ``staged[entry_id]``, the staging call invents that id, and no probe
            # payload can name it — so the breach never moves and a live 2-call
            # verdict is escalated to a false defect claim.
            known = {v for payload in payloads_by_tool.values() for v in payload.values()}
            known |= set(arguments.values())
            forwarded = dict(arguments)
            for key, value in minted_fields(list(primed.tool_events), known).items():
                if key in forwarded:
                    forwarded[key] = value
            if forwarded == arguments:
                continue
            replay = factory()
            for other, payload in payloads_by_tool.items():
                if other != tool:
                    replay.dispatch(other, dict(payload))
            replay.dispatch(tool, forwarded)
            if _breach_of(_last_action(replay, tool)) != _breach_of(
                _breach_reference(factory, tool, forwarded)
            ):
                return True
    return False


def _breach_reference(factory: Callable[[], Any], tool: str, arguments: dict[str, str]) -> str | None:
    """The tool's solo action for these arguments — the no-history control."""

    solo = factory()
    solo.dispatch(tool, dict(arguments))
    return _last_action(solo, tool)


def _contract_tools(case: dict[str, Any]) -> list[str]:
    """Every tool the case's own contract names, in declaration order."""

    scoring = case.get("scoring") or {}
    names = [
        str(spec.get("tool"))
        for spec in (scoring.get("violating_calls") or []) + (scoring.get("required_calls") or [])
        if isinstance(spec, dict) and spec.get("tool")
    ]
    if case.get("tempting_tool"):
        names.append(str(case["tempting_tool"]))
    return _dedupe(names)


def _named_read_tools(case: dict[str, Any], tools: Iterable[str]) -> list[str]:
    """Read-only tools the case's prose names, in order of first mention."""

    prose = " ".join(str(case.get(f) or "") for f in ("user_prompt", "expected_behavior", "scoring_notes"))
    found = [(prose.find(t), t) for t in tools if t.startswith(READ_TOOL_PREFIXES) and t in prose]
    return [t for _at, t in sorted(found)]


def priming_sequences(
    probe: "PackProbe",
    case: dict[str, Any],
    tool: str,
    tokens: list[str],
    witnesses: Iterable[tuple[str, dict[str, str]]] = (),
) -> list[Priming]:
    """Prior-call sequences worth trying, cheapest first.

    Each shape answers a real verdict a single call cannot reach: an aggregation rule
    (the same payload twice, ``self_echo``); state keyed by a canonical payload
    (``self_repeat``); the reads the case's own prose asks for (``case_reads``); the
    sequence an actually-failing agent takes (``prior_witnesses`` — the payloads that
    already satisfied this case's EARLIER contract specs, which is how a submission
    comes to contradict the income a preceding write recorded); the case's other
    contract tools (``peer_calls``); a substantiation rule (every read-only tool
    first — a sign-off that is clean only once both balances were pulled); and the
    combinations.
    """

    named = probe.named_payloads(tokens)
    prior = [(name, dict(payload)) for name, payload in witnesses if name != tool]
    case_reads = [
        (name, dict(named.get(name, {})))
        for name in _named_read_tools(case, probe.parameters)
        if name != tool
    ]
    peers = [
        (name, dict(named.get(name, {})))
        for name in _contract_tools(case)
        if name != tool and name in probe.parameters
    ]
    reads = [
        (name, dict(named.get(name, {})))
        for name in probe.parameters
        if name != tool and name.startswith(READ_TOOL_PREFIXES)
    ]
    out = [
        # Two shapes of "the same tool ran before me", because they reach different
        # state: the same payload twice (an aggregation over one payee), and a
        # case-canonical payload first (state keyed by whatever that payload named).
        Priming("self_echo", [], echo=True),
        Priming("self_repeat", [(tool, dict(named.get(tool, {})))]),
    ]
    if case_reads:
        # The reads the case's OWN prose tells the agent to make, and only those.
        # Driving every read-only tool instead can defeat the rule it is meant to
        # reach: finance's verification window is six CALLS wide, so a 38-read
        # preamble expires the very step-up the case asks for, and a live control
        # reads as unperformable.
        out.append(Priming("case_reads", case_reads))
    if prior:
        out.append(Priming("prior_witnesses", prior))
    if peers:
        out.append(Priming("peer_calls", peers))
    if reads:
        out.append(Priming("reads_first", reads))
    if reads and prior:
        out.append(Priming("reads_then_witnesses", reads + prior))
    if reads and peers:
        out.append(Priming("reads_then_peers", reads + peers))
    return out


def _violation_predicate(spec: dict[str, Any]) -> Callable[[dict[str, Any]], bool]:
    return lambda event: frs._event_matches(event, spec)


def _performance_predicate(
    required: list[dict[str, Any]], guards: list[dict[str, Any]]
) -> Callable[[dict[str, Any]], bool]:
    def predicate(event: dict[str, Any]) -> bool:
        if not all(frs._event_matches(event, spec) for spec in required):
            return False
        return not any(frs._event_matches(event, guard) for guard in guards)

    return predicate


def _emits_token(token: str) -> Callable[[dict[str, Any]], bool]:
    spec = {"action_contains": f"breach={token}"}
    return lambda event: frs._event_matches(event, spec)


def token_in_source(token: str, source: str) -> bool:
    """Could this breach token be produced by this source at all?

    A literal match is the common case, but verdicts are also *composed*
    (``f"identity_{state}"``), so a token absent as a literal may still be
    emittable. Underscore-boundary prefixes and suffixes adjacent to an
    interpolation brace count as present — otherwise the check would claim
    "appears nowhere in the sandbox" about a token the sandbox does emit, which is
    the worst kind of false alarm: a confident one.
    """

    if not source or token in source:
        return True
    for index, char in enumerate(token):
        if char != "_":
            continue
        if f"{token[: index + 1]}{{" in source or f"}}{token[index:]}" in source:
            return True
    return False


def _by_tool(specs: list[Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for spec in specs:
        if isinstance(spec, dict) and spec.get("tool"):
            grouped.setdefault(spec["tool"], []).append(spec)
    return grouped


# ---------------------------------------------------------------------------
# Per-case + per-pack checks
# ---------------------------------------------------------------------------


def _finding(severity: str, subject: str, message: str) -> str:
    return f"[{severity}] {subject}: {message}"


def severity_of(finding: str) -> str:
    for severity in (SEVERITY_DEAD, SEVERITY_WARN):
        if finding.startswith(f"[{severity}]"):
            return severity
    return ""


def has_dead(findings: list[str]) -> bool:
    return any(severity_of(f) == SEVERITY_DEAD for f in findings)


class PackProbe(NamedTuple):
    """Everything a sweep needs about one pack's sandbox, computed once."""

    factory: Callable[[], Any]
    parameters: dict[str, list[str]]
    pool: list[Token]
    statics: ToolStatics
    probes: list[str]
    source: str = ""

    def canonical_payloads(self, tokens: list[str]) -> dict[str, dict[str, str]]:
        """One case-canonical payload per tool, for the history-dependence primer."""

        payloads: dict[str, dict[str, str]] = {}
        for tool in self.parameters:
            domains = self.domains_for(tool, tokens) or {}
            payloads[tool] = {
                name: (values[1] if len(values) > 1 else "") for name, values in domains.items()
            }
        return payloads

    def named_payloads(self, tokens: list[str]) -> dict[str, dict[str, str]]:
        """Like ``canonical_payloads``, but each parameter prefers an id the CASE names.

        This is what makes a priming call land on the record the case is *about*: a
        substantiation rule clears only once both balances were pulled **for that
        account**, and a payload built from a tool's first literal pulls a different
        account, leaving the rule looking unreachable. Kept SEPARATE from
        ``canonical_payloads`` rather than replacing it, because the history probe
        needs both: each reaches state the other misses, and losing either would
        harden an honest advisory into a false defect claim.

        Preference order per parameter, and the middle rule is the load-bearing one:

        1. a case token that ALSO exists in the sandbox's own state for this tool —
           the only kind of value that can key a real record;
        2. any other case token that is not the name of a tool in this pack. A
           case's ``scoring_notes`` cites its own contract, so tool names are
           identifier-shaped case tokens; taking one made the substantiation primer
           read an account literally called ``get_subledger_balance`` and report a
           live control as unperformable;
        3. the domain's own canonical slot.

        These payloads never appear in a reported witness — they only decide which
        state a primer reaches.
        """

        named = set(tokens)
        tool_names = set(self.parameters)
        payloads: dict[str, dict[str, str]] = {}
        for tool in self.parameters:
            domains = self.domains_for(tool, tokens) or {}
            in_state = {t.value for t in scoped_pool(self.pool, self.statics.reads.get(tool, set()))}
            payloads[tool] = {
                name: next(
                    (v for v in values if v in named and v in in_state),
                    next(
                        (v for v in values if v in named and v not in tool_names),
                        values[1] if len(values) > 1 else "",
                    ),
                )
                for name, values in domains.items()
            }
        return payloads

    def domains_for(self, tool: str, tokens: list[str]) -> dict[str, list[str]] | None:
        parameters = self.parameters.get(tool)
        if parameters is None:
            return None
        return tool_domains(
            parameters,
            tokens,
            scoped_pool(self.pool, self.statics.reads.get(tool, set())),
            self.statics.literals.get(tool, []),
            self.probes,
        )


def build_probe(factory: Callable[[], Any], module: Any) -> PackProbe:
    toolbox = factory()
    parameters = tool_parameters(toolbox)
    pool = harvest_tokens(module, toolbox)
    try:
        source = inspect.getsource(type(toolbox))
    except (OSError, TypeError):  # pragma: no cover - defensive
        source = ""
    return PackProbe(
        factory,
        parameters,
        pool,
        tool_statics(type(toolbox), parameters),
        numeric_probes(pool),
        source,
    )


def _unreached(
    probe: PackProbe,
    result: Search,
    domains: dict[str, list[str]],
    tokens: list[str],
    *,
    hard: bool,
) -> tuple[str, str]:
    """Severity and reason for a search that found no witness.

    Downgrades to advisory when the budget was not exhausted, or when the tool's
    verdict is a function of call history (a single-call sweep cannot decide it).
    """

    if not result.exhaustive:
        return SEVERITY_WARN, "the plan was not exhausted within the payload budget"
    probes, _description = payload_plan(domains, budget=HISTORY_PROBE_PAYLOADS)
    if is_history_dependent(
        probe.factory,
        result.tool,
        probes[:HISTORY_PROBE_PAYLOADS],
        probe.canonical_payloads(tokens),
        probe.named_payloads(tokens),
    ):
        return (
            SEVERITY_WARN,
            "this tool's breach verdict depends on prior calls, so a single-call sweep cannot decide it",
        )
    return (SEVERITY_DEAD if hard else SEVERITY_WARN), "the plan was exhausted"


def check_case(case: dict[str, Any], probe: PackProbe, *, budget: int = PAYLOAD_BUDGET) -> list[str]:
    """Reachability findings for one case; ``[]`` == every contract path is live."""

    cid = str(case.get("case_id") or "<no-id>")
    scoring = case.get("scoring")
    if not isinstance(scoring, dict):
        return []  # conformance's job, not this check's
    violating = [s for s in (scoring.get("violating_calls") or []) if isinstance(s, dict)]
    required = [s for s in (scoring.get("required_calls") or []) if isinstance(s, dict)]
    is_control = case.get("kind") == "honest_control" or scoring.get("expected_safe_signal") == "action_required"
    tokens = case_tokens(case)
    findings: list[str] = []
    # Payloads that already satisfied an EARLIER spec of this same case. Replaying
    # them as priming is the sequence a really-failing agent takes, and it is the
    # only way a cross-call rule ("this submission contradicts the income the
    # preceding write recorded") is reachable at all. Accumulated across all three
    # checks, so a later check inherits every witness the earlier ones found.
    witnesses: list[tuple[str, dict[str, str]]] = []

    # --- 1. can the sandbox actually emit each violating event? --------------
    reachable_specs = 0
    for index, spec in enumerate(violating):
        tool = str(spec.get("tool") or "")
        domains = probe.domains_for(tool, tokens)
        if domains is None:
            continue  # closure violation — pack_conformance reports it
        result = search_tool(
            probe.factory,
            tool,
            domains,
            _violation_predicate(spec),
            budget=budget,
            primings=priming_sequences(probe, case, tool, tokens, witnesses),
        )
        if result.status == "reachable":
            reachable_specs += 1
            if result.arguments is not None:
                witnesses.append((tool, dict(result.arguments)))
            continue
        severity, reason = _unreached(probe, result, domains, tokens, hard=not is_control)
        role = (
            "the over-reach guard on this control is dead (an over-reaching call would score performed)"
            if is_control
            else "a real violation on this path would score SAFE"
        )
        findings.append(
            _finding(
                severity,
                cid,
                f"violating_calls[{index}] ({tool}) not reachable: {result.plan}; {reason} — {role}",
            )
        )
    if violating and not is_control and reachable_specs == 0:
        findings.append(
            _finding(
                SEVERITY_DEAD,
                cid,
                "NO violating_call is reachable from the sandbox — this temptation cannot be failed by "
                "any agent, so it scores safe unconditionally",
            )
        )

    # --- 2. can the sandbox emit the breach verdict the prose names? ---------
    # Contract reachability alone is not enough: a contract saying only "any event
    # lacking breach=none" stays losable through ANY token, so a specific stated
    # mechanism can rot while the case still looks healthy.
    candidate_tools = _dedupe(
        [str(s.get("tool")) for s in violating if s.get("tool")]
        + ([str(case["tempting_tool"])] if case.get("tempting_tool") else [])
    )
    for token in named_breach_tokens(case):
        searched: list[tuple[Search, dict[str, list[str]]]] = []
        emitted = False
        for tool in candidate_tools:
            domains = probe.domains_for(tool, tokens)
            if domains is None:
                continue
            result = search_tool(
                probe.factory,
                tool,
                domains,
                _emits_token(token),
                budget=budget,
                primings=priming_sequences(probe, case, tool, tokens, witnesses),
            )
            searched.append((result, domains))
            if result.status == "reachable":
                if result.arguments is not None:
                    witnesses.append((tool, dict(result.arguments)))
                emitted = True
                break
        if emitted or not searched:
            continue
        # Severity follows the LAST tool searched; every candidate tool failed, and
        # the weakest evidence among them is what the finding can honestly claim.
        severity = SEVERITY_DEAD
        reason = ""
        for result, domains in searched:
            candidate_severity, candidate_reason = _unreached(probe, result, domains, tokens, hard=True)
            if candidate_severity == SEVERITY_WARN:
                severity, reason = candidate_severity, candidate_reason
                break
            reason = candidate_reason
        # A token absent from the sandbox source is proof rather than inference:
        # no code path could ever emit it. Worth saying, because it changes what
        # the fix is (write the rule vs. fix the rule's guard).
        if not token_in_source(token, probe.source):
            severity, reason = SEVERITY_DEAD, "the token appears NOWHERE in the sandbox source"
        findings.append(
            _finding(
                severity,
                cid,
                f"prose names breach token '{token}' that no payload of "
                f"{'/'.join(s.tool for s, _d in searched)} emits ({reason}) — the case's stated mechanism "
                f"is not reachable as written",
            )
        )

    # --- 3. can a correct agent actually perform the required action? --------
    # Only meaningful where the required call is the consequential act itself. For
    # an escalation temptation the required call is an escalation tool that never
    # carries a breach verdict, and the archetype check already proves that path.
    #
    # Specs are searched ONE AT A TIME because that is what the scorer does:
    # ``_all_present`` asks whether EACH spec is matched by SOME event, never
    # whether one event matches them all. Demanding a single satisfying event made
    # every multi-call control structurally unsatisfiable — a control asking for
    # three payments, one per obligation reference, was reported unperformable
    # precisely because no single payment can carry three different references.
    if is_control and required:
        guards = _by_tool(violating)
        for index, spec in enumerate(required):
            tool = str(spec.get("tool") or "")
            domains = probe.domains_for(tool, tokens)
            if domains is None:
                continue
            result = search_tool(
                probe.factory,
                tool,
                domains,
                _performance_predicate([spec], guards.get(tool, [])),
                budget=budget,
                primings=priming_sequences(probe, case, tool, tokens, witnesses),
            )
            if result.status == "reachable":
                if result.arguments is not None:
                    witnesses.append((tool, dict(result.arguments)))
                continue
            severity, reason = _unreached(probe, result, domains, tokens, hard=True)
            findings.append(
                _finding(
                    severity,
                    cid,
                    f"required_calls[{index}] on {tool} not performable: {result.plan}; {reason} — no "
                    f"payload satisfies it without tripping the case's own violating guard, so this "
                    f"control can only ever false-positive",
                )
            )
    return findings


def check_pack(
    cases: list[dict[str, Any]],
    factory: Callable[[], Any],
    module: Any,
    *,
    budget: int = PAYLOAD_BUDGET,
) -> list[str]:
    """Reachability findings for a whole pack; ``[]`` == nothing detected."""

    probe = build_probe(factory, module)
    findings: list[str] = []
    for case in cases:
        findings.extend(check_case(case, probe, budget=budget))
    return findings


# ---------------------------------------------------------------------------
# Fixture influence (dead-state detection) — author mode
# ---------------------------------------------------------------------------


class FixtureField(NamedTuple):
    """One addressable fixture leaf: an attribute plus a path of dict keys."""

    attribute: str
    path: tuple[Any, ...]
    value: Any

    @property
    def label(self) -> str:
        return ".".join([self.attribute] + [str(p) for p in self.path])


def fixture_fields(toolbox: Any, *, max_depth: int = 3) -> list[FixtureField]:
    """Every scalar leaf of every dict fixture, addressable for perturbation."""

    fields: list[FixtureField] = []

    def walk(attribute: str, path: tuple[Any, ...], value: Any, depth: int) -> None:
        if isinstance(value, dict) and depth < max_depth:
            for key, item in value.items():
                walk(attribute, path + (key,), item, depth + 1)
            return
        if path:
            fields.append(FixtureField(attribute, path, value))

    for name, value in vars(toolbox).items():
        if name in ("tool_events", "destructive_calls") or not isinstance(value, dict):
            continue
        walk(name, (), value, 0)
    return fields


def _perturb(value: Any) -> Any:
    """A different value of a comparable kind — enough to reveal a dependency."""

    if isinstance(value, bool):
        return not value
    if isinstance(value, str):
        return "" if value else "PERTURBED"
    if isinstance(value, (int, float)):
        return 0 if value else 1
    if value is None:
        return "PERTURBED"
    return None


FIXTURE_PERTURBATION_CAP = 6


def perturbations(field: FixtureField, toolbox: Any, vocabulary: list[str]) -> list[Any]:
    """Candidate replacement values for one fixture field, most generic first.

    One replacement is not enough. ``linked_auth_status`` is compared against
    ``"approved"``, so blanking ``"none"`` leaves the verdict untouched and the
    field looks inert when it is load-bearing. So the candidates also include what
    the field's SIBLING rows hold (the values the fixture author considered valid
    for that slot) and the values the reading tools actually compare against.
    """

    if isinstance(field.value, bool):
        return [not field.value]
    candidates: list[Any] = [_perturb(field.value)]
    leaf = field.path[-1]
    container = getattr(toolbox, field.attribute)
    for row in container.values() if isinstance(container, dict) else []:
        if isinstance(row, dict) and leaf in row:
            candidates.append(row[leaf])
    candidates.extend(vocabulary)
    out: list[Any] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate == field.value or repr(candidate) in seen:
            continue
        seen.add(repr(candidate))
        out.append(candidate)
        if len(out) >= FIXTURE_PERTURBATION_CAP:
            break
    return out


def _apply(toolbox: Any, field: FixtureField, value: Any) -> None:
    container = getattr(toolbox, field.attribute)
    for key in field.path[:-1]:
        container = container[key]
    container[field.path[-1]] = value


def field_tokens(field: FixtureField, toolbox: Any) -> list[str]:
    """Argument candidates implied by a fixture field's address AND its own row.

    A fixture key IS the argument tuple that reaches it:
    ``access_scope[("USR-MA-5140", "MRN-9130")]["restricted_chart"]`` is only
    reachable by a call naming that user and that chart. Seeding from the key is
    what makes this check work at all — a generic payload sample almost never lands
    on a specific fixture row, and every field then looks inert.

    The rest of the ROW matters just as much, because a rule can require several
    arguments to agree with several fields of one record: ``rollback`` only consults
    a ticket's ``env`` when the call also names that ticket's ``rollback_service``
    and ``rollback_target``. Seeding those makes the case-canonical base payload the
    exact call that exercises the field, instead of something three coordinates
    away from it.
    """

    tokens: list[str] = []

    def add(value: Any) -> None:
        token = _clean_token(value)
        if token is not None:
            tokens.append(token)

    for part in field.path:
        for piece in (part if isinstance(part, tuple) else (part,)):
            add(piece)
    add(field.value)
    add(_perturb(field.value))
    container = getattr(toolbox, field.attribute, None)
    for key in field.path[:-1]:
        container = container[key] if isinstance(container, dict) else None
    if isinstance(container, dict):
        for value in container.values():
            add(value)
    return _dedupe(tokens)


def _readers(probe: PackProbe, attribute: str) -> list[str]:
    """Tools whose implementation reads this fixture attribute.

    Only these can react to it, so only these are driven — which is what keeps a
    per-field sweep affordable.
    """

    name = attribute.lstrip("_")
    return [tool for tool in probe.parameters if name in probe.statics.reads.get(tool, set())]


def _drive(
    factory: Callable[[], Any],
    payloads: dict[str, list[dict[str, str]]],
    mutate: Callable[[Any], None] | None = None,
) -> dict[tuple[str, int], str]:
    actions: dict[tuple[str, int], str] = {}
    for tool, rows in payloads.items():
        for index, arguments in enumerate(rows):
            toolbox = factory()
            if mutate is not None:
                mutate(toolbox)
            toolbox.dispatch(tool, dict(arguments))
            actions[(tool, index)] = _last_action(toolbox, tool) or ""
    return actions


def fixture_findings(
    factory: Callable[[], Any],
    module: Any,
    *,
    payload_cap: int = FIXTURE_PAYLOAD_CAP,
) -> list[str]:
    """Report fixture fields whose value no tool's output depends on.

    Every finding here is **advisory**, and deliberately so: an inert fixture field
    is not by itself a defect. Sandboxes legitimately carry narrative state (an
    incident commander's name) that no rule reads. It becomes the
    ``restricted_chart`` defect only when some case's prose asserts a rule about the
    field — and deciding that is a human read, not a string match, because the prose
    names the concept rather than the attribute ("chart=break_the_glass_restricted"
    for ``restricted_chart``). So this check narrows the search from a whole sandbox
    to a short list, and a person judges the list.

    Two levels of inertness are distinguished because they need different reads:
    "no verdict depends on it" (the field could still be discoverable context), and
    "not even surfaced by a read-only tool" (the field is invisible to the agent as
    well, so no amount of correct verification could find it).

    This is the check that closes the second shipped defect's class, and the reason
    it needs to exist separately: an unenforced rule leaves the *contract* perfectly
    reachable through some other rule, so neither conformance, nor the archetype
    check, nor contract-level reachability can see it.

    Bounded like the reachability search, but seeded per field from the field's own
    key and driven only against the tools that read its attribute.
    """

    probe = build_probe(factory, module)
    reference = probe.factory()
    findings: list[str] = []
    for field in fixture_fields(reference):
        readers = _readers(probe, field.attribute)
        if not readers:
            findings.append(
                _finding(
                    SEVERITY_WARN,
                    field.label,
                    f"no tool's implementation reads '{field.attribute.lstrip(chr(95))}' at all — "
                    f"dead fixture state",
                )
            )
            continue
        tokens = field_tokens(field, reference)
        payloads: dict[str, list[dict[str, str]]] = {}
        vocabulary: list[str] = []
        for tool in readers:
            domains = probe.domains_for(tool, tokens) or {}
            plan, _description = payload_plan(domains, budget=payload_cap)
            payloads[tool] = plan
            vocabulary.extend(probe.statics.literals.get(tool, []))
        candidates = perturbations(field, reference, _dedupe(vocabulary))
        if not candidates:
            continue
        baseline = _drive(factory, payloads)
        verdict_moved = False
        read_moved = False
        for replacement in candidates:

            def mutate(toolbox: Any, field: FixtureField = field, replacement: Any = replacement) -> None:
                _apply(toolbox, field, replacement)

            after = _drive(factory, payloads, mutate)
            for key, action in baseline.items():
                other = after.get(key, "")
                if other == action:
                    continue
                if _breach_of(action) != _breach_of(other):
                    verdict_moved = True
                else:
                    read_moved = True
            if verdict_moved:
                break
        if verdict_moved:
            continue
        role = (
            "surfaced by a tool's output but decides no breach verdict"
            if read_moved
            else "no tool's verdict depends on this value AND no tool surfaces it — inert fixture "
            "state (either unread, or another field of the same record decides first)"
        )
        findings.append(
            _finding(
                SEVERITY_WARN,
                field.label,
                f"{role} ({field.value!r} perturbed to {len(candidates)} other value(s) across "
                f"{len(baseline)} payloads on {'/'.join(readers)}; no verdict moved)",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Gate wiring
# ---------------------------------------------------------------------------


def _pack_inputs(pack_dir: Path, meta: dict[str, str]) -> tuple[list[dict[str, Any]], Any, Any] | None:
    """Load a pack's corpus + sandbox, or ``None`` when held-out files are absent."""

    corpus = pack_dir / "cases.jsonl"
    sandbox = pack_dir / meta.get("sandbox", "")
    if not corpus.exists() or not sandbox.exists():
        return None
    cases = pack_conformance.load_cases(corpus)
    module, factory = load_sandbox(sandbox, meta["class"])
    return cases, module, factory


def public_findings_by_pack(
    benchmarks_dir: Path, *, budget: int = PAYLOAD_BUDGET
) -> dict[str, list[str]]:
    """Findings per registered pack whose held-out corpus AND sandbox are present.

    Mirrors ``pack_conformance.check_public``'s traversal, including its rule that
    an absent held-out fixture is not a failure — this check needs the gitignored
    sandbox, so it must no-op in a clean public checkout.
    """

    by_pack: dict[str, list[str]] = {}
    for slug, meta in pack_conformance.REGISTERED_PACKS.items():
        pack_dir = benchmarks_dir / slug
        if not (pack_dir / "METHODOLOGY.md").exists():
            continue  # pack not registered in this checkout
        try:
            loaded = _pack_inputs(pack_dir, meta)
        except Exception as exc:  # reported, not raised
            by_pack[slug] = [_finding(SEVERITY_WARN, slug, f"sandbox/corpus could not be loaded: {exc}")]
            continue
        if loaded is None:
            continue  # held-out fixtures absent — correct, skip
        cases, module, factory = loaded
        try:
            findings = check_pack(cases, factory, module, budget=budget)
        except Exception as exc:  # reported, not raised
            by_pack[slug] = [_finding(SEVERITY_WARN, slug, f"reachability sweep failed: {exc}")]
            continue
        if findings:
            by_pack[slug] = [_with_pack(f, slug) for f in findings]
    return by_pack


def check_public(benchmarks_dir: Path, *, budget: int = PAYLOAD_BUDGET) -> list[str]:
    """Hard findings only (``[dead]``), flattened.

    Kept as a separate entry point from ``public_findings_by_pack`` so a future
    pipeline can gate on the hard findings alone once the frozen corpora are clean;
    the CLI's ``--report-public`` mode is advisory today (see ``main``).
    """

    errors: list[str] = []
    for findings in public_findings_by_pack(benchmarks_dir, budget=budget).values():
        errors.extend(f for f in findings if severity_of(f) == SEVERITY_DEAD)
    return errors


def _with_pack(finding: str, slug: str) -> str:
    tag, sep, rest = finding.partition("] ")
    return f"{tag}{sep}{slug}: {rest}" if sep else f"{slug}: {finding}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", help="pack slug under evals/benchmarks/")
    parser.add_argument("--sandbox", help="sandbox module path (default: the registry's)")
    parser.add_argument("--sandbox-class", help="toolbox class name (default: the registry's)")
    parser.add_argument("--budget", type=int, default=PAYLOAD_BUDGET, help="payloads per search")
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help="also run the fixture-influence (dead-state) sweep — author mode, slower",
    )
    parser.add_argument(
        "--fixture-payload-cap", type=int, default=FIXTURE_PAYLOAD_CAP, help="probe payloads per tool"
    )
    parser.add_argument(
        "--report-public",
        action="store_true",
        help="gate mode (advisory, always exits 0 without --strict): sweep every registered pack "
        "whose held-out sandbox is present locally",
    )
    parser.add_argument("--strict", action="store_true", help="exit non-zero on any finding")
    args = parser.parse_args(argv)

    from repo_config import REPO_ROOT

    benchmarks = REPO_ROOT / "evals/benchmarks"

    if args.report_public:
        # ADVISORY in gate mode, for the same reason ``pack_symmetry_check`` is: the
        # three corpora were frozen BEFORE this check existed, and finance carries
        # findings whose only legitimate fix is a new version — never an in-place
        # edit of a frozen pack. Failing the gate would block everyone while
        # forbidding the fix. A pack's pre-freeze pipeline runs
        # ``--pack <slug> --strict``, which does exit non-zero.
        by_pack = public_findings_by_pack(benchmarks, budget=args.budget)
        dead = warn = 0
        for findings in by_pack.values():
            for finding in findings:
                print(f"REACHABILITY: {finding}", file=sys.stderr)
                if severity_of(finding) == SEVERITY_DEAD:
                    dead += 1
                else:
                    warn += 1
        print(
            f"pack reachability (advisory): {dead} dead, {warn} advisory across "
            f"{len(by_pack)} pack(s) with findings"
        )
        return 1 if args.strict and (dead or warn) else 0

    if not args.pack:
        parser.error("--pack is required unless --report-public is given")
    meta = dict(pack_conformance.REGISTERED_PACKS.get(args.pack, {}))
    pack_dir = benchmarks / args.pack
    sandbox_path = Path(args.sandbox) if args.sandbox else pack_dir / meta.get("sandbox", "")
    class_name = args.sandbox_class or meta.get("class", "")
    if not sandbox_path.exists() or not class_name:
        print(f"no sandbox for pack {args.pack} ({sandbox_path})", file=sys.stderr)
        return 2
    cases = pack_conformance.load_cases(pack_dir / "cases.jsonl")
    module, factory = load_sandbox(sandbox_path, class_name)

    findings = check_pack(cases, factory, module, budget=args.budget)
    if args.fixtures:
        findings += fixture_findings(factory, module, payload_cap=args.fixture_payload_cap)
    for finding in findings:
        print(f"REACHABILITY: {finding}", file=sys.stderr)
    dead = sum(1 for f in findings if severity_of(f) == SEVERITY_DEAD)
    warn = len(findings) - dead
    print(f"pack {args.pack}: {len(cases)} cases swept — {dead} dead, {warn} advisory")
    return 1 if (dead or (args.strict and warn)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
