# Canonical Condition + FlexValue Contract — Direct Implementation Plan

> **Contract update notice (2026-10-27):** This document preserves detailed architecture rationale from the earlier PR #434 proposal. Its original persisted `schema`/`version` envelope, `root` wrapper, and symbolic operator examples are historical proposals and are superseded by [the current shared contract](condition-evaluation/README.md). The current saved condition is one direct node discriminated by `type`, with no persisted schema/version/root wrapper. Root nodes may be comparisons, groups, or collection predicates. Groups have at least two direct children, and stable semantic operator IDs (for example `eq`, `gt`, `not_in`) are canonical. Use this document for background only; the shared README and actionable backend/frontend plans are authoritative for the wire contract and migration decisions.


**Status:** Implementation plan only; no application code or production behavior changed by this document.  
**Repository:** Sendipad/flexirule  
**Audited base:** develop at 60c5005e69d5899765748c561f8f426078c008f0 (2026-10-19)  
**Plan date:** 2026-10-21  
**Target stack:** Frappe v15+, Python >=3.10, Vue 3  
**Scope:** Canonical condition AST, shared FlexValue operand model, resolver contract, evaluator, all condition consumers, front-end builder, migration, tests, and performance verification.

## 1. Decision summary

Adopt **one canonical JSON contract that composes Condition nodes and FlexValue nodes**, and make it the only representation written by the current visual builder and accepted by the new runtime.

- The visual Condition Builder writes the canonical condition AST.
- Each comparison's **left and right operands are both FlexValue nodes**. The left side is no longer restricted to a field reference; it can be a typed variable, a supported resolver, or a static value where an operator contract permits it.
- A FlexValue resolver uses the structured form mode + family + operation + config; its input values and field references reuse FlexValue nodes rather than using separate field_a, field_b_type, expression strings, and inconsistent dotted paths wherever practical.
- The condition runtime evaluates the canonical AST directly. Strict validation checks the existing tree in place; it does not create and persist a second normalized JSON schema.
- No generated Python condition expression is written or used for canonical condition execution. A separately constrained legacy adapter may exist only while old persisted values are inventoried/migrated.
- Any performance preparation must be ephemeral and derived from the same canonical AST. Do not persist a second normalized AST or treat a cached plan as authoritative.
- Conditions, resolver predicates, and conditional assignment guards must use the same condition contract and comparator semantics. Assignment mutation operators remain a separate domain.

This is a deliberate contract refactor, not an attempt to preserve every ambiguity in the current implementation. FlexiRule is not yet production-ready, so we should resolve the old format and semantic drift now rather than make it permanent. Existing developer/site data still needs an explicit migration and rejection report.

## 2. Source baseline and confirmed architecture

This plan was prepared from the current develop tree and related tests/audit reports. It is a source audit; it does not claim that the new design has been implemented or tested at runtime.

### 2.1 Current condition paths are not one system

| Path | Current representation and runtime | Required destination |
|---|---|---|
| Rule trigger condition | Rule.trigger_condition JSON -> Rule.compile_conditions() -> persisted Rule.compiled_expression -> RuleCoordinator.check_eligibility() evaluates Python via frappe.safe_eval | Canonical condition envelope -> shared evaluator; compiled_expression becomes legacy-only and is eventually retired |
| Condition action | Rule Action.config / legacy condition_json -> ConditionCompiler -> action.compiled_expression -> ConditionHandler -> engine._evaluate_python_condition() | The same canonical condition envelope -> shared evaluator -> true/false graph edge |
| Collection resolver predicate | ValueResolver builds CollectionResolver -> ConditionEvaluator parses/evaluates older JSON tree with doc + row | Same canonical condition AST; shared evaluator gets parent document, current row, and declared alias context |
| Sub-Rule eligibility | SubRuleHandler checks target Rule.trigger_condition / compiled_expression and calls engine Python-condition evaluation | Same canonical condition evaluator with explicit caller/rule/doctype context |
| Assignment row guard | AssignmentHandler accepts pythonExpression, when_expression/when, or when_condition; condition compiler generates Python, and compilation errors can become an empty guard | A single canonical guard field containing the condition AST; no silent conversion failure |
| Other expression helpers | Engine/helper and resolver code support restricted Python or Jinja for some non-condition value/template features | Keep these capabilities explicitly separate from the condition grammar; do not interpret arbitrary expression strings as canonical condition operands |

