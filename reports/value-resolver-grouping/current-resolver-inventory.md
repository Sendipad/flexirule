# Current Resolver Inventory & Analysis

## 1. Overview

This document provides a comprehensive inventory of all 10 development-era Value Resolver implementations currently present in FlexiRule as of commit `b3c3e43172cf2f65d31725173f2b49bc57308d2f`.

Each resolver strategy was inspected across:
- Frontend Vue components (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/`)
- Frontend strategy registry (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`)
- Backend class implementations (`flexirule/ruleflow/core/value_resolver.py`)
- Test suites (`flexirule/ruleflow/tests/`)

---

## 2. Exhaustive Strategy Inventory

### 1. `date_formula`
- **Frontend Component**: `DateFormulaResolver.vue`
- **Backend Class**: `DateFormulaResolver(CompiledResolver)`
- **User Problem Solved**: Computing future or past dates relative to a base date.
- **Data/Value Type**: `Date`, `Datetime`
- **Current Operations**: `add` (plus), `subtract` (minus) with units `days`, `weeks`, `months`, `years`.
- **Backend Compilation**: Outputs Python string expression invoking `frappe.utils.add_to_date(...)`.
- **Issues / Overlap**: Conceptually isolated from `date_diff` and date formatting, forcing users to switch components for related date operations.

---

### 2. `math_formula`
- **Frontend Component**: `MathFormulaResolver.vue`
- **Backend Class**: `MathFormulaResolver(CompiledResolver)`
- **User Problem Solved**: Performing basic arithmetic and rounding between two values or fields.
- **Data/Value Type**: `Float`, `Int`, `Currency`
- **Current Operations**: `add` (`+`), `subtract` (`-`), `multiply` (`*`), `divide` (`/`), `round` (`round(x, n)`).
- **Backend Compilation**: Outputs SafeEval expression or direct numeric evaluation.
- **Issues / Overlap**: Does not include currency formatting or percentage calculations.

---

### 3. `date_diff`
- **Frontend Component**: `DateDiffResolver.vue`
- **Backend Class**: `DateDiffResolver(CompiledResolver)`
- **User Problem Solved**: Calculating the integer difference between two dates.
- **Data/Value Type**: `Integer` (days/hours count)
- **Current Operations**: `date_diff` (in days), `time_diff` (in hours/seconds).
- **Backend Compilation**: Outputs `frappe.utils.date_diff(a, b)` or `frappe.utils.time_diff_in_hours(a, b)`.
- **Issues / Overlap**: Small single-operation strategy that belongs under a unified **Date & Time** family.

---

### 4. `child_aggregation`
- **Frontend Component**: `AggregationResolver.vue`
- **Backend Class**: `ChildAggregationResolver(CompiledResolver)`
- **User Problem Solved**: Aggregating numeric column values from Frappe child tables.
- **Data/Value Type**: `Float`, `Int`, `Currency`
- **Current Operations**: `sum`, `avg`, `min`, `max`, `count`.
- **Backend Compilation**: Iterates over `doc.get(child_table_field)` and computes mathematical aggregation over target field.
- **Issues / Overlap**: Overlaps with `collection` resolver's `count` and numeric operations, but focuses specifically on child table fields.

---

### 5. `string_formula`
- **Frontend Component**: `StringFormulaResolver.vue`
- **Backend Class**: `StringFormulaResolver(CompiledResolver)`
- **User Problem Solved**: Basic text manipulation (concatenation, casing, formatting currency).
- **Data/Value Type**: `String`
- **Current Operations**: `concat`, `uppercase`, `lowercase`, `fmt_money`.
- **Backend Compilation**: String joins or Python string methods.
- **Issues / Overlap**: Heavy overlap with `normalization` (casing) and `format` (`fmt_money`). `fmt_money` here is a duplicate.

---

### 6. `normalization`
- **Frontend Component**: `NormalizationResolver.vue`
- **Backend Class**: `NormalizationResolver(CompiledResolver)`
- **User Problem Solved**: Executing text cleanup pipelines (trimming, casing, slugifying).
- **Data/Value Type**: `String`
- **Current Operations**: Multi-step pipeline supporting `trim`, `slug`, `snake`, `title`, `upper`, `lower`, `normalize`.
- **Backend Compilation**: Delegates to `flexirule.ruleflow.utils.normalization.execute_normalization_pipeline`.
- **Issues / Overlap**: `upper` and `lower` duplicate `string_formula`'s `uppercase` and `lowercase`.

