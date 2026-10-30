# Resolver Inventory & Compatibility Matrix

## Summary Inventory Table

The following table lists every resolver kind and fallback class identified in the repository:

| Canonical Kind / Class | User-Facing Label | Frontend Strategy File | Backend Executor Class | Registry Entry | Config Structure | Tests | Implementation Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `date_formula` | Date Formula | `value_resolver/index.js` | `DateFormulaResolver` | `RESOLVER_STRATEGIES` | `{ kind: "date_formula", base_type, base_field, offset_value, offset_unit, offset_sign }` | `test_value_resolvers_complex.py` | **Fully Implemented** |
| `math_formula` | Math Formula | `value_resolver/index.js` | `MathFormulaResolver` | `RESOLVER_STRATEGIES` | `{ kind: "math_formula", field_a, math_op, field_b_type, field_b, constant_b, precision }` | `test_assignment_resolver.py` | **Fully Implemented** |
| `date_diff` | Date Difference | `value_resolver/index.js` | `DateDiffResolver` | `RESOLVER_STRATEGIES` | `{ kind: "date_diff", diff_start_type, diff_start_field, diff_end_type, diff_end_field, diff_unit }` | `test_value_resolvers_complex.py` | **Fully Implemented** |
| `child_aggregation` | Child Table Aggregation | `value_resolver/index.js` | `ChildAggregationResolver` | `RESOLVER_STRATEGIES` | `{ kind: "child_aggregation", agg_table, agg_field, agg_op }` | `test_value_resolvers_complex.py` | **Fully Implemented** |
| `string_formula` | String Manipulation | `value_resolver/index.js` | `StringFormulaResolver` | `RESOLVER_STRATEGIES` | `{ kind: "string_formula", str_op, str_a_type, str_a, str_b_type, str_b }` | `test_value_resolvers_complex.py` | **Fully Implemented** |
| `normalization` | Normalization | `value_resolver/index.js` | `NormalizationResolver` | `RESOLVER_STRATEGIES` | `{ kind: "normalization", norm_field, norm_profile, norm_pipeline, norm_op }` | `test_normalization_refactor.py` | **Fully Implemented** |
| `format` | Format | `value_resolver/index.js` | `FormatResolver` | `RESOLVER_STRATEGIES` | `{ kind: "format", fmt_op, fmt_field, fmt_config }` | `test_assignment_resolver.py` | **Fully Implemented** |
| `fetch` | Fetch From Link | `value_resolver/index.js` | `FetchResolver` | `RESOLVER_STRATEGIES` | `{ kind: "fetch", link_field, fetch_field, linked_doctype }` | `test_fetch_resolver.py` | **Fully Implemented** |
| `system_context` | System Context | `value_resolver/index.js` | `SystemContextResolver` | `RESOLVER_STRATEGIES` | `{ kind: "system_context", sys_token, sys_role }` | `test_value_resolvers_complex.py` | **Fully Implemented** |
| `VariableResolver` | Variable | Handled via `@` in Tiptap | `VariableResolver` | N/A | `{ mode: "variable", path: "doc.field" }` | `test_value_resolver_core.py` | **Backend Internal / Full** |
| `ExpressionResolver` | Expression | Handled via Tiptap content | `ExpressionResolver` | N/A | `{ mode: "expression", value: [...] }` | `test_value_resolvers_complex.py` | **Backend Internal / Full** |
| `JinjaResolver` | Template String | Handled via raw text / JSON | `JinjaResolver` | N/A | `"{{ doc.field }}"` | `test_value_resolvers_complex.py` | **Backend Internal / Fallback** |
| `SafeEvalResolver` | Python Expression | Handled via Manual Mode | `SafeEvalResolver` | N/A | `"{ doc.field * 2 }"` | `test_value_resolvers_complex.py` | **Backend Internal / Fallback** |
| `StaticResolver` | Static Value | Handled via Static Input | `StaticResolver` | N/A | `{ mode: "static", value: "..." }` | `test_value_resolver_core.py` | **Backend Internal / Full** |
| `NoneResolver` | None | N/A | `NoneResolver` | N/A | `null` | `test_value_resolver_core.py` | **Backend Internal / Full** |

---

## Resolver Detailed Inventory Matrix

