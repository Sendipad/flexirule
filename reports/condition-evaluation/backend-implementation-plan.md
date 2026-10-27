# Backend Jules Task — Canonical Condition Evaluation

**Task type:** Backend implementation plan for FlexiRule.  
**Depends on:** [Shared contract and handoff](README.md).  
**Baseline:** Primary specification PR #460 (`reports/condition-evaluation/README.md`).

## Objective

Implement an authoritative, typed condition contract and evaluator, then migrate every backend condition consumer to that single runtime. New canonical conditions must never be compiled into Python source. Invalid conditions must never become equality comparisons, True, False, or an empty “run unconditionally” guard through fallback behavior.

Keep this task backend-only. Use the shared static JSON fixture contract (`flexirule/ruleflow/fixtures/condition_contract_fixtures.json`) so the independent frontend task can integrate against it.

## Scope Boundaries & Safety Principles

1. **Zero Runtime Modifications in Task 0:** Task 0 freezes contracts and creates static JSON fixtures only. Implementation steps below apply to subsequent backend execution tasks.
2. **Single Server-Owned Registry:** The backend is authoritative for operator IDs, arity, operand types, field applicability, and resolver capabilities.
3. **Fail-Closed Policy:** Missing path variables in binary comparisons, invalid schema/version formats, unknown operators, and execution errors MUST fail closed. An invalid condition payload or evaluation error is never converted into an ordinary `false` or `true` result.
4. **Absent vs Empty/Malformed Boundary:**
   - Missing/omitted or `null` consumer condition field = Absent optional guard (Pass / Unconditional execution).
   - Present payload with `children: []`, invalid JSON, unknown schema/version, or malformed node/operator = Invalid condition (Fails validation / Error).

---

## Detailed Implementation Stages for Subsequent Backend Task

### Stage B0 — Reconcile active work and freeze server contract

1. Reconcile PR #438 and adopt the exact `flexirule.condition` v1 envelope and FlexValue union specified in `reports/condition-evaluation/README.md`.
2. Consume `flexirule/ruleflow/fixtures/condition_contract_fixtures.json` for backend unit testing.
3. Build the backend-owned registry for canonical operators (`equals`, `not_equals`, `greater_than`, `less_than`, `greater_than_or_equals`, `less_than_or_equals`, `is_one_of`, `is_not_one_of`, `contains_text`, `is_set`, `is_not_set`, `is_empty`, `is_not_empty`, `is_submittable`, `has_field`).
4. Implement operator metadata endpoints returning translatable labels, capabilities, and field applicability.

### Stage B1 — Strict FlexValue contract and resolver boundary

1. Add `flexirule/ruleflow/core/flexvalue_contract.py` enforcing strict mode discriminants (`static`, `variable`, `resolver`, `template`).
2. Add support for typed document references (`value_type: "document_reference"`, carrying `{ "doctype": "...", "name": "..." }`).
3. Enforce strict list typing: two-item lists are evaluated as ordinary lists unless left-operand metadata in legacy migration adapters proves otherwise.
4. Enforce resolver capability policy (`condition_operand_allowed = true`). Database-backed resolvers default to disallowed unless explicit permission and resource limit policies are set.

### Stage B2 — AST Evaluator Engine

1. Add `flexirule/ruleflow/core/condition_evaluator_v2.py` implementing short-circuit AND/OR group traversal and typed operand evaluation.
2. Implement strict missing vs null handling:
   - Unary `is_set` / `is_not_set` handle missing paths safely.
   - Binary operators encountering missing paths raise `ERR_MISSING_VARIABLE_PATH`.
3. Support collection predicates (`quantifier: "any" | "all" | "none"`) with scoped row aliases and a 10,000-row safety guard.

### Stage B3 — Consumer Migration

1. Migrate Rule trigger conditions, Condition action handler, Sub-Rule gate, Assignment run-if guard, and CollectionResolver to the canonical evaluator.
2. Ensure an invalid Assignment guard fails execution rather than evaluating unconditionally.

### Stage B4 — Legacy Inventory and Migration Adapter

1. Build deterministic migration adapter for `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`, `not_in`.
2. Generate explicit migration diagnostics (`MIGRATE_NON_CANONICAL_OPERATOR_*`) for ambiguous tokens (`like`, `not like`, `regex`, `has_changed`, `is`, `is not`).