---

### 7. `format`
- **Frontend Component**: `FormatResolver.vue`
- **Backend Class**: `FormatResolver(CompiledResolver)`
- **User Problem Solved**: Applying standard Frappe formatting to dates, numbers, or currency.
- **Data/Value Type**: `String` (formatted presentation)
- **Current Operations**: `format_date`, `fmt_money`, `format_number`.
- **Backend Compilation**: Calls `frappe.utils.format_date` or `frappe.utils.fmt_money`.
- **Issues / Overlap**: `fmt_money` duplicated for the third time in this component. "Format" is a capability rather than a data type.

---

### 8. `fetch`
- **Frontend Component**: `FetchResolver.vue`
- **Backend Class**: `FetchResolver(CompiledResolver)`
- **User Problem Solved**: Fetching a field value from a linked Frappe document.
- **Data/Value Type**: Any (field type of target document)
- **Current Operations**: `fetch_link` (resolves `frappe.db.get_value(doctype, name, fieldname)`).
- **Backend Compilation**: Resolves link field dynamically or queries DB via `FieldResolver`.
- **Issues / Overlap**: Technical name ("Fetch From Link") is low-level; better described as **Lookup**.

---

### 9. `system_context`
- **Frontend Component**: `SystemContextResolver.vue`
- **Backend Class**: `SystemContextResolver(CompiledResolver)`
- **User Problem Solved**: Injecting runtime environment metadata into rule evaluation.
- **Data/Value Type**: `String`, `List`, `Date`
- **Current Operations**: `current_user`, `user_roles`, `today`, `now`, `current_company`.
- **Backend Compilation**: Reads from `frappe.session.user`, `frappe.flags`, or system utils.
- **Issues / Overlap**: Works well, but label should be updated to **System & Context**.

---

### 10. `collection`
- **Frontend Component**: `CollectionResolver.vue`
- **Backend Class**: `CollectionResolver(CompiledResolver)`
- **User Problem Solved**: Querying, filtering, and checking elements in lists and child tables.
- **Data/Value Type**: `List[Dict]`, `List[Any]`, `Dict`, `Boolean`, `Integer`
- **Current Operations**: `count`, `any`, `all`, `first`, `filter`, `pluck`, `unique` (plus alias `find`).
- **Backend Compilation**: Evaluates structured row conditions using `ConditionEvaluator` with 10,000 row safety bounds.
- **Issues / Overlap**: Overlaps conceptually with `child_aggregation`.

---

## 3. Inventory Summary Matrix

| Current Kind | Component | Target Operations | Identified Overlaps | Proposed Family |
| :--- | :--- | :--- | :--- | :--- |
| `date_formula` | `DateFormulaResolver.vue` | Date offset calculation | Isolated from date diff/formatting | **Date & Time** |
| `math_formula` | `MathFormulaResolver.vue` | Basic arithmetic, rounding | Missing currency/percentage | **Number** |
| `date_diff` | `DateDiffResolver.vue` | Days/hours difference | Isolated from date formula | **Date & Time** |
| `child_aggregation` | `AggregationResolver.vue` | Child table column math | Overlaps with collection | **Collections & Tables** |
| `string_formula` | `StringFormulaResolver.vue` | Concat, upper/lower, fmt_money | Duplicates normalization & format | **Text** / **Number** |
| `normalization` | `NormalizationResolver.vue` | Text pipeline (slug, trim, etc.) | Duplicates upper/lower | **Text** |
| `format` | `FormatResolver.vue` | Date, currency, number format | Duplicates fmt_money & date format | **Date** / **Text** / **Number** |
| `fetch` | `FetchResolver.vue` | Link field resolution | Technical naming | **Lookup** |
| `system_context` | `SystemContextResolver.vue` | User, roles, current date | Good, minor label update | **System & Context** |
| `collection` | `CollectionResolver.vue` | List filtering, pluck, any/all | Overlaps with child aggregation | **Collections & Tables** |
