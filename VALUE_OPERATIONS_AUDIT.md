# Value Operations Discovery Audit Report

## A. Capability Inventory

This inventory lists all value manipulation capabilities exposed in FlexiRule, categorized by their entry point.

### 1. Structured Value Resolvers (via `ValueResolverControl`)
| Kind | Name | Description | Sub-Operations |
| :--- | :--- | :--- | :--- |
| `date_formula` | Date Formula | Calculate a date by adding or subtracting days, months, or years from a base field or today. | Add/Subtract Days, Months, Years |
| `date_diff` | Date Difference | Calculate the time difference between two dates in days, months, or years. | Days, Months, Years |
| `math_formula` | Math Formula | Perform basic arithmetic between two fields or a field and a constant value. | `+`, `-`, `*`, `/` |
| `child_aggregation` | Child Table Aggregation | Aggregate numeric values from a child table using Sum, Average, or Count. | Sum, Average, Count |
| `string_formula` | String Manipulation | Combine text fields, change casing, or format currency strings. | Concatenate, Uppercase, Lowercase, Format Currency |
| `normalization` | Normalization | Clean up text data by trimming whitespace, changing case, or converting to slug/snake case. | Pipeline of 25+ operations (Trim, Slug, Masking, etc.) |
| `format` | Format | Presentation-level formatting for dates, currency, and templates. | Date/Time, Currency, String Template |
| `fetch` | Fetch From Link | Fetch a value from a linked document. | Database lookup across DocTypes |
| `system_context` | System Context | Resolve global values like current user or role status. | Current User, Role Check |

### 2. Formula Registry & Slash Commands (`formula_registry.js`)
These are exposed as autocomplete suggestions or slash commands in the `FlexValueControl`.

**Slash Commands (Value-Related):**
- `/formula`: Opens logic selection.
- `/resolver`: Opens structured resolver.
- `/formatter`: Opens formatting UI.
- `/normalize`: Opens normalization UI.
- `/fetch`: Opens link fetching UI.
- `/link`: Opens link picker.
- `/boolean`: Opens toggle UI.

**Formula Registry Items (by Category):**
- **TEXT:** `concat`, `normalize`, `format`, `replace`, `trim`, `upper`, `lower`, `slug`.
- **NUMERIC:** `sum`, `round`, `avg`, `min`, `max`, `percentage`, `abs`.
- **DATE:** `today`, `now`, `add_days`, `add_months`, `date_diff`, `format_date`, `start_of`, `end_of`.
- **BOOLEAN:** `if`, `equals`, `not`.
- **LINK:** `lookup`.
- **TABLE:** `sum`, `count`, `map`, `filter`, `reduce`.

### 3. Normalization Operations (`normalization.py`)
Exposed primarily through the `NormalizationResolver` pipeline.

- **Cleaning:** `trim`, `remove_spaces`, `remove_extra_spaces`, `remove_punctuation`, `remove_numbers`.
- **Casing:** `lowercase`, `uppercase`, `casefold`, `title_case`, `name_normalize`.
- **Transformations:** `slug`, `snake_case`, `unicode_normalize`, `remove_diacritics`, `translate_chars` (Arabic/Persian digits & characters).
- **Specialized:** `phone_normalize`, `email_normalize`, `currency_to_number`, `tax_id_clean`, `standard_date`.
- **Masking:** `mask_email`, `mask_phone`, `mask_credit_card`, `mask_partial`.

---

## B. Runtime Mapping

This table traces frontend capabilities to their backend execution logic.

| Frontend Identifier | Backend Implementation Path | Actual Execution Logic |
| :--- | :--- | :--- |
| `date_formula` | `ValueResolver.compile` → `DateFormulaResolver.resolve` | `frappe.utils.add_days` or `frappe.utils.add_to_date` |
| `math_formula` | `ValueResolver.compile` → `MathFormulaResolver.resolve` | `frappe.utils.flt(a op b, precision)` |
| `date_diff` | `ValueResolver.compile` → `DateDiffResolver.resolve` | `frappe.utils.date_diff` or `frappe.utils.month_diff` |
| `child_aggregation`| `ValueResolver.compile` → `ChildAggregationResolver.resolve` | List comprehension over `doc.get(table)` with `sum()`/`len()` |
| `string_formula` | `ValueResolver.compile` → `StringFormulaResolver.resolve` | Python `str.upper()`, `str.lower()`, or `frappe.utils.fmt_money` |
| `normalization` | `ValueResolver.compile` → `NormalizationResolver.resolve` | `flexirule.ruleflow.utils.normalization.execute_normalization_pipeline` |
| `format` | `ValueResolver.compile` → `FormatResolver.resolve` | `frappe.utils.format_date`, `frappe.utils.fmt_money`, or `"".format()` |
| `fetch` | `ValueResolver.compile` → `FetchResolver.resolve` | `frappe.db.get_value` |
| `system_context` | `ValueResolver.compile` → `SystemContextResolver.resolve` | `frappe.session.user` or `frappe.get_roles` |
| `today()` (Formula) | `RuleEngine._build_eval_locals` | `frappe.utils.nowdate` mapped as `nowdate` in context |
| `add_days()` (Formula)| `RuleEngine._build_eval_locals` | `frappe.utils.add_days` mapped as `add_days` in context |
| `sum()` (Formula) | `ActionHandler._build_template_context` | Python built-in `sum()` |
| `normalize()` (Jinja)| `ActionHandler._build_template_context` | `flexirule.ruleflow.process.normalization.normalization.apply_transformations` |

---

