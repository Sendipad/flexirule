# Canonical Condition Evaluation — Shared Contract and Handoff

**Status:** Source-reviewed implementation plan only. No application behavior was changed and no implementation/test result is claimed.

**Repository:** [Sendipad/flexirule](https://github.com/Sendipad/flexirule)  
**Source review:** Current develop source fetched on 2026-10-26.  
**Task plans:** [Backend implementation plan](backend-implementation-plan.md) · [Frontend implementation plan](frontend-implementation-plan.md)

## 1. Why this work is required

The current source has multiple paths that define conditions differently:

- [core/compiler.py](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/core/compiler.py) turns older condition trees into Python source. Unsupported nodes can disappear and an empty compiled result can become True. Its operator map, labels and supported operators do not fully agree.
- [core/evaluator.py](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/core/evaluator.py) evaluates a separate JSON condition format, has its own operator table, and applies sibling joins differently from Python operator precedence.
- [core/condition_payload.py](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/core/condition_payload.py) accepts multiple legacy wrappers, serialized trees and raw strings.
- [Rule.validate()/compile_conditions()](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/doctype/rule/rule.py), [ConditionHandler](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/core/action_handlers/condition.py), [SubRuleHandler](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/core/action_handlers/sub_rule.py), and [AssignmentHandler](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/core/action_handlers/assignment.py) consume or compile conditions differently. Assignment guard compilation currently catches an exception and returns an empty expression, which can turn a broken guard into “run unconditionally.”
- [ValueResolver / CollectionResolver](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/core/value_resolver.py) uses the legacy ConditionEvaluator for row predicates.
- [ConditionBuilder.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/condition_builder/ConditionBuilder.vue) edits the legacy op/conditions tree; [SimpleCondition.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/condition_builder/SimpleCondition.vue) uses a field picker for the left operand and FlexValue for the right, and includes static operator fallbacks.

Existing analysis is useful but is not implementation evidence: [PR #412 — condition architecture audit](https://github.com/Sendipad/flexirule/pull/412), [PR #434 — canonical condition/FlexValue proposal](https://github.com/Sendipad/flexirule/pull/434), [PR #438 — focused FlexValue backend-contract handoff](https://github.com/Sendipad/flexirule/pull/438), and [PR #433 — benchmark/parity investigation](https://github.com/Sendipad/flexirule/pull/433). PR #433 recorded a known semantic disagreement around has_changed, so its timing results are not proof of full semantic parity.

## 2. Frozen public contract for implementation

The following is the shared wire contract for both task plans. Any deviation must be raised in review and applied to backend, frontend and fixtures together; do not introduce a second schema.

### 2.1 Condition envelope

A complete canonical condition is JSON-serializable and uses this envelope:

~~~json
{
  "schema": "flexirule.condition",
  "version": 1,
  "root": {
    "type": "group",
    "operator": "and",
    "children": [
      {
        "type": "comparison",
        "operator": "==",
        "left": {
          "mode": "variable",
          "path": { "scope": "doc", "segments": ["status"] }
        },
        "right": {
          "mode": "static",
          "value_type": "string",
          "value": "Open"
        }
      }
    ]
  }
}
~~~

- Rule trigger condition storage contains the envelope above.
- The Condition action’s existing config field contains the envelope itself; the UI must not add another condition wrapper. Legacy condition_json is read only by the explicit legacy adapter.
- Assignment run-if guards and nested row predicates use the same schema. Their owning field may be absent for a documented “no guard” state; a present malformed condition is never treated as absent.
- UI IDs are ephemeral and must be stripped before persistence.
- Saved JSON is the source of truth. Do not persist generated Python or a second normalized/compiled JSON tree.

### 2.2 Canonical nodes and operands

**Group:** type = group, operator = and/or, non-empty children. All siblings in a group use the same operator; express mixed logic using nested groups. Preserve child order.

**Comparison:** type = comparison, canonical operator, left and—except where the operator is explicitly unary—right. Both operands are FlexValue nodes. Operator metadata defines arity, supported value types, Fieldtype constraints, link policy and missing/null behavior.

**Collection predicate:** type = collection_predicate, quantifier = any/all/none, a variable/path source, validated local alias as, and nested where condition node. The initial canonical contract permits only a variable/path as the collection source. The row alias is scoped to that predicate and its descendants.

**FlexValue union:**

- **Static:** mode = static with value_type and value. Preserve string, integer, decimal, boolean, null, date, datetime, time, list and object distinctions. Decimal values are serialized as strings and converted to Decimal at the typed runtime boundary.
- **Variable:** mode = variable with path.scope and path.segments. Canonical scopes are doc, old_doc, vars, item, loop, row, caller, rule, doctype, and a locally declared collection alias. No implicit “try doc, then vars” lookup in canonical mode.
- **Resolver:** mode = resolver with family, operation and config. Config is operation-specific, backend-owned and recursively validated. Resolver output type/capability must be declared; no general resolver is automatically safe as a condition operand.
- **Template:** mode = template with typed text/value segments, where value segments recursively contain a valid FlexValue. No raw Python/Jinja expression is allowed in canonical conditions.

Reject unknown keys, variants, scopes, operators, operations and schema versions. Do not infer a node or FlexValue kind merely from the keys that happen to be present.

### 2.3 Semantic decisions for v1

1. A group evaluates left-to-right with strict short-circuit AND/OR. Mixed logic requires nested groups; no implicit Python precedence.
2. An absent trigger filter means no trigger filter. A missing assignment guard means unconditional assignment. A Condition action must be configured before activation. Any present empty group, malformed tree or failed conversion is invalid; it cannot mean True.
3. Preserve a present null separately from a missing path. is_set returns false and is_not_set true for missing/null/empty string; whitespace is set. Other operators encountering a missing runtime value raise a typed evaluation error. A present null can be compared to a typed null; empty string remains distinct. False is never coerced to numeric zero.
4. Canonical operators use one server-owned registry. V1 keeps typed equality/order, membership (in, not in), literal substring (contains, not_contains), presence/emptiness, length comparisons, and metadata operators (is_submittable, has_field) with explicit arity/type contracts.
5. V1 does not include regex, has_changed, identity operators (is/is not), unknown operator fallbacks, or generated-Python condition expressions. like/not like are legacy tokens with ambiguous historical behavior: inventory them; do not auto-rewrite them unless the migration decision is explicitly approved. Legacy not_in is a migration alias for canonical not in, not a second runtime token.
6. Do not infer a Link tuple from any two-item list. Legacy link tuples can be converted only when left-side DocType metadata proves the tuple target matches; otherwise emit a migration issue.
7. Invalid schema/operator/resolver configuration is a validation failure. A runtime resolution/type/configuration error is a distinct typed error—not a normal false condition and never a true/pass-through result. Consumer adapters may apply existing Frappe lifecycle/on-error policy, but must retain a distinct diagnostic; trigger errors fail closed (rule does not run) and are logged as errors, not reported as an ordinary false filter.
8. Reuse the existing collection row guard of 10,000 rows as one shared constant. Add bounded work limits for AST depth, node count, resolver recursion, path segments and template segments; define them once in the backend contract and test their boundaries. Never silently truncate collections.

### 2.4 Server-owned metadata

The backend is authoritative for operators, arity, operand types, Fieldtype applicability, resolver family/operation config, output type, condition_operand_allowed, required resolver level/capability, allowed scopes and resource limits. Extend the existing authenticated builder API pattern (currently get_operator_config) with a versioned condition-contract DTO. Keep the current endpoint compatible while legacy consumers still use it. Frontend metadata is for UX, not security.

Resolver families/operations default to **not allowed as condition operands** unless the backend registry explicitly sets condition_operand_allowed = true, output type, required configuration, permission policy and regression tests. In particular, lookup/database-backed resolvers must have a verified permission and query-limit policy before being enabled.

## 3. Architecture and implementation ordering

The backend owns validation and runtime semantics; the frontend owns interaction, not condition meaning.

1. **Contract first:** contract DTO, strict FlexValue/condition validation, canonical fixtures and stable path-specific diagnostics.
2. **Backend evaluator:** typed context access, comparator registry, short-circuit AST traversal and scoped collection predicates. No eval/exec/frappe.safe_eval for canonical conditions.
3. **Frontend builder:** load/edit the canonical AST, use the contract DTO for operator/resolver options, and round-trip with no semantic loss.
4. **Consumer adapters:** Rule trigger gate, Condition action routing, callable Sub-Rule gate, assignment run-if guard and CollectionResolver all use the same evaluator.
5. **Legacy inventory/migration:** convert only deterministic payloads. Ambiguous legacy conditions are reported for explicit repair, not silently rewritten on load.
6. **Deprecation/performance:** remove generated-Python and old evaluator routes only after consumer parity, migration and cache tests pass. Any optimization is ephemeral/rebuildable and derived from canonical JSON; no persisted compiled condition.

The frontend and backend tasks may begin in parallel against this contract, but final runtime/UI integration is not merge-ready until both sides pass shared fixture round-trip tests. The backend plan is responsible for inspecting and reconciling [PR #438](https://github.com/Sendipad/flexirule/pull/438): it is a focused task brief, so do not create a competing FlexValue contract implementation in parallel. Reuse its branch/work where useful or supersede it explicitly.



## 5. Prior architecture report and related implementation evidence

The full upstream architecture plan from merged PR #434 is now included in this branch at [canonical-condition-flexvalue-implementation-plan.md](../canonical-condition-flexvalue-implementation-plan.md). It is the detailed background report; this directory's README freezes the cross-task v1 wire contract, and the backend/frontend files are the actionable Jules task plans. If a detail differs, stop and reconcile it before coding rather than silently diverging.

Relevant existing work to inspect before implementation:

- [PR #416 — condition tree validation/operator registry/evaluator prototype](https://github.com/Sendipad/flexirule/pull/416): draft implementation with useful source and tests, but not merge-ready. Its report/PR says generated-Python legacy paths remain and several compatibility gates are outstanding. Reuse verified pieces selectively; do not treat the draft as the finished canonical evaluator or merge it wholesale.
- [PR #433 — benchmark and parity investigation](https://github.com/Sendipad/flexirule/pull/433): includes `reports/condition-backend-comparison-benchmark.md`, raw `reports/condition_benchmark_results.json`, benchmark runner and tests. The recorded correctness gate failed (12 of 13 fixtures agreed; `has_changed` disagreed), so benchmark numbers are not a semantic approval or a release gate pass. Benchmark source branch/commit were recorded as “not captured”; rerun on a pinned source SHA after semantic parity is resolved.
- [PR #412 — condition architecture audit](https://github.com/Sendipad/flexirule/pull/412): use as supporting source inventory, not as implementation evidence.
- [PR #438 — canonical FlexValue backend contract task](https://github.com/Sendipad/flexirule/pull/438): task brief only at last inspection; reconcile its current state before creating overlapping contract code.

## 6. Repository guardrails

- Follow [AGENTS.md](https://github.com/Sendipad/flexirule/blob/develop/AGENTS.md): use established action-handler/contract patterns, keep state out of shared handler singletons, preserve mutation policy, and inspect cache invalidation paths.
- Reuse Frappe Document.validate, DocType metadata, existing whitelisted builder API/access checks, FrappeTestCase, FieldResolver, and existing CompiledResolver/ValueResolver operations where their canonical input has been validated. Do not replace those with a second parallel framework.
- Query Records/Frappe filters are a separate query contract; do not convert them to condition predicates by assumption. Assignment mutation operators are separate from condition comparison operators.
- This PR and these files are planning-only. No application code, database patch, DocType field, dependency, benchmark or test result is introduced by this PR.