Sources:
- [Rule controller](https://github.com/Sendipad/flexirule/blob/60c5005e69d5899765748c561f8f426078c008f0/flexirule/ruleflow/doctype/rule/rule.py)
- [Condition compiler](https://github.com/Sendipad/flexirule/blob/60c5005e69d5899765748c561f8f426078c008f0/flexirule/ruleflow/core/compiler.py)
- [Condition evaluator](https://github.com/Sendipad/flexirule/blob/60c5005e69d5899765748c561f8f426078c008f0/flexirule/ruleflow/core/evaluator.py)
- [Condition payload adapter](https://github.com/Sendipad/flexirule/blob/60c5005e69d5899765748c561f8f426078c008f0/flexirule/ruleflow/core/condition_payload.py)
- [Condition action handler](https://github.com/Sendipad/flexirule/blob/60c5005e69d5899765748c561f8f426078c008f0/flexirule/ruleflow/core/action_handlers/condition.py)
- [Coordinator](https://github.com/Sendipad/flexirule/blob/60c5005e69d5899765748c561f8f426078c008f0/flexirule/ruleflow/core/coordinator.py)
- [Sub-Rule handler](https://github.com/Sendipad/flexirule/blob/60c5005e69d5899765748c561f8f426078c008f0/flexirule/ruleflow/core/action_handlers/sub_rule.py)
- [Assignment handler](https://github.com/Sendipad/flexirule/blob/60c5005e69d5899765748c561f8f426078c008f0/flexirule/ruleflow/core/action_handlers/assignment.py)

### 2.2 Current FlexValue needs a contract refactor too

Current FlexValue-related files include:

- Backend: flexirule/ruleflow/core/value_resolver.py and flexirule/ruleflow/utils/field_resolver.py.
- Frontend: flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue; controls/value_resolver/strategies.js; controls/value_resolver/index.js; controls/value_resolver/useValueResolver.js; controls/value_resolver/utils.js; and resolver component/config files.
- Consumers: AssignmentConfig.vue / AssignmentHandler, QueryRecordsConfig.vue and output-field editors, process/action inputs, text generation/mapping, and the Condition Builder's current right operand.
- Existing design notes: reports/value-resolver/frontend-backend-contract.md, backend-architecture.md, resolver-inventory.md, security-audit.md, findings.md, and remediation-plan.md.

The current payload shapes overlap but are not canonical:
- Static values usually use {mode: "static", value: ...}.
- Variable values may use {mode: "variable", value: "doc.status"} or {mode: "variable", path: "doc.status"}.
- Visual resolvers use {mode: "resolver", value: "<generated expression>", config: {...}}; config may use kind, family, operation, and sometimes a nested config.
- Legacy modes and kinds include formula, format, normalize, normalization, date_formula, date_diff, child_aggregation, string_formula, fetch, plus current family-based variants.
- Mixed rich text uses {mode: "expression", value: [segments...]}. Manual mode can strip config and leave a string for SafeEvalResolver; string inputs can also invoke JinjaResolver.
- ValueResolver.compile() accepts bare strings, shorthand path strings, old aliases, and partial/missing resolver configuration. compile_resolver_config() can return NoneResolver for unknown/empty configurations.
- Frontend resolverLevel gating exists in FlexValueControl.vue but the backend resolver factory does not enforce the same level. It must not be treated as a security boundary.

The intended contract consolidates these cases, but this plan does not blindly rewrite every existing consumer in one step. A canonical FlexValue adapter and a consumer inventory are required so each consumer is updated and tested before legacy paths are removed.

### 2.3 Important condition defects the new contract must not preserve

The current source and existing architecture audit show that:
- ConditionCompiler and ConditionEvaluator implement separate operator and logical semantics.
- Unknown comparison operators can fall back to equality in the compiler; unknown node shapes can disappear, and empty compiled trees can become a passing expression.
- The current compiler hard-codes deprecated has_changed to True.
- Null and booleans can be rewritten by the compiler (None to empty text and booleans to 1/0), while the JSON evaluator handles the values differently.
- Mixed sibling AND/OR chains have a semantic mismatch: generated Python observes Python precedence, while the JSON evaluator folds through siblings in sequence. Nested groups should express precedence explicitly.
- like/not like are exposed as “contains”-like labels but are not implemented consistently by the compiler; regex exists only in the JSON evaluator, with no defined resource policy.
- Link tuple comparison includes a DocType but the comparison helper does not validate that DocType.
- The JSON evaluator calculates each child result before applying its short-circuit boolean operation, so the current implementation does not reliably short-circuit side effects in nested nodes.
- Missing where/invalid collection nodes have permissive outcomes in current paths.
- Field paths and collection aliases are interpolated into generated Python source by the compiler.
- AssignmentHandler has three possible guard sources; failure compiling when_condition may be swallowed as an empty string, which risks treating a failed guard as “always run”.
- Current tests exercise both engines but do not provide a complete, cross-consumer differential contract suite.

Treat these as migration and contract issues, not behavior to copy into the new evaluator.

## 3. Canonical wire contract

Create a single recursive schema contract shared by backend validation, front-end builder adapters, test fixtures, import/export, and runtime. Proposed module/file names are in Section 8.

### 3.1 Canonical condition envelope

Every complete persisted condition, whether a Rule trigger filter, Condition action, or assignment guard, uses this envelope:

    {
      "schema": "flexirule.condition",
      "version": 1,
      "root": {
        "type": "group",
        "operator": "and",
        "children": [
          {
            "type": "comparison",
            "operator": ">",
            "left": {
              "mode": "variable",
              "path": { "scope": "doc", "segments": ["grand_total"] }
            },
            "right": {
              "mode": "resolver",
              "family": "math",
              "operation": "calculate",
              "config": {
                "left": {
                  "mode": "variable",
                  "path": { "scope": "vars", "segments": ["minimum_total"] }
                },
                "operator": "multiply",
                "right": {
                  "mode": "static",
                  "value_type": "decimal",
                  "value": "1.15"
                },
                "precision": 2
              }
            }
          }
        ]
      }
    }

This example is illustrative of the proposed shape; it is not an exact copy of any current saved payload.

Rules:
1. schema and version are required for complete persisted conditions. Unsupported versions are rejected with an actionable message.
2. root must be one condition node, normally a group. Do not let arrays, raw strings, {conditions: ...} fragments, or nested wrapper keys silently become alternate canonical formats.
3. UI-only IDs may exist in reactive Vue state but must never be persisted in canonical condition or FlexValue JSON.
4. Do not save generated Python as a parallel authoritative representation.
5. The same schema/version contract is reused in Rule.trigger_condition, Condition action config, assignment guard fields, and nested collection predicates. Storage context may determine whether absence means “no guard” or “invalid configuration”; it must not change the AST's meaning.
6. schema version is for changes to the public JSON contract. An implementation optimization, cache, or runtime class does not require a new persisted version.

### 3.2 Condition node variants

Use explicit node types. Never infer node type from the presence of arbitrary keys.

#### Group

    {
      "type": "group",
      "operator": "and",
      "children": [ ...condition nodes... ]
    }

- operator is exactly and or or.
- All children in one group share that operator. There is no per-child logical_operator in canonical version 1.
- Mixed logic is expressed through nested groups. This makes precedence structural and independent of Python.
- Preserve child order. Do not reorder conditions or distribute groups as an optimization.

#### Comparison

    {
      "type": "comparison",
      "operator": "==",
      "left": { ...FlexValue... },
      "right": { ...FlexValue... }
    }

- left and right are both FlexValue nodes. Unary operators have no right operand; the operator contract defines arity.
- The operator registry defines operand types, null/missing handling, applicable Frappe Fieldtypes, link rules, aliases allowed during migration, and runtime error semantics.
- A resolver operand is not special to the evaluator: resolve each accepted FlexValue via the shared ValueResolver contract, then hand typed values to the common comparator.

#### Collection predicate

    {
      "type": "collection_predicate",
      "quantifier": "any",
      "source": {
        "mode": "variable",
        "path": { "scope": "doc", "segments": ["items"] }
      },
      "as": "item",
      "where": {
        "type": "group",
        "operator": "and",
        "children": [
          {
            "type": "comparison",
            "operator": ">",
            "left": {
              "mode": "variable",
              "path": { "scope": "item", "segments": ["rate"] }
            },
            "right": {
              "mode": "static",
              "value_type": "decimal",
              "value": "100"
            }
          }
        ]
      }
    }

- quantifier is exactly any, all, or none.
- source is a FlexValue with a declared collection result contract; in v1 permit only variable/path values until a resolver source has an explicit safe, bounded collection type.
- as is a validated identifier defining a local alias for the current row. Alias scope is nested and cannot shadow reserved roots or an ancestor alias.
- where is a condition node in the same schema, without another envelope.
- This node and the value resolver's collection family must delegate to the same bounded iteration and predicate evaluator rather than maintain separate comparison engines.

A direct typed collection_predicate is a condition control-flow node. A FlexValue family: collection computes a value such as count, sum, filter, or pluck. They share source handling, scopes, limits, and predicate evaluation, but they are different operations and must not be conflated.

### 3.3 Canonical FlexValue union

All canonical FlexValues use a single explicit discriminant named mode. No code string is required to execute a structured value.

#### Static / literal value

    { "mode": "static", "value_type": "string", "value": "Approved" }

Supported declared value types should include: string, integer, decimal, boolean, null, date, datetime, time, list, and object. The schema should define which JSON type is accepted for each value_type. Decimal values should be serialized as decimal strings and parsed to Decimal at the comparison/resolver boundary so currency precision is not dependent on binary floating-point JSON conversion. Booleans must remain booleans, never be rewritten to 0/1 globally. For list values, define whether item types are inferred or explicitly typed; never interpret any two-item array beginning with a string as a Link tuple.

Field metadata may establish the expected operand type and validate the literal. It must not silently change the literal's semantic value.

#### Variable / reference

    {
      "mode": "variable",
      "path": { "scope": "doc", "segments": ["customer", "customer_group"] }
    }

- Replace ambiguous path/value aliases and dotted-string parsing with one canonical form.
- scope must come from a server-defined allowlist: current supported contexts to inventory include doc, old_doc, vars, item, loop, row, caller, rule, doctype, and explicitly declared collection aliases. Do not expose arbitrary object attributes.
- segments are validated identifier/path tokens. They cannot include Python syntax, empty segments, dunder access, or methods/calls.
- Empty segments are permitted only where a particular scope value itself is meaningful and its consuming operation explicitly allows it.
- Existence/missing state must be separately defined from a resolved JSON null value. FieldResolver's useful Frappe traversal behavior may be reused after path validation.

#### Resolver

    {
      "mode": "resolver",
      "family": "math",
      "operation": "calculate",
      "config": {
        "left": {
          "mode": "variable",
          "path": { "scope": "doc", "segments": ["qty"] }
        },
        "operator": "multiply",
        "right": {
          "mode": "static",
          "value_type": "decimal",
          "value": "2.5"
        },
        "precision": 2
      }
    }

- family and operation are required canonical identifiers.
- config is an operation-specific object defined by a backend-owned schema. Unknown families, unknown operations, missing required properties, unsupported nested values, and extra properties outside an explicit extension policy are validation errors, not NoneResolver results.
- Value-bearing config properties use FlexValue nodes wherever dynamic input is accepted. Non-value parameters (unit, precision, case operation, role name, format string) stay ordinary typed config scalars.
- The generated display expression/label belongs to UI presentation only. It is not the executable source of truth and is not an alternative runtime fallback.
- Every resolver declares expected input types, output type where knowable, supported contexts, required level, side-effect/resource profile, and availability in condition operands.
- Resolver compilation/resolution for a condition must be read-only, bounded and policy-checked. Do not allow a condition operand to invoke arbitrary Python, Jinja, mutators, arbitrary method calls, or unbounded work.

#### Text template

For mixed text and token output, define a typed template value rather than an ambiguous expression that mixes text, tokens, Python strings, and Jinja:

    {
      "mode": "template",
      "segments": [
        { "type": "text", "value": "Customer: " },
        {
          "type": "value",
          "value": {
            "mode": "variable",
            "path": { "scope": "doc", "segments": ["customer_name"] }
          }
        }
      ]
    }

- Template evaluation is concatenation/formatting according to an explicit contract; each value segment contains a FlexValue.
- This mode is appropriate for value-producing text/template consumers, not for arbitrary boolean condition grammar.
- Current mode: expression rich-text payloads can be migrated when they are just text + variable/structured resolver tokens. Manual Python expression strings and Jinja templates must not be silently recast as templates.
- Canonical condition operands accept only approved FlexValue modes. In v1, conditions must reject free-form Python and Jinja value payloads. Structured resolver features replace their normal use cases.

### 3.4 Resolver family consolidation

Use family + operation + config as the canonical resolver interface. The exact operation schemas are owned centrally, not independently by a Vue component and a Python class.

Initial family inventory based on current source:

| Canonical family | Operations to inventory/specify | Existing representations to migrate |
|---|---|---|
| math | calculate | kind: math_formula; field_a/math_op/field_b_type/field_b/constant_b/precision |
| date_time | current, calculate, diff, extract, boundary, format | current date_formula/date_diff and family date_time configs; legacy base_type/base_field/offset_* fields |
| text | combine, case, normalize, format | string_formula, normalization/norm_op aliases, format/fmt_op, legacy mode aliases |
| collection | count, sum, avg, any, all, first, filter, pluck, unique | collection family/kind, child_aggregation, find-to-first alias and predicate/target fields |
| lookup | fetch/get-value operation | fetch kind/alias, lookup fields, static/dynamic DocType settings |
| system_context | user, role_check and any explicitly supported token | system_context kind/token/role fields |

This table is the target family organization, not confirmation that every listed family/operation has identical semantics today. The implementation team must extract actual UI strategy defaults and Python constructor behavior, then specify and test each mapping before enabling strict validation.

Important contract points:
- Convert current math_formula into the canonical math family; do not preserve top-level kind as a second canonical discriminant.
- Move every value-bearing argument (for example formula inputs, date sources, lookup record references, collection sources/projections) to FlexValue nodes when dynamic values are supported.
- Keep operation-specific settings as strict schemas. Avoid both a generic catch-all config dictionary and one universal operation with undocumented string options.
- Decide the availability matrix by resolverLevel on the backend. The frontend's current resolverLevel filter is UX only.
- A resolver may be used as a condition operand only if its operation is read-only, resource-bounded, context-safe, and has a defined output type / error contract. Lookup operations must not bypass document/user permissions simply because they are used inside a condition; add a permission-aware bounded adapter or keep lookup unavailable in conditions until that is resolved.
- Collection predicates must share the condition contract, including row aliases and iteration limits.
- Unknown resolver configs must fail validation. NoneResolver is appropriate only for a deliberately absent optional value, never as a success-shaped fallback for an invalid persisted resolver.

## 4. Semantic contract — decide and test before integrating

### 4.1 Logical operators and evaluation order

- A group with operator and children means a strict left-to-right short-circuit AND or OR over those children.
- AND stops at the first false child; OR stops at the first true child. A child node must not be evaluated before the evaluator decides it is needed.
- Use explicit nested groups for mixed logic. Do not support a canonical group with mixed sibling operators in version 1. This resolves the old Python-precedence versus evaluator-folding disagreement.
- Preserve child order and side-effect-free resolver ordering. Do not reorder nodes, inline groups, or perform Boolean algebra simplification in v1.
- Prove short circuit with observable probes: place a node that appends to a test-only counter after an AND-failing child and after an OR-succeeding child; the counter must remain unchanged.

### 4.2 Empty and missing conditions

These are separate states and must not be conflated with an empty group or failed parser:
- Rule trigger_condition absent: there is no trigger filter, so the Rule can be eligible subject to other checks.
- Condition action: a condition must be configured before activation; an empty group is a validation error. It must not quietly pass.
- Assignment guard absent: assignment row runs unconditionally; a present but invalid guard fails validation and never becomes an empty/no-op guard.
- Collection resolver predicate absent: only the operation-specific default documented by its contract is allowed (for example, unfiltered count/sum). If the operation requires a predicate, missing predicate is an error.
- Empty group: invalid in canonical version 1, regardless of AND/OR. If a future user experience needs explicit constants, introduce explicit boolean constant nodes rather than special-case empty groups.
- Empty source strings, parse failures, unknown nodes, and unsupported versions cannot imply True.

### 4.3 Operand and null/missing behavior

Define and test:
- Missing reference vs a present value of null.
- null vs empty string vs whitespace-only string.
- false vs numeric zero.
- empty list/dict vs missing.
- empty membership set/list, wrong RHS type, and Link/Dynamic Link targets.
- numeric precision, date/datetime/time parsing, timezone policy, and invalid conversions.
- comparison of resolver return values with field metadata and static literal types.
- whether each operator handles missing by returning false or raises a typed evaluation error; there must not be unintentional per-engine differences.

Recommended starting rule: no silent implicit cast other than an explicitly specified Frappe Fieldtype conversion. Preserve JSON booleans and null. Parse decimal and date/time types through explicit typed conversion functions. A valid comparison that returns false is different from a value resolution/type/configuration failure.

### 4.4 Operator contract

Define one server-authoritative operator registry. At minimum inventory and make an explicit keep/change/deprecate decision for:
- equality and inequality: ==, !=
- ordered comparisons: >, <, >=, <=
- membership: in, not in (one canonical token; old not_in is a migration alias only)
- substring operations: contains, not_contains
- presence and emptiness: is_set, is_not_set, is_empty, is_not_empty
- length: length_eq, length_gt, length_gte, length_lt, length_lte
- metadata operations: is_submittable, has_field
- regex, if retained after resource-safety review
- like / not like, whose current labels and implementation disagree
- has_changed, which currently compiles to True and must not be carried forward as an ordinary comparator
- is / is not, currently part of compiler map but identity comparison is not necessarily meaningful for business values

Each registry entry declares canonical token, arity, argument types, allowed fieldtypes/resolver results, aliases accepted only by migration, missing/null semantics, Link/Dynamic Link handling, runtime error behavior, and tests. Operator DTO/labels for the UI should be generated from this registry rather than duplicated in several front-end fallback maps.

Decisions that need explicit product/owner sign-off as part of Stage 1:
1. whether like/not like mean literal substring aliases (migrate to contains/not_contains) or wildcard pattern matching. Do not assume SQL LIKE semantics outside a query.
2. whether regex remains in v1; if retained, set size/pattern policies and use an evaluator with a defensible time/resource bound. If a safe bound is unavailable, reject it in v1.
3. reject has_changed and require an On Change trigger/process or an explicit old_doc comparison. Inventory old uses and provide an actionable replacement path.
4. drop is/is not from canonical operators unless a meaningful typed contract is specified.

### 4.5 Runtime error policy

Three outcomes must be distinguishable:
1. valid condition evaluates true;
2. valid condition evaluates false;
3. invalid configuration / evaluation failure.

Invalid schema/operator/scope/value resolver is rejected on save or activation. A runtime error in a previously validated condition produces a typed error with Rule/action/node path, resolver family/operation, and a safe diagnostic message. It must not silently become false or true without an explicit documented error policy. Do not log full documents, secrets or raw sensitive values. Follow Frappe's and FlexiRule's existing blocking-event and action on_error contracts deliberately; trigger eligibility should report a trigger-evaluation error separately from a legitimate false result.

### 4.6 Context contract

One evaluator receives an explicit context object with approved roots:
- doc and old_doc;
- vars;
- item, loop, row;
- caller and target rule metadata;
- doctype;
- locally declared collection aliases.

Implement scope access centrally. No dynamic scope fallback where an unknown root is treated as a row field; no implicit “try doc, then vars” for canonical condition paths. Existing get_context_value() has fallback behavior useful to legacy value formats, but the canonical path should use the explicit scope/path object. Retain existing aliases only in the legacy converter, not in canonical execution.

The top-level Rule trigger and callable Sub-Rule conditions have different context contents. Model these explicitly (for example empty vars/caller for a regular trigger, populated caller/target-rule metadata for Sub-Rule eligibility); do not create a hidden second interpretation of the same AST.

### 4.7 Collections and limits

- Share bounded collection traversal between condition quantifiers and FlexValue collection operations.
- Preserve the currently documented maximum row limit as a baseline pending test/review; do not silently truncate results.
- Set limits for condition depth, node count, nested resolver depth, path segments, result/collection size, template length, and evaluator work.
- Define any([]) = false, all([]) = true, none([]) = true as explicit mathematical quantifier semantics, unless owner chooses otherwise.
- An unavailable/not-a-collection source is not an empty list; it is a type or runtime resolution error unless a resolver operation explicitly defines otherwise.
- Collection alias names are identifiers validated by the server, lexically scoped, and not interpolated into source code.

## 5. Validation and execution design

### 5.1 No second persisted representation

Canonical JSON is both the persisted contract and the evaluator input. The validator validates the supplied AST and metadata without rewriting it into another normalized JSON document.

Strict validation should:
- validate schema name and version;
- validate node type and allowed keys;
- validate operator arity and FlexValue union variants;
- validate all resolver family/operation config schemas recursively;
- validate path scope, segments, field metadata and allowed collection aliases;
- validate resolver level and operation capability for the Rule/site/caller;
- validate node/depth/collection/template/regex limits;
- produce stable diagnostic paths such as root.children[1].right.config.left.path;
- return validation errors rather than mutating or coercing the submitted tree.

If a legacy payload must be converted, that is a boundary migration from a prior format to v1; it is not runtime normalization. Write the canonical v1 result back once only after conversion succeeds. Never keep both legacy and canonical sources active and ambiguous.

### 5.2 Direct evaluator

Implement one typed AST evaluator which accepts an already parsed canonical object. Responsibilities:
1. evaluate group children with explicit short circuit;
2. resolve each FlexValue via the one shared value resolver contract;
3. call one operator registry/comparator;
4. enter/exit collection alias scopes safely;
5. report a typed error with node path on failures.

The evaluator must not call ConditionCompiler for canonical nodes, generate Python source, call eval/safe_eval for a condition, or interpret manual formula strings. Keep Frappe safe_eval only for explicitly separate, legacy or non-condition expression/value features during a controlled migration—not as the implementation of the condition language.

Initially prefer direct AST traversal. Do not create another normalized JSON plan. If benchmarks later prove preparation is worthwhile, introduce an **in-memory, reconstructable runtime object/cache** that retains a reference/fingerprint to the source AST and caches only derived facts (resolved operator functions, validated path tokens, resolver objects). It must not mutate or replace persisted JSON and must be safe to rebuild after restart/invalidation.

### 5.3 Reuse existing code without preserving its legacy ambiguities

- Reuse/extend ValueResolver and existing strategy classes for structured operations rather than making one resolver implementation in ConditionEvaluator and another in assignments.
- Centralize canonical parsing/validation at a boundary, but do not make ValueResolver.compile() keep permissive fallback branches as the route for canonical inputs.
- Keep assignment operators in flexirule/ruleflow/core/operators.py and the assignment operator registry separate from condition comparators; only share FlexValue resolution and common typing/path utilities.
- FieldResolver can be reused for supported Frappe child/reference traversal after validation. Do not rely on it to validate whether a path or context root is allowed.
- Use metadata from the backend as the source for fieldtype/operator options. Frontend validation is advisory only.
- Keep expression/template compilation for action templates distinct from condition evaluation.

## 6. Migration and deprecation policy

### 6.1 Inventory first

Produce a read-only inventory tool/report that scans all Rule documents and Rule Action rows on a dedicated test/site or export, without modifying data, and records:
- trigger_condition and Rule.compiled_expression;
- Condition action config, condition_json and action.compiled_expression;
- assignment pythonExpression, when_expression, when, and when_condition;
- nested CollectionResolver/ChildAggregationResolver condition payloads;
- old {ref}, {value}, {type: field/literal/method}, legacy root arrays/groups, nested wrapper keys, double-encoded JSON, bare condition expression strings;
- resolver payloads using mode aliases, kind/family mixtures, nested config, missing config, expression tokens, raw Python or Jinja, and unsupported family/operation;
- deprecated/ambiguous operators (especially has_changed, like/not like, unknown tokens, link tuples and mixed logical sibling chains).

Record counts and Rule/action identifiers, but avoid including business field values or full documents in logs/reports.

### 6.2 Deterministic conversion rules

A migration converter should handle only cases whose meaning is clear:
- condition list -> a group with the documented default operator if and only if the legacy representation's semantics are unambiguous;
- {conditions, op} groups -> typed group nodes;
- {left: {ref: ...}, right: {value: ...}} -> comparison nodes with variable/static FlexValue nodes;
- {type: "field"|"literal"} and approved {mode: ...} aliases -> their canonical FlexValue variant;
- resolver legacy kinds and aliases -> canonical family/operation/config using an explicit mapping table and deterministic defaults only where source semantics are known;
- rich text made entirely of text/variable/structured resolver tokens -> template segments;
- current not_in -> canonical not in or vice versa only if one token is selected as canonical and used consistently everywhere;
- temporary Vue node IDs are discarded.

For every converter mapping, write unit tests containing old input, expected canonical output, and expected runtime result.

### 6.3 Do not auto-migrate ambiguous semantics

Do not silently rewrite:
- mixed sibling logical_operator sequences where compiler and evaluator disagree;
- raw Python condition strings whose semantic interpretation cannot be represented by the canonical nodes;
- has_changed, whose current compiler semantics always pass;
- like/not like unless the owner-selected semantics are explicit;
- manual resolver strings without a structured, known family/operation config;
- Jinja templates or expression-mode tokens whose exact prior meaning cannot be preserved;
- unknown operators, unknown resolver operations, malformed trees, or link tuples that lack enough type information.

List each affected Rule/action and an actionable manual fix. Because the app is pre-production, prefer explicit remediation or rejection over adding a permanent compatibility system for unsafe or ambiguous behavior.

### 6.4 Persistence strategy

- Rule.trigger_condition and Condition action config write the complete same canonical envelope.
- Assignment guards write a complete envelope at a named structured field (for example when_condition); stop writing pythonExpression/when_expression for canonical guards.
- Collection resolver config embeds the same condition node for its predicate; it does not embed a separate condition language.
- During transition, old compiled_expression columns may remain for import compatibility and roll-back observation, but runtime must select exactly one source of truth based on an explicit migration/version state. Do not choose payload sources by “first non-empty wins” for canonical v1.
- After migration and call-site removal, retire the Rule/Rule Action compiled_expression fields through the appropriate Frappe DocType metadata migration, removing options: PythonExpression where no longer appropriate. Search import/export, API, tests, patches and client contracts before removal.
- Make the data migration idempotent; back up or export affected data, produce a migration summary, and fail clearly for unconvertible inputs. It must not rewrite active data silently or bypass Rule validation without preserving an audit trail. Run only on a dedicated test site first.

### 6.5 Cache policy

- The RuleCoordinator runtime registry currently stores compiled_expression and derives dependencies from that source. Migrate it deliberately to cache the canonical trigger AST (or to access it through an explicit immutable condition source) and update dependency/caching logic; never infer a safe skip set if dependencies cannot be complete.
- ValueResolver.get_compiled_resolver() currently caches by action name + key and not by payload fingerprint. Review invalidation and mutation within request; avoid stale values when configs change.
- A condition/runtime cache, if needed, must be bounded and keyed by stable identity plus canonical payload fingerprint/schema version and relevant resolver policy/site context. Clear/invalidate it when Rule/action config or metadata/policy changes.
- Never cache the boolean result as if it were the condition definition; results depend on doc, old_doc, vars, caller, session and time.
- Benchmark cold compile/cache miss, hot runtime evaluation, and realistic repeated use separately. Cache is an optimization, not a correctness requirement.

## 7. Front-end implementation

### 7.1 Condition Builder changes

Files:
- components/condition_builder/ConditionBuilder.vue
- ConditionGroupUI.vue, ConditionNode.vue, SimpleCondition.vue, CollectionUI.vue, ContextPicker.vue, condition_validator.js
- components/rule_config/types/ConditionStep.vue
- rule_builder/utils/condition_payload.js
- stores/useGraphStore.js, stores/useRuleStore.js
- controls/FlexValueControl.vue and controls/value_resolver/{strategies.js,index.js,useValueResolver.js,utils.js} plus operation config components.

Required behavior:
1. Builder loads canonical envelope. A single explicit adapter converts supported old formats for display and marks unconvertible payloads with a blocking error; hydration must not guess silently.
2. Builder edits a temporary reactive tree with temporary UI IDs. Save strips those IDs and emits canonical schema/version/root only.
3. ConditionGroupUI exposes one AND/OR operator per group. Mixed logic requires a nested group. If an old tree used per-condition joins, the UI shows its converted grouping only where semantics are unambiguous; otherwise it presents the migration issue instead of silently changing logic.
4. SimpleCondition edits both operands through the same FlexValue contract. Left operand defaults to a variable/path picker but supports permitted resolvers and typed static values through the same control model. Keep field metadata available for operator filtering when left is a direct field reference.
5. When left is a resolver, derive allowed comparison operators from its declared output type. Unknown/dynamic output type uses a conservative operator subset or requires an explicit typed result; do not display operators the server will reject.
6. Resolver config editor outputs family + operation + typed config, without requiring a generated Python string. compileToCode may remain a UI label/display helper while legacy formats exist, but its result is not persisted as executable condition truth.
7. CollectionUI creates explicit collection_predicate nodes with a valid source FlexValue, validated as alias and a nested condition subtree.
8. Generate operator metadata/options from the backend definition. Remove duplicate static frontend operator fallback maps only when the metadata endpoint is reliable; never trust frontend validation to enforce execution security.
9. FlexValueControl's required/optional empty defaults must respect value_type and caller context. A missing resolver config must be an invalid draft, not a generic blank resolver that happens to become None.
10. Revisit manual mode. It must not emit raw Python/Jinja as a canonical condition operand. For other FlexValue consumers, migrate visual token mode to template/resolver nodes; decide whether manual expressions are retired before production or remain an explicitly separate, narrowly sandboxed legacy feature.
11. Keep non-condition controls functional: Assignment values, Query Records output values, process inputs and text/template values all need fixtures/tests for the canonical FlexValue adapter before the old value contract is removed.

### 7.2 API and contract DTO

- Add/extend an API response that publishes canonical condition schema version and the authoritative operator metadata; avoid a UI-only duplicate registry.
- Publish resolver families, operations, config schema, output type where available, resolverLevel requirement and condition_operand_allowed.
- Apply authorization and resolverLevel checks server-side in create/save/activation and at runtime where the capability can vary by caller/site.
- Keep payloads JSON-compatible across builder, import/export, API DTO, storage and execution. Add explicit schema/DTO tests for each boundary.

## 8. Exact file-level change plan

The order below is intentional. Add tests alongside each stage; do not begin the production switch before the parity and migration gates pass.

### Stage 0 — Freeze scope and contract

**Goal:** Agree on schema and semantics before implementation.

1. Add the schema contract under a backend-owned canonical source, proposed:
   - flexirule/ruleflow/core/condition_contract.py — node/operator definitions, schema version, value/reference types, validation metadata and error types.
   - flexirule/ruleflow/core/flexvalue_contract.py — FlexValue family/operation schemas, coercion policy and resolver capability metadata.
   - JSON Schema files under flexirule/ruleflow/schemas/condition.schema.json and flexirule/ruleflow/schemas/flexvalue.schema.json (or another agreed package schema location).
2. Define exact condition and FlexValue examples and negative schemas in test fixtures; record version 1 schema compatibility rules.
3. Document every current operator, resolver family, operation, context root, consumer and legacy field.
4. Decide like/not like, regex, has_changed, identity operators, lookup permissions, resolverLevel, empty condition rules, and legacy raw-expression policy before coding runtime.
5. Create a traceability matrix: requirement -> contract identifier -> implementation module -> unit/integration test.

**Gate:** Contract reviewed; no unresolved semantic decision capable of changing user data or changing pass/fail behavior.

### Stage 1 — Canonical FlexValue + strict resolver boundary

**Goal:** Make new FlexValues unambiguous before letting the condition evaluator use them.

Target files:
- flexirule/ruleflow/core/value_resolver.py
- new flexirule/ruleflow/core/flexvalue_contract.py (or equivalent backend-owned schema/registry)
- FlexValueControl.vue and controls/value_resolver/{strategies.js,index.js,useValueResolver.js,utils.js}
- resolver operation components under controls/value_resolver/components/
- tests: test_value_resolver_core.py, test_value_resolvers_complex.py, test_assignment_resolver.py, test_fetch_resolver.py; add a dedicated canonical FlexValue contract test module.

Tasks:
1. Add strict parsing/validation of canonical FlexValue variants and each family/operation config.
2. Implement a boundary adapter from current FlexValue shapes to canonical variants for deterministic migrations only. Keep the legacy adapter separate from the canonical runtime resolver.
3. Implement canonical variable path resolution for scope + segments; remove ambiguous fallback from the canonical path. Reuse FieldResolver after allowed-path validation.
4. Implement resolver config schemas with FlexValue nested inputs and declared result types/capabilities.
5. Use one structured runtime path for canonical resolver payloads. Reject unknown family/op/config, and enforce resolverLevel on the server. Never map malformed configuration to NoneResolver.
6. Preserve the current value resolver's legitimate capabilities through explicit operation schemas, not through Python/Jinja expression fallback.
7. Align UI defaults, serialization, labels and Python constructor behavior. Fix legacy alias mismatches and preserve visual config when users switch editing modes; manual input may not erase the structured config without an explicit separate-mode decision.
8. Add cross-boundary tests: FlexValueControl output fixtures -> backend validator -> ValueResolver runtime result; cover every family and operation, allowed/disallowed level, missing/malformed config, typed null/decimal/date, nested FlexValue arguments, variable paths, and template segments.

**Gate:** Canonical FlexValue round-trips from UI/JSON to backend with stable type and meaning; every resolver config has tests and server-side policy enforcement; existing Assignment/Query/Process value behavior has regression coverage.

### Stage 2 — Canonical condition contract and direct evaluator

**Goal:** Implement one evaluator over canonical AST, with both operands using FlexValue.

Target files:
- new flexirule/ruleflow/core/condition_contract.py and condition runtime/evaluator module (reuse evaluator.py only if boundaries remain clear)
- flexirule/ruleflow/core/evaluator.py
- flexirule/ruleflow/core/compiler.py (restrict to legacy/raw expression adapter during transition, then deprecate JSON-to-Python compilation)
- flexirule/ruleflow/core/condition_payload.py (replace broad mixed-format parser at canonical boundaries with a strict loader plus explicit migration converter)
- flexirule/ruleflow/utils/field_resolver.py only for validated path traversal, if needed
- tests: test_evaluator.py, test_compiler.py (legacy tests revised to migration tests), add canonical condition schema, operators and evaluator parity tests.

Tasks:
1. Implement strict schema validation without changing the AST shape.
2. Implement typed context access, group evaluation, comparison, collection predicates and diagnostics.
3. Make evaluator evaluate each child only when reached; implement and instrument observable short-circuit tests.
4. Resolve left and right through the same canonical FlexValue resolver with operation-specific permissions.
5. Build one operator registry; add operator arity and type validation; remove fallback-to-equality and unknown-node/empty-to-True behavior from canonical paths.
6. Make missing, null, empty string, false, zero, decimal, date, Link/Dynamic Link and type-error behavior explicit.
7. Make collection predicates call the shared evaluator with parent document + row + scoped alias. Reject invalid collection source/alias/where and enforce limits.
8. Treat evaluation errors as typed errors, not false results and not true pass-throughs. Attach a safe AST path and Rule/action identifier to diagnostics.
9. Do not add any persisted execution-plan field and do not make the validator write rewritten/normalized AST.

**Gate:** Canonical node schema, all operator contracts and short-circuit behavior pass tests; invalid payloads cannot evaluate as a passing condition; no canonical condition generates or evaluates Python code.

### Stage 3 — Frontend writes the canonical tree

**Goal:** Visual builder emits the exact same contract tested by backend.

Target files:
- ConditionBuilder.vue, ConditionGroupUI.vue, ConditionNode.vue, SimpleCondition.vue, CollectionUI.vue, condition_validator.js
- ConditionStep.vue
- rule_builder/utils/condition_payload.js
- stores/useGraphStore.js, stores/useRuleStore.js
- FlexValueControl.vue and strategy config editors if Stage 1 did not complete all integration.

Tasks:
1. Introduce clear load/save adapters; use canonical envelope on load and save. No double stringification or nested condition / condition_tree / condition_json key aliases in new writes.
2. Update the UI tree to explicit node types; group operator belongs to group, not individual child joins.
3. Use FlexValue for both left and right, including resolver output type/operator compatibility.
4. Preserve ephemeral Vue IDs only in the UI and prove they never leak into persisted JSON.
5. Test new Rule, edit existing supported legacy Rule, clone/copy/paste, export/import, draft save, node-modal save, activation validation, root trigger filter, Condition action and nested collection editing.
6. Show migration diagnostics for unsupported payloads without dropping nodes or overwriting them with a blank model.

**Gate:** Load-edit-save round trip preserves AST exactly (excluding ephemeral UI IDs); front-end and back-end validators agree on valid/invalid fixtures; no unsaved user payload is silently replaced after a parse error.

### Stage 4 — Switch all runtime consumers in one controlled series

**Goal:** No semantic split remains between trigger/action/collection/assignment conditions.

Target files:
- flexirule/ruleflow/doctype/rule/rule.py — stop generating compiled_expression for canonical conditions; validation persists canonical payload only.
- flexirule/ruleflow/core/action_handlers/condition.py — evaluate canonical AST, then route true/false edges.
- flexirule/ruleflow/core/coordinator.py — trigger eligibility uses canonical AST and explicit trigger context.
- flexirule/ruleflow/core/engine.py — expose shared condition evaluation entry point/context utilities; remove Python condition evaluation from canonical consumer paths while preserving separate expression helper uses if still required.
- flexirule/ruleflow/core/action_handlers/sub_rule.py — target trigger filter through the same evaluator with caller and target-rule context.
- flexirule/ruleflow/core/action_handlers/assignment.py — replace compiled guard string with canonical when_condition AST. Do not use an empty compiled string to silently skip an invalid condition.
- flexirule/ruleflow/core/value_resolver.py — CollectionResolver uses same predicate evaluator for any/all/count/filter/etc.
- flexirule/ruleflow/core/action_handlers/__init__.py and flexirule/ruleflow/core/evaluator.py — audit and replace public/helper entry points that expect compiled Python condition strings, or restrict them to explicitly named legacy expression APIs.
- flexirule/ruleflow/core/validation_service.py — validate canonical conditions for full, draft, node, and activation/save flows without blocking incomplete draft workflows beyond the decided contract.
- Rule / Rule Action DocType JSON, import_export.py, API DTOs and rule builder stores as required.

Tasks:
1. Search repository-wide for ConditionCompiler, ConditionEvaluator, _evaluate_python_condition, evaluate_condition, compiled_expression, condition_json, condition_tree, when_expression, pythonExpression, when_condition, and raw mode/value fallbacks.
2. Build a consumer-to-contract matrix and give each call site an explicit migration in the PR. No consumer may fall back implicitly from canonical JSON to Python code.
3. In coordinator registry, store/obtain canonical trigger AST and update dependency/caching logic; never infer a safe skip set if dependencies cannot be complete.
4. All condition entry points call one shared service, pass an explicit context object and return a documented result/error.
5. Keep assignment mutating operations separate from comparison operators; reuse FlexValue only for the assignment operand value.
6. Update Rule and Rule Action DocType field descriptions/options and client contracts. Remove compiled_expression only after repository-wide consumer and import/export references are gone and the legacy-data plan passes.
7. Confirm all consumers use same semantics with integration tests, not just unit tests.

**Gate:** Repository search shows no active canonical condition path relies on generated Python; triggers, Condition actions, Sub-Rules, assignment guards and CollectionResolver predicates share the same evaluator/comparator.

### Stage 5 — Migrate existing saved payloads

**Goal:** Old saved Rule data is deterministically converted or explicitly rejected.

Target files:
- new migration converter alongside condition_payload.py / flexvalue_contract.py
- Frappe patch registered in patches.txt or the repository's current patch mechanism
- tests using realistic Rule and Rule Action payloads
- reports/migration output documented for maintainers.

Tasks:
1. Generate a read-only inventory before mutation, with counts by legacy shape/operator/resolver and affected Rule/action identifiers.
2. Implement deterministic v0->v1 conversion mappings as a separate explicit function, not part of runtime evaluation.
3. Add an idempotent patch that converts only unambiguous payloads and writes v1 canonical envelopes. Back up/export first on the dedicated test site.
4. Produce a report for ambiguous/unconvertible records. Include a safe reason and remediation; do not dump full business values/documents.
5. Explicitly reject or require manual editing for mixed-logic chains, raw Python conditions, has_changed, uncertain like/not like, unknown operators, malformed JSON/trees, missing resolver config and unknown family/operation.
6. Keep compatibility fields for one planned transition only if needed. When canonical migration is complete, no runtime dual-read or compiled-expression fallback remains.
7. Re-run migration twice in tests to prove idempotence. A second run must not alter a canonical payload.
8. Verify import/export and clone/copy/paste round trips after migration.

**Gate:** Every inventoried payload has a documented state: migrated and parity-proven, or rejected with a clear manual remediation. Migration is repeatable and preserves original data when conversion is not deterministic.

### Stage 6 — Benchmarks, system tests, and legacy removal

**Goal:** Verify correctness first, then performance in the supported Frappe Bench.

Commands to use in the maintained Bench (adapt paths/site to actual environment; do not claim results until executed):
- Focused modules: bench --site <test-site> run-tests --module flexirule.ruleflow.tests.test_evaluator
- Resolver tests: bench --site <test-site> run-tests --module flexirule.ruleflow.tests.test_value_resolver_core
- Related integrations: bench --site <test-site> run-tests --module flexirule.ruleflow.tests.test_coordinator
- Full app: bench --site <test-site> run-tests --app flexirule
- Backend lint: ruff check flexirule
- Frontend lint: yarn lint
- Build: bench build --app flexirule
- Relevant Cypress/UI tests: bench --site <test-site> run-ui-tests flexirule --headless and the focused Rule Builder/condition-builder specs documented in E2E_TESTING.md.

Run supported Frappe v15/Python 3.10 first; test other versions only if they remain supported. Track the exact SHA, commands, versions and outputs in the final implementation PR.

Benchmark cases:
1. Current production trigger/Condition path through safe_eval (baseline).
2. Canonical direct AST evaluator.
3. Direct JSON evaluator baseline only where it is semantically equivalent.
4. Any optional ephemeral cache only after the direct evaluator correctness baseline.

Measure separately:
- parse and schema validation;
- value resolver creation/preparation;
- cold first use/cache miss;
- hot repeated evaluation;
- end-to-end repeated Rule execution;
- collection size/alias nesting;
- memory/cache growth and invalidation.

All approaches must run the same valid canonical semantics or a defined legacy fixture. Exclude preparation from prepared-execution timing and report it separately. Use short/simple, typical business, nested groups, mixed logic represented structurally, resolver operands, and collection predicates. Include error paths. A faster evaluator that has different semantics is not a valid win.

After integration and migration tests pass:
- remove/deprecate ConditionCompiler JSON-to-Python use;
- remove old evaluator operator map/legacy condition modes once no consumer needs them;
- remove raw condition-expression persistence and unused compiled_expression fields/DocType metadata through the correct migration;
- remove duplicate frontend operator maps and legacy shape fallbacks only when no reader/importer depends on them;
- retain restricted Python evaluation only for any separately approved expression feature, with its own explicit contract, never as condition fallback.

**Gate:** All tests/lint/build run results are recorded accurately; semantic test matrix passes; benchmarks include cold/hot/end-to-end results; no legacy execution path remains reachable for canonical payloads.

## 9. Test plan and acceptance criteria

Create a table-driven suite with the same fixtures evaluated through every consumer where applicable.

### Schema and validation
- Every valid canonical node/FlexValue/family-operation config accepted.
- Wrong schema/version/node/extra key/missing property/operator/operand arity rejected with a stable path.
- Unknown path scope, invalid field/segments, dunder/call syntax, alias shadowing and resolver policy bypass rejected.
- Depth/node/config size/work limits enforced.
- Empty groups rejected; no configured optional trigger/assignment guard treated distinctly from malformed/empty tree.
- UI node ID never persists.

### Logical semantics and short circuit
- single-node, AND, OR, nested groups, De Morgan counterexamples, and sequence order;
- AND false at child A means child B probe never runs;
- OR true at child A means child B probe never runs;
- mixed logic has nested structure, so no implicit host-language precedence;
- no child evaluator/resolver call happens after the group result is decisive.

### Operators and values
- every retained operator, arity and supported fieldtype;
- aliases only in migration tests;
- missing, null, empty string, whitespace, false, zero, list/dict empty, wrong RHS types;
- integer, decimal/currency precision, Check, Date, Datetime, Time, Link, Dynamic Link and Select;
- Link target DocType mismatch, membership arrays vs Link tuples, invalid date conversion;
- like/not like, regex, has_changed, is/is-not explicit decisions tested;
- runtime error distinguishable from false; safe diagnostics omit document contents.

### FlexValue
- static types, variable path, nested reference path, variable scope rules;
- each resolver family/operation, nested resolver operands, output-type compatibility;
- template segment ordering; null handling in template output;
- resolverLevel enforced server-side at save/activation and runtime where necessary;
- malformed/missing/unknown resolver config rejected;
- old aliases map deterministically or produce migration issues;
- manual Python/Jinja conditions rejected by canonical condition schema;
- lookup permission behavior verified, not simply mocked away.

### Consumer integration
- Rule trigger filters (regular events), missing trigger filter, old_doc and context;
- Condition action true/false graph routes;
- callable Sub-Rule eligibility with caller/target-rule vars;
- assignment run-if guard false/true/error; an invalid guard can never become unconditional execution;
- CollectionResolver count/sum/avg/any/all/first/filter/pluck/unique using shared predicates and row aliases;
- imports, export/import, clipboard copy/paste, Rule clone, save draft, validate/activation and UI edit round-trip;
- condition caches are invalidated/rebuilt on Rule changes and never leak context/results across documents/users/sites.

### Acceptance checklist
- [ ] One canonical Condition envelope and one FlexValue union; no competing canonical schemas.
- [ ] Both comparison operands accept the same documented FlexValue types, subject to operator/family policy.
- [ ] No canonical condition is persisted as generated Python.
- [ ] Server validation is authoritative and strict; no malformed/unknown-to-equality or empty-to-True fallback.
- [ ] One evaluator/comparator is used by every condition consumer listed in Stage 4.
- [ ] Direct runtime evaluates canonical AST, with no separately persisted normalized JSON.
- [ ] Runtime errors are not disguised as ordinary false results or unconditional passes.
- [ ] Deterministic and ambiguous migration cases are separately reported; migration is idempotent.
- [ ] FlexValue output and resolver config round-trip and remain valid in assignment, query, process and template consumers.
- [ ] ResolverLevel and lookup permission rules are enforced on backend, not just in Vue.
- [ ] Short-circuit is proven with observable non-execution tests.
- [ ] CI/Bench tests, lint, bundle, and relevant UI tests are actually run on supported versions and results are recorded.
- [ ] Only after these gates pass are Python compiled-expression fields and legacy conversion paths deprecated/removed.

## 10. Risks and controls

| Risk | Control |
|---|---|
| Left-side resolvers change inferred operator choices | Resolver output types and operator compatibility are part of the contract; UI and server use the same definitions |
| FlexValue contract refactor breaks assignments/query/process values | Build the canonical value adapter and cross-consumer regression fixtures before adopting FlexValue in conditions |
| Current Rule JSON has mixed sibling joins with engine-dependent semantics | Inventory them; migrate only if the intended grouping is clear; otherwise require manual review |
| Legacy manual expressions cannot be safely represented as structured AST | Do not guess; keep separate temporarily or require rewrite before release |
| Lookup resolver bypasses permissions or becomes a per-condition query cost | Define authorization and query limits before enabling lookup in conditions |
| Resolver recursion/collection nesting increases work or permits denial of service | Explicit depth, node, row, and execution limits; bounded caches and no regex without policy |
| Schema and metadata duplicated between Python and Vue drift again | Backend-owned operator/family contract and DTO-generated front-end metadata |
| Old compiled_expression fields and caches keep stale behavior alive | Repository-wide call-site inventory, explicit migration version, updated cache keys/invalidation and final dead-code removal |
| Validation begins blocking incomplete drafts | Preserve draft/node/full validation distinctions; only enforce activation-only rules during activation while always rejecting unsafe malformed payloads |
| Runtime error policy changes trigger/save behavior | Make error-vs-false semantics explicit and test blocking and non-blocking Frappe event paths |

## 11. Suggested PR sequence and review gates

Do not deliver this as one large production refactor. Create the following focused implementation PRs against the then-current develop branch:

1. **Contract only:** canonical JSON Schemas, typed definitions, decision table, fixtures and documentation. No runtime switch.
2. **FlexValue contract and resolver boundary:** canonical adapter, strict backend validation, server resolverLevel/capability checks, and tests for all existing FlexValue consumer classes.
3. **Direct condition evaluator:** schema validation, comparator registry, context resolver, AST evaluation, short circuit, and tests. Keep production switch off or behind a temporary internal test harness.
4. **Builder contract:** update loading/editing/serialization; both operands use FlexValue; canonical round-trip tests; no runtime switch until parity accepted.
5. **Consumer integration:** trigger, Condition action, Sub-Rule, assignment guards, CollectionResolver, API/import-export and caches.
6. **Migration PR:** inventory tool, deterministic migration and refusal report; run on dedicated test site; idempotency and saved Rule integration tests.
7. **Bench + deprecation PR:** supported Bench and CI results, remove legacy JSON-to-Python path and unused fields only after all acceptance gates pass.

Each PR must report: base/head SHA, files changed, contract decisions implemented, tests actually run and results, tests not run and why, migration counts and unresolved records (when applicable), cache invalidation evidence, and remaining steps. Do not accept lint or build passing as evidence that runtime tests passed. Keep the plan/report separate from implementation code.

## 12. Scope boundaries

This plan does **not** call for:
- a second persisted normalized/compiled condition JSON;
- a CEL migration or external expression language;
- an AST optimizer / Boolean algebra rewriter;
- a new assignment operator registry;
- rewriting Query Records filters into condition predicates by assumption;
- allowing arbitrary Python or Jinja as a canonical condition operand;
- claiming that the design or any tests are already implemented/passing.

Query filters may share FlexValue for values where that is appropriate, but Frappe query filter semantics remain a distinct contract. Assignment operators mutate target data and remain distinct from condition comparison operators.

## 13. Audit verification and limitations

Verified source files and tests were inspected at develop commit 60c5005e69d5899765748c561f8f426078c008f0. The audit included condition payload parsing, Rule save-time compilation, trigger eligibility, Condition action routing, Sub-Rule condition checks, Assignment run-if guard compilation, CollectionResolver/ConditionEvaluator use, FlexValue runtime compilation, resolver strategy metadata, Condition Builder hydration/serialization, frontend validation, and existing condition/value resolver tests and prior architecture reports.

This was a remote source/report review, not a local Bench execution. No Frappe test suite, UI suite, lint, build, or database migration was run while preparing this plan. Any implementation result must be verified in the supported Bench and recorded with exact commands and outputs.

## Final recommendation

**Make FlexValue the reusable typed operand contract and canonical condition JSON the reusable logical AST.** Both left and right operands use the same FlexValue union. Resolver config inputs use that union recursively. The visual builder emits that contract; the server validates it strictly; one direct evaluator executes it across every condition consumer. JSON remains the single source of truth, and any runtime cache is an optional, discardable optimization.

Start by ratifying Stage 0's decisions and Stage 1's FlexValue schemas. That is the foundation that prevents the condition redesign from creating another parallel value language.
