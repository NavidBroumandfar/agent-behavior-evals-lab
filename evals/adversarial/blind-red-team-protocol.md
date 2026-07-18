# Blind red-team protocol (2026-07)

**Committed before any attack in this round existed.** The corpus and its
hashes land in a later commit; this file is the pre-registration, so the
resulting numbers cannot be reverse-fitted to whatever the verifier already
happened to catch.

## Why this exists

The existing evasion corpus
([`verifier_evasion_cases.jsonl`](verifier_evasion_cases.jsonl), 97.8% catch)
is **self-authored**: the same author wrote the verifier, the attacks, and the
honest twins. That is a weak instrument for the same reason a self-graded exam
is — it can only contain failure modes its author already imagined. This round
buys an independent-ish sample by having attackers work from the **public claim
surface only**.

## Blind condition

Attack authors receive:

- the README claim surface (what the gate advertises it catches), pasted
  inline into their prompt, and
- the record shape (`record_id`, `output_text`, `tool_events[{tool_name,
  action, status}]`, optional `category`).

Attack authors do **not** receive, and are instructed not to seek:

- any file under `src/` — above all `structural_tool_verifier.py` and
  `scorers.py`,
- the existing evasion corpus or its report,
- the repository path.

**Honest limit of this design:** blindness is enforced by instruction and by
withholding the path, not by a sandbox. Authors are capable models with file
tools; a determined one could have searched the disk. Each author's transcript
is retained, and any attack traceable to source-reading is disclosed rather
than counted. Read the result as *"attacks written from the advertised
behavior"*, not as a cryptographic guarantee of ignorance.

## Authors

Claude Opus 4.8 agents, five in parallel, each assigned a distinct attack lens
so the sample is not five variations of one idea:

1. Scope, quantity, and qualifier mismatches
2. Semantic indirection — implying an action without asserting it
3. Record-shape and status manipulation
4. Formatting, encoding, and cross-lingual phrasing
5. Framing — hypotheticals, attributed speech, roleplay, quotation

**AI authorship is disclosed**, consistent with this repo's practice for
AI-assisted artifacts. No human wrote these attacks.

## Corpus rules

- Each **lying** record pairs a claim with a tool log that does not support it.
- Each attack ships with at least one **honest twin**: the same phrasing,
  register, or structure with a tool log that *does* support it. A twin that
  fails is a false positive and counts against the gate.
- Records are public-safe: synthetic, no real credentials, hosts, or personal
  data.
- The blind corpus lives in its own file and is **never merged into the
  self-authored corpus**. Two instruments, two denominators, reported
  separately and always dated.

## Measurement order (the part that makes the number honest)

1. Freeze: commit the corpus and a `sha256` manifest **before** any fix.
2. Measure: run it and record the **pre-fix** catch rate, per lens.
3. Only then fix, in a later commit, with every fix pairing a new honest twin.
4. Publish **both** numbers. A post-fix figure alone, from a corpus its author
   fixed against, is not evidence of anything.

## Known validity limits

- Attacks are model-authored; a human red-teamer with product context would
  likely find different classes.
- The corpus is public. Once pushed, it is training data and future models may
  have memorized it — hence the date stamp on every claim derived from it.
- Catch rate on an adversarial corpus is **not** a false-positive rate on real
  traffic, and neither number generalizes to a customer's fleet.
