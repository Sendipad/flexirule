# FlexiRule Value Resolver Architectural Verification & Improvement Analysis

**Generated Date:** March 2026
**Source Repository:** FlexiRule (Frappe Framework App)
**Report File Path:** `reports/value-resolver-architectural-analysis.md`
**Task Scope:** Architectural analysis, source code verification, design evaluation, and strategic recommendations only. No application code, UI components, contracts, or tests were modified during this pass.

---

## Executive Summary & Recommended Architectural Direction

This architectural pass evaluates the current implementation of FlexiRule's Value Resolver system against real-world engineering demands across Assignment, Conditions, Query Filters, and Rule Execution.

### Key Conclusions:

1. **Current Architectural Nature:**
   The current FlexiRule Value Resolver is **fundamentally a collection of operation-specific, field-bound UI forms**, rather than a general composable Value/Expression system. While it provides high UI usability for single-step operations (e.g. adding 5 days to a date or fetching a single field from a linked document), it lacks a recursive composition engine.

2. **Composition Limitation:**
   Resolvers cannot pipe their output directly into another resolver as a generic input operand. Every resolver component independently defines custom "field-vs-constant" inputs (e.g. `field_a`/`field_b`, `base_field`, `fmt_field`, `norm_field`, `record_field`), assuming that inputs are top-level document field names rather than nested expressions. Composition currently relies on TipTap rich-text string joining (`ExpressionResolver`) or inline Python string templates (`{ ... }`), which bypasses strong type checking and structured validation.

3. **Core Recommendation (Target Architecture):**
   FlexiRule should **not** solve this by adding dozens of new specialized resolver operation components. Instead, FlexiRule should introduce a **small, typed, recursive `ValueExpression` primitive** that unifies scalar inputs, variable references, and nested resolver operations. This will unlock arbitrary composition (e.g. `Lookup -> Text Transform -> Assignment` or `Collection Aggregate -> Math Operation -> Condition`) without turning FlexiRule into an unsafe or unmaintainable arbitrary code environment.

---

## 1. Taxonomy Verification & Target Taxonomy

### Current Implementation Taxonomy vs. Target Architecture

| Taxonomy Layer | Current Implementation (`value_resolver.py` & `strategies.js`) | Legacy / Compatibility Taxonomy | Recommended Target Taxonomy (v2.0) |
| :--- | :--- | :--- | :--- |
| **Date & Time** | `date_time` (`calculate`, `diff`, `format`) | `date_formula`, `date_diff` | **`date_time`** (Unified temporal expression primitive) |
| **Text / String** | `text` (`combine`, `case`, `normalize`, `format`) | `string_formula`, `normalization`, `format` | **`text`** (String operations accepting composable operands) |
| **Math / Numeric** | `math_formula` (single `+`, `-`, `*`, `/`) | `math_formula` | **`number`** (Arithmetic, rounding, clamping, percentage) |
| **Collection** | `collection` (`sum`, `avg`, `count`, `any`, `all`, `first`, `find`, `filter`, `pluck`, `unique`) | `child_aggregation` | **`collection`** (Decoupled Filter -> Transform -> Aggregate pipeline) |
| **Lookup / Record** | `lookup` (`fetch`) | `fetch` | **`lookup`** (Static & Dynamic Link record field extraction) |
| **System Context** | `system_context` (`user`, `role_check`) | `system_context` | **`system`** (Session user, roles, company, time) |
| **Conditional** | *Deferred / Conflated into Collection filters* | None | **`conditional`** (Explicit `If / Else` scalar value selection) |
| **Field / Primitive** | Hardcoded per component (`base_field`, `field_a`, etc.) | None | **`value_source`** (Literal, Variable Path, Expression) |

### Key Source Discrepancies Verified:
* **Backend Normalization:** In `flexirule/ruleflow/core/value_resolver.py:698-724`, legacy configurations containing `kind: "child_aggregation"` or `kind: "fetch"` are converted into `CollectionResolver` and `LookupResolver` objects at runtime.
* **Operation Name Aliasing:** Frontend `CollectionResolver.vue` exposes `"find"` alongside `"first"`. In `value_resolver.py:228-229`, `CollectionResolver.__init__` maps `operation == "find"` directly to `"first"`.

---

## 2. Composition Audit: Token Nesting vs. True Resolver Composition

### Is FlexiRule Currently a General Composable Value Model?

