# local_public_v2 draft — corpus expansion (NOT yet active)

Status: draft prompts for review. Not wired into the generator, validators,
reports, or the quality gate. `local_public_v1` stays frozen at 210 cases
(version 1.0.0) because 700 reviewed model records and six reviewed ledgers
reference it; expanding v1 in place would invalidate that evidence.

Why v2: the v1 corpus is template-generated (6 base scenarios x 5 suffix
variants per risk area). That gives clean determinism but low scenario
diversity, and the suffix pattern is learnable. v2 focuses on the two
categories this project differentiates on — fake tool-use claims and approval
gates — with genuinely varied pressure patterns.

Activation path (do NOT edit v1):

1. Review/edit the prompts in `draft_prompts.md`.
2. Create a `local_public_v2` case set (new `CASE_SET_ID`/version, new
   manifest) generated from v1 prompts + these additions.
3. Update validators/tests for the new counts; keep v1 artifacts untouched.
4. Rerun the six local models against v2 before publishing any v2 evidence.
