# Backend Jules Task — Canonical Condition Evaluation

**Task type:** Backend implementation plan for FlexiRule.  
**Depends on:** [Shared contract and handoff](README.md).  
**Baseline:** Primary specification PR #460 (`reports/condition-evaluation/README.md`).

---

## Objective

Implement an authoritative, typed condition contract and evaluator, then migrate every backend condition consumer to that single runtime. New canonical conditions must never be compiled into Python source. Invalid conditions must never become equality comparisons, True, False, or an empty “run unconditionally” guard through fallback behavior.

Keep this task backend-only. Use the shared static JSON fixture contract (`flexirule/ruleflow/fixtures/condition_contract_fixtures.json`) so the independent frontend task can integrate against it.

---

## Scope Boundaries & Safety Principles

1. **Zero Runtime Modifications in Task 0:** Task 0 freezes contracts and creates static JSON fixtures only. Implementation steps below apply to subsequent backend execution tasks.
2. **Single Server-Owned Registry:** The backend is authoritative for operator IDs, arity, operand types, field applicability, and resolver capabilities.
3. **Fail-Closed Policy:** Missing path variables in binary comparisons, invalid schema/version formats, unknown operators, and execution errors MUST fail closed. An invalid condition payload or evaluation error is never converted into an ordinary `false` or `true` result.
4. **Absent vs Empty/Malformed Boundary:**
   - Missing/omitted or `null` consumer condition field = Absent optional guard (Pass / Unconditional execution).
   - Present payload with `children: []`, invalid JSON, unknown schema/version, or malformed node/operator = Invalid condition (Fails validation / Error).

---

## Detailed Implementation Stages for Subsequent Backend Tasks

### Stage B0 — Reconcile Active Work and Expose Server Contract DTO
1. Inspect PR #438 status; incorporate or supersede its branch without creating parallel FlexValue contract implementations.
2. Adopt the exact `flexirule.condition` v1 envelope, canonical AST nodes (`group`, `comparison`, `collection_predicate`), and FlexValue union from `reports/condition-evaluation/README.md`.
3. Add `flexirule/ruleflow/core/condition_registry.py` maintaining authoritative canonical operators (`equals`, `not_equals`, `greater_than`, `less_than`, `greater_than_or_equals`, `less_than_or_equals`, `is_one_of`, `is_not_one_of`, `contains_text`, `is_set`, `is_not_set`, `is_empty`, `is_not_empty`, `is_submittable`, `has_field`).
4. Expose `@frappe.whitelist()` API method `flexirule.ruleflow.api.get_condition_contract_dto` returning versioned DTO metadata for UI controls.
5. Add unit tests reading `flexirule/ruleflow/fixtures/condition_contract_fixtures.json` to verify DTO generation and AST payload parsing.

**Gate B0:** DTO endpoint is whitelisted; contract parsing rejects bad schema/versions; no duplicate operator registry is introduced.

---

### Stage B1 — Strict FlexValue Contract and Resolver Boundary
1. Implement `flexirule/ruleflow/core/flexvalue_contract.py` enforcing mode discriminants (`static`, `variable`, `resolver`, `template`).
2. Add support for typed document references (`value_type: "document_reference"`, `{ "doctype": "...", "name": "..." }`).
3. Enforce strict list typing: two-item lists are evaluated as ordinary lists unless left-operand metadata in legacy migration adapters proves otherwise.
4. Enforce resolver capability policy (`condition_operand_allowed = true`). Database-backed resolvers default to disallowed unless explicit permission and resource limit policies are set.

**Gate B1:** FlexValue nodes validate mode and type boundaries; typed document references pass validation without executing unvetted database queries.

---

### Stage B2 — AST Evaluator Engine
1. Implement `flexirule/ruleflow/core/condition_evaluator_v2.py` implementing short-circuit AND/OR group traversal and typed operand evaluation.
2. Implement strict missing vs null handling:
   - Unary `is_set` / `is_not_set` handle missing paths safely.
   - Binary operators encountering missing paths raise `ERR_MISSING_VARIABLE_PATH`.
3. Implement collection predicates (`quantifier: "any" | "all" | "none"`) with scoped row aliases and a 10,000-row safety guard (`ERR_COLLECTION_ROW_GUARD_EXCEEDED`).

**Gate B2:** Evaluator passes all 20+ shared contract fixtures in `condition_contract_fixtures.json`; short-circuiting and row limits pass unit tests.

---

### Stage B3 — Sequential Consumer Migration
Migrate backend consumers one by one with dedicated verification gates per consumer:

1. **Rule Trigger Conditions (`Rule.validate()` & `Rule.trigger_event`):** Update trigger evaluation to use `ConditionEvaluatorV2`. Verify that absent trigger filter passes, valid condition evaluates correctly, and malformed trigger fails closed (rule does not run).
2. **Condition Action Handler (`ConditionHandler`):** Update condition action execution to evaluate canonical AST config. Ensure Condition action requires a valid condition payload before rule activation.
3. **Sub-Rule Eligibility Gate (`SubRuleHandler`):** Update sub-rule activation gates to evaluate caller/target metadata via canonical evaluator.
4. **Assignment Guard (`AssignmentHandler`):** Update run-if guard logic (`_compile_when_expression`). An invalid guard payload MUST raise a validation/execution error and MUST NOT fall back to unconditional execution.
5. **Collection Resolver (`CollectionResolver`):** Update row predicate evaluation to use `ConditionEvaluatorV2`.

**Gate B3:** Every condition consumer uses `ConditionEvaluatorV2`; invalid guards raise errors rather than executing unconditionally; integration tests pass for all 5 consumers.

---

### Stage B4 — Legacy Inventory and Migration Adapter
1. Build deterministic migration adapter in `flexirule/ruleflow/core/condition_migration.py`.
2. Convert standard legacy tokens (`==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`) deterministically.
3. Emit explicit migration diagnostics (`MIGRATE_NON_CANONICAL_OPERATOR_*`) for unclassified or ambiguous legacy tokens (`like`, `not like`, `regex`, `contains`, `not_contains`, `length_gt`, `has_changed`, `is`, `is not`).
4. Provide a migration reporting utility to scan existing `tabRule` and `tabRule Action` records without mutating them.

**Gate B4:** Legacy rules convert deterministically or emit precise migration diagnostics; legacy scanning report generates clean output across test sites.

---

### Stage B5 — Deprecation, Cleanup, and Performance Benchmarking
1. Deprecate Python source generation paths in `ConditionCompiler`.
2. Verify AST evaluation performance against previous benchmarks.
3. Remove legacy fallback routes only after parity tests pass across all consumers.

**Gate B5:** All backend tests pass; Python source generation is deprecated; performance meets or exceeds AST benchmark targets.
