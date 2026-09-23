# Fieldtype Support & Matrix

## Overview

FlexiRule dynamically adapts available resolvers and slash commands based on the Frappe field type of the target control. Fieldtype mappings are centrally defined in `flexirule/public/js/flexirule/core/formula_registry.js`.

---

## Fieldtype Compatibility Matrix

| Fieldtype | Static | Variable (`@`) | Allowed Resolver Kinds (`getAllowedBuilderKinds`) | Command Palette (`/`) | Backend Evaluator Support | Notes |
| :--- | :---: | :---: | :--- | :--- | :---: | :--- |
| **Data** | Yes | Yes | `normalization`, `format`, `fetch`, `string_formula`, `system_context` | `/formula`, `/resolver`, `/formatter`, `/normalize`, `/clear` | Full | Default group `TEXT` |
| **Small Text** | Yes | Yes | `normalization`, `format`, `fetch`, `string_formula`, `system_context` | `/formula`, `/resolver`, `/formatter`, `/normalize` | Full | Group `TEXT` |
| **Long Text / Text** | Yes | Yes | `normalization`, `format`, `fetch`, `string_formula`, `system_context` | `/formula`, `/resolver`, `/formatter`, `/normalize` | Full | Group `TEXT` |
| **Text Editor / Code / JSON** | No | Yes | `normalization`, `format`, `fetch`, `string_formula`, `system_context` | `/formula`, `/resolver`, `/json`, `/clear` | Full | Pure text editors skip static input mode |
| **Int / Float / Currency / Percent / Duration** | Yes | Yes | `math_formula`, `child_aggregation`, `date_diff`, `fetch`, `format`, `system_context` | `/formula`, `/resolver`, `/formatter`, `/clear` | Full | Group `NUMERIC` |
| **Date / Datetime / Time** | Yes | Yes | `date_formula`, `date_diff`, `fetch`, `format`, `system_context` | `/formula`, `/resolver`, `/formatter`, `/clear` | Full | Group `DATE` |
| **Check (Boolean)** | Yes | Yes | `fetch`, `system_context` | `/boolean`, `/condition`, `/clear` | Full | Group `BOOLEAN` |
| **Link / Dynamic Link** | Yes | Yes | `fetch`, `string_formula`, `format`, `system_context` | `/link`, `/fetch`, `/clear` | Full | Group `LINK` |
| **Select** | Yes | Yes | `normalization`, `format`, `fetch`, `string_formula`, `system_context` | `/select`, `/clear` | Full | Group `SELECT` |
| **MultiSelect / Table MultiSelect** | Yes | Yes | `fetch`, `string_formula`, `format`, `system_context` | `/multiselect`, `/clear` | Full | Rendered via `MultiSelectList` |

---

## Frontend vs Backend Validation Discrepancies

### 1. Child Aggregation Availability on Text Fields
- **Frontend**: `getAllowedBuilderKinds()` only includes `child_aggregation` for numeric fieldtypes (`Int`, `Float`, `Currency`, `Percent`, `Duration`). It is excluded for `Data` or `Text` fieldtypes.
- **Backend**: `ChildAggregationResolver` in Python can aggregate or count any field regardless of the rule action's target fieldtype. If a user manually crafts a payload with `kind: "child_aggregation"` on a `Data` field, the backend executes it without issue.

### 2. Math Formula on Text / Date Fields
- **Frontend**: `getAllowedBuilderKinds()` restricts `math_formula` to numeric fieldtypes.
- **Backend**: `MathFormulaResolver` converts inputs using `frappe.utils.flt()`. If executed on non-numeric fields, `flt()` coerces string representations to `0.0`.

### 3. Fetch Resolver Ubiquity
- **Frontend**: `getAllowedBuilderKinds()` includes `fetch` for nearly all fieldtypes (`Date`, `Numeric`, `Text`, `Link`, `Check`).
- **Backend**: `FetchResolver` performs a standard `frappe.db.get_value(linked_doctype, link_value, fetch_field)` lookup, returning raw database scalar values regardless of target fieldtype.
