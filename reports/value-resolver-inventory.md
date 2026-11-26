# FlexiRule Value Resolver Inventory & Evidence Report

**Generated Date:** March 2026
**Source Repository:** FlexiRule (Frappe Framework App)
**Report Purpose:** Complete factual baseline inventory of all currently implemented Value Resolver capabilities, operations, configuration fields, UI controls, external consumers, backend parity, and test coverage.

---

## Executive Summary & Taxonomy Overview

The FlexiRule Value Resolver system is a hybrid compilation and runtime framework that converts user-configured dynamic expressions into optimized, request-cached executable python strategies (`CompiledResolver`).

The active resolver implementation consists of:
* **Backend Registry & Compiler**: `flexirule/ruleflow/core/value_resolver.py` (`ValueResolver`, `get_compiled_resolver`, and 16 `CompiledResolver` subclasses).
* **Frontend Strategy Registry**: `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/` (`strategies.js`, `index.js`, `useValueResolver.js`).
* **Frontend Controls**: `ValueResolverControl.vue`, `FlexValueControl.vue`, `ResolverTokenView.vue`.
* **Canonical Resolver Families**: `date_time`, `text`, `collection`, `math_formula`, `lookup`, `system_context`.
* **Legacy Alias / Hidden Families**: `child_aggregation` (maps to `collection`), `fetch` (maps to `lookup`).

---

## 1. Complete Resolver Strategy & Class Inventory

### Summary Matrix of All Resolver Families

| Family ID (Frontend / Backend) | Strategy Key | Backend Strategy Class | Frontend Component | Display Label | Icon | Exposed in UI? | Tested? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `date_time` | `date_time` | `DateFormulaResolver`<br>`DateDiffResolver`<br>`FormatResolver` | `DateTimeResolver.vue` | Date & Time | `fa fa-calendar` | Yes | Yes |
| `text` | `text` | `StringFormulaResolver`<br>`NormalizationResolver`<br>`FormatResolver` | `TextTransformResolver.vue` | Text Transform | `fa fa-font` | Yes | Yes |
| `collection` | `collection` | `CollectionResolver` | `CollectionResolver.vue` | Collection Query | `fa fa-list-ol` | Yes | Yes |
| `math_formula` | `math_formula` | `MathFormulaResolver` | `MathFormulaResolver.vue` | Math Formula | `fa fa-calculator` | Yes | Yes |
| `lookup` | `lookup` | `LookupResolver` | `LookupResolver.vue` | Lookup | `fa fa-search` | Yes | Yes |
| `system_context` | `system_context` | `SystemContextResolver` | `SystemContextResolver.vue` | System Context | `fa fa-globe` | Yes | Yes |
| `child_aggregation` *(Legacy)* | `child_aggregation` | `ChildAggregationResolver`<br>*(delegates to `CollectionResolver`)* | `AggregationResolver.vue` | Child Aggregation | `fa fa-calculator` | Hidden | Yes |
| `fetch` *(Legacy)* | `fetch` | `FetchResolver`<br>*(subclass of `LookupResolver`)* | `FetchResolver.vue` | Lookup | `fa fa-search` | Hidden | Yes |

---

## 2. Exhaustive Operation Inventory

