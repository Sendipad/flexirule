# Backend Jules Task — Canonical Condition Evaluation

**Task type:** Backend implementation plan for FlexiRule.  
**Depends on:** [Shared contract and handoff](README.md).  
**Baseline:** inspect the actual PR base/source before coding; this is a plan, not a claim that implementation or tests have run.

## Objective

Implement an authoritative, typed condition contract and evaluator, then migrate every backend condition consumer to that single runtime. New canonical conditions must never be compiled into Python source. Invalid conditions must never become equality comparisons, True, False, or an empty “run unconditionally” guard through fallback behavior.

Keep this task backend-only. Use the shared fixture contract so the independent frontend task can integrate against it.

## Related reports and prototypes to inspect first

Before implementation, read the full [canonical condition + FlexValue implementation plan](../canonical-condition-flexvalue-implementation-plan.md). Inspect [PR #416](https://github.com/Sendipad/flexirule/pull/416) for the draft operator registry, evaluator integration and regression tests; reuse only after comparing its current head/diff against the shared v1 decisions. Inspect [PR #433](https://github.com/Sendipad/flexirule/pull/433), its [benchmark report](../condition-backend-comparison-benchmark.md), [raw benchmark data](../condition_benchmark_results.json), and benchmark tests. Its recorded correctness gate failed (12/13 fixtures agreed, with `has_changed` disagreement), and its source branch/SHA were not captured; rerun only after parity is fixed on a pinned commit. Do not merge PR #416 wholesale or cite PR #433 timing data as correctness evidence.

## Source-first review: confirmed current paths

Inspect current source and preserve the distinction between verified code behavior and prior reports:

- **core/compiler.py:** legacy ConditionCompiler emits Python source from op/conditions, left/op/right and collection nodes. Unknown comparison tokens can fall through to equality; malformed nodes can be omitted; an empty compiled tree becomes True.
- **core/evaluator.py:** legacy ConditionEvaluator has a separate operator map and JSON traversal. Its in/not_in, contains, presence, regex and row semantics are not the same contract as ConditionCompiler; sibling joins differ from Python precedence, and current collection failure/default behavior is too permissive for canonical conditions.
- **core/condition_payload.py:** supports multiple wrappers and raw strings for compatibility. Do not reuse its permissive parse path as canonical validation.
- **ruleflow/doctype/rule/rule.py:** validate() calls compile_conditions() and uses draft/full validation modes.
- **core/action_handlers/condition.py:** Condition action execution currently depends on compiled_expression and the engine’s Python-condition path.
- **core/action_handlers/sub_rule.py:** Sub-Rule eligibility compiles/evaluates the target Rule trigger condition with caller/target metadata.
- **core/action_handlers/assignment.py:** _compile_when_expression() accepts pythonExpression, when_expression, when, and when_condition; a condition compile exception currently returns an empty string.
- **core/value_resolver.py:** CollectionResolver already delegates row filtering to ConditionEvaluator and has a collection-row guard. Reuse the resolver/runtime foundation where safe; replace only the canonical condition path, not unrelated assignment/query/process value behavior.
- **ruleflow/api.py:** get_operator_config() publishes compiler operator tables; frontend metadata currently has fallback duplication.

Also inspect [ConditionBuilder.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/condition_builder/ConditionBuilder.vue), [ConditionStep.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/types/ConditionStep.vue), and [FlexValueControl.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue) to confirm the cross-layer storage contract. These source references are context for coordination, not permission to modify frontend files in this task.

## Implementation scope

### Stage B0 — Reconcile active work and freeze server contract

1. Inspect the actual status, head and diff of [PR #438](https://github.com/Sendipad/flexirule/pull/438). Its current description says it contains a backend task brief only. Do not implement a parallel flexvalue_contract.py if that PR has started to acquire code. Reuse/continue the existing branch, or explicitly supersede it after confirming there is no unmerged implementation.
2. Adopt the exact direct condition-node shape and FlexValue union from README.md. There is no persisted schema/version/root envelope. Create shared JSON fixture files or Python fixture builders consumed by both backend and frontend tests.
3. Add/extend one backend-owned registry for canonical operators, arity, accepted operand/output types, Fieldtypes, aliases allowed only in migration, missing/null behavior, runtime error semantics and UI labels.
4. Add/extend one resolver-family/operation contract with input config metadata, output type, required resolver level/capability and condition_operand_allowed. Defaults are deny. Enable a resolver operation as a condition operand only after source audit, tests and permission/resource review.
5. Define and test stable error code + AST path diagnostics. Do not include full documents, secrets or sensitive operand values in logs.

**Gate B0:** no unresolved contract decision changes pass/fail behavior; no duplicate operator or resolver registry is introduced.

### Stage B1 — Strict FlexValue contract and resolver boundary

Target modules (confirm locations against latest base before coding):

- Add flexirule/ruleflow/core/flexvalue_contract.py, or continue the equivalent from PR #438.
- Add flexirule/ruleflow/tests/test_flexvalue_contract.py.
- Reuse flexirule/ruleflow/core/value_resolver.py, flexirule/ruleflow/utils/field_resolver.py and existing resolver classes through a strict canonical adapter rather than replacing all value resolver implementations.
- Add focused API/contract tests under existing RuleFlow test conventions if a contract DTO is introduced.

Required behavior:

1. Validate mode exactly, required/allowed keys, value types and recursive children without mutating the submitted payload. Distinguish missing key from explicit null.
2. Static values preserve bool/null/zero/list/object; validate decimal strings and explicit date/time formats. Convert Decimal/date/time at a typed boundary, not during UI hydration.
3. Validate path scopes and each segment; reject empty, dunder, call/syntax or unknown roots. Canonical path resolution must not inherit get_context_value()’s legacy “try doc then vars” fallback.
4. Strictly validate resolver family, operation, config, nested FlexValues, operation-specific properties, declared output type and condition-operand capability. Do not let unknown/missing config fall into NoneResolver or raw Python/Jinja handling.
5. Validate template segment types and recursive FlexValue children. Raw expression/Jinja segments are not canonical.
6. Establish central, tested limits: condition depth 32; condition nodes 1,000; resolver nesting 16; path segments 32; template segments 1,000; collection rows 10,000 (reuse the existing guard). Keep these limits in one backend module and enforce them before expensive work.
7. If current value resolver APIs cannot safely distinguish canonical from legacy payloads, add an explicit canonical entry point, for example resolve_canonical_value(value, context, purpose="condition_operand"). Do not globally tighten ValueResolver.compile() in a way that silently breaks assignments, Query Records, process inputs or templates.

**Gate B1:** valid canonical FlexValues have typed stable results; malformed/unknown canonical payloads fail with stable code/path; current legacy resolver tests still pass.

### Stage B2 — Strict condition schema and direct evaluator

Target modules:

- Add flexirule/ruleflow/core/condition_contract.py.
- Add flexirule/ruleflow/core/condition_evaluator.py or make an equally clear separation inside the existing evaluator module; do not overload the legacy evaluator without explicit API boundaries.
- Keep core/compiler.py as a legacy-only adapter until consumers are migrated.
- Update condition_payload.py to expose separate strict canonical parsing and legacy inventory/conversion paths; canonical callers may not use the permissive parser as validation.
- Add focused tests such as test_condition_contract.py, test_canonical_condition_evaluator.py and test_condition_semantics.py following repo conventions.

Required behavior:

1. Validate the direct root node and every recursive node/FlexValue variant, exact keys, stable operator IDs and arity, operand types, Fieldtype constraints, context scopes, field paths, collection aliases, config capabilities and limits. Do not expect or accept a persisted schema/version/root wrapper. Return path-specific errors such as children[1].right.config.left.path.segments[1].
2. Evaluate the canonical AST directly. Do not generate source code and do not use eval, exec or frappe.safe_eval for canonical condition evaluation.
3. Implement strict left-to-right short-circuit AND/OR. No child resolver/evaluator is called after the result is decisive. Mixed logic uses explicit nested groups.
4. Resolve both comparison operands with the same canonical FlexValue resolver entry point, then call a single comparator registry.
5. Use a private MISSING sentinel to distinguish an unknown/missing runtime path from a present null. is_set returns false and is_not_set true for missing/null/empty string; whitespace is set. Other comparisons involving MISSING raise a typed evaluation error. A null literal remains comparable as null.
6. Keep type conversion explicit: no bool-to-int conversion, no implicit generic string coercion, Decimal arithmetic/comparison is decimal-safe, date/datetime/time handling has defined timezone and invalid-input behavior, and Link metadata is not inferred from arbitrary arrays.
7. collection_predicate resolves a validated collection source, binds as only within its subtree, delegates row comparisons to this same evaluator, preserves the parent doc and caller contexts, and shares the 10,000-row limit. Invalid source/alias/where and limit violations raise typed errors.
8. The canonical registry uses stable semantic IDs: eq, ne, gt, gte, lt, lte, in, not_in, contains, not_contains, starts_with, ends_with, is_set, is_not_set, is_null, is_not_null, is_empty, is_not_empty, length_eq, length_gt, length_gte, length_lt, length_lte, is_submittable and has_field, only where defined by the registry. Do not include regex, has_changed, is, is not, like, not like, unknown tokens or legacy aliases as live canonical IDs.
9. Return distinguishable outcomes: true, false, validation failure and runtime evaluation failure. Runtime errors include a safe Rule/action/node path and do not masquerade as false/true.

**Gate B2:** node/operator semantics, root comparison/group/collection cases, nested groups, scoped collection evaluation and observable short-circuit tests pass; canonical path never compiles Python.

### Stage B3 — Publish the canonical API contract

Add an authenticated versioned method (for example, get_condition_contract) following existing API and require_builder_access() patterns. Its DTO is built from the backend registries—not duplicated constants—and includes:

- canonical direct-node shape and node variants; if the DTO is versioned, report the API/contract version separately from the persisted payload;
- canonical operators, labels, arity, applicable Fieldtypes and allowed value types;
- approved resolver families/operations with input shape, result type, required capability/resolver level and condition_operand_allowed;
- allowed scopes, collection quantifiers and server limits.

Keep get_operator_config() stable while old UI consumers remain. Add API contract tests for DTO shape and authorization. Version this API DTO separately from the unversioned saved condition-node payload. Do not expose internal Python callables or permission bypass controls.

**Gate B3:** frontend can render options only from this DTO; a missing endpoint is an explicit error, not a misleading fallback to static operators.

### Stage B4 — Integrate every backend consumer

Do this only after B1/B2 are green. Inventory every call site repository-wide, then switch all canonical condition consumers to the same validator/evaluator:

1. **Rule trigger condition:** integrate in Rule validation and RuleCoordinator eligibility. Absent filter remains “no filter”; malformed present data fails validation. Runtime errors are logged as a distinct error outcome and fail closed (rule does not run) without misreporting them as a legitimate false filter.
2. **Condition action:** validate its config at save/activation and route the result to next_step_if_true / next_step_if_false. A runtime exception follows the existing action error policy, not the false branch.
3. **Callable Sub-Rule:** evaluate the target Rule’s canonical condition with explicit doc, old_doc if available, vars, caller metadata and target Rule/doctype metadata. Do not share cached values across invocations.
4. **Assignment run-if guard:** replace pythonExpression/when_expression/when as live condition mechanisms with the canonical guard. A missing guard remains unconditional; a present invalid guard must fail validation and can never be converted to an empty string. Guard evaluation must complete before assignment mutation.
5. **CollectionResolver and other row predicate consumers:** replace their direct ConditionEvaluator use with the shared evaluator and explicit row/alias scope. Preserve operation-specific defaults for aggregate operations, but reject missing predicates for operations that require one.
6. **API simulation/validation endpoints:** use the same canonical validator/evaluator; return structured diagnostics rather than evaluating malformed input as passing.
7. **Rule/import/export/clone and persistence adapters:** preserve canonical JSON exactly and strip UI IDs. Do not alter Query Records filter semantics by assumption.

Keep existing compiled-expression fields and legacy code present while still needed for old saved payloads, but canonical values must not be compiled or evaluated through them. Add cache tests: canonical AST caches may hold immutable, rebuildable derived data only; cache keys include evaluator/registry semantics version and canonical payload fingerprint; invalidation follows Rule/config edits. Never cache document context, resolved operand values or result booleans across executions.

**Gate B4:** all listed consumers use identical canonical semantics; no known call site silently falls back to the old engine for a canonical payload; context does not leak across documents/users.

### Stage B5 — Inventory and controlled migration

1. Add a read-only inventory/diagnostic command or report for existing Rules and Rule Actions. Record Rule/action identifiers and issue codes, not business values or full documents.
2. Inventory trigger conditions, Condition action config/condition_json/compiled expressions, assignment guard sources, nested CollectionResolver predicates and old FlexValue shapes.
3. Convert only deterministic legacy formats with table-driven legacy-to-canonical-node fixtures. Strip transient UI IDs. Make conversion idempotent and rerunnable.
4. Do not silently rewrite mixed sibling logical joins where old engines disagree, legacy like/not like, has_changed, regex, Python/Jinja condition strings, unknown operators, malformed payloads or mismatched Link tuples. Report each with an actionable repair path. Symbolic legacy operator tokens may be mapped to stable IDs only by a deterministic migration with fixtures; any ID rename or semantic change requires an explicit idempotent migration.
5. Write canonical node JSON only after a conversion fully succeeds. Never make two live representations compete. Do not auto-save a partially converted payload.
6. Do not add an irreversible database migration without inventory counts and a dry-run report. Add a migration patch only if source conventions and review prove it safe and idempotent for supported Frappe versions.

**Gate B5:** dry-run counts, deterministic conversions, ambiguous failures and rerun idempotency are recorded against a dedicated test site/export.

### Stage B6 — Deprecation, performance and final removal

1. Remove JSON-to-Python execution for conditions and delete dead legacy adapters only when repository-wide search proves no supported legacy path needs them and migration acceptance is met. Do not remove the DocType compiled_expression field in this task unless a separate deprecation plan proves it safe.
2. Use PR #433 as a historical hypothesis, not proof. Re-run parity fixtures first; then benchmark the canonical evaluator against representative simple, nested, collection and resolver-heavy cases on supported Frappe/Python versions. Record source branch/head SHA and environment. Correctness gates timing.
3. Keep any optimized evaluator plan ephemeral and reconstructable from saved JSON. No persisted second AST/condition plan.
4. Update relevant developer docs only where contracts change; do not mix unrelated cleanup into this task.

## Test and verification checklist

Run in the supported Frappe Bench and record exact commands, versions, source SHA and honest outcomes:

- Contract tests: direct root node variants/nested nodes/FlexValue, valid and invalid config, path-specific errors, required/allowed-key checks, non-mutation and size/depth/node limits.
- Semantics: all canonical operator IDs and arity; root comparison, root group, root collection predicate, root group mixing direct comparisons and nested groups, AND/OR/nested groups; reject empty groups, one-child canonical groups and trees with no predicate leaf; missing vs null vs empty string/whitespace vs false/zero vs empty list/dict; Decimal precision; date/time invalid values; Link/Dynamic Link target mismatch; unknown operators fail rather than equality.
- Short-circuit probes: in AND, a false first child prevents resolving the next child; in OR, a true first child prevents resolving the next child.
- Collection tests: any/all/none; empty collections; nested scope; alias shadowing; parent doc plus row; 10,000 and 10,001 rows; malformed predicate; one shared comparator.
- Consumer tests: trigger absent/true/false/error; Condition action true/false/error routing; Sub-Rule caller context; assignment guard absent/true/false/error and no mutation before error; CollectionResolver count/sum/avg/any/all/first/filter/pluck/unique; API authorization and response shape; import/export/clone round-trip.
- Regression suites: existing test_compiler.py, test_evaluator.py, test_link_semantics.py, test_value_resolver_core.py, test_value_resolvers_complex.py, test_assignment_resolver.py, test_fetch_resolver.py, and related Rule engine/trigger/Sub-Rule tests. Update legacy tests to explicitly test the adapter; do not delete them simply because canonical runtime changes.
- Run pre-commit run --all-files; if it modifies files, retain intended formatting and rerun until it passes without modifying the tree. Run focused server tests/lint. Verify Frappe v15; if Frappe v16 remains supported, run condition semantic tests there too—the existing nested-set-only v16 workflow is not sufficient evidence.

Do not report any command as passing unless it was actually run. This planning PR did not run Bench tests, lint, frontend tests or Cypress.

## Acceptance criteria

- [ ] One backend-owned condition/FlexValue contract and registry; no duplicate operator maps in new code.
- [ ] Canonical conditions are typed JSON and never generated Python.
- [ ] Invalid canonical data always fails closed with stable code/path; it never becomes a passing condition or unconditional assignment guard.
- [ ] All condition consumers listed in B4 use one comparator/evaluator.
- [ ] Resolver capability, permissions, output type, path scopes and work limits are backend-enforced.
- [ ] No persisted compiled plan or second normalized AST.
- [ ] Legacy inventory/migration is deterministic, idempotent and reports ambiguous cases.
- [ ] Existing non-condition FlexValue consumers and Frappe lifecycle behavior pass regression tests.
- [ ] Exact tests/commands/results are recorded; no unrun test is reported as passing.

## Jules execution notes

Read this plan and the shared README, then inspect source at the current task base. First reconcile PR #438 as described in B0. Keep the change backend-only; do not copy UI operator assumptions into server code. Use the backend registry as the source of truth and add tests before switching production consumers.
