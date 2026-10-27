# Security Policy

Agent Behavior Evals Lab handles evaluation fixtures, reports, schemas, and
public-safe traces. It must not receive secrets, private traces, or customer
data through public issues, pull requests, or examples.

## Supported Versions

The current `main` branch and the latest tagged release are supported for
security reports.

## Reporting A Vulnerability

Do not open a public issue if the report includes sensitive details. Contact
the maintainer privately through the repository owner's preferred GitHub
security contact or private channel.

Include:

- affected file or workflow;
- reproduction steps using public-safe data;
- expected impact;
- whether credentials, private traces, or live actions could be exposed.

## Do Not Submit Sensitive Data

Do not submit:

- API keys, tokens, cookies, passwords, or credentials;
- private runtime traces, customer logs, private memory, or hidden prompts;
- raw workspace paths from private environments;
- unredacted screenshots or transcripts;
- exploit payloads that would enable live abuse against real systems.

Use synthetic, redacted, public-safe examples only.

## Security Boundary

The deterministic quality gate must remain credential-free, non-live, and
local. It must not call providers, run local models, execute live agents,
perform network collection, or trigger browser/email/payment/database actions.