### Family 1: Date & Time (`family: "date_time"`, `kind: "date_time"`)
* **Registry Key:** `date_time`
* **Frontend Component:** `DateTimeResolver.vue` (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/DateTimeResolver.vue`)
* **Icon:** `fa fa-calendar`

#### Operation 1.1: Calculate (`operation: "calculate"`)
* **Display Label:** Date & Time Formula
* **Frontend Component:** `DateTimeCalculateConfig.vue` (`.../components/operations/DateTimeCalculateConfig.vue`)
* **Backend Class:** `DateFormulaResolver` (`flexirule/ruleflow/core/value_resolver.py:96-131`)
* **Compiles to Code/Python Expression:** Yes (`{frappe.utils.nowdate()}` or `{frappe.utils.add_days(...)` / `{frappe.utils.add_to_date(...)`)
* **Executes through `resolve()`:** Yes (`DateFormulaResolver.resolve(context)`)
* **Supported Behavior:** Adds or subtracts time units (days, weeks, months, years, hours) to/from today or a document field date value.
* **Required Config:** `base_type`
* **Optional Config:** `base_field` (required if `base_type === 'doc_field'`), `offset_sign`, `offset_value`, `offset_unit`
* **Default Values:** `{ base_type: "today", base_field: "", offset_sign: "+", offset_value: 0, offset_unit: "days" }`
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes (Assignment, Conditions, Query Records)
* **Tested:** Tested (`test_value_resolvers_complex.py:46-73`)

#### Operation 1.2: Difference (`operation: "diff"`)
* **Display Label:** Date & Time Difference
* **Frontend Component:** `DateTimeDiffConfig.vue` (`.../components/operations/DateTimeDiffConfig.vue`)
* **Backend Class:** `DateDiffResolver` (`flexirule/ruleflow/core/value_resolver.py:173-207`)
* **Compiles to Code/Python Expression:** Yes (`{frappe.utils.date_diff(end, start)}` or `{frappe.utils.month_diff(end, start)}`)
* **Executes through `resolve()`:** Yes (`DateDiffResolver.resolve(context)`)
* **Supported Behavior:** Computes numeric difference between two date/datetime values in days, months, or years.
* **Required Config:** `diff_start_type`, `diff_end_type`, `diff_unit`
* **Optional Config:** `diff_start_field` (required if `diff_start_type === 'doc_field'`), `diff_end_field` (required if `diff_end_type === 'doc_field'`)
* **Default Values:** `{ diff_start_type: "today", diff_start_field: "", diff_end_type: "doc_field", diff_end_field: "", diff_unit: "days" }`
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_value_resolvers_complex.py:75-88`)

#### Operation 1.3: Format Date (`operation: "format"`)
* **Display Label:** Format Date & Time
* **Frontend Component:** `DateTimeFormatConfig.vue` (`.../components/operations/DateTimeFormatConfig.vue`)
* **Backend Class:** `FormatResolver` (`flexirule/ruleflow/core/value_resolver.py:425-452`)
* **Compiles to Code/Python Expression:** Yes (`{frappe.utils.format_date(field, "YYYY-MM-DD")}`)
* **Executes through `resolve()`:** Yes (`FormatResolver.resolve(context)` with `fmt_op="format_date"`)
* **Supported Behavior:** Formats a date/datetime field value according to a template string.
* **Required Config:** `fmt_field`
* **Optional Config:** `fmt_config`
* **Default Values:** `{ fmt_field: "", fmt_config: "YYYY-MM-DD" }`
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_value_resolvers_complex.py:90-99`)

---

### Family 2: Text Transform (`family: "text"`, `kind: "text"`)
* **Registry Key:** `text`
* **Frontend Component:** `TextTransformResolver.vue` (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/TextTransformResolver.vue`)
* **Icon:** `fa fa-font`

#### Operation 2.1: Combine (`operation: "combine"`)
* **Display Label:** Combine Text
* **Frontend Component:** `TextTransformResolver.vue` (inline template section `modelValue.operation === 'combine'`)
* **Backend Class:** `StringFormulaResolver` (`flexirule/ruleflow/core/value_resolver.py:357-386`)
* **Compiles to Code/Python Expression:** Yes (`{str(val_a or "") + str(val_b or "")}`)
* **Executes through `resolve()`:** Yes (`StringFormulaResolver.resolve(context)` with `str_op="concat"`)
* **Supported Behavior:** Concatenates two string inputs (document fields or static string literals).
* **Required Config:** `str_a_type`, `str_b_type`
* **Optional Config:** `str_a`, `str_b`
* **Default Values:** `{ str_a_type: "field", str_a: "", str_b_type: "constant", str_b: "" }`
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_value_resolvers_complex.py:215-228`)

#### Operation 2.2: Case Change (`operation: "case"`)
* **Display Label:** Change Case
* **Frontend Component:** `TextTransformResolver.vue` (inline template section `modelValue.operation === 'case'`)
* **Backend Class:** `StringFormulaResolver` (for `uppercase`/`lowercase`) or `NormalizationResolver` (for `titlecase`, `slug`, `snake`)
* **Compiles to Code/Python Expression:** Yes (`{str(field or "").upper()}`, `{str(field or "").lower()}`, `{execute_normalization_pipeline(...)}`)
* **Executes through `resolve()`:** Yes (`StringFormulaResolver` or `NormalizationResolver`)
* **Supported Behavior:** Transforms field casing to uppercase, lowercase, title case, slug, or snake case.
* **Required Config:** `field`, `case_mode`
* **Optional Config:** None
* **Default Values:** `{ field: "", case_mode: "uppercase" }`
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_value_resolvers_complex.py:230-238`)

#### Operation 2.3: Normalize (`operation: "normalize"`)
* **Display Label:** Normalize
* **Frontend Component:** `TextTransformResolver.vue` (inline template section `modelValue.operation === 'normalize'`)
* **Backend Class:** `NormalizationResolver` (`flexirule/ruleflow/core/value_resolver.py:388-423`)
* **Compiles to Code/Python Expression:** Yes (`{execute_normalization_pipeline(field, profile=..., pipeline=...)}`)
* **Executes through `resolve()`:** Yes (`NormalizationResolver.resolve(context)`)
* **Supported Behavior:** Runs a text string through normalization profiles or custom pipeline steps (trim, strip, slug, snake_case, uppercase, lowercase, etc.).
* **Required Config:** `norm_field`
* **Optional Config:** `norm_profile`, `norm_pipeline`
* **Default Values:** `{ norm_field: "", norm_profile: "Custom", norm_pipeline: ["trim"] }`
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_value_resolvers_complex.py:240-248`)

#### Operation 2.4: Template Format (`operation: "format"`)
* **Display Label:** Template Format
* **Frontend Component:** `TextTransformResolver.vue` (inline template section `modelValue.operation === 'format'`)
* **Backend Class:** `FormatResolver` (`flexirule/ruleflow/core/value_resolver.py:425-452`)
* **Compiles to Code/Python Expression:** Yes (`{("{}").format(field)}`)
* **Executes through `resolve()`:** Yes (`FormatResolver.resolve(context)` with `fmt_op="format"`)
* **Supported Behavior:** Formats string values using Python `{}` format string templates.
* **Required Config:** `fmt_field`
* **Optional Config:** `fmt_config`
* **Default Values:** `{ fmt_field: "", fmt_config: "" }`
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_value_resolvers_complex.py:250-258`)

