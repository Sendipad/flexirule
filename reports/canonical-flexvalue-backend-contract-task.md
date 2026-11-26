# Canonical FlexValue Backend Contract — Focused Implementation Brief

**Purpose:** Handoff-ready implementation task for Jules, extracted from [FlexiRule PR #434](https://github.com/Sendipad/flexirule/pull/434).

**Scope:** One backend-only implementation stage: define and strictly validate canonical FlexValue payloads. This brief is not a claim that the implementation exists or that tests have run.

## Objective

Introduce one explicit backend-owned definition of the canonical FlexValue wire contract and a strict, independently testable validator.

The validator must reject malformed or unsupported **canonical** payloads with stable, path-specific diagnostics. It must not silently coerce values, guess missing resolver configuration, fall back to raw Python/Jinja, or turn invalid resolver configuration into a successful NoneResolver.

Keep the current production resolver and its legacy payload behavior unchanged in this task. This creates the contract boundary that later condition-evaluator and consumer-integration tasks can adopt safely.

## Source-first work required before coding

Inspect the current develop source at the exact base SHA and verify at least:

- flexirule/ruleflow/core/value_resolver.py: ValueResolver.compile(), compile_resolver_config(), current resolver classes, supported config properties, and current fallback behavior.
- flexirule/ruleflow/utils/field_resolver.py: field-path behavior that may be reused only after canonical path validation.
- flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue.
- flexirule/public/js/flexirule/rule_builder/controls/value_resolver/strategies.js and index.js, plus each registered resolver configuration component that establishes current public options/defaults.
- Existing tests: test_value_resolver_core.py, test_value_resolvers_complex.py, test_assignment_resolver.py, test_fetch_resolver.py, and test_normalization_refactor.py.
- Current project dependencies and supported Python/Frappe versions before selecting any schema-validation library.

PR #434 and older resolver inventory reports are useful design inputs, not substitutes for current source. There have been legacy kind payloads and newer family / operation payloads in different parts of the app. Reconcile the current frontend registry with the backend dispatcher before defining the canonical family/operation list. Do not copy an outdated list blindly.

Record a short mapping in the PR description or task report: current UI strategy → canonical family/operation → current backend implementation → existing regression test(s) → decisions still unresolved.

## Proposed implementation boundary

### New backend module

Create flexirule/ruleflow/core/flexvalue_contract.py (unless source inspection establishes a stronger existing home).

It should own:

- canonical FlexValue variant definitions;
- a backend-authoritative registry for allowed resolver families, operations, strict config shape, known output type (or explicitly dynamic output type), required resolver level, and capability flags such as whether the operation is eligible for use as a condition operand;
- path/scope policy and bounded recursive validation;
- a structured validation error with a stable error code, payload path, and safe human-readable message;
- a public validator entry point for already-decoded JSON-compatible Python values.

Prefer Python standard-library validation unless the supported Bench demonstrably guarantees a suitable schema package. Do not add a dependency simply for convenience. Use Frappe-native exception conventions only at integration boundaries; keep the low-level validator independently unit-testable.

Suggested public contract (names can change if existing conventions justify it):

    validate_flexvalue(
        payload,
        *,
        resolver_level=None,
        purpose="value",
        path="$",
    ) -> None

The API should validate without returning a normalized or rewritten payload. A validation exception should expose at least code, path, and a safe message. Avoid depending on live document contents, database access, session state, or resolver execution to validate the shape.

This task does not require an application-wide save/runtime integration yet. Keep the new validator independently callable and covered by tests; the later consumer integration task will wire it into the relevant server entry points.

## Canonical wire shape to validate

Use the shape specified by PR #434 unless current-source review identifies a concrete contradiction that must be resolved before implementation. Document such a conflict instead of silently changing the contract.

### 1. Static / typed literal

    {"mode": "static", "value_type": "string", "value": "Approved"}

Support the agreed types: string, integer, decimal, boolean, null, date, datetime, time, list, and object.

Validate JSON/Python value types exactly. In particular, Python booleans must not accidentally pass an integer check. Keep decimals as strings in canonical payloads and validate that the string represents a decimal without converting or rewriting the saved value. Date/time payloads should have documented string-shape validation; do not silently convert them during validation.

### 2. Variable / path reference

    {
      "mode": "variable",
      "path": {"scope": "doc", "segments": ["customer", "customer_group"]}
    }

- Require an explicit, supported scope and a non-empty array of path segments according to the final contract.
- Reject empty or malformed segments, dunder access, method/call syntax, and arbitrary attribute traversal.
- Establish the allowed scope set from actual supported execution contexts and the agreed canonical contract. Do not inherit the legacy implicit “try doc, then vars” fallback.
- Validate any collection alias against an explicitly supplied alias/context policy; do not let an arbitrary unknown scope silently become a row field.

### 3. Structured resolver

    {
      "mode": "resolver",
      "family": "math",
      "operation": "calculate",
      "config": {
        "left": {
          "mode": "variable",
          "path": {"scope": "doc", "segments": ["qty"]}
        },
        "operator": "multiply",
        "right": {"mode": "static", "value_type": "decimal", "value": "2.5"},
        "precision": 2
      }
    }

- Require an explicitly supported family, operation, and operation-specific config.
- Each operation schema must identify required keys, optional keys, exact allowed keys, expected nested FlexValue locations, and the output type/capability metadata.
- Recursively validate nested FlexValues with depth/node limits.
- Reject unknown operations, missing required configuration, wrong types, unexpected keys, and unsupported nested payloads. No fallback-to-NoneResolver semantics exist in the canonical validator.
- The generated display expression/label is not executable source of truth. Canonical resolver payloads must not depend on compileToCode output, raw Python, or Jinja.
- Do not blindly mark every current resolver as suitable for conditions. Operations that read records, depend on session state, or have unresolved permission/resource behavior must be explicitly classified. If safety cannot be proven from current source, mark them unavailable for condition operands in this stage and document why.
- Resolver-level metadata must be enforced by the validator when a level/purpose is supplied, not merely exposed for the UI. It must fail closed for unknown families, operations, levels, or purposes.

Do not expand this PR into implementing new resolver algorithms, permission-aware database lookups, or executing canonical resolvers. This stage defines and validates their contract; subsequent work implements and integrates execution.

### 4. Typed template

    {
      "mode": "template",
      "segments": [
        {"type": "text", "value": "Customer: "},
        {
          "type": "value",
          "value": {
            "mode": "variable",
            "path": {"scope": "doc", "segments": ["customer_name"]}
          }
        }
      ]
    }

- Accept only the agreed segment variants.
- Text segments require string values; value segments recursively contain a valid FlexValue.
- Reject raw executable expression segments and malformed/unknown segment types.

### Strictness and resource guards

- Canonical inputs are decoded JSON-compatible values, not serialized JSON strings. JSON decoding remains the responsibility of the caller/boundary.
- Reject unrecognized top-level keys and invalid/missing discriminants rather than inferring a variant from whichever keys happen to be present.
- Set explicit maximum recursion depth, node count, path-segment count, and reasonable string/list/object sizes. Document values and test boundary conditions. Avoid arbitrary huge limits.
- Validation must be deterministic, side-effect-free, and must not mutate the submitted structure.
- Paths in diagnostics should identify the exact location, for example $.config.right.path.segments[1], without logging full business payloads.
- Define the difference between a present null literal and a missing required key; tests must cover both.

## Compatibility constraints

This is an additive contract boundary.

Do not change ValueResolver.compile(), compile_resolver_config(), get_compiled_resolver(), current resolver classes, or existing handler behavior unless a minimal integration is essential and independently proven to preserve legacy behavior. Prefer no runtime wiring at all in this task.

Specifically out of scope:

- modifying Rule/Rule Action/Assignment/Query/Process consumers;
- changing Rule triggers, Condition actions, Sub-Rule evaluation, or CollectionResolver predicates;
- changing frontend Vue controls, strategy files, generated labels, or serialization;
- adding condition evaluation, an AST evaluator, or a persisted execution plan;
- migrating saved payloads or adding Frappe patches / DocType changes;
- removing legacy resolver aliases, raw-expression support, or compiled_expression;
- adding a third-party dependency without confirming it is guaranteed on supported Bench installations;
- broad resolver refactoring or rewriting existing value operations.

Any proposal to adjust the canonical wire contract must be called out before implementation, with the conflicting current-source behavior and a specific recommendation. Do not silently expand this task.

## Test plan

Add flexirule/ruleflow/tests/test_flexvalue_contract.py (or the existing project-conventional equivalent) with table-driven unit tests.

### Valid payload tests

- Each canonical variant and every explicitly supported resolver family/operation.
- Static values for each declared type.
- Valid paths for each allowed scope, nested paths, and allowed collection aliases.
- Nested resolver inputs and template value segments.
- Capability validation for the allowed resolver level and purpose.

### Invalid payload tests

- missing/unknown mode, unknown top-level keys, extra fields, malformed nested objects;
- wrong literal types, including bool vs int, malformed decimal strings, and invalid date/time string shapes;
- missing scope/path/segments, unknown roots, empty/invalid segments, dunder or call syntax;
- unknown resolver family/operation, absent config, missing required keys, unexpected keys, wrong config types, and invalid nested FlexValues;
- resolver operation disallowed at the requested resolver level or purpose;
- malformed template segments, raw expression/Jinja payloads in canonical mode;
- depth/node/path/size limit boundaries;
- confirm validation does not mutate payloads and returns stable error code/path for repeated invalid inputs.

### Regression verification

Run the focused new test module and the existing resolver suites in the supported Frappe Bench. At minimum, confirm these remain unchanged:

- flexirule.ruleflow.tests.test_value_resolver_core
- flexirule.ruleflow.tests.test_value_resolvers_complex
- flexirule.ruleflow.tests.test_assignment_resolver
- flexirule.ruleflow.tests.test_fetch_resolver
- flexirule.ruleflow.tests.test_normalization_refactor

Run backend lint for touched files. Do not report commands as passing unless they were executed; include site, Python/Frappe versions, exact commands, and outcomes in the PR.

## Acceptance criteria

- [ ] The new canonical contract and strict validator are backend-owned in one module.
- [ ] Every accepted canonical resolver family/operation has explicit, tested config/capability metadata derived from current source.
- [ ] Unknown and malformed canonical payloads are rejected with stable code/path diagnostics.
- [ ] Typed literals preserve distinctions among null, false, zero, integer, and decimal.
- [ ] Paths and nested structures are validated with bounded work and no implicit legacy scope fallback.
- [ ] Resolver level and purpose/capability restrictions fail closed when the validator is given that context.
- [ ] Validation is side-effect-free and does not normalize or mutate payloads.
- [ ] Existing legacy resolver behavior and tests remain unchanged.
- [ ] No UI, condition evaluator, runtime consumer switch, migration, DocType change, or cache redesign sneaks into the diff.
- [ ] All new and regression tests run, with honest results documented against the actual head SHA.

## Suggested Jules workflow

1. Inspect the source and dependencies first; report any conflict between this brief and the current develop code before resolving it by assumption.
2. Implement the backend contract module only, then add its focused tests.
3. Commit the validator and tests as separate logical commits if practical.
4. Run focused tests, resolver regression suites, and lint in the maintained Frappe Bench.
5. Review the final diff for legacy behavior changes and unrelated edits. Report exact base/head SHAs, files changed, commands actually run, test results, and any operation intentionally excluded from condition-capability.
6. Do not begin the condition evaluator or consumer integration as part of this task. Those are separate follow-up stages from PR #434.
