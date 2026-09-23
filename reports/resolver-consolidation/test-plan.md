# Test Plan

## Overview
This test plan defines the test matrix required to verify the Value Resolver consolidation, including unit tests, backward compatibility tests, edge case validations, and security regressions.

---

## Test Matrix

### 1. Value Source Resolver (`value_source`)
* Test static primitive resolution (string, integer, boolean, float, null).
* Test document field resolution (`doc.grand_total`).
* Test variable resolution (`vars.calculated_rate`).
* Test system context token resolution (`user`, `role_check`).

### 2. Date Resolver (`date`)
* Test `add` operation with positive/negative offsets across days/months/years.
* Test `subtract` operation across days/months/years.
* Test `diff` operation in days/months/years between two date fields or today.
* Edge cases: NULL start/end date, invalid date strings.

### 3. Text Resolver (`text`)
* Test `concat` combining fields and constants.
* Test case conversion: `upper`, `lower`, `title`, `snake`, `slug`.
* Test whitespace stripping: `trim`.
* Test string replacement: `replace`.
* Test string formatting: `format_date`, `fmt_money`, `pattern`.
* Edge cases: NULL input values, missing fields.

### 4. Math Resolver (`math`)
* Test arithmetic operations: `+`, `-`, `*`, `/`.
* Test min/max calculations across fields/constants.
* Test rounding precision.
* Edge cases: Division by zero (must handle gracefully without raising unhandled Python ZeroDivisionError), NULL field values treated as 0.0.

### 5. Collection Resolver (`collection`)
* Test array operations: `count`, `any`, `all`, `first`, `filter`, `pluck`, `unique`.
* Test condition evaluation over array item rows.
* Edge cases: Empty list input, exceeding `MAX_COLLECTION_ROWS` (10,000 items) limit.

### 6. Aggregate Resolver (`aggregate`)
* Test scalar reductions over child tables: `sum`, `avg`, `min`, `max`, `count`.
* Edge cases: Empty child table (must return 0/0.0), non-existent child table.

### 7. Lookup Resolver (`lookup`)
* Test database getter: `get` retrieving value from linked DocType.
* Test record existence check: `exists`.
* Edge cases: NULL link field value, missing linked record.

### 8. Conditional Resolver (`conditional`)
* Test condition evaluation returning `true_value` when true, `false_value` when false.
* Test nested resolvers in true/false branches.

### 9. Type Conversion Resolver (`type_conversion`)
* Test casting string to integer/decimal/boolean.
* Test casting numeric values to text.
* Edge cases: Invalid string to integer conversion (returns default/null).

### 10. Backward Compatibility Suite
* Execute legacy `date_formula` config payload → verify identical result.
* Execute legacy `date_diff` config payload → verify identical result.
* Execute legacy `string_formula` config payload → verify identical result.
* Execute legacy `normalization` config payload → verify identical result.
* Execute legacy `format` config payload → verify identical result.
* Execute legacy `child_aggregation` config payload → verify identical result.
* Execute legacy `fetch` config payload → verify identical result.
* Execute legacy `system_context` config payload → verify identical result.

### 11. Security Suite
* Verify SafeEval blocks dangerous dunder attributes (`__subclasses__`, `__globals__`).
* Verify Jinja context excludes raw `frappe` module access.
* Verify `lookup` resolver respects Frappe permission filters.
