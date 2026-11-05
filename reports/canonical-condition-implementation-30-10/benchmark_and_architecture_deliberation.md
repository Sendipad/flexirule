# War Room Deliberation & Architectural Decision Record: Contract Remediation & Validation Lifecycle

**Date:** October 30, 2026
**Topic:** Remediation of Contract Discrepancies, Sealed Plan Execution Strategy, and Integration with Frappe Validation Lifecycle
**Status:** Approved Architectural Directive (PR #469 Contract Aligned)

---

## Executive Operational Summary

The war room conducted a thorough review of canonical condition architecture, remediating discrepancies to align strictly with PR #469's authoritative backend contract (`flexirule/ruleflow/core/condition_contract.py`, `flexvalue_contract.py`, and `condition_evaluator.py`).

### Key Decisions & Corrections:
1. **Authoritative Schema Contract:** All canonical condition payloads MUST use PR #469's contract representations:
   - Group Node: `{"type": "group", "operator": "and"|"or", "children": [...]}`
   - Comparison Node: `{"type": "comparison", "operator": "eq"|"ne"|..., "left": {...}, "right": {...}}`
   - Collection Predicate: `{"type": "collection_predicate", "quantifier": "all"|"any"|"none", "source": {...}, "as": "item", "where": {...}}`
   - FlexValue Variable: `{"mode": "variable", "path": {"scope": "doc"|"parent"|"root"|"local"|"system"|"env", "segments": ["status"]}}`
2. **Authoritative Limits:** System enforces `CONDITION_LIMITS`:
   - Depth: `32`
   - Nodes: `1,000`
   - Path Segments: `32`
   - Payload Bytes: `1,000,000` (1 MB)
   - Collection Rows: `10,000`
3. **Sealed Artifact Integrity:** Execution relies on `_PreparedCanonicalCondition` carrying process-local seals (`_seal`), SHA-256 condition digests, evaluator versions, and resolver fingerprints. Unsealed plan objects or caching by Python `id()` are strictly prohibited.
4. **Validation Lifecycle Integration:** Conceptual validation stages (Save-Time, Activation-Time, Runtime) are integrated into existing Frappe `Rule.validate()` and `validation_service` methods rather than creating parallel duplicate validators.

---

## Detailed Deliberation Transcript

### Round 4: Contract Discrepancy Remediation

**The Devil's Advocate:**
> "The earlier prototype proposal introduced incompatible AST identifiers (`node_type`, `rules`, `collection_field`, `field_path`) and invented lower limits (10 depth, 100 nodes, 64KB payload). This creates schema fragmentation!
>
> Furthermore, the prototype resolved document attributes using raw `getattr()`, bypassing `safe_read_segment()`, and silently coerced invalid business numbers to `Decimal(0)`. A malformed numeric input in financial or approval rules must throw a fast-failing `ConditionEvaluationError`, not silently become zero!"

**The Engineer:**
> "I agree completely. We discard the prototype schema and align 100% with PR #469's contract:
> - Use `safe_read_segment()` for safe boundary-checked Document attribute access.
> - Fail fast on malformed numeric inputs or unrecognized FlexValue modes.
> - Enforce `CONDITION_LIMITS` strictly."

---

### Round 5: The Validation Lifecycle Architecture

**The Lazy Developer:**
> "We need to ensure users can save draft rules without being blocked by incomplete configurations, while preventing incomplete rules from ever executing."

**The Specialist Expert:**
> "The conceptual validation responsibilities are integrated into the existing Frappe Rule lifecycle:
>
> - **Save-Time (`Rule.validate()` -> `validate_rule_definition(mode="draft")`):**
>   Validates AST syntax, operator IDs, FlexValue modes, and `CONDITION_LIMITS`. Allows incomplete draft configurations for authoring convenience.
> - **Activation-Time (`Rule.validate()` -> `validate_rule_definition(mode="full")`):**
>   Enforced when `is_active = 1`. Validates field existence against DocType metadata (`frappe.get_meta()`) and verifies required action configurations.
> - **Runtime Execution Preflight:**
>   Executes via `prepare_condition()` and `evaluate_prepared_condition()`. Any endpoint attempting to run an inactive or draft rule MUST perform full execution preflight prior to executing modifications."

---

### Round 6: Performance Architecture & Sealed Artifact Trust

**The Devil's Advocate:**
> "The previous performance proposal suggested an unsealed `FastPreparedPlan` dataclass. Anyone could instantiate that dataclass, bypassing validation seals, semantics versions, and resolver fingerprints!
>
> PR #469 already has a sealed artifact: `_PreparedCanonicalCondition`. It carries `plan`, `doctype`, `condition_digest`, `semantics_version`, `evaluator_version`, `resolver_fingerprint`, and an unpicklable `_seal` object."

**The Engineer:**
> "Correct. `_PreparedCanonicalCondition` is the trusted execution artifact. `evaluate_condition()` accepts pre-compiled `_PreparedCanonicalCondition` objects directly, allowing `RuleEngine` to re-use sealed prepared conditions across action steps within an execution plan at maximum velocity (**7.5–16.5 µs/op**)."

---

## Architectural Verdict

1. **Schema Compliance:** Strict adherence to PR #469 contract schemas and `CONDITION_LIMITS`.
2. **Integrated Lifecycle:** Validation stages embedded into `Rule.validate()` and `validation_service`.
3. **Sealed Artifact Trust:** `_PreparedCanonicalCondition` remains the sole trusted execution artifact.
