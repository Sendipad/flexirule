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

### 2.1 Direct canonical condition node (no persisted envelope)

A complete condition payload is **one condition node itself**. Do not wrap it in `schema`, `version`, or `root` properties. The node's `type` discriminant identifies its kind.

A root may be a `comparison`, `group`, or `collection_predicate`. A group is needed only when combining predicates or explicitly grouping logic. For example, this root group expresses “status is Open AND (total is greater than 1000 OR is_priority is true)”:

~~~json
{
  "type": "group",
  "operator": "and",
  "children": [
    {
      "type": "comparison",
      "operator": "eq",
      "left": {
        "mode": "variable",
        "path": { "scope": "doc", "segments": ["status"] }
      },
      "right": {
        "mode": "static",
        "value_type": "string",
        "value": "Open"
      }
    },
    {
      "type": "group",
      "operator": "or",
      "children": [
        {
          "type": "comparison",
          "operator": "gt",
          "left": {
            "mode": "variable",
            "path": { "scope": "doc", "segments": ["grand_total"] }
          },
          "right": {
            "mode": "static",
            "value_type": "decimal",
            "value": "1000"
          }
        },
        {
          "type": "comparison",
          "operator": "eq",
          "left": {
            "mode": "variable",
            "path": { "scope": "doc", "segments": ["is_priority"] }
          },
          "right": {
            "mode": "static",
            "value_type": "boolean",
            "value": true
          }
        }
      ]
    }
  ]
}
~~~

A single root comparison is also valid and needs no enclosing group. Every persisted logical group has at least two direct children; children may be comparisons, nested groups, or collection predicates. Groups apply one `and` or `or` operator to their direct children. Mixed logic is represented with nested groups, never per-child joins.

Persistence boundaries:

- Rule trigger condition storage contains the node directly as JSON.
- The Condition action's existing config field contains the condition node itself; do not add an additional `condition`, `root`, or envelope wrapper. Legacy `condition_json` is read only through the explicit legacy adapter.
- Assignment run-if guards and nested row predicates use the same node contract. Their owning field may be absent for a documented “no guard” state; a present malformed condition is never treated as absent.
- UI IDs are ephemeral and must be stripped before persistence.
- Saved JSON is the source of truth. Do not persist generated Python or a second normalized/compiled JSON tree.
- Versioning of the authenticated contract API/DTO is independent from the saved condition payload and must not add version metadata around the node.

### 2.2 Canonical nodes and operands

**Group:** `type = "group"`, `operator = "and" | "or"`, and `children` containing at least two condition nodes. All direct children share the group's operator; express mixed logic using nested groups. Preserve child order. Do not serialize per-child `logical_operator`.

**Comparison:** `type = "comparison"`, a stable semantic operator ID, and left/right FlexValue operands unless the operator registry explicitly defines the operator as unary. Both operands use the same FlexValue union.

**Collection predicate:** `type = "collection_predicate"`, `quantifier = "any" | "all" | "none"`, a variable/path source, validated local alias `as`, and a `where` condition node. The `where` may be a single comparison/collection predicate or a valid group; do not wrap a single predicate in a one-child group. The initial contract permits only a variable/path as the collection source. The row alias is scoped to that predicate and its descendants.

**FlexValue union:**

- **Static:** `mode = "static"` with `value_type` and `value`. Preserve string, integer, decimal, boolean, null, date, datetime, time, list and object distinctions. Decimal values are serialized as strings and converted to Decimal at the typed runtime boundary.
- **Variable:** `mode = "variable"` with `path.scope` and `path.segments`. Canonical scopes are `doc`, `old_doc`, `vars`, `item`, `loop`, `row`, `caller`, `rule`, `doctype`, and a locally declared collection alias. No implicit “try doc, then vars” lookup in canonical mode.
- **Resolver:** `mode = "resolver"` with `family`, `operation` and `config`. Config is operation-specific, backend-owned and recursively validated. Resolver output type/capability must be declared; no general resolver is automatically safe as a condition operand.
- **Template:** `mode = "template"` with typed text/value segments, where value segments recursively contain a valid FlexValue. No raw Python/Jinja expression is allowed in canonical conditions.

The saved condition format has no envelope or payload version property. Reject unknown keys, node/FlexValue variants, scopes, operators, operations and resolver config. A payload with a canonical `type` discriminant but an unknown node type is invalid; do not retry it as a legacy payload or infer a kind merely from other keys.

