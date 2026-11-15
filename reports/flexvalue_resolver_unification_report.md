# FlexValue and Resolver Architecture: Integration Status & Historical Benchmark Record

## 1. Current Architecture Status

This report describes the architecture at the current PR review baseline. It does **not** claim that every historical FlexValue/resolver call site has been removed or that all legacy compatibility code is inactive.

- **Shared resolver registry:** `ValueResolver.REGISTRY` aliases `CONDITION_RESOLVER_REGISTRY`; built-in resolver metadata and factories are registered centrally. The condition-specific and general FlexValue validation entry points remain distinct because they enforce different consumer contracts.
- **Canonical condition validation:** `condition_contract.validate_condition_node()` uses the strict condition FlexValue contract. Resolver operands are deny-by-default; a condition-enabled resolver must declare `permission_policy="no_data_access"`.
- **General FlexValue validation:** `ValueResolver.validate_flex_value()` applies the requested consumer's supported-consumer policy. Resolver config validators receive and preserve that consumer for every nested FlexValue.
- **Compilation boundary:** `ValueResolver.compile_flex_value()` validates canonical static, variable, resolver, and template payloads before compilation. The separate `ValueResolver.compile()` API remains for explicitly retained legacy payloads and must not be treated as the canonical validator/compiler.
- **Condition runtime:** Canonical conditions are validated and compiled into prepared plans and evaluated as structured AST; no Python expression or `safe_eval` compilation is used for canonical nodes. AND/OR evaluation short-circuits.
- **Legacy boundary:** The legacy condition evaluator remains reachable from `CollectionResolver` only for non-canonical predicates. It is deprecated compatibility code and is not the canonical path.

### Resolver security invariant

A resolver that is allowed as a condition operand must be read-only and declare `permission_policy="no_data_access"`. Nested resolver configuration is validated under the same consumer as its parent; this prevents an approved outer resolver from hiding a database-backed `lookup.fetch` operation in a nested source/offset. The general resolver registration API enforces the same invariant as the condition-specific registration API. Every mutation of the shared registry invalidates the single shared resolver fingerprint used by prepared-condition and request-local FlexValue cache keys. Request-local cache entries are keyed by action, operand, consumer, and fingerprint. Callers without a known consumer use the fail-closed `all` consumer, which cannot invoke a resolver restricted to Assignment, Query Records, or another named consumer.

## 2. Historical Benchmark Record (Not Current-Head Evidence)

The committed benchmark artifacts below were generated on **29 October 2026**, using protocol **v3**, branch `jules-3100235434379853320-7a89fca0`, commit `5ce124cbc1b2a6b2b879af0f242a1ddc6e814a77`, with a dirty working tree. They are retained as historical experiment data only. The current benchmark runner uses protocol v5; these numbers and the historical test totals below are **not evidence for the current PR head** and must not be used as current performance claims.

### Historical workloads evaluated
- Simple conditions with multiple scalar operands.
- Nested AND/OR conditions.
- Condition trees with dynamic resolver operands.
- Short-circuit lazy execution verification.

### Historical results
- **Cold Compilation:** ~0.012s across the condition validation test suite (historical protocol-v3 run).
- **Warm Cached Plan Execution:** historical measurement only; it is not a claim of zero runtime overhead.
- **Lazy Short-Circuit Invocations:** 0 invocations executed on short-circuited branches in the historical test run.
- **Backend / JavaScript / Cypress totals:** the historical totals below are preserved as recorded at the time and are not current-head CI results: 738 backend tests passed (2 skipped), 35 fast JS tests passed, and the historical smoke Cypress flow passed.
- **Production selection:** remains **Not established**. No candidate is declared production-selected from this historical benchmark.

## 3. Registered Resolver Catalogue

The list below describes registered built-ins; registration does not imply that every operation is allowed in every consumer. In particular, `lookup.fetch` is not a condition operand.

1. `date_time.current` -> `DateCurrentResolver` (output: `Date`)
2. `date_time.calculate` -> `DateFormulaResolver` (output: `Date`)
3. `date_time.diff` -> `DateDiffResolver` (output: `Int`)
4. `date_time.extract` -> `DateExtractResolver` (output: `Int`)
5. `date_time.boundary` -> `DateBoundaryResolver` (output: `Date`)
6. `date_time.format` -> `FormatResolver` (output: `Data`)
7. `math.formula` -> `MathFormulaResolver` (output: `Float`)
8. `text.combine` -> `StringFormulaResolver` (output: `Data`)
9. `text.case` -> `StringFormulaResolver` (output: `Data`)
10. `text.normalize` -> `NormalizationResolver` (output: `Data`)
11. `text.format` -> `FormatResolver` (output: `Data`)
12. `lookup.fetch` -> `LookupResolver` (output: `Data`; authorized-read consumer only)
13. `collection.*` (`any`, `all`, `count`, `sum`, `avg`, `first`, `last`, `filter`, `pluck`, `unique`) -> `CollectionResolver`
14. `system_context.get` -> `SystemContextResolver` (output: `Data`)

## 4. Remaining Release Evidence

- Run the read-only condition inventory against a representative site/export and review ambiguous legacy payloads before defining any write migration.
- Keep a complete consumer-by-consumer execution matrix for trigger eligibility, Condition routing, Sub-Rule eligibility, Assignment guards/no partial mutation, collection predicates, Text Generator loop aliases, and preview/helper routes.
- Regenerate benchmark JSON/Markdown from protocol v5 on a clean checkout before making performance claims or selecting a production implementation.
- Continue adversarial tests for payload depth/size, cyclic input, nested collection budgets, and metadata changes after plan-cache hits.
- Keep resolver families deny-by-default until each enabled family has reviewed output typing, permissions, resource budgets, and regression coverage.