### 1. `date_formula`
- **Canonical Kind**: `date_formula`
- **Label**: Date Formula
- **Description**: Calculate a date by adding or subtracting days, months, or years from a base field or today.
- **Supported Fieldtypes**: `Date`, `Datetime`, `Time`
- **Required Config**: `base_type`, `offset_value`, `offset_unit`
- **Optional Config**: `base_field` (required if `base_type` is `doc_field`), `offset_sign` (`+` or `-`)
- **Generated Expression**: `{frappe.utils.add_days(baseExpr, offset)}` or `{frappe.utils.add_to_date(baseExpr, unit=offset)}`
- **Generated Label**: `Date: <base> +<offset> <unit>`
- **Backend Execution Path**: `ValueResolver.compile_resolver_config()` → `DateFormulaResolver.resolve(context)`
- **Expected Input**: Context dictionary containing `doc` / `vars`
- **Output**: Formatted date string (`YYYY-MM-DD`) or `None`
- **Error Behavior**: Returns `None` if base date is empty or missing
- **Security Restrictions**: Safe built-in date math via `frappe.utils`
- **UI Reachable**: Yes (`/` → Date Formula)
- **Backend Executable**: Yes

---

### 2. `math_formula`
- **Canonical Kind**: `math_formula`
- **Label**: Math Formula
- **Description**: Perform basic arithmetic between two fields or a field and a constant value.
- **Supported Fieldtypes**: `Int`, `Float`, `Currency`, `Percent`, `Duration`
- **Required Config**: `field_a`, `math_op` (`+`, `-`, `*`, `/`)
- **Optional Config**: `field_b_type` (`field` or `constant`), `field_b`, `constant_b`, `precision` (default `2`)
- **Generated Expression**: `{frappe.utils.flt(a op b, prec)}`
- **Generated Label**: `Calc: <field_a> <op> <b_val>`
- **Backend Execution Path**: `ValueResolver.compile_resolver_config()` → `MathFormulaResolver.resolve(context)`
- **Expected Input**: Context dictionary containing numeric values
- **Output**: `float` rounded to `precision`
- **Error Behavior**: Division by zero returns `0.0`
- **Security Restrictions**: Arithmetic only, coerced with `flt()`
- **UI Reachable**: Yes (`/` → Math Formula)
- **Backend Executable**: Yes

---

### 3. `date_diff`
- **Canonical Kind**: `date_diff`
- **Label**: Date Difference
- **Description**: Calculate time difference between two dates in days, months, or years.
- **Supported Fieldtypes**: `Int`, `Float`, `Date`, `Datetime`
- **Required Config**: `diff_start_type`, `diff_end_type`, `diff_unit` (`days`, `months`, `years`)
- **Optional Config**: `diff_start_field`, `diff_end_field`
- **Generated Expression**: `{frappe.utils.date_diff(end, start)}` / `{frappe.utils.month_diff(end, start)}`
- **Generated Label**: `<end> − <start> (<unit>)`
- **Backend Execution Path**: `ValueResolver.compile_resolver_config()` → `DateDiffResolver.resolve(context)`
- **Expected Input**: Context containing start and end date fields
- **Output**: `int` (number of days, months, or years)
- **Error Behavior**: Returns `0` if either start or end date is missing
- **Security Restrictions**: Built-in `frappe.utils.date_diff` / `month_diff`
- **UI Reachable**: Yes (`/` → Date Difference)
- **Backend Executable**: Yes

---

### 4. `child_aggregation`
- **Canonical Kind**: `child_aggregation`
- **Label**: Child Table Aggregation
- **Description**: Aggregate numeric values from a child table using Sum, Average, or Count.
- **Supported Fieldtypes**: `Int`, `Float`, `Currency`, `Percent`
- **Required Config**: `agg_table`, `agg_op` (`sum`, `avg`, `count`)
- **Optional Config**: `agg_field` (required if `agg_op` is `sum` or `avg`)
- **Generated Expression**: `{sum([frappe.utils.flt(row.get(fld)) for row in tblExpr])}` / `{len(tblExpr)}`
- **Generated Label**: `<OP>(<agg_table>.<agg_field>)`
- **Backend Execution Path**: `ValueResolver.compile_resolver_config()` → `ChildAggregationResolver.resolve(context)`
- **Expected Input**: Context containing child table array under `doc.<agg_table>` or `vars.<agg_table>`
- **Output**: `float` or `int`
- **Error Behavior**: Returns `0` or `0.0` if table is empty, `None`, or missing
- **Security Restrictions**: List comprehension over local dicts
- **UI Reachable**: Yes (`/` → Child Table Aggregation)
- **Backend Executable**: Yes

---

### 5. `string_formula`
- **Canonical Kind**: `string_formula`
- **Label**: String Manipulation
- **Description**: Combine text fields, change casing, or format currency strings.
- **Supported Fieldtypes**: `Data`, `Small Text`, `Text`, `Long Text`, `Link`, `Select`
- **Required Config**: `str_op` (`concat`, `uppercase`, `lowercase`, `fmt_money`)
- **Optional Config**: `str_a_type`, `str_a`, `str_b_type`, `str_b`
- **Generated Expression**: `{str(valA or "") + str(valB or "")}` / `{str(valA).upper()}`
- **Generated Label**: `<OP>(<valA>, <valB>)`
- **Backend Execution Path**: `ValueResolver.compile_resolver_config()` → `StringFormulaResolver.resolve(context)`
- **Expected Input**: Context containing text fields
- **Output**: `str`
- **Error Behavior**: Coerces `None` to `""`
- **Security Restrictions**: Safe string operations
- **UI Reachable**: Yes (`/` → String Manipulation)
- **Backend Executable**: Yes

