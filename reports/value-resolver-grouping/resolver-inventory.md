# Canonical Value Resolver Inventory

## Executive Summary

This document provides a comprehensive repository-wide inventory of all Value Resolvers implemented, registered, referenced, or executed within the FlexiRule codebase as of current commit analysis.

FlexiRule provides a dynamic value evaluation framework spanning:
- **Python Backend Execution Registry**: `ValueResolver` and `CompiledResolver` subclasses (`flexirule/ruleflow/core/value_resolver.py`)
- **Vue.js Frontend Strategy Registry**: `registerStrategy` and `ValueResolverControl` UI (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/`)
- **Rich-Text Command & Formula Registry**: `SLASH_COMMANDS` and `FORMULA_REGISTRY` (`flexirule/public/js/flexirule/core/formula_registry.js`)
- **Interactive Multi-Mode Value Control**: `FlexValueControl.vue` tiptap token parser and serializer (`flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue`)

---

## 1. Master Inventory Table

| Resolver Kind | User-Facing Label | Primary Purpose | Input Data Type | Output Data Type | Supported Fieldtypes | Frontend Strategy Builder | Backend Compiled Class | Status & Reachability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `date_formula` | Date Formula | Date arithmetic (+/- offset) | Date / Datetime / "today" | Date / Datetime | Date, Datetime, Time | `DateFormulaResolver.vue` | `DateFormulaResolver` | Implemented, Registered, Executable, Tested |
| `math_formula` | Math Formula | Basic arithmetic (+, -, *, /) | Numeric field / Constant | Float / Int | Int, Float, Currency, Percent, Duration | `MathFormulaResolver.vue` | `MathFormulaResolver` | Implemented, Registered, Executable, Tested |
| `date_diff` | Date Difference | Measure time delta between dates | 2 Date fields / "today" | Int (Days / Months / Years) | Date, Datetime, Int, Float | `DateDiffResolver.vue` | `DateDiffResolver` | Implemented, Registered, Executable, Tested |
| `child_aggregation` | Child Table Aggregation | Aggregate child rows (Sum, Avg, Count) | Child Table field (`doc.items`) | Float / Int | Int, Float, Currency, Percent, Table | `AggregationResolver.vue` | `ChildAggregationResolver` | Implemented, Registered, Executable, Tested |
| `string_formula` | String Manipulation | Text concat, casing, money format | Field / Constant text | String | Data, Small Text, Text, Long Text, Link | `StringFormulaResolver.vue` | `StringFormulaResolver` | Implemented, Registered, Executable, Tested |
| `normalization` | Normalization | Pipeline cleaning (trim, slug, case) | Text field / Profile / Pipeline | String | Data, Small Text, Text, Long Text, Select | `NormalizationResolver.vue` | `NormalizationResolver` | Implemented, Registered, Executable, Tested |
| `format` | Format | Date/money formatting, Python format | Field + Format mask | String | Date, Datetime, Currency, Data, Text | `FormatResolver.vue` | `FormatResolver` | Implemented, Registered, Executable, Tested |
| `fetch` | Fetch From Link | Single-field DB lookup across link | Link Field + Target Field | Any (Scalar) | All Fieldtypes (as target), Link | `FetchResolver.vue` | `FetchResolver` | Implemented, Registered, Executable, Tested |
| `system_context` | System Context | Session context (user, role check) | System token ("user", "role_check") | String / Boolean | All Fieldtypes | `SystemContextResolver.vue` | `SystemContextResolver` | Implemented, Registered, Executable, Tested |
| `collection` | Collection Query | Query, check, filter, pluck child tables | Table / List Variable + Condition | List / Row / Scalar / Bool | Table, Table MultiSelect, MultiSelect | `CollectionResolver.vue` | `CollectionResolver` | Implemented, Registered, Executable, Tested |
| *`variable`* | Variable Reference | Direct path lookup (`doc.x`, `vars.y`) | Path string | Any | All Fieldtypes | Integrated in Tiptap token | `VariableResolver` | Implicit Core Mode |
| *`static`* | Static Value | Constant literal value | Raw scalar value | Any | All Fieldtypes | Integrated in `ControlFactory` | `StaticResolver` | Implicit Core Mode |
| *`expression`* | Composite Expression | Concatenation of text & tokens | Segment array | String | Text, Data, Code | Tiptap Editor | `ExpressionResolver` | Implicit Core Mode |
| *`jinja`* | Jinja Template | Jinja template evaluation | Template string | Any | Text, Data, Code | `jsonToken` / Raw text | `JinjaResolver` | Fallback Evaluator |
| *`safe_eval`* | Safe Python Expression | Python AST safe evaluation | Expression string | Any | Text, Data, Code | Manual Formula Mode | `SafeEvalResolver` | Fallback Evaluator |

---

## 2. Detailed Technical Profiles

### 2.1. `date_formula`
- **Canonical Identifier**: `date_formula`
- **User-Facing Label**: Date Formula
- **Purpose**: Calculate a date by adding or subtracting days, months, or years from a base date field or `today`.
- **Input Data Model**: `base_type` (`"today"` | `"doc_field"`), `base_field` (`str`), `offset_value` (`int`), `offset_unit` (`"days"` | `"months"` | `"years"`), `offset_sign` (`"+"` | `"-"`).
- **Output Data Model**: Date / Datetime string (`YYYY-MM-DD`).
- **Configuration Schema**:
  ```json
  {
    "kind": "date_formula",
    "base_type": "today",
    "base_field": "posting_date",
    "offset_sign": "+",
    "offset_value": 7,
    "offset_unit": "days"
  }
  ```
- **Generated Expression**: `{frappe.utils.add_days(frappe.utils.nowdate(), 7)}`
- **Backend Class**: `DateFormulaResolver`
- **Tests**: `test_value_resolvers.py`, `test_value_resolvers_complex.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested.

### 2.2. `math_formula`
- **Canonical Identifier**: `math_formula`
- **User-Facing Label**: Math Formula
- **Purpose**: Perform simple binary arithmetic (`+`, `-`, `*`, `/`) between two numeric fields or a field and a constant.
- **Input Data Model**: `field_a` (`str`), `math_op` (`"+"` | `"-"` | `"*"` | `"/"`), `field_b_type` (`"field"` | `"constant"`), `field_b` (`str`), `constant_b` (`float`), `precision` (`int`).
- **Output Data Model**: Float / Integer.
- **Configuration Schema**:
  ```json
  {
    "kind": "math_formula",
    "field_a": "doc.amount",
    "math_op": "*",
    "field_b_type": "constant",
    "constant_b": 0.18,
    "precision": 2
  }
  ```
- **Generated Expression**: `{frappe.utils.flt(doc.amount * 0.18, 2)}`
- **Backend Class**: `MathFormulaResolver`
- **Tests**: `test_value_resolvers.py`, `test_value_resolvers_complex.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested.

### 2.3. `date_diff`
- **Canonical Identifier**: `date_diff`
- **User-Facing Label**: Date Difference
- **Purpose**: Calculate integer time delta between two date fields or today.
- **Input Data Model**: `diff_start_type`, `diff_start_field`, `diff_end_type`, `diff_end_field`, `diff_unit` (`"days"` | `"months"` | `"years"`).
- **Output Data Model**: Integer (days/months/years).
- **Configuration Schema**:
  ```json
  {
    "kind": "date_diff",
    "diff_start_type": "doc_field",
    "diff_start_field": "doc.creation",
    "diff_end_type": "today",
    "diff_unit": "days"
  }
  ```
- **Generated Expression**: `{frappe.utils.date_diff(frappe.utils.nowdate(), doc.creation)}`
- **Backend Class**: `DateDiffResolver`
- **Tests**: `test_value_resolvers.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested.

### 2.4. `child_aggregation`
- **Canonical Identifier**: `child_aggregation`
- **User-Facing Label**: Child Table Aggregation
- **Purpose**: Compute Sum, Average, or Count of numeric values from child table rows.
- **Input Data Model**: `agg_table` (`str`), `agg_field` (`str`), `agg_op` (`"sum"` | `"avg"` | `"count"`).
- **Output Data Model**: Float / Int.
- **Configuration Schema**:
  ```json
  {
    "kind": "child_aggregation",
    "agg_table": "doc.items",
    "agg_field": "amount",
    "agg_op": "sum"
  }
  ```
- **Generated Expression**: `{sum([frappe.utils.flt(row.get("amount")) for row in doc.items])}`
- **Backend Class**: `ChildAggregationResolver`
- **Tests**: `test_value_resolvers.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested, **Overlaps with Collection Resolver (`count`, `pluck` + `sum`)**.

### 2.5. `string_formula`
- **Canonical Identifier**: `string_formula`
- **User-Facing Label**: String Manipulation
- **Purpose**: Concatenate strings, adjust casing, or format currency strings.
- **Input Data Model**: `str_op` (`"concat"` | `"uppercase"` | `"lowercase"` | `"fmt_money"`), `str_a_type`, `str_a`, `str_b_type`, `str_b`.
- **Output Data Model**: String.
- **Configuration Schema**:
  ```json
  {
    "kind": "string_formula",
    "str_op": "concat",
    "str_a_type": "field",
    "str_a": "doc.first_name",
    "str_b_type": "field",
    "str_b": "doc.last_name"
  }
  ```
- **Generated Expression**: `{str(doc.first_name or "") + str(doc.last_name or "")}`
- **Backend Class**: `StringFormulaResolver`
- **Tests**: `test_value_resolvers.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested, **Overlaps with Format and Normalization**.

### 2.6. `normalization`
- **Canonical Identifier**: `normalization`
- **User-Facing Label**: Normalization
- **Purpose**: Execute multi-step string cleaning pipelines (trim, slug, snake_case, title_case, uppercase, lowercase).
- **Input Data Model**: `norm_field` (`str`), `norm_profile` (`str` | `None`), `norm_pipeline` (`list[str]`), `norm_op` (`str` | legacy).
- **Output Data Model**: String.
- **Configuration Schema**:
  ```json
  {
    "kind": "normalization",
    "norm_field": "doc.title",
    "norm_profile": "URL Safe",
    "norm_pipeline": ["trim", "slug"]
  }
  ```
- **Generated Expression**: `{flexirule.ruleflow.utils.normalization.execute_normalization_pipeline(doc.title, profile="URL Safe")["normalized_value"]}`
- **Backend Class**: `NormalizationResolver`
- **Tests**: `test_normalization_refactor.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested.

### 2.7. `format`
- **Canonical Identifier**: `format`
- **User-Facing Label**: Format
- **Purpose**: Format dates (`format_date`), money (`fmt_money`), or general templates (`format`).
- **Input Data Model**: `fmt_op` (`"format_date"` | `"fmt_money"` | `"format"`), `fmt_field` (`str`), `fmt_config` (`str`).
- **Output Data Model**: String.
- **Configuration Schema**:
  ```json
  {
    "kind": "format",
    "fmt_op": "format_date",
    "fmt_field": "doc.posting_date",
    "fmt_config": "dd-mm-yyyy"
  }
  ```
- **Generated Expression**: `{frappe.utils.format_date(doc.posting_date, "dd-mm-yyyy")}`
- **Backend Class**: `FormatResolver`
- **Tests**: `test_value_resolvers.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested, **Overlaps with `string_formula.fmt_money`**.

### 2.8. `fetch`
- **Canonical Identifier**: `fetch`
- **User-Facing Label**: Fetch From Link
- **Purpose**: Single-field database value retrieval across a Link field relation using `frappe.db.get_value`.
- **Input Data Model**: `link_field` (`str`), `linked_doctype` (`str`), `fetch_field` (`str`).
- **Output Data Model**: Any scalar field value.
- **Configuration Schema**:
  ```json
  {
    "kind": "fetch",
    "link_field": "doc.customer",
    "linked_doctype": "Customer",
    "fetch_field": "customer_group"
  }
  ```
- **Generated Expression**: `{frappe.db.get_value("Customer", doc.customer, "customer_group")}`
- **Backend Class**: `FetchResolver`
- **Tests**: `test_fetch_resolver.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested.

### 2.9. `system_context`
- **Canonical Identifier**: `system_context`
- **User-Facing Label**: System Context
- **Purpose**: Extract session environmental context such as current user or evaluate user role membership.
- **Input Data Model**: `sys_token` (`"user"` | `"role_check"`), `sys_role` (`str`).
- **Output Data Model**: String (email/user) or Boolean.
- **Configuration Schema**:
  ```json
  {
    "kind": "system_context",
    "sys_token": "role_check",
    "sys_role": "System Manager"
  }
  ```
- **Generated Expression**: `{"System Manager" in frappe.get_roles(frappe.session.user)}`
- **Backend Class**: `SystemContextResolver`
- **Tests**: `test_value_resolvers.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested.

### 2.10. `collection`
- **Canonical Identifier**: `collection`
- **User-Facing Label**: Collection Query
- **Purpose**: Execute row filtering, condition checks, item extraction, and distinct value gathering on child table collections or list variables.
- **Input Data Model**: `source` (`str`), `operation` (`"count"` | `"any"` | `"all"` | `"first"` | `"find"` | `"filter"` | `"pluck"` | `"unique"`), `condition` (`dict` | `list` | `None`), `target_field` (`str` | `None`).
- **Output Data Model**: Integer / Boolean / Row Dict / List of Rows / List of Field Values.
- **Configuration Schema**:
  ```json
  {
    "kind": "collection",
    "source": "doc.items",
    "operation": "pluck",
    "target_field": "item_code",
    "condition": [{"field": "row.rate", "operator": ">", "value": 100}]
  }
  ```
- **Generated Expression**: `{PLUCK(doc.items, "item_code")}`
- **Backend Class**: `CollectionResolver`
- **Tests**: `test_collection_resolver.py`
- **Status Classification**: Implemented, Registered, Reachable, Executable, Tested.

---

## 3. Discrepancy & Overlap Observations

1. **`child_aggregation` vs `collection`**: `child_aggregation` performs `count`, `sum`, and `avg` on child tables. `collection` performs `count`, `any`, `all`, `first`, `filter`, `pluck`, `unique`. `child_aggregation.count` is completely redundant with `collection.count`.
2. **`string_formula.fmt_money` vs `format.fmt_money`**: The currency formatting operation is defined twice in two separate resolvers with different config structures.
3. **`string_formula` casing (`uppercase`/`lowercase`) vs `normalization` casing (`upper`/`lower`)**: Both resolvers handle string casing with different pipeline/op configurations.
4. **`collection.find` vs `collection.first`**: In `CollectionResolver.__init__`, if `operation == "find"`, it is immediately normalized to `self.operation = "first"`. `find` is a UI alias for `first`.