### 2.3 Semantic decisions for the canonical contract

1. A group evaluates left-to-right with strict short-circuit AND/OR. Mixed logic requires nested groups; no implicit Python precedence.
2. An absent trigger filter means no trigger filter. A missing assignment guard means unconditional assignment. A Condition action must be configured before activation. Any present empty group, one-child canonical group, malformed tree or failed conversion is invalid; it cannot mean True. The frontend may collapse its own redundant one-child groups before serializing, while backend validation rejects a submitted canonical one-child group.
3. Preserve a present null separately from a missing path. `is_set` returns false and `is_not_set` true for missing/null/empty string; whitespace is set. Other operators encountering a missing runtime value raise a typed evaluation error. `is_null`/`is_not_null` test a present null value; a missing path remains a typed error. False is never coerced to numeric zero.
4. Use stable, lowercase semantic operator IDs, independent of Python syntax and labels. The proposed initial catalogue is:
   - Equality/order: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`.
   - Membership: `in`, `not_in`.
   - Literal, case-sensitive text matching: `contains`, `not_contains`, `starts_with`, `ends_with`.
   - Presence/null: `is_set`, `is_not_set`, `is_null`, `is_not_null`.
   - Emptiness: `is_empty`, `is_not_empty`.
   - Length: `length_eq`, `length_gt`, `length_gte`, `length_lt`, `length_lte`.
   - Frappe metadata: `has_field`, `is_submittable`, with explicit operand and context contracts.
   - `and`/`or` are group operators, and `any`/`all`/`none` are collection quantifiers; none of these are comparison IDs.
5. The registry defines arity, accepted value types, applicable Frappe Fieldtypes, output/operand type rules, aliases accepted only by migration, missing/null semantics and typed-error behavior. String operators are literal and case-sensitive; length operations require a supported sized value and numeric RHS. `is_empty`/`is_not_empty` apply only to explicitly supported empty-capable types; null is handled by null operators. Do not silently coerce booleans/numbers or arbitrary values to strings.
6. Do not include regex, `has_changed`, `is`/`is not`, unknown operator fallbacks, or generated-Python condition expressions in the canonical registry. Legacy `like`/`not like` have ambiguous historical behavior: inventory and report them; do not auto-rewrite them. Existing symbolic tokens such as `==`, `!=`, `>`, `>=`, `<`, `<=`, and `not in` may be mapped to the semantic IDs only by a deterministic, tested legacy migration. An operator rename or semantic change requires an explicit, idempotent migration and old-to-new fixtures; do not change meaning in place.
7. Do not infer a Link tuple from any two-item list. Legacy link tuples can be converted only when left-side DocType metadata proves the tuple target matches; otherwise emit a migration issue.
8. Invalid node/operator/resolver configuration is a validation failure. A runtime resolution/type/configuration error is a distinct typed error—not a normal false condition and never a true/pass-through result. Consumer adapters may apply existing Frappe lifecycle/on-error policy, but must retain a distinct diagnostic; trigger errors fail closed (rule does not run) and are logged as errors, not reported as an ordinary false filter.
9. Reuse the existing collection row guard of 10,000 rows as one shared constant. Add bounded work limits for tree depth, node count, resolver recursion, path segments and template segments; define them once in the backend contract and test their boundaries. Never silently truncate collections.

### 2.4 Server-owned metadata

The backend is authoritative for operator IDs, labels, arity, operand types, Fieldtype applicability, resolver family/operation config, output type, condition_operand_allowed, required resolver level/capability, allowed scopes and resource limits. Extend the existing authenticated builder API pattern (currently get_operator_config) with a versioned condition-contract DTO. This API/DTO version is independent from the unversioned persisted condition node; do not serialize a schema/version envelope around saved conditions. Keep the current endpoint compatible while legacy consumers still use it. Frontend metadata is for UX, not security.

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

The full upstream architecture plan from merged PR #434 is included in this branch at [canonical-condition-flexvalue-implementation-plan.md](../canonical-condition-flexvalue-implementation-plan.md) as historical rationale. Some of its original payload-envelope and symbolic-operator proposals are superseded by this review. This README is authoritative for the direct-node condition shape and semantic operator IDs; the backend/frontend files are the actionable task plans. If either task plan conflicts with this README, stop and reconcile before coding.

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