---

### Family 3: Collection Query (`family: "collection"`, `kind: "collection"`)
* **Registry Key:** `collection`
* **Frontend Component:** `CollectionResolver.vue` (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/CollectionResolver.vue`)
* **Icon:** `fa fa-list-ol`
* **Backend Class:** `CollectionResolver` (`flexirule/ruleflow/core/value_resolver.py:209-342`)

#### Operations under Collection Query:
1. `sum` - Sum Numeric Values: sums `target_field` across rows matching `condition`.
2. `avg` - Average Numeric Values: averages `target_field` across rows matching `condition`.
3. `count` - Count Rows: counts rows matching `condition`.
4. `any` - Check Any Match: returns boolean `True` if any row matches `condition`.
5. `all` - Check All Match: returns boolean `True` if all rows match `condition`.
6. `first` (and UI alias `find`) - Find First Row: returns the entire row dictionary of the first matching row.
7. `filter` - Filter Sub-Collection: returns a list of row dictionaries matching `condition`.
8. `pluck` - Extract Field Values: returns a list of values for `target_field` from matching rows.
9. `unique` - Extract Unique Values: returns a deduplicated list of values for `target_field` from matching rows.

* **Compiles to Code/Python Expression:** Yes (`{SUM(source, "target_field")}`, `{COUNT(source)}`, etc.)
* **Executes through `resolve()`:** Yes (`CollectionResolver.resolve(context)`)
* **Default Values:** `{ source: "", operation: "any", target_field: "", condition: null }`
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_collection_resolver.py:1-210`)

---

### Family 4: Math Formula (`family: "math_formula"`, `kind: "math_formula"`)
* **Registry Key:** `math_formula`
* **Frontend Component:** `MathFormulaResolver.vue` (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/MathFormulaResolver.vue`)
* **Icon:** `fa fa-calculator`
* **Backend Class:** `MathFormulaResolver` (`flexirule/ruleflow/core/value_resolver.py:133-171`)

#### Operation 4.1: Arithmetic Formula (`math_op`: `+`, `-`, `*`, `/`)
* **Display Label:** Math Formula
* **Supported Behavior:** Evaluates `field_a (math_op) field_b` or `field_a (math_op) constant_b`, rounded to `precision`.
* **Required Config:** `field_a`, `math_op`, `field_b_type`
* **Optional Config:** `field_b` (if `field_b_type === 'field'`), `constant_b` (if `field_b_type === 'constant'`), `precision`
* **Default Values:** `{ field_a: "", math_op: "+", field_b_type: "field", field_b: "", constant_b: 0, precision: 2 }`
* **Compiles to Code/Python Expression:** Yes (`{flt(...) + flt(...)}`)
* **Executes through `resolve()`:** Yes (`MathFormulaResolver.resolve(context)`)
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_value_resolvers_complex.py:315-335`)

---

### Family 5: Lookup (`family: "lookup"`, `kind: "lookup"`)
* **Registry Key:** `lookup`
* **Frontend Component:** `LookupResolver.vue` (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/LookupResolver.vue`)
* **Icon:** `fa fa-search`
* **Backend Class:** `LookupResolver` (`flexirule/ruleflow/core/value_resolver.py:467-553`)

#### Operation 5.1: Fetch Field Value (`operation: "fetch"`)
* **Display Label:** Lookup
* **Supported Behavior:** Resolves `frappe.db.get_value(resolved_doctype, link_value, fetch_field)` with permission checks and dynamic/static DocType mode support.
* **Required Config:** `doctype_mode`, `record_source_type`, `record_field`, `fetch_field`
* **Optional Config:** `target_doctype` (required if `doctype_mode === 'static'`), `doctype_source` (required if `doctype_mode === 'dynamic'`)
* **Default Values:** `{ doctype_mode: "static", target_doctype: "", doctype_source: "", record_source_type: "doc_field", record_field: "", fetch_field: "" }`
* **Compiles to Code/Python Expression:** Yes (`{frappe.db.get_value(dt, rec, "field")}`)
* **Executes through `resolve()`:** Yes (`LookupResolver.resolve(context)`)
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_fetch_resolver.py:1-300`)

---