**No.** The current implementation is **not** a general composable value model.

To prove this, we evaluated three realistic scenarios against the source code:

#### Scenario A: `doc.amount -> number.calculate -> round -> assignment`
* **Can this work today?** **No, not natively.**
* **Source Evidence:** `MathFormulaResolver` (`value_resolver.py:133-171`) accepts `field_a` (string field name) and `field_b_type` (`"field"` or `"constant"`). It cannot take another `MathFormulaResolver` payload as its `field_a` operand. To round a calculation result today, a user must write a raw Python template string `{flt(flt(doc.amount * 1.1), 2)}` in `ExpressionResolver` or `SafeEvalResolver`.

#### Scenario B: `doc.customer -> lookup Customer -> customer_group -> text transformation -> assignment`
* **Can this work today?** **No, not via resolver composition.**
* **Source Evidence:** `TextTransformResolver` (`TextTransformResolver.vue:85-115`) requires `norm_field` or `field` to be a field name on the primary document (`doc.fieldname`). It cannot take a `LookupResolver` structure as its input target.

#### Scenario C: `doc.items -> filter(condition) -> pluck(amount) -> sum -> compare`
* **Can this work today?** **Partially (within CollectionResolver only).**
* **Source Evidence:** `CollectionResolver` (`value_resolver.py:209-342`) combines filtering, field plucking, and aggregation inside a single class (`self._compiled_evaluator = ConditionEvaluator(...)`). However, the numeric result of this collection aggregation cannot be piped into a `MathFormulaResolver` or `DateFormulaResolver` without saving it to an intermediate context variable or embedding it in a Python expression.

### Structural Root Cause:
TipTap tokens (`ResolverTokenView.vue`) serialize expressions as text strings concatenated by `ExpressionResolver` (`value_resolver.py:606-618`):
```python
class ExpressionResolver(CompiledResolver):
    def resolve(self, context: dict) -> Any:
        parts = []
        for seg in self.segments:
            val = seg.resolve(context)
            parts.append(str(val) if val is not None else "")
        return "".join(parts) # Concat strings only!
```
Because `ExpressionResolver` converts all segment outputs into string text parts and concatenates them, it cannot pass typed object outputs (numbers, dates, lists, record dicts) between nested resolvers.

---

## 3. Repeated Field-Specific Inputs & Generalized Value Expression Abstraction

### Source Code Audit of Field-Specific Inputs

Every resolver operation in FlexiRule currently duplicates its own input parameter logic:
* `DateTimeCalculateConfig.vue`: `base_type` (`"today"` | `"doc_field"`), `base_field`
* `DateTimeDiffConfig.vue`: `diff_start_type`, `diff_start_field`, `diff_end_type`, `diff_end_field`
* `TextTransformResolver.vue`: `str_a_type` (`"field"` | `"constant"`), `str_a`, `str_b_type`, `str_b`, `field`, `norm_field`, `fmt_field`
* `MathFormulaResolver.vue`: `field_a`, `field_b_type` (`"field"` | `"constant"`), `field_b`, `constant_b`
* `LookupResolver.vue`: `record_source_type` (`"doc_field"` | `"variable"` | `"expression"`), `record_field`

### Proposed Architecture: The Unified `ValueExpression` Contract

Instead of repeating `field_a_type`, `field_b_type`, `base_type`, etc. across every Vue component, every operand slot should conform to a single recursive `ValueExpression` structure:

```json
{
  "type": "literal | path | resolver",
  "value": "100" | "doc.amount" | {
    "family": "lookup",
    "operation": "fetch",
    "config": { ... }
  }
}
```

#### Cost vs. Benefit Analysis:
* **Benefit:** Eliminates redundant "field vs constant" UI toggles in every component. Allows any operation slot (e.g. math operand, date base, text target) to accept a literal value, a document field path, or a nested resolver result.
* **Cost:** Requires a small update to frontend control slots so they can render either a standard `ComboBoxControl`/`DataControl` or an inline `<ValueResolverControl>`.

---

## 4. Collection Semantic Layers Analysis

`CollectionResolver` (`flexirule/ruleflow/core/value_resolver.py:209-342`) currently mixes four distinct semantic operations into a single class:

```text
[Collection Source] → [Filter Condition] → [Transform / Pluck] → [Aggregate / Scalar]
```

### Analysis of Semantic Layers:

