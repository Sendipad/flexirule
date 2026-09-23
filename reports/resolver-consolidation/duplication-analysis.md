# Duplication Analysis

## Executive Summary
This document presents a conceptual and structural analysis of functional overlap across FlexiRule's existing value resolvers, demonstrating why consolidation is required and explaining the architectural boundaries chosen.

---

## 1. Date Operations: `date_formula` vs `date_diff`

### Pre-Consolidation State
* **`date_formula`**: Handled date addition and subtraction using an offset value (`offset_value`), unit (`days`, `months`, `years`), and sign (`+` or `-`).
* **`date_diff`**: Calculated the numeric difference between a start date and end date in `days`, `months`, or `years`.

### Problem & Overlap
Both resolvers deal exclusively with date fields/values and date calculations. Having two top-level resolver kinds (`date_formula` and `date_diff`) in the UI dropdown forced users to decide between two separate date tools depending on whether they were adding or subtracting days.

### Consolidation Design
Merge into a single canonical **`date`** resolver with three distinct operations:
1. `add`: `base_date + offset`
2. `subtract`: `base_date - offset`
3. `diff`: `end_date - start_date` in specified units.

---

## 2. Text Operations: `string_formula` vs `normalization` vs `format`

### Pre-Consolidation State
* **`string_formula`**: Handled string concatenation, `uppercase`, `lowercase`, and `fmt_money`.
* **`normalization`**: Executed text transformations such as `trim`, `slug`, `snake_case`, `title_case`, `uppercase`, and `lowercase`.
* **`format`**: Performed date formatting (`format_date`), money formatting (`fmt_money`), and template string interpolation (`format`).

### Duplication Matrix
* Upper casing was implemented in both `string_formula.uppercase` and `normalization.upper`.
* Lower casing was implemented in both `string_formula.lowercase` and `normalization.lower`.
* Currency formatting was implemented in both `string_formula.fmt_money` and `format.fmt_money`.

### Consolidation Design
Unify all string transformation, cleaning, casing, and string formatting operations under a single canonical **`text`** resolver:
* Operations: `concat`, `trim`, `lower`, `upper`, `replace`, `slug`, `snake`, `title`, `format_date`, `fmt_money`, `pattern`.

---

## 3. Numeric & Aggregation: `math_formula` vs `child_aggregation` vs `collection`

### Pre-Consolidation State
* **`math_formula`**: Evaluated binary numeric arithmetic (`+`, `-`, `*`, `/`) between two field values or constants.
* **`child_aggregation`**: Calculated scalar reductions (`sum`, `avg`, `count`) over child table columns.
* **`collection`**: Provided array inspection/filtering (`any`, `all`, `first`, `find`, `filter`, `pluck`, `unique`, `count`).

### Critical Semantic Boundary: Collection vs Aggregate
* **Collection Resolver (`kind: "collection"`)**: Operates on arrays and returns sets or structural selections or boolean queries (e.g. `filter` returns `List[Dict]`, `pluck` returns `List[Any]`, `any`/`all` return `bool`, `first` returns `Dict`).
* **Aggregate Resolver (`kind: "aggregate"`)**: Reduces an array of records to a single scalar numeric metric (`sum`, `avg`, `min`, `max`, `count`).

While `child_aggregation.count` duplicated `collection.count`, merging array structural operations with numeric reductions creates conceptual confusion. Therefore, we preserve **`collection`** for array operations and rebrand/expand child aggregation into a canonical **`aggregate`** resolver.

---

## 4. Lookup: `fetch` vs Collection & Query Records

### Pre-Consolidation State
* **`fetch`**: Read a single field value from a linked DocType given a local link field name (`doc.customer` → `Customer.customer_group`).

### Analysis
Users confused `fetch` with in-memory child table collection filtering and full backend multi-record Query Records actions. By establishing **`lookup`** as a dedicated single-record database getter (`get`, `exists`), database queries are clearly isolated from context collection filtering.

---

## 5. Value Sources vs Internal Execution Strategies

### The Anti-Pattern
Exposing execution engines (`SafeEvalResolver`, `JinjaResolver`, `ExpressionResolver`) alongside domain resolvers (`Date`, `Text`, `Math`) in the primary formula selector confused users between *what* value they were computing and *how* the expression engine evaluates it.

### Resolved Architecture
* **User-Facing Domain Taxonomy**: Expose domain concepts (`Value Source`, `Date`, `Text`, `Math`, `Collection`, `Aggregate`, `Lookup`, `Conditional`, `Type Conversion`).
* **Internal Execution Strategies**: Internal classes (`SafeEvalResolver`, `JinjaResolver`, `ExpressionResolver`, `StaticResolver`, `VariableResolver`) handle runtime execution and fallback token evaluation under the hood without appearing in primary strategy selection dropdowns.
