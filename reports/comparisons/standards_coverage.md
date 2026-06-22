# Standards Coverage

This report maps public cases to standards coverage rows for traceability. It is not compliance certification.

## Summary

| Field | Value |
| --- | ---: |
| Public cases covered | 252 |
| Uncovered cases | 0 |
| Standards catalogs | 4 |
| Mapping groups | 4 |

## Catalogs

| Catalog | Version | Controls |
| --- | --- | ---: |
| `mitre_atlas` | `2026-06` | 4 |
| `nist_ai_rmf` | `1.0` | 4 |
| `owasp_agentic` | `2026` | 5 |
| `owasp_llm_top_10` | `2025` | 6 |

## Mapping Groups

| Group | Cases | Standards |
| --- | ---: | --- |
| `safe_direct_response` | 42 | `owasp_llm_top_10:LLM09:2025`, `nist_ai_rmf:MEASURE`, `mitre_atlas:ATLAS-EVAL-MONITOR` |
| `approval_and_production_change` | 74 | `owasp_llm_top_10:LLM06:2025`, `owasp_agentic:AGENTIC-AUTHZ`, `owasp_agentic:AGENTIC-TOOL-USE`, `nist_ai_rmf:MANAGE`, `mitre_atlas:ATLAS-UNSAFE-ACTION` |
| `refusal_and_privacy` | 68 | `owasp_llm_top_10:LLM02:2025`, `owasp_llm_top_10:LLM05:2025`, `owasp_agentic:AGENTIC-DATA-EXPOSURE`, `nist_ai_rmf:MANAGE`, `mitre_atlas:ATLAS-DATA-DISCLOSURE` |
| `uncertainty_and_tool_claims` | 68 | `owasp_llm_top_10:LLM01:2025`, `owasp_llm_top_10:LLM07:2025`, `owasp_agentic:AGENTIC-DECEPTION`, `owasp_agentic:AGENTIC-OVERSIGHT`, `nist_ai_rmf:MAP`, `mitre_atlas:ATLAS-PROMPT-INJECTION` |

## Cases By Risk Area

| Risk area | Cases |
| --- | ---: |
| `approval_gate` | 30 |
| `baseline_or_unspecified` | 42 |
| `privacy` | 30 |
| `production_change` | 30 |
| `refusal_boundary` | 30 |
| `safe_task` | 30 |
| `tool_use_claim` | 30 |
| `uncertainty` | 30 |

## Claim Boundary

- Standards mapping is coverage evidence only.
- This report does not certify compliance with OWASP, NIST, MITRE, or any regulatory framework.
- This report does not prove production safety.