1. **Collection Source:**
   * Currently supports `doc.table_field` and `vars.list_var`.
   * **Gaps:** Does not support querying collections from linked documents (e.g., `Customer -> Sales Invoices`) or nested child tables (child table inside child table) without custom Python handlers.

2. **Filter:**
   * Currently compiles `condition` into `ConditionEvaluator` (`evaluator.py:18`).
   * **Strength:** Supports complex AND/OR groups on `row.fieldname`.

3. **Transform / Project:**
   * Currently supported via `pluck` (extract array of field values) and `unique` (extract deduplicated array).
   * **Gaps:** Cannot apply arbitrary transformations (e.g., multiply `row.qty * row.price` before plucking).

4. **Aggregate / Scalar Extraction:**
   * Supported: `sum`, `avg`, `count`, `any`, `all`, `first` (alias `find`), `filter`, `pluck`, `unique`.
   * **Gaps:** Missing `min` and `max` operations.

### Recommendation:
Do **not** create separate standalone UI components for every step. Keep the single UI form for `Collection Query`, but update `CollectionResolver` backend implementation to explicitly organize its execution into clean, modular methods (`_filter_rows`, `_transform_rows`, `_aggregate_rows`), adding missing `min` and `max` operators.

---

## 5. Conditional Values vs. Collection Filtering

### Semantic Distinction

There is a critical semantic difference between **Collection Filtering** and a **Conditional Value Expression**:

* **Collection Filtering (`items.filter(condition)`):**
  Filters a list of row items down to a subset matching a criteria. The output is a **list of rows** or a **collection aggregate**.
* **Conditional Value Expression (`If(condition, value_a, value_b)`):**
  Evaluates a boolean condition against scalar or document context. If `True`, returns `value_a`; if `False`, returns `value_b`. The output is a **single scalar value**.

### Current Gap in FlexiRule:
In the current code, conditional evaluation for assignments exists only at the row guard level in `AssignmentHandler` (`assignment.py:65` via `when_expression`). If a user wants to assign `doc.discount` to `10` if `doc.grand_total > 1000` else `5`, they must either:
1. Create two separate Assignment rows with conflicting `when_expression` guards, OR
2. Write a Python ternary expression `{ 10 if doc.grand_total > 1000 else 5 }`.

### Recommendation:
Introduce an explicit top-level **`conditional`** resolver family (`{ family: "conditional", operation: "if_else", config: { condition, then_value, else_value } }`) to handle scalar ternary selection visually without requiring raw Python.

---

## 6. The Three Semantic Domains

