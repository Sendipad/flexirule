# Resolver Types Deep Dive

This document provides complete specification and technical deep dives for all 9 canonical resolver kinds and the 6 internal/fallback resolver classes.

---

## 1. `date_formula`

### Purpose
Calculates a target date by adding or subtracting days, months, or years from a starting date (a document date field or current date `today`).

### User Interaction
1. Focus field in `FlexValueControl.vue`.
2. Type `/` → Select **Date Formula** or type `/formula`.
3. Configure via Modal/Popover:
   - Base Type: **Today** or **Document Field**
   - Base Field: e.g., `posting_date`
   - Offset Sign: `+` or `-`
   - Offset Value: e.g., `7`
   - Offset Unit: **days**, **months**, or **years**

### Configuration Structure
```json
{
  "kind": "date_formula",
  "base_type": "doc_field",
  "base_field": "posting_date",
  "offset_sign": "+",
  "offset_value": 7,
  "offset_unit": "days"
}
```

### Frontend Implementation
- **Registry**: `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`
- **Component**: `DateFormulaResolver.vue`
- **Compiler**: `compileToCode()` outputs `{frappe.utils.add_days(doc.posting_date, 7)}`
- **Validation**: Ensures `base_field` exists in target DocType metadata when `base_type === "doc_field"`.

### Generated Expression
`{frappe.utils.add_days(doc.posting_date, 7)}`

### Backend Implementation
- **Class**: `DateFormulaResolver` in `flexirule/ruleflow/core/value_resolver.py`
- **Execution**:
  ```python
  def resolve(self, context: dict) -> Any:
      base_date = frappe.utils.nowdate() if self.base_type == "today" else get_context_value(context, self.base_field)
      if not base_date: return None
      offset = int(self.offset_value or 0)
      if self.offset_sign == "-" and offset > 0: offset = -offset
      if self.offset_unit == "days": return frappe.utils.add_days(base_date, offset)
      return frappe.utils.add_to_date(base_date, **{self.offset_unit: offset})
  ```

### Example
Set payment due date to 30 days after posting date:
`base_field="doc.posting_date"`, `offset_sign="+"`, `offset_value=30`, `offset_unit="days"` → Returns `"2026-06-21"`.

### Tests
- `flexirule/ruleflow/tests/test_value_resolvers_complex.py::test_date_formula_resolver`

### Status
**Fully Implemented**

---

## 2. `math_formula`

### Purpose
Performs basic arithmetic (`+`, `-`, `*`, `/`) between two numeric fields or a field and a constant.

### User Interaction
1. Type `/` → Select **Math Formula**.
2. Configure:
   - Field A: e.g., `qty`
   - Operator: `*`
   - Field B Type: **Constant Value** or **Field**
   - Constant / Field B: `100` or `rate`
   - Precision: `2`

### Configuration Structure
```json
{
  "kind": "math_formula",
  "field_a": "doc.qty",
  "math_op": "*",
  "field_b_type": "constant",
  "constant_b": 100,
  "precision": 2
}
```

### Frontend Implementation
- **Component**: `MathFormulaResolver.vue`
- **Compiler**: `{frappe.utils.flt(frappe.utils.flt(doc.qty) * 100, 2)}`
- **Validation**: Checks field existence in DocType metadata.

### Generated Expression
`{frappe.utils.flt(frappe.utils.flt(doc.qty) * 100, 2)}`

### Backend Implementation
- **Class**: `MathFormulaResolver`
- **Execution**: Coerces values using `flt()`, computes operation, handles division by zero safely by returning `0.0`, and applies rounding.

### Example
Calculate total amount: `field_a="doc.qty"`, `math_op="*"`, `field_b="doc.rate"` → `2 * 50.0 = 100.0`.

### Tests
- `flexirule/ruleflow/tests/test_assignment_resolver.py::test_math_formula_operations`

### Status
**Fully Implemented**

---

## 3. `date_diff`

### Purpose
Calculates the numerical difference between two dates in days, months, or years.

### Configuration Structure
```json
{
  "kind": "date_diff",
  "diff_start_type": "doc_field",
  "diff_start_field": "posting_date",
  "diff_end_type": "today",
  "diff_end_field": "",
  "diff_unit": "days"
}
```

### Generated Expression
`{frappe.utils.date_diff(frappe.utils.nowdate(), doc.posting_date)}`

### Backend Execution
Uses `frappe.utils.date_diff` or `frappe.utils.month_diff`. Returns `0` if either date is missing.

### Tests
- `flexirule/ruleflow/tests/test_value_resolvers_complex.py::test_date_diff_resolver`