## C. Duplicate List (Exact Duplicates)

Operations that use identical underlying logic but are exposed under different names or categories:

1.  **Currency Formatting:**
    - `String Formula` resolver → `fmt_money`
    - `Format` resolver → `fmt_money`
    - *Both call `frappe.utils.fmt_money`.*
2.  **Basic Casing:**
    - `String Formula` resolver → `uppercase`/`lowercase`
    - `Normalization` resolver → `uppercase`/`lowercase` pipeline steps
    - *Both call Python `.upper()` / `.lower()`.*
3.  **Date Difference:**
    - `Date Difference` resolver
    - `/formula` suggestion for `date_diff()`
    - *Both call `frappe.utils.date_diff`.*

---

## D. Similarity List (Functional Overlaps)

Operations that produce substantially similar results through different mechanisms:

1.  **Concatenation:**
    - `String Formula` resolver: 2-field visual builder.
    - `concat()` Formula: Variadic text function.
    - `String Template` (Format resolver): Uses `"{field_a}{field_b}".format()`.
2.  **Date Math:**
    - `Date Formula` resolver: Step-based UI (Add 5 days).
    - `add_days()` / `add_months()` Formulas: Functional approach.
3.  **Normalization vs Formulas:**
    - `trim()`, `upper()`, `lower()`, `slug()` exist both as standalone formulas and as steps in the `Normalization` pipeline.
4.  **Aggregation:**
    - `Child Table Aggregation` resolver: Visual UI for Sum/Avg/Count.
    - `sum()`, `count()`, `len()` formulas: Direct access to Python aggregations.

---

## E. Observations

### 1. Registry vs. Runtime Gaps
The `formula_registry.js` contains many items (like `map`, `reduce`, `slug`) that are primarily UI "hints." There is no single centralized "Formula Library" on the backend; instead, the `RuleEngine` and `ActionHandler` manually inject various helpers into different evaluation contexts (Python Eval vs. Jinja), leading to inconsistent availability of functions depending on where they are used.

### 2. Architectural Redundancy
The `String Formula` resolver is largely a subset of the `Format` and `Normalization` resolvers. It appears to be a legacy entry point that has been superseded by more specialized strategies.

### 3. Hidden Backend Power
The `normalization.py` utility contains sophisticated logic (Arabic character unification, diacritic removal, various masking strategies) that is only fully accessible through the `Normalization` resolver's "Custom Pipeline" mode. These capabilities are not exposed in the simpler `/formula` or `/formatter` registries.

### 4. Implementation Leakage
Several frontend strategies (e.g., `Aggregation`) "leak" implementation details by compiling complex Python list comprehensions in the frontend `compileToCode` function. This makes it difficult to change the aggregation logic (e.g., adding null checks) without updating the frontend registry.

### 5. Inconsistent Scoping
The `Fetch` resolver defaults to `doc.` scoping if no scope is provided, while the `Formula` system requires explicit scoping or relies on the evaluator's local resolution logic.

### 6. Special Case Context
The `Assignment` action handler injects a special `value` variable into the evaluation context specifically for Normalization and Formatting steps. This "current value" awareness is not consistently available across other action types or resolvers.

---

## F. Capability Coverage Matrix

Mapping of unique value operations to their availability across different entry points.

| Capability | Formula | String | Normalize | Format | Date | Math | Aggreg | Fetch | System |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **TEXT** | | | | | | | | | |
| trim | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| lowercase | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| uppercase | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| title_case | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| concat | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| slug | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| snake_case | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| template format | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| remove_spaces | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| remove_punctuation | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **NUMERIC** | | | | | | | | | |
| sum | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |
| average | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |
| count | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ |
| arithmetic (+,-,*,/) | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| round | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ |
| currency format | ✗ | ✓ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **DATE/TIME** | | | | | | | | | |
| today / now | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| add_days/months | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ |
| date_diff | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| format_date | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **SPECIALIZED** | | | | | | | | | |
| phone_normalize | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| email_normalize | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| mask_email/phone | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Arabic unification | ✗ | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| lookup / fetch | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| current_user | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| role_check | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |

---

## G. Matrix Analysis

### 1. Multi-Source Capabilities
Capabilities like **lowercase**, **uppercase**, **sum**, and **average** are heavily distributed, appearing in 3 or more places. This suggests high demand but inconsistent implementation across the UI.

### 2. Single-Source Capabilities
- **Masking** and **Arabic unification** are exclusive to the Normalization Resolver.
- **Arithmetic operators** are exclusive to the Math Resolver (when using the builder) or raw Formulas.
- **Role checks** are exclusive to the System Resolver.
- **Fetch** logic is centralized in the Fetch Resolver.

### 3. Resolvers with No Unique Capability
The **String Formula Resolver** contributes no unique capabilities. Everything it does (concat, upper, lower, fmt_money) is available through either the Normalization Resolver, Format Resolver, or direct Formulas.

### 4. UX Wrappers
- The **Math Resolver** is essentially a UX wrapper for Python's `flt()` and arithmetic operators.
- The **Date Resolver** is a UX wrapper for `frappe.utils.add_days` and `add_months`.
- The **Child Aggregation Resolver** is a UX wrapper for list comprehensions.

### 5. Hidden Capabilities
The **Normalization Resolver** contains many specialized operations (Phone/Email normalization, Punctuation removal, Masking, Arabic unification) that are powerful but hidden from the general "Format" or "Formula" user journeys. These are currently "locked" behind a specific resolver kind, making them inaccessible for users who don't think to look under "Normalization."