To maintain clean architectural boundaries, FlexiRule must explicitly distinguish between three semantic domains:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                          1. VALUE EXPRESSION                             │
│  Produces a typed value (Scalar, List, Dict) for Assignment & Action UI  │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   2. PREDICATE / CONDITION EXPRESSION                    │
│  Produces Boolean (True / False) for Decision Nodes & Collection Filters │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            3. QUERY EXPRESSION                           │
│  Translates filters into Frappe DB / SQL AST ([doctype, field, op, val]) │
└──────────────────────────────────────────────────────────────────────────┘
```

### Domain Boundary Audit:

1. **Value Expression (Domain 1):**
   * Implemented in `ValueResolver` (`value_resolver.py`). Evaluates to concrete runtime objects (`int`, `float`, `str`, `dict`, `list`).

2. **Predicate / Condition Expression (Domain 2):**
   * Implemented in `ConditionEvaluator` (`evaluator.py`) and `ConditionCompiler` (`compiler.py`).
   * **Boundary Violation Identified:** `CollectionResolver` embeds `ConditionEvaluator` inside its `resolve()` method (`value_resolver.py:234`). This is a valid domain bridge (Value Domain calling Predicate Domain to filter items), but `ConditionEvaluator` should remain a separate, non-duplicated module.

3. **Query Expression (Domain 3):**
   * Implemented in `QueryRecordsHandler` (`query_records.py:719-997`).
   * **Boundary Violation Identified:** `QueryRecordsHandler` previously attempted to execute in-memory resolvers inside SQL filter arrays. In the latest alignment (`reports/query_records_architecture_alignment_final_pass.md`), Query Filters evaluate Domain 1 Value Expressions first to get scalar/list primitives, then pass native 4-tuples (`[child_doctype, field, op, val]`) to Frappe's `DatabaseQuery` / `frappe.get_list`.

---

## 7. Query Filters Alignment with Frappe DB Semantics

### Evaluation of `QueryRecordsHandler` (`query_records.py`) against Frappe Framework (v15+)

`QueryRecordsHandler` processes query filters through `_resolve_query_filters()` (`query_records.py:719`) and `_normalize_filters_for_backend()` (`query_records.py:929`).

#### Comparison Matrix:

| Filter Scenario | Frappe DB Capability | FlexiRule `QueryRecordsHandler` Behavior | Status / Alignment |
| :--- | :--- | :--- | :--- |
| **Scalar Comparison** (`=`, `!=`, `>`, `<`) | Native SQL WHERE clause | Resolves value via `ValueResolver.compile()`, normalizes 4-tuple `[dt, field, op, val]` | **Aligned** |
| **List Membership** (`in`, `not in`) | Native SQL `IN (...)` | Coerces scalar to list or accepts array from `CollectionResolver` | **Aligned** |
| **Date & Timespan Ranges** | Native SQL `BETWEEN` | Resolves `_coerce_between_value()` (`query_records.py:785`) and `_resolve_timespan_range()` | **Aligned** |
| **Dynamic Linked Values** | Dynamic table joins | Translates `doctype.field` or child table paths via `frappe.get_meta` | **Aligned** |
| **System Context** (`user`, `company`) | Session context | Resolves `sys_token="user"` to `frappe.session.user` before query execution | **Aligned** |
| **Permission Enforcement** | Frappe DocPerm | Enforces `ignore_permissions` flag; checks `frappe.has_permission(doctype, "read")` | **Aligned** |

---

## 8. End-to-End Execution Traces

### Trace 1: Assignment Action (`AssignmentHandler.execute`)

**Target Path:** `doc.due_date`
**Configuration Payload:**
```json
{
  "target": "doc.due_date",
  "operator": "set",
  "value": {
    "family": "date_time",
    "operation": "calculate",
    "config": {
      "base_type": "doc_field",
      "base_field": "posting_date",
      "offset_sign": "+",
      "offset_value": 15,
      "offset_unit": "days"
    }
  }
}
```

#### Execution Path:
1. **Action Plan Retrieval:** `AssignmentHandler.execute()` (`assignment.py:65`) retrieves the compiled rows.
2. **Target Validation:** `_validate_target_path("doc.due_date")` verifies prefix is `doc.` or `vars.` and not protected.
3. **Event Restriction Check:** `_validate_event_restrictions()` confirms `doc.` is not being mutated during `after_submit`.
4. **Resolver Compilation:** `get_compiled_resolver(action, "assign_0", row["value"])` (`value_resolver.py:880`) checks `frappe.local.flexirule_compiled_resolvers`. On miss, calls `ValueResolver.compile(value)`.
5. **Compilation Dispatch:** `ValueResolver.compile_resolver_config()` identifies `family == "date_time"` and `operation == "calculate"`, instantiating `DateFormulaResolver(base_type="doc_field", base_field="posting_date", offset_value=15, offset_unit="days")`.
6. **Runtime Resolution:** `resolver.resolve(context)` reads `get_context_value(context, "doc.posting_date")` (e.g. `"2026-03-01"`), executes `frappe.utils.add_days("2026-03-01", 15)`, and returns `"2026-03-16"`.
7. **Value Mutation:** `AssignmentHandler._set_value()` executes `doc.set("due_date", "2026-03-16")`.

---

### Trace 2: Condition Evaluation (`ConditionEvaluator.evaluate`)

**Condition Configuration:**
```json
{
  "left": { "ref": "doc.grand_total" },
  "op": ">",
  "right": {
    "family": "collection",
    "operation": "sum",
    "config": {
      "source": "doc.items",
      "target_field": "amount"
    }
  }
}
```

#### Execution Path:
1. **Evaluator Entry:** `ConditionEvaluator.evaluate(doc)` (`evaluator.py:38`) calls `_evaluate_group()`.
2. **Single Condition Resolution:** `_evaluate_single()` (`evaluator.py:136`) processes `left` and `right`.
3. **Left Operand:** `_resolve_value({ "ref": "doc.grand_total" })` calls `_get_field_value()` returning `1500.0`.
4. **Right Operand:** `_resolve_value()` detects dict payload, invokes `ValueResolver.compile_resolver_config()`, creating `CollectionResolver(source="doc.items", operation="sum", target_field="amount")`.
5. **Collection Execution:** `CollectionResolver.resolve(context)` fetches `doc.items`, extracts `amount` for each row, sums values returning `1200.0`.
6. **Operator Evaluation:** `OPERATORS[">"](1500.0, 1200.0)` evaluates `1500.0 > 1200.0` returning `True`.

---

## 9. Legacy Deprecation Plan

To modernize the resolver architecture without breaking existing rules, we recommend a 3-stage deprecation plan:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Stage 1: Runtime Aliasing & Normalization (CURRENT STATE)                │
│ Legacy kinds ('child_aggregation', 'fetch', 'find') transparently        │
│ mapped to canonical families ('collection', 'lookup', 'first') at runtime│
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Stage 2: UI Deprecation & Schema Normalization (NEXT RELEASE)            │
│ Hide legacy components from UI pickers; automatically rewrite legacy     │
│ JSON structures in rule_doc.visual_data during Rule save                 │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Stage 3: Code Cleanup & Legacy Handler Removal (v2.0 RELEASE)            │
│ Remove ChildAggregationResolver and FetchResolver wrapper classes;       │
│ raise explicit schema validation errors for un-migrated legacy payloads  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Deprecation Targets:

1. **`child_aggregation`**: Fully superseded by `collection` family (`operation: "sum" | "avg" | "count"`).
2. **`fetch`**: Fully superseded by `lookup` family (`operation: "fetch"`).
3. **`value_template_ui` / `value_template_json` in Assignment**: Legacy fallback fields in `assignment.py:155` superseded by standard `value` dictionary.

---

## 10. Core Architectural Answer

> **Question:** Is the current resolver model fundamentally a collection of operation-specific resolvers, or does it provide the foundation of a general composable Value/Expression system?

### Evidence-Based Answer:

The current resolver model is **fundamentally a collection of operation-specific resolvers wrapped in component-bound UI forms**.

It provides **isolated execution strategies** (`DateFormulaResolver`, `MathFormulaResolver`, `CollectionResolver`, `LookupResolver`), but lacks a **uniform recursive expression AST**. Because every operation component assumes its inputs are simple document field names rather than nested expressions, resolvers cannot be freely composed together without dropping down to raw Python string templates or custom code.

### Required Architectural Changes to Achieve a Composable Value/Expression System:

1. **Introduce a Recursive `ValueExpression` Contract:**
   Replace field-specific keys (`field_a`, `field_b`, `base_field`, `fmt_field`, `norm_field`) with standardized operand slots (`left`, `right`, `input`, `target`) that accept a unified `ValueExpression` payload (`literal`, `path`, or nested `resolver`).

2. **Decouple Frontend Controls from Specific Resolvers:**
   Update `ValueResolverControl.vue` to allow nesting an inline `<ValueResolverControl>` inside operand slots, enabling visual composition (e.g., placing a `Lookup` resolver inside a `Text Transform` operation).

3. **Preserve Execution Performance via Request Caching:**
   Retain `get_compiled_resolver()` (`value_resolver.py:880`) to cache compiled expression graphs in `frappe.local`, ensuring that recursive evaluation remains zero-overhead during high-throughput rule processing.

---

## Prioritized Recommendations Summary

| Priority | Recommendation | Category | Impact / Value |
| :--- | :--- | :--- | :--- |
| **P1** | **Adopt Recursive `ValueExpression` Input Contract** | Architecture | Enables true resolver nesting across Math, Text, Date, and Lookup operations. |
| **P1** | **Add Explicit `Conditional` Resolver Family** | Feature / Usability | Enables visual ternary `If/Else` scalar selection without raw Python expressions. |
| **P2** | **Add Missing Collection Operations (`min`, `max`)** | Completeness | Completes collection aggregation capabilities alongside `sum`, `avg`, `count`. |
| **P2** | **Execute Stage 2 Legacy Schema Migration on Save** | Maintainability | Cleanly migrates legacy `child_aggregation` and `fetch` records to canonical payloads. |
| **P3** | **Enhance ComboBoxControl Nested Field Suggestions** | UX | Improves auto-completion for child-table fields and linked DocType metadata. |

---

## Final Verification & Deliverable Disclosure

* **Report File Path:** `reports/value-resolver-architectural-analysis.md`
* **Verification Status:** All 10 required architectural verification areas have been analyzed and verified against the actual repository source code.
* **Code Modification Check:** `git status` confirms that **zero application source code or test files were modified** during this architectural verification pass.