### Status
**Fully Implemented**

---

## 4. `child_aggregation`

### Purpose
Aggregates values across child table rows (`sum`, `avg`, `count`).

### Configuration Structure
```json
{
  "kind": "child_aggregation",
  "agg_table": "doc.items",
  "agg_field": "amount",
  "agg_op": "sum"
}
```

### Generated Expression
`{sum([frappe.utils.flt(row.get("amount")) for row in doc.items])}`

### Backend Execution
Extracts child rows list from context via `get_context_value`. Safe against `None` or missing child table fields.

### Tests
- `flexirule/ruleflow/tests/test_value_resolvers_complex.py::test_child_aggregation_resolver`

### Status
**Fully Implemented**

---

## 5. `string_formula`

### Purpose
Manipulates text fields via concatenation, casing changes (`uppercase`, `lowercase`), or currency formatting (`fmt_money`).

### Configuration Structure
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

### Generated Expression
`{str(doc.first_name or "") + str(doc.last_name or "")}`

### Tests
- `flexirule/ruleflow/tests/test_value_resolvers_complex.py::test_string_formula_resolver`

### Status
**Fully Implemented**

---

## 6. `normalization`

### Purpose
Applies normalization profiles or step pipelines (`trim`, `slug`, `snake_case`, `title_case`, `uppercase`, `lowercase`) to text data.

### Configuration Structure
```json
{
  "kind": "normalization",
  "norm_field": "doc.customer_name",
  "norm_profile": "Clean Text",
  "norm_pipeline": ["trim", "title_case"]
}
```

### Generated Expression
`{flexirule.ruleflow.utils.normalization.execute_normalization_pipeline(doc.customer_name, profile="Clean Text")["normalized_value"]}`

### Tests
- `flexirule/ruleflow/tests/test_normalization_refactor.py`

### Status
**Fully Implemented**

---

## 7. `format`

### Purpose
Formats dates (`format_date`), money (`fmt_money`), or custom string templates (`format`).

### Configuration Structure
```json
{
  "kind": "format",
  "fmt_op": "format_date",
  "fmt_field": "doc.creation",
  "fmt_config": "yyyy-MM-dd"
}
```

### Generated Expression
`{frappe.utils.format_date(doc.creation, "yyyy-MM-dd")}`

### Tests
- `flexirule/ruleflow/tests/test_assignment_resolver.py::test_compile_format_resolver`

### Status
**Fully Implemented**

---

## 8. `fetch`

### Purpose
Fetches a field value from a linked document in the database using `frappe.db.get_value`.

### Configuration Structure
```json
{
  "kind": "fetch",
  "link_field": "doc.customer",
  "fetch_field": "customer_group",
  "linked_doctype": "Customer"
}
```

### Generated Expression
`{frappe.db.get_value("Customer", doc.customer, "customer_group")}`

### Tests
- `flexirule/ruleflow/tests/test_fetch_resolver.py`

### Status
**Fully Implemented**

---

## 9. `system_context`

### Purpose
Provides system session context (`user` ID or `role_check`).

### Configuration Structure
```json
{
  "kind": "system_context",
  "sys_token": "role_check",
  "sys_role": "System Manager"
}
```

### Generated Expression
`{"System Manager" in frappe.get_roles(frappe.session.user)}`

### Tests
- `flexirule/ruleflow/tests/test_value_resolvers_complex.py::test_system_context_resolver`

### Status
**Fully Implemented**

---

## 10. Fallback & Internal Resolvers

### `VariableResolver`
- **Config**: `{ "mode": "variable", "path": "doc.status" }`
- **Execution**: Evaluates `get_context_value(context, path)`.
- **Status**: Backend Internal / Full

### `ExpressionResolver`
- **Config**: `{ "mode": "expression", "value": [ ... ] }`
- **Execution**: Compiles each item in `value` and concatenates resolved strings.
- **Status**: Backend Internal / Full

### `JinjaResolver`
- **Trigger**: String containing `{{` or `{%`, or `jsonToken` inside expression.
- **Execution**: Calls `frappe.render_template(template, context)`.
- **Status**: Backend Internal / Fallback

### `SafeEvalResolver`
- **Trigger**: String starting with `{` and ending with `}`, or raw expression string when `config` is omitted.
- **Execution**: Calls `_safe_eval(expression, context)` with `SafeEvalVisitor` AST checks.
- **Status**: Backend Internal / Fallback

### `StaticResolver` & `NoneResolver`
- **Trigger**: Plain literal scalar, static mode dict, or `None`.
- **Execution**: Returns static value or `None`.
- **Status**: Backend Internal / Full