### Family 6: System Context (`family: "system_context"`, `kind: "system_context"`)
* **Registry Key:** `system_context`
* **Frontend Component:** `SystemContextResolver.vue` (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/SystemContextResolver.vue`)
* **Icon:** `fa fa-globe`
* **Backend Class:** `SystemContextResolver` (`flexirule/ruleflow/core/value_resolver.py:454-465`)

#### Operation 6.1: Current User (`sys_token: "user"`)
* **Display Label:** Current User
* **Behavior:** Returns `frappe.session.user`
* **Compiles to Code/Python Expression:** Yes (`{frappe.session.user}`)
* **Executes through `resolve()`:** Yes (`SystemContextResolver.resolve(context)`)

#### Operation 6.2: Has Role Check (`sys_token: "role_check"`)
* **Display Label:** Has Role?
* **Behavior:** Returns boolean indicating if `sys_role` is in `frappe.get_roles(frappe.session.user)`
* **Required Config:** `sys_role`
* **Compiles to Code/Python Expression:** Yes (`{"Role Name" in frappe.get_roles(frappe.session.user)}`)
* **Executes through `resolve()`:** Yes (`SystemContextResolver.resolve(context)`)

* **Default Values:** `{ sys_token: "user", sys_role: "" }`
* **Backend Support:** Supported
* **Frontend Exposed:** Exposed
* **Consumed by Feature:** Yes
* **Tested:** Tested (`test_value_resolvers_complex.py:337-350`)

---

## 3. Configuration Field Reference Table

Below is the complete field-level inventory for all configuration parameters across all resolver operations:

| Family | Operation | Field Key | Required | Type | Input / Control Component | Options / Choices | Default | Visibility / Dependency | Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `date_time` | `calculate` | `base_type` | Yes | string | `SelectControl` | `today`, `doc_field` | `"today"` | Always visible | Base date source |
| `date_time` | `calculate` | `base_field` | Conditional | string | `ComboBoxControl` | Date/Datetime doc fields | `""` | Visible when `base_type === 'doc_field'` | Document field containing base date |
| `date_time` | `calculate` | `offset_sign` | Optional | string | `SelectControl` | `+`, `-` | `"+"` | Always visible | Direction of time offset |
| `date_time` | `calculate` | `offset_value` | Optional | integer | `DataControl` (Int) | Any integer | `0` | Always visible | Numeric amount of offset |
| `date_time` | `calculate` | `offset_unit` | Optional | string | `SelectControl` | `days`, `weeks`, `months`, `years`, `hours` | `"days"` | Always visible | Time unit for offset calculation |
| `date_time` | `diff` | `diff_start_type` | Yes | string | `SelectControl` | `today`, `doc_field` | `"today"` | Always visible | Start date source |
| `date_time` | `diff` | `diff_start_field` | Conditional | string | `ComboBoxControl` | Date/Datetime doc fields | `""` | Visible when `diff_start_type === 'doc_field'` | Document field for start date |
| `date_time` | `diff` | `diff_end_type` | Yes | string | `SelectControl` | `today`, `doc_field` | `"doc_field"` | Always visible | End date source |
| `date_time` | `diff` | `diff_end_field` | Conditional | string | `ComboBoxControl` | Date/Datetime doc fields | `""` | Visible when `diff_end_type === 'doc_field'` | Document field for end date |
| `date_time` | `diff` | `diff_unit` | Yes | string | `SelectControl` | `days`, `months`, `years` | `"days"` | Always visible | Unit of difference result |
| `date_time` | `format` | `fmt_field` | Yes | string | `ComboBoxControl` | Date/Datetime/String doc fields | `""` | Always visible | Target date field to format |
| `date_time` | `format` | `fmt_config` | Optional | string | `DataControl` | Format strings (e.g. `YYYY-MM-DD`) | `"YYYY-MM-DD"` | Always visible | Date format specification string |
| `text` | `combine` | `str_a_type` | Yes | string | `SelectControl` | `field`, `constant` | `"field"` | Always visible | Source type for first string operand |
| `text` | `combine` | `str_a` | Yes | string | `ComboBoxControl` / `DataControl` | Doc fields or free text | `""` | Always visible | Field name or string value for Value A |
| `text` | `combine` | `str_b_type` | Yes | string | `SelectControl` | `field`, `constant` | `"constant"` | Always visible | Source type for second string operand |
| `text` | `combine` | `str_b` | Optional | string | `ComboBoxControl` / `DataControl` | Doc fields or free text | `""` | Always visible | Field name or string value for Value B |
| `text` | `case` | `field` | Yes | string | `ComboBoxControl` | String doc fields | `""` | Always visible | Target string field to transform |
| `text` | `case` | `case_mode` | Yes | string | `SelectControl` | `uppercase`, `lowercase`, `titlecase`, `slug`, `snake` | `"uppercase"` | Always visible | Casing strategy |
| `text` | `normalize` | `norm_field` | Yes | string | `ComboBoxControl` | String doc fields | `""` | Always visible | Target field to normalize |
| `text` | `normalize` | `norm_profile` | Optional | string | `SelectControl` | `Custom`, + profiles from API | `"Custom"` | Always visible | Predefined normalization profile |
| `text` | `normalize` | `norm_pipeline` | Optional | array[string] | `MultiSelectList` | Available normalization ops | `["trim"]` | Editable when `norm_profile === 'Custom'` | Ordered normalization pipeline steps |
| `text` | `format` | `fmt_field` | Yes | string | `ComboBoxControl` | String doc fields | `""` | Always visible | Target field for formatting |
| `text` | `format` | `fmt_config` | Optional | string | `DataControl` | String template (e.g. `Hello {0}`) | `""` | Always visible | Format string template |
| `collection` | All ops | `source` | Yes | string | `ComboBoxControl` | Child table paths (`doc.items`, `vars.x`) | `""` | Always visible | Collection/Child Table source path |
| `collection` | All ops | `operation` | Yes | string | `SelectControl` | `sum`, `avg`, `count`, `any`, `all`, `first`, `find`, `filter`, `pluck`, `unique` | `"any"` | Always visible | Collection operation identifier |
| `collection` | `sum`,`avg`,`pluck`,`unique` | `target_field` | Yes | string | `ComboBoxControl` | Child table fields | `""` | Visible for target-field requiring ops | Target child-table field name |
| `collection` | All ops | `condition` | Optional | object/array | `ConditionBuilder` (Modal) | Filter conditions | `null` | Triggered via "Filter Condition" modal button | Sub-collection filter rule structure |
| `math_formula` | `math_op` | `field_a` | Yes | string | `ComboBoxControl` | Numeric doc fields | `""` | Always visible | Left numeric field |
| `math_formula` | `math_op` | `math_op` | Yes | string | `SelectControl` | `+`, `-`, `*`, `/` | `"+"` | Always visible | Arithmetic operator |
| `math_formula` | `math_op` | `field_b_type` | Yes | string | `SelectControl` | `field`, `constant` | `"field"` | Always visible | Right operand source type |
| `math_formula` | `math_op` | `field_b` | Conditional | string | `ComboBoxControl` | Numeric doc fields | `""` | Visible when `field_b_type === 'field'` | Right numeric field name |
| `math_formula` | `math_op` | `constant_b` | Conditional | number | `DataControl` (Float) | Numeric literal | `0` | Visible when `field_b_type === 'constant'` | Right numeric fixed value |
| `math_formula` | `math_op` | `precision` | Optional | integer | `DataControl` (Int) | Decimal digits | `2` | Always visible | Decimal rounding precision |
| `lookup` | `fetch` | `doctype_mode` | Yes | string | `SelectControl` | `static`, `dynamic` | `"static"` | Always visible | DocType resolution strategy |
| `lookup` | `fetch` | `target_doctype` | Conditional | string | `ComboBoxControl` | All DocTypes | `""` | Visible when `doctype_mode === 'static'` | Fixed target DocType name |
| `lookup` | `fetch` | `doctype_source` | Conditional | string | `ComboBoxControl` | Doc fields providing DocType | `""` | Visible when `doctype_mode === 'dynamic'` | Document field containing DocType name |
| `lookup` | `fetch` | `record_source_type` | Yes | string | `SelectControl` | `doc_field`, `variable`, `expression` | `"doc_field"` | Always visible | Link record ID source type |
| `lookup` | `fetch` | `record_field` | Yes | string | `ComboBoxControl` / `DataControl` | Doc fields, vars, or expressions | `""` | Always visible | Link record name/ID path |
| `lookup` | `fetch` | `fetch_field` | Yes | string | `ComboBoxControl` | Fields of target DocType | `""` | Always visible | Target field to read from record |
| `system_context` | `user`/`role_check` | `sys_token` | Yes | string | `SelectControl` | `user`, `role_check` | `"user"` | Always visible | System context token key |
| `system_context` | `role_check` | `sys_role` | Conditional | string | `ComboBoxControl` | All Frappe Roles | `""` | Visible when `sys_token === 'role_check'` | Role name to verify for current user |

---

## 4. Nested Configuration Structures

The canonical outer container payload emitted by `useValueResolver` is formatted as follows:

```json
{
  "family": "collection",
  "operation": "sum",
  "kind": "collection",
  "config": {
    "source": "doc.items",
    "target_field": "amount",
    "condition": {
      "op": "and",
      "conditions": [
        {
          "left": { "ref": "row.is_taxable" },
          "op": "==",
          "right": { "value": 1 }
        }
      ]
    }
  }
}
```

### Complete Nested Property Breakdown

1. **`config.condition` (Collection Filter Structure):**
   * Object containing:
     * `op`: Logical operator string (`"and"` or `"or"`).
     * `conditions`: Array of condition objects:
       * `left`: Object `{ "ref": "row.fieldname" }` or `{ "value": primitive }`.
       * `op`: Comparison operator (`"=="`, `"!="`, `">"`, `"<"`, `">="`, `"<="`, `"in"`, `"not in"`, `"contains"`).
       * `right`: Object `{ "value": primitive }`, `{ "ref": path }`, or resolver structure.

2. **`config.norm_pipeline` (Normalization Steps Array):**
   * Array of string identifiers representing ordered pipeline operations:
     * e.g., `["trim", "snake_case", "uppercase"]`.

---

## 5. Resolver Composition & Nesting Capabilities

Resolvers can consume or nest within other expression layers in the following ways:

1. **Token Editor Segments (`ExpressionResolver`):**
   * A TipTap rich text or string expression field can contain multiple interleaved segments (`text`, `variableToken`, `resolverToken`, `jsonToken`).
   * Evaluated sequentially by `ExpressionResolver` (`flexirule/ruleflow/core/value_resolver.py:606-618`) and joined as text.

2. **Collection Condition Resolvers:**
   * `CollectionResolver` compiles its `condition` JSON payload into a `ConditionEvaluator` instance.
   * Row-level evaluation can inspect `row.fieldname` and evaluate dynamic values inside collection filters.

3. **Lookup Scoped Resolution:**
   * `LookupResolver._resolve_scoped_value()` dynamically evaluates paths against contextual scopes (`row.`, `item.`, `vars.`, `doc.`, `ctx.`).

---

## 6. UI Capabilities vs Backend Matrix

| Capability / Operation | Implemented in Backend? | Exposed in UI? | UI Control Location | Notes / Parity Discrepancy |
| :--- | :--- | :--- | :--- | :--- |
| `date_time` -> `calculate` | Yes | Yes | `DateTimeCalculateConfig.vue` | Exact parity |
| `date_time` -> `diff` | Yes | Yes | `DateTimeDiffConfig.vue` | Exact parity |
| `date_time` -> `format` | Yes | Yes | `DateTimeFormatConfig.vue` | Exact parity |
| `text` -> `combine` | Yes | Yes | `TextTransformResolver.vue` | Exact parity |
| `text` -> `case` | Yes | Yes | `TextTransformResolver.vue` | `titlecase`, `slug`, `snake` mapped to `NormalizationResolver` |
| `text` -> `normalize` | Yes | Yes | `TextTransformResolver.vue` | UI fetches available ops dynamically from backend API |
| `text` -> `format` | Yes | Yes | `TextTransformResolver.vue` | Exact parity |
| `collection` -> All ops | Yes | Yes | `CollectionResolver.vue` | UI provides modal `ConditionBuilder` for collection filters |
| `math_formula` | Yes | Yes | `MathFormulaResolver.vue` | Exact parity |
| `lookup` | Yes | Yes | `LookupResolver.vue` | Supports Dynamic Link auto-detection |
| `system_context` | Yes | Yes | `SystemContextResolver.vue` | Exact parity |
| `child_aggregation` | Yes (Legacy) | Hidden (Alias) | `AggregationResolver.vue` | Hidden from strategy picker; auto-normalized to `collection` |
| `fetch` | Yes (Legacy) | Hidden (Alias) | `FetchResolver.vue` | Hidden from strategy picker; auto-normalized to `lookup` |

---

## 7. Tracing Resolver Usage Outside Resolver Components

### Consumer Summary Table

| Consumer Feature | File / Component Path | Resolver Entry Point | Accepted Families / Operations | Indirect / Direct Flow |
| :--- | :--- | :--- | :--- | :--- |
| **Assignment Action** | `flexirule/ruleflow/core/action_handlers/assignment.py:118` | `get_compiled_resolver(action, f"assign_{idx}", row["value"])` | All families & operations | **Direct**: Compiles and resolves value during action execution |
| **Assignment UI** | `.../types/AssignmentConfig.vue:119` | `<FlexValueControl>` | All strategies | **Direct**: Renders token/popover builder for assignment value |
| **Condition Builder** | `.../condition_builder/SimpleCondition.vue:401` | `<FlexValueControl>` | All strategies | **Direct**: Renders resolver controls for condition right-hand side |
| **Condition Evaluator**| `flexirule/ruleflow/core/evaluator.py` | `ConditionCompiler` / safe eval | Python expression compiled from resolver | **Indirect**: Evaluates expressions generated by resolver compilers |
| **Query Records Filter UI** | `.../types/QueryRecordsConfig.vue:229, 246, 321` | `<FlexValueControl>` | All strategies | **Direct**: Configures dynamic query filter values |
| **Query Records Backend** | `flexirule/ruleflow/core/action_handlers/query_records.py:1145` | `_clean_flex_value()` / `ValueResolver.compile()` | All families | **Direct**: Resolves dynamic filter values prior to executing query |
| **Filter Group UI** | `.../rule_config/FilterGroup.vue:78, 101, 126` | `<FlexValueControl>` | All strategies | **Direct**: Shared filter UI component |
| **TipTap Token View** | `.../controls/ResolverTokenView.vue:3` | `<ValueResolverControl>` | All strategies | **Direct**: Inline formula token in rich text editors |

---

## 8. Input / Value Categories Reference

The current Value Resolver system can represent and evaluate the following input categories:

1. **Literal Text**: Fixed string inputs (e.g. `str_a`, `fmt_config`, constant values).
2. **Literal Number**: Fixed integer/float inputs (e.g. `offset_value`, `constant_b`, `precision`).
3. **Literal Boolean**: Boolean results from `any`, `all`, or `role_check`.
4. **Null / Empty Value**: Handled gracefully by `NoneResolver()` or empty fallbacks.
5. **Document Field (`doc.field`)**: Directly resolved via `VariableResolver` or `get_context_value()`.
6. **Nested Document Field (`doc.parent.child`)**: Supported via dot-notation path traversing in `get_context_value()`.
7. **Child Table Collection (`doc.items`)**: Queried and aggregated via `CollectionResolver`.
8. **Linked Record Value**: Fetched across DocTypes via `LookupResolver` (`frappe.db.get_value`).
9. **Current User**: Fetched via `SystemContextResolver` (`sys_token="user"`).
10. **Role Check**: Verified via `SystemContextResolver` (`sys_token="role_check"`).
11. **Current Date / Today**: Generated via `frappe.utils.nowdate()`.
12. **Calculated Values**: Produced by `MathFormulaResolver` or `DateFormulaResolver`.
13. **Conditional Values**: Derived via row-filtered `CollectionResolver` queries.
14. **Aggregated Values**: Sum, average, and count of collections.
15. **Formatted Values**: Dates formatted via `frappe.utils.format_date()` or string templates via `.format()`.
16. **Composite Expressions**: Interleaved tokens joined via `ExpressionResolver`.

---

## 9. Backend / Frontend Parity Analysis

### Identified Mismatches & Normalization Behaviors:

1. **Legacy `child_aggregation` Mappings**:
   * Frontend `useValueResolver.js:33-53` transparently converts legacy `child_aggregation` payloads (`agg_table`, `agg_field`, `agg_op`) into canonical `collection` payloads (`source`, `target_field`, `operation`).
   * Backend `ValueResolver.compile_resolver_config()` (`value_resolver.py:698-724`) also supports legacy `child_aggregation` fields as a fallback.

2. **Legacy `fetch` Mappings**:
   * Frontend `useValueResolver.js:77-90` transparently converts legacy `fetch` payloads (`linked_doctype`, `link_field`) into canonical `lookup` payloads (`target_doctype`, `record_field`).
   * Backend `FetchResolver` (`value_resolver.py:555-565`) acts as a subclass wrapper around `LookupResolver`.

3. **Operation Name Mapping (`find` vs `first`)**:
   * Frontend `CollectionResolver.vue` lists operation `"find"` alongside `"first"`.
   * Backend `CollectionResolver.__init__` (`value_resolver.py:228-229`) explicitly normalizes `"find"` to `"first"`.

4. **Text Case Mappings**:
   * Operations `"titlecase"`, `"slug"`, and `"snake"` under `text -> case` in `TextTransformResolver.vue` are compiled to code calls to `execute_normalization_pipeline` on frontend, while backend `compile_resolver_config` routes them through `NormalizationResolver`.

---

## 10. Test Coverage Reference

| Test File Path | Covered Family / Operation | Configuration Shape Tested? | Runtime `resolve()` Tested? | Frontend Tested? |
| :--- | :--- | :--- | :--- | :--- |
| `flexirule/ruleflow/tests/test_value_resolver_core.py` | Basic compilation (`Static`, `Variable`, `None`, `Jinja`, `SafeEval`) | Yes | Yes | No |
| `flexirule/ruleflow/tests/test_assignment_resolver.py` | Assignment integration with `ValueResolver` | Yes | Yes | No |
| `flexirule/ruleflow/tests/test_value_resolvers_complex.py` | `date_time`, `text`, `math_formula`, `system_context` | Yes | Yes | No |
| `flexirule/ruleflow/tests/test_collection_resolver.py` | `collection` (all operations and conditions) | Yes | Yes | No |
| `flexirule/ruleflow/tests/test_fetch_resolver.py` | `lookup` / `fetch` (static & dynamic DocTypes, permissions) | Yes | Yes | No |

---

## 11. Final Structured Machine-Readable Inventory

```yaml
Family: date_time
  Registry Key: date_time
  Backend Identifier: date_time
  Display Label: Date & Time
  Icon: fa fa-calendar
  Component: DateTimeResolver.vue
  Operations:
    calculate:
      Label: Date & Time Formula
      Component: DateTimeCalculateConfig.vue
      Backend Class: DateFormulaResolver
      Fields:
        base_type:
          type: string
          required: true
          control: SelectControl
          default: "today"
          options: ["today", "doc_field"]
        base_field:
          type: string
          required: conditional
          control: ComboBoxControl
          default: ""
          dependencies: base_type == 'doc_field'
        offset_sign:
          type: string
          required: false
          control: SelectControl
          default: "+"
          options: ["+", "-"]
        offset_value:
          type: integer
          required: false
          control: DataControl (Int)
          default: 0
        offset_unit:
          type: string
          required: false
          control: SelectControl
          default: "days"
          options: ["days", "weeks", "months", "years", "hours"]
    diff:
      Label: Date & Time Difference
      Component: DateTimeDiffConfig.vue
      Backend Class: DateDiffResolver
      Fields:
        diff_start_type:
          type: string
          required: true
          control: SelectControl
          default: "today"
          options: ["today", "doc_field"]
        diff_start_field:
          type: string
          required: conditional
          control: ComboBoxControl
          default: ""
          dependencies: diff_start_type == 'doc_field'
        diff_end_type:
          type: string
          required: true
          control: SelectControl
          default: "doc_field"
          options: ["today", "doc_field"]
        diff_end_field:
          type: string
          required: conditional
          control: ComboBoxControl
          default: ""
          dependencies: diff_end_type == 'doc_field'
        diff_unit:
          type: string
          required: true
          control: SelectControl
          default: "days"
          options: ["days", "months", "years"]
    format:
      Label: Format Date & Time
      Component: DateTimeFormatConfig.vue
      Backend Class: FormatResolver
      Fields:
        fmt_field:
          type: string
          required: true
          control: ComboBoxControl
          default: ""
        fmt_config:
          type: string
          required: false
          control: DataControl
          default: "YYYY-MM-DD"

Family: text
  Registry Key: text
  Backend Identifier: text
  Display Label: Text Transform
  Icon: fa fa-font
  Component: TextTransformResolver.vue
  Operations:
    combine:
      Label: Combine Text
      Backend Class: StringFormulaResolver
      Fields:
        str_a_type:
          type: string
          required: true
          control: SelectControl
          default: "field"
          options: ["field", "constant"]
        str_a:
          type: string
          required: true
          control: ComboBoxControl / DataControl
          default: ""
        str_b_type:
          type: string
          required: true
          control: SelectControl
          default: "constant"
          options: ["field", "constant"]
        str_b:
          type: string
          required: false
          control: ComboBoxControl / DataControl
          default: ""
    case:
      Label: Change Case
      Backend Class: StringFormulaResolver / NormalizationResolver
      Fields:
        field:
          type: string
          required: true
          control: ComboBoxControl
          default: ""
        case_mode:
          type: string
          required: true
          control: SelectControl
          default: "uppercase"
          options: ["uppercase", "lowercase", "titlecase", "slug", "snake"]
    normalize:
      Label: Normalize
      Backend Class: NormalizationResolver
      Fields:
        norm_field:
          type: string
          required: true
          control: ComboBoxControl
          default: ""
        norm_profile:
          type: string
          required: false
          control: SelectControl
          default: "Custom"
        norm_pipeline:
          type: array[string]
          required: false
          control: MultiSelectList
          default: ["trim"]
          dependencies: norm_profile == 'Custom'
    format:
      Label: Template Format
      Backend Class: FormatResolver
      Fields:
        fmt_field:
          type: string
          required: true
          control: ComboBoxControl
          default: ""
        fmt_config:
          type: string
          required: false
          control: DataControl
          default: ""

Family: collection
  Registry Key: collection
  Backend Identifier: collection
  Display Label: Collection Query
  Icon: fa fa-list-ol
  Component: CollectionResolver.vue
  Operations: [sum, avg, count, any, all, first, find, filter, pluck, unique]
  Backend Class: CollectionResolver
  Fields:
    source:
      type: string
      required: true
      control: ComboBoxControl
      default: ""
    operation:
      type: string
      required: true
      control: SelectControl
      default: "any"
      options: ["sum", "avg", "count", "any", "all", "first", "find", "filter", "pluck", "unique"]
    target_field:
      type: string
      required: conditional
      control: ComboBoxControl
      default: ""
      dependencies: operation in ["sum", "avg", "pluck", "unique"]
    condition:
      type: object / array
      required: false
      control: ConditionBuilder (Modal)
      default: null

Family: math_formula
  Registry Key: math_formula
  Backend Identifier: math_formula
  Display Label: Math Formula
  Icon: fa fa-calculator
  Component: MathFormulaResolver.vue
  Operations:
    math_op:
      Label: Math Formula
      Backend Class: MathFormulaResolver
      Fields:
        field_a:
          type: string
          required: true
          control: ComboBoxControl
          default: ""
        math_op:
          type: string
          required: true
          control: SelectControl
          default: "+"
          options: ["+", "-", "*", "/"]
        field_b_type:
          type: string
          required: true
          control: SelectControl
          default: "field"
          options: ["field", "constant"]
        field_b:
          type: string
          required: conditional
          control: ComboBoxControl
          default: ""
          dependencies: field_b_type == 'field'
        constant_b:
          type: number
          required: conditional
          control: DataControl (Float)
          default: 0
          dependencies: field_b_type == 'constant'
        precision:
          type: integer
          required: false
          control: DataControl (Int)
          default: 2

Family: lookup
  Registry Key: lookup
  Backend Identifier: lookup
  Display Label: Lookup
  Icon: fa fa-search
  Component: LookupResolver.vue
  Operations:
    fetch:
      Label: Lookup
      Backend Class: LookupResolver
      Fields:
        doctype_mode:
          type: string
          required: true
          control: SelectControl
          default: "static"
          options: ["static", "dynamic"]
        target_doctype:
          type: string
          required: conditional
          control: ComboBoxControl
          default: ""
          dependencies: doctype_mode == 'static'
        doctype_source:
          type: string
          required: conditional
          control: ComboBoxControl
          default: ""
          dependencies: doctype_mode == 'dynamic'
        record_source_type:
          type: string
          required: true
          control: SelectControl
          default: "doc_field"
          options: ["doc_field", "variable", "expression"]
        record_field:
          type: string
          required: true
          control: ComboBoxControl / DataControl
          default: ""
        fetch_field:
          type: string
          required: true
          control: ComboBoxControl
          default: ""

Family: system_context
  Registry Key: system_context
  Backend Identifier: system_context
  Display Label: System Context
  Icon: fa fa-globe
  Component: SystemContextResolver.vue
  Operations:
    user:
      Label: Current User
      Backend Class: SystemContextResolver
      Fields:
        sys_token:
          type: string
          required: true
          control: SelectControl
          default: "user"
          options: ["user", "role_check"]
    role_check:
      Label: Has Role Check
      Backend Class: SystemContextResolver
      Fields:
        sys_token:
          type: string
          required: true
          control: SelectControl
          default: "role_check"
        sys_role:
          type: string
          required: true
          control: ComboBoxControl
          default: ""
          dependencies: sys_token == 'role_check'
```
