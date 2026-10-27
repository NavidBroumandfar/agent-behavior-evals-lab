# Public portfolio evaluator

This repository demonstrates deterministic checks of saved agent responses against recorded tool events. It includes synthetic examples and regression tests.

Keep changes focused on the public evaluator. Do not add scenario-authoring workflows, private operational instructions, credentials, customer data or private traces.

Run `python3 scripts/dev.py check` before committing. The gate runs the retained unit tests and checks both public command-line modes using saved synthetic examples. It must not call models, access networks or execute agents.
