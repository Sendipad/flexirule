# Executive Summary: Value Resolver Architecture

## 1. Context & Objectives

FlexiRule is an enterprise rule engine built on the Frappe framework. Value Resolvers are the foundational mechanism used by FlexiRule actions (such as Assignments, Condition Evaluations, and Sub-rule Arguments) to compute dynamic values from document fields, expressions, formulas, context variables, and external lookups.

As FlexiRule prepares for its **first public/installable release**, this architectural investigation was conducted to eliminate development-era complexity and establish a clean, production-grade Value Resolver architecture.

---

## 2. Key Findings of Current State

1. **Fragmented User Mental Model**:
   The current UI exposes 10 implementation-centric resolver strategies (`date_formula`, `math_formula`, `date_diff`, `child_aggregation`, `string_formula`, `normalization`, `format`, `fetch`, `system_context`, `collection`) directly to the user. Users are forced to choose an *implementation strategy* first rather than stating *what kind of value* they are computing.

2. **Conceptual Duplication (`fmt_money`)**:
   Money and currency formatting logic is duplicated across `StringFormulaResolver.vue` (`str_op: "fmt_money"`), `FormatResolver.vue` (`fmt_op: "fmt_money"`), and backend action handlers.

3. **Collection vs Child Aggregation Ambiguity**:
   Both `CollectionResolver.vue` and `AggregationResolver.vue` handle table/list operations. While `child_aggregation` targets Frappe child tables specifically with direct SQL/Python math, `collection` provides memory-safe row predicate filtering and plucking. These represent different execution strategies for a single cohesive user concept: **Collections & Tables**.

4. **Zero Public Legacy Constraint**:
   Because FlexiRule has not had its first public/installable release, there is no external public API contract constraint. However, approximately 120 test assertions and internal development fixtures depend on existing resolver structures. A lightweight load/save normalization layer completely satisfies development compatibility while providing a clean canonical contract for v1.0.

---

## 3. Proposed First-Release Taxonomy

The proposed user taxonomy reduces 10 fragmented components to **8 cohesive value families**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FlexiRule Value Families                              │
├───────────────┬───────────────┬───────────────┬─────────────────────────────┤
│ Date & Time   │ Text          │ Number        │ Collections & Tables        │
├───────────────┼───────────────┼───────────────┼─────────────────────────────┤
│ Lookup        │ System        │ Conversion    │ Conditional                 │
└───────────────┴───────────────┴───────────────┴─────────────────────────────┘
```

### Family Summary

1. **Date & Time** (`date`): Calculate future/past dates, compute date differences, and format dates.
2. **Text** (`text`): String concatenation, case transformation, text normalization pipeline, and text formatting.
3. **Number** (`number`): Arithmetic operations, rounding, currency formatting (`fmt_money`), and percentages.
4. **Collections & Tables** (`collection`): Counting, predicate checks (`any`, `all`), row lookup (`first`/`find`), filtering, field plucking, uniqueness, and aggregation (`sum`, `average`).
5. **Lookup** (`lookup`): Fetching linked document fields or resolving related records.
6. **System & Context** (`system`): Contextual values such as current user, user roles, system date, and company context.
7. **Conversion** (`conversion`): Explicit type casting (`to_text`, `to_number`, `to_date`, `to_boolean`).
8. **Conditional** (`conditional`): Inline branching (`if_else`, `coalesce`).

---

## 4. Canonical Contract Schema

The canonical first-release persisted format replaces flat `kind` dispatch with a structured `family + operation + config` payload:

```json
{
  "family": "text",
  "operation": "normalize",
  "config": {
    "source_type": "field",
    "source_field": "doc.title",
    "pipeline": ["trim", "slug"]
  }
}
```

A transparent normalizer at `ValueResolver.compile_resolver_config()` automatically converts legacy `{ "kind": "normalization", ... }` structures into the canonical contract at runtime.

---

## 5. Architectural Benefits

- **Reduced Cognitive Load**: Non-technical Rule Designers select the data domain first, then choose from a clear dropdown of business operations.
- **Single Source of Truth**: Currency formatting (`fmt_money`) resides strictly under the **Number** family as `format_money`.
- **Extensibility**: Adding a new text operation (e.g., `regex_replace`) requires adding an entry to the `text` operation registry without creating a new Vue component or top-level concept.
- **Maintainability**: Pure separation between UI component, operation configuration, AST compilation, and backend execution runtime.