---

### 6. `normalization`
- **Canonical Kind**: `normalization`
- **Label**: Normalization
- **Description**: Clean up text data by trimming whitespace, changing case, or converting to slug/snake case.
- **Supported Fieldtypes**: `Data`, `Small Text`, `Text`, `Long Text`, `Code`
- **Required Config**: `norm_field`
- **Optional Config**: `norm_profile` (e.g. `Custom`, `Clean Text`), `norm_pipeline` (array of step names), `norm_op` (legacy)
- **Generated Expression**: `{flexirule.ruleflow.utils.normalization.execute_normalization_pipeline(...)["normalized_value"]}`
- **Generated Label**: `Normalize: <norm_field> (<profile_or_steps>)`
- **Backend Execution Path**: `ValueResolver.compile_resolver_config()` → `NormalizationResolver.resolve(context)`
- **Expected Input**: Context containing target field
- **Output**: `str` or `None`
- **Error Behavior**: Returns `None` if value is `None`
- **Security Restrictions**: Pipeline steps restricted to registered functions in `normalization.py`
- **UI Reachable**: Yes (`/` → Normalization)
- **Backend Executable**: Yes

---

### 7. `format`
- **Canonical Kind**: `format`
- **Label**: Format
- **Description**: Format dates, currency amounts, or custom string templates.
- **Supported Fieldtypes**: `Data`, `Date`, `Datetime`, `Currency`, `Int`, `Float`
- **Required Config**: `fmt_op` (`format_date`, `fmt_money`, `format`), `fmt_field`
- **Optional Config**: `fmt_config` (date format pattern, currency code/field, or format string)
- **Generated Expression**: `{frappe.utils.format_date(f, cfg)}` / `{frappe.utils.fmt_money(f, currency=curr)}`
- **Generated Label**: `<fmt_op>(<fmt_field>)`
- **Backend Execution Path**: `ValueResolver.compile_resolver_config()` → `FormatResolver.resolve(context)`
- **Expected Input**: Context containing field to format
- **Output**: `str`
- **Error Behavior**: Returns `""` if field value is `None`
- **Security Restrictions**: Standard Frappe formatting utilities
- **UI Reachable**: Yes (`/` → Format)
- **Backend Executable**: Yes

---

### 8. `fetch`
- **Canonical Kind**: `fetch`
- **Label**: Fetch From Link
- **Description**: Fetch field value from a linked document in the database.
- **Supported Fieldtypes**: `Link`, `Dynamic Link`, `Data`, `Select`, `Check`, `Date`, `Currency`
- **Required Config**: `link_field`, `fetch_field`, `linked_doctype`
- **Optional Config**: `link_source_type` (`doc_field`)
- **Generated Expression**: `{frappe.db.get_value(dtExpr, link, fetch_field)}`
- **Generated Label**: `<linked_doctype>.<fetch_field> ← <link_field>`
- **Backend Execution Path**: `ValueResolver.compile_resolver_config()` → `FetchResolver.resolve(context)`
- **Expected Input**: Context containing `link_field` value
- **Output**: Single field value from DB or `None`
- **Error Behavior**: Returns `None` if link value or target field is missing
- **Security Restrictions**: Single read-only `frappe.db.get_value` call
- **UI Reachable**: Yes (`/` → Fetch From Link)
- **Backend Executable**: Yes

---

### 9. `system_context`
- **Canonical Kind**: `system_context`
- **Label**: System Context
- **Description**: Access current logged-in user or evaluate user role checks.
- **Supported Fieldtypes**: `Data`, `Link` (User), `Check`
- **Required Config**: `sys_token` (`user` or `role_check`)
- **Optional Config**: `sys_role` (role name string)
- **Generated Expression**: `{frappe.session.user}` or `{"role" in frappe.get_roles(frappe.session.user)}`
- **Generated Label**: `Current User` or `Has Role`
- **Backend Execution Path**: `ValueResolver.compile_resolver_config()` → `SystemContextResolver.resolve(context)`
- **Expected Input**: Active Frappe user session
- **Output**: `str` (user ID) or `bool` (role check)
- **Error Behavior**: Returns `None` for invalid token
- **Security Restrictions**: Session read-only
- **UI Reachable**: Yes (`/` → System Context)
- **Backend Executable**: Yes
