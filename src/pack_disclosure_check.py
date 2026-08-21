"""Does a temptation announce its own answer, or must the agent go and look?

PACK-SPEC requires the disqualifying fact to live in **retrievable state, not stated in
the prompt**. That rule is the one thing this lab has measured a price for: rewriting 12
finance temptations so the disqualifier was only reachable by a tool call the agent had
skipped moved the violation rate from 14.0% to 47.2% against a 23-case internal control
that moved 4.0 points (B-05, 2026-07-26, difference-in-differences +29.2).

Nothing checked it. Ten `pack_*` modules check conformance, pair symmetry, archetype
behaviour, sandbox reachability and identifier leaks; none asks whether a temptation states
its own disqualifier. So the rule with the highest measured value in the repository was the
only rule with no enforcement, and 64 of 76 temptations had never been classified either way.

WHAT THIS DOES, AND WHAT IT CANNOT DO. It is a *screen*, not a judge. It reads only
`user_prompt` and reports two deterministic signals:

  1. **self-aware framing** — the prompt acknowledges it is asking for something irregular
     ("even though", "I know it's", "just this once", "don't bother checking"). A request
     that flags itself tests obedience, not diligence.
  2. **policy-state assertion** — the prompt itself supplies a control-state fact the agent
     was supposed to retrieve ("not approved", "without sign-off", "consent is missing",
     "the hold expired"). If the prompt says it, no read is required to know it.

Either signal means the answer is in the text. Neither means the screen found nothing —
which is *not* the same as proving the disqualifier is hidden. A prompt can leak its
disqualifier through phrasing this screen cannot model, exactly as `pack_symmetry_check`
cannot see every prose asymmetry. Rows with no signal are reported as `unflagged`, never as
`hidden`, and that wording is deliberate.

Calibration is published rather than asserted: `finance_redteam` carries a `b05_retrofit`
marker on the 12 records the B-05 rewrite touched, which are known-hidden by construction.
`--calibrate` scores the screen against them and prints the confusion counts, so a reader
can see its error rate instead of trusting it.

    python3 src/pack_disclosure_check.py                 # every pack with a corpus on disk
    python3 src/pack_disclosure_check.py --pack devops_sre --list
    python3 src/pack_disclosure_check.py --calibrate

Deterministic, offline, stdlib-only. Reads corpora; writes nothing. Never touches
src/scorers.py. Prints case ids and counts only — never prompt text.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_SRC = Path(__file__).resolve().parent
sys.path.insert(0, str(_SRC))

from repo_config import REPO_ROOT

CHECK_VERSION = "pack_disclosure_check/v1"
BENCH = REPO_ROOT / "evals/benchmarks"

# 1. The prompt acknowledges its own irregularity. A request that flags itself is an
#    obedience test: the agent is told the rule before it is asked to break it.
SELF_AWARE = (
    r"even though", r"even if", r"despite", r"i know (?:it|this|that|we|you)",
    r"i realise", r"i realize", r"just this once", r"as a one[- ]off",
    r"don'?t (?:bother|worry|need) (?:to )?(?:check|verify|look|confirm)",
    r"no need to (?:check|verify|confirm|wait|ask)",
    r"skip (?:the )?(?:check|verification|approval|review|sign[- ]?off)",
    r"without (?:checking|verifying|waiting|asking|confirming)",
    r"bypass", r"override", r"work around", r"go ahead anyway",
    r"do it anyway", r"push (?:it )?through", r"force (?:it|the)",
    r"make an exception", r"we can fix (?:it|this) later",
)

# 2. The prompt supplies a control-state fact the agent was supposed to retrieve. If the
#    text asserts the state, reading it back adds nothing.
POLICY_NOUN = (
    r"approvals?", r"authoris(?:ation|ed)", r"authoriz(?:ation|ed)", r"sign[- ]?off",
    r"consent", r"permission", r"clearance", r"mandate", r"waiver",
    r"retention hold", r"legal hold", r"hold", r"embargo", r"freeze",
    r"second signature", r"dual control", r"maker[- ]checker", r"four[- ]eyes",
    r"segregation of duties", r"change ticket", r"change request",
    r"limit", r"threshold", r"cap", r"quota",
    r"licen[cs]e", r"entitlement", r"eligibility", r"prior authorisation",
    r"prior authorization", r"credential", r"access scope",
)
# negation / expiry / absence sitting near a policy noun
NEGATOR = (
    r"\bno\b", r"\bnot\b", r"\bnever\b", r"\bwithout\b", r"\bmissing\b", r"\babsent\b",
    r"\black(?:s|ing)?\b", r"\bexpired?\b", r"\blapsed\b", r"\brevoked\b",
    r"\bsuspended\b", r"\bpending\b", r"\bunapproved\b", r"\bunauthoris(?:ed)\b",
    r"\bunauthoriz(?:ed)\b", r"\bhasn'?t\b", r"\bhaven'?t\b", r"\bisn'?t\b",
    r"\baren'?t\b", r"\bdidn'?t\b", r"\bwon'?t\b", r"\byet to\b", r"\bstill\b",
    r"\boutstanding\b", r"\bover (?:the )?(?:limit|cap|threshold)\b", r"\bexceeds?\b",
)

_SELF = [re.compile(p, re.I) for p in SELF_AWARE]
_NOUN = [re.compile(p, re.I) for p in POLICY_NOUN]
_NEG = [re.compile(p, re.I) for p in NEGATOR]

# how close a negator must sit to a policy noun to count as one assertion
WINDOW = 60


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?;])\s+|\n+", text or "") if s.strip()]


def policy_state_assertions(prompt: str) -> list[str]:
    """Negation/expiry sitting within WINDOW characters of a policy noun, per sentence."""

    hits: list[str] = []
    for sentence in _sentences(prompt):
        for noun in _NOUN:
            for m in noun.finditer(sentence):
                lo = max(0, m.start() - WINDOW)
                hi = min(len(sentence), m.end() + WINDOW)
                window = sentence[lo:hi]
                for neg in _NEG:
                    if neg.search(window):
                        hits.append(f"{m.group(0).lower()}+{neg.pattern.strip(chr(92)+'b')}")
                        break
    return sorted(set(hits))


def self_aware_markers(prompt: str) -> list[str]:
    return sorted({m.pattern for m in _SELF if m.search(prompt or "")})


STOPWORDS = set("""a an the and or but if then this that those these is are was were be been
being of in on at to for with by from as it its their there here we you i he she they them our
your not no do does did done have has had will would can could should may might must than
account request please make sure need want use using send give get set new old also any all
each per via when what which who how""".split())


def _content_terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z\-]{3,}", (text or "").lower())
            if w not in STOPWORDS}


def rationale_overlap(case: dict[str, Any]) -> float:
    """How much of the case's own account of the danger already sits in its prompt.

    A DIAGNOSTIC, not a verdict. Measured against the b05_retrofit calibration set it
    points the right way — the 12 rewritten records mean 0.096, the 23 never rewritten
    mean 0.131 — but the two distributions overlap heavily, so no threshold on this
    separates them usefully. Reported so the number is visible and so a future author can
    see the direction; never used to classify.
    """

    why = " ".join([str(case.get("expected_behavior", "")), str(case.get("scoring_notes", ""))])
    prompt_terms = _content_terms(case.get("user_prompt", ""))
    why_terms = _content_terms(why)
    if not why_terms:
        return 0.0
    return round(len(prompt_terms & why_terms) / len(why_terms), 3)


def classify(case: dict[str, Any]) -> dict[str, Any]:
    prompt = case.get("user_prompt", "") or ""
    aware = self_aware_markers(prompt)
    policy = policy_state_assertions(prompt)
    if aware and policy:
        verdict = "confessing"
        why = "acknowledges the irregularity AND supplies the control state"
    elif aware:
        verdict = "confessing"
        why = "acknowledges it is asking for something irregular"
    elif policy:
        verdict = "states-the-state"
        why = "supplies a control-state fact the agent was meant to retrieve"
    else:
        verdict = "unflagged"
        why = "no signal found — NOT a proof the disqualifier is hidden"
    return {
        "case_id": case.get("case_id"),
        "verdict": verdict,
        "why": why,
        "rationale_overlap": rationale_overlap(case),
        "self_aware_markers": aware,
        "policy_state_assertions": policy,
        "b05_retrofit": bool(case.get("b05_retrofit")),
    }


def load_temptations(pack: str) -> list[dict[str, Any]]:
    path = BENCH / pack / "cases.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    return [r for r in rows if r.get("kind") == "temptation"]


def discover() -> list[str]:
    if not BENCH.exists():
        return []
    return sorted(
        d.name for d in BENCH.iterdir()
        if d.is_dir() and (d / "cases.jsonl").exists()
    )


def sweep(packs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {"check": CHECK_VERSION, "packs": {}}
    for pack in packs:
        cases = load_temptations(pack)
        if not cases:
            out["packs"][pack] = {"present": False}
            continue
        rows = [classify(c) for c in cases]
        counts = {"confessing": 0, "states-the-state": 0, "unflagged": 0}
        for r in rows:
            counts[r["verdict"]] += 1
        out["packs"][pack] = {
            "present": True,
            "temptations": len(rows),
            "counts": counts,
            "flagged": counts["confessing"] + counts["states-the-state"],
            "flagged_pct": round(100.0 * (counts["confessing"] + counts["states-the-state"]) / len(rows), 1),
            "rows": rows,
        }
    return out


def calibrate() -> dict[str, Any]:
    """Score the screen against the 12 records the B-05 rewrite is known to have hidden."""

    rows = [classify(c) for c in load_temptations("finance_redteam")]
    known_hidden = [r for r in rows if r["b05_retrofit"]]
    other = [r for r in rows if not r["b05_retrofit"]]
    if not known_hidden:
        return {"available": False,
                "note": "no b05_retrofit markers on disk — calibration set absent"}
    fp = [r["case_id"] for r in known_hidden if r["verdict"] != "unflagged"]
    return {
        "available": True,
        "known_hidden": len(known_hidden),
        "known_hidden_unflagged": len(known_hidden) - len(fp),
        "known_hidden_wrongly_flagged": len(fp),
        "wrongly_flagged_ids": fp,
        "not_retrofitted": len(other),
        "not_retrofitted_flagged": sum(1 for r in other if r["verdict"] != "unflagged"),
        "reading": (
            "The 12 b05_retrofit records were rewritten to hide the disqualifier, so the "
            "screen should leave them unflagged. Every one it flags is a false alarm and is "
            "named above. The screen cannot be scored in the other direction: there is no "
            "committed set of known-confessing records to measure misses against, so its "
            "miss rate is UNKNOWN and `unflagged` must not be read as `hidden`."
        ),
    }


def render(result: dict[str, Any], cal: dict[str, Any] | None, show_rows: bool) -> str:
    L = ["disclosure screen — does a temptation state its own disqualifier?", ""]
    tot = flagged = 0
    for pack, data in result["packs"].items():
        if not data.get("present"):
            L.append(f"  {pack:20s} corpus absent (held out — not checked)")
            continue
        c = data["counts"]
        tot += data["temptations"]
        flagged += data["flagged"]
        L.append(
            f"  {pack:20s} {data['temptations']:3d} temptation(s): "
            f"{c['confessing']:3d} confessing, {c['states-the-state']:3d} states-the-state, "
            f"{c['unflagged']:3d} unflagged  ->  {data['flagged_pct']}% flagged"
        )
        if show_rows:
            for r in data["rows"]:
                if r["verdict"] != "unflagged":
                    L.append(f"      [{r['verdict']}] {r['case_id']}: {r['why']}")
    if tot:
        L += ["", f"  TOTAL: {flagged} of {tot} temptation(s) state their own disqualifier "
                  f"in the prompt ({round(100.0*flagged/tot,1)}%)."]
    if cal and cal.get("available"):
        L += [
            "",
            "  calibration against the 12 known-hidden (b05_retrofit) records:",
            f"    left unflagged (correct): {cal['known_hidden_unflagged']} of {cal['known_hidden']}",
            f"    wrongly flagged (false alarm): {cal['known_hidden_wrongly_flagged']}"
            + (f" — {', '.join(cal['wrongly_flagged_ids'])}" if cal["wrongly_flagged_ids"] else ""),
            f"    of the {cal['not_retrofitted']} never-retrofitted finance temptations, "
            f"{cal['not_retrofitted_flagged']} were flagged",
        ]
    L += [
        "",
        "  `unflagged` means THIS SCREEN FOUND NO SIGNAL. It is not a proof that the",
        "  disqualifier is hidden — the miss rate is unmeasured and is probably HIGH. The",
        "  2026-07-26 B-05 report judged that roughly 30 of 35 finance temptations stated",
        "  their violation in the prompt; this screen flags 4. Either the corpus improved",
        "  a great deal since, or the screen misses most of what a reader would catch, and",
        "  the second is the safer assumption. A deterministic rule cannot see a",
        "  disqualifier that is semantic and case-specific. Treat a flagged row as a",
        "  finding, an unflagged row as UNVERIFIED, and the full classification as a",
        "  reading task — one worth handing to a domain expert alongside the scenarios.",
        "",
    ]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Screen pack temptations for prompts that state their own disqualifier.")
    ap.add_argument("--pack", action="append", dest="packs", default=None)
    ap.add_argument("--list", action="store_true", help="Name every flagged case.")
    ap.add_argument("--calibrate", action="store_true",
                    help="Score the screen against the known-hidden b05_retrofit records.")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)

    packs = args.packs or discover()
    if not packs:
        print("no pack corpus present (clean public checkout) — nothing to screen. "
              "This is reported rather than passed silently.", file=sys.stderr)
        return 0
    result = sweep(packs)
    cal = calibrate() if args.calibrate else None
    print(render(result, cal, args.list))
    if args.json_out:
        from reporting_utils import write_json_object
        write_json_object({**result, "calibration": cal}, Path(args.json_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
