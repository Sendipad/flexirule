# Date/Time Resolver Investigation

## 1. Executive Finding

The current Date/Time resolver implementation in FlexiRule (`family: "date_time"`) provides a clean, functional foundation for basic date arithmetic, differences, and string formatting. However, when measured against the requirements of enterprise business rule engines (such as SLA deadline calculations, time-based event triggers, shift/schedule calculations, boundary normalization, and timezone conversions), **the current Date/Time configuration model is incomplete and partially misaligned across execution layers.**

Specifically:

1. **Arithmetic is Limited to Scalar Offsets:** The `calculate` operation supports scalar addition/subtraction of `days`, `weeks`, `months`, `years`, and `hours`. However, minutes and seconds cannot be added/subtracted, nor can base date/time values be combined dynamically with variable/field offset amounts.
2. **Date Difference Calculation Silently Drops Time Units:** While `diff_unit` in `DateDiffResolver` allows selecting `days`, `months`, and `years`, selecting or attempting `hours`, `minutes`, or `seconds` either defaults to 0 or is unsupported, because the underlying execution calls `frappe.utils.date_diff` or `frappe.utils.month_diff` which discard time components.
3. **Missing Critical Calendar Operations:** Common business rule needs such as **Component Extraction** (`year`, `month`, `day`, `hour`, `weekday`), **Boundary Normalization** (`start_of_day`, `end_of_month`, `start_of_year`), and **Timezone Conversions** (`system_to_utc`, `utc_to_user`, `convert_timezone`) are completely absent from the Date/Time resolver.
4. **Sub-Optimal Frappe API Integration:** The resolver reimplements simple date math (`add_days`, `add_to_date`) directly while ignoring robust native Frappe APIs (`frappe.utils.get_first_day`, `frappe.utils.get_last_day`, `frappe.utils.time_diff_in_hours`, `frappe.utils.time_diff_in_seconds`, `frappe.utils.get_datetime_in_timezone`).

**Final Central Conclusion:**

> _Does the current Date/Time resolver provide a sufficiently complete configuration model for the practical date/time requirements of FlexiRule?_
> **No.** While the existing 3 operations (`calculate`, `diff`, `format`) cover elementary date math, the configuration model is too restrictive to represent practical real-world operations (such as component extraction, boundary normalization, sub-hour arithmetic, exact duration differences, and timezone awareness). A minimalist, non-breaking expansion of the `date_time` family operations and configuration schema is strongly recommended.

---

## 2. Current Implementation

The Date/Time resolver system spans both backend Python classes and frontend Vue.js components.

### Backend Architecture (`flexirule/ruleflow/core/value_resolver.py`)

- **Canonical Family:** `family: "date_time"` or `kind: "date_time"`.
- **Compiled Resolver Classes:**
    - `DateFormulaResolver`: Handles the `calculate` operation by calling `frappe.utils.add_days` or `frappe.utils.add_to_date`.
    - `DateDiffResolver`: Handles the `diff` operation by calling `frappe.utils.date_diff` or `frappe.utils.month_diff`.
    - `FormatResolver`: Handles the `format` operation by delegating to `frappe.utils.format_date`.
- **Dispatch Logic (`ValueResolver.compile_resolver_config`):** Inspects `family == "date_time"` or `kind == "date_time"` and dispatches based on `config.get("operation")` (defaulting to `"calculate"`).

### Frontend Architecture (`flexirule/public/js/flexirule/rule_builder/controls/value_resolver/`)

- **Strategy Registration (`index.js`):** Registers strategy `"date_time"` with `label: "Date & Time"` and description _"Calculate date & time values, compute time differences, or format date/time values."_
- **Main UI Component (`components/DateTimeResolver.vue`):** Renders an operation selector dropdown containing:
    - `calculate` ("Date & Time Formula") -> `DateTimeCalculateConfig.vue`
    - `diff` ("Date & Time Difference") -> `DateTimeDiffConfig.vue`
    - `format` ("Format Date & Time") -> `DateTimeFormatConfig.vue`
- **Reactivity & Compilation Composable (`useValueResolver.js`):** Normalizes legacy configs into canonical `{ family: "date_time", operation: "...", config: { ... } }`.

---

## 3. Resolver Data Flow

```
+-----------------------------------------------------------------------+
| 1. UI Configuration (DateTimeResolver.vue + Operation Sub-Components) |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 2. Canonical JSON Payload                                              |
|    {                                                                  |
|      "family": "date_time",                                           |
|      "operation": "calculate" | "diff" | "format",                    |
|      "config": { ... }                                                |
|    }                                                                  |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 3. Frontend Variable Preview Generator (index.js -> date_time)        |
|    Generates human-readable string like:                              |
|    "{frappe.utils.add_to_date(doc.creation, days=5)}"                 |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 4. Backend Dispatch (ValueResolver.compile_resolver_config)           |
|    Constructs DateFormulaResolver, DateDiffResolver, or FormatResolver|
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 5. Runtime Execution (.resolve(context))                              |
|    Evaluates field values from context and calls frappe.utils         |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 6. Return Value                                                       |
|    Returns ISO string, formatted string, or integer difference        |
+-----------------------------------------------------------------------+
```

---

## 4. Current Configuration Schema

### Canonical Payload Structure

```json
{
  "family": "date_time",
  "operation": "calculate" | "diff" | "format",
  "config": { ... }
}
```

### Operation 1: `calculate`

| Key            | Type    | Optional/Required | Default   | Frontend Control                           | Backend Interpretation                                                      |
| -------------- | ------- | ----------------- | --------- | ------------------------------------------ | --------------------------------------------------------------------------- |
| `base_type`    | String  | Required          | `"today"` | `SelectControl` (`"today"`, `"doc_field"`) | `"today"` -> `frappe.utils.nowdate()`, `"doc_field"` -> lookup `base_field` |
| `base_field`   | String  | Conditional       | `""`      | `ComboBoxControl`                          | Field path evaluated via `get_context_value`                                |
| `offset_sign`  | String  | Required          | `"+"`     | `SelectControl` (`"+"`, `"-"`)             | Negates `offset_value` if `"-"`                                             |
| `offset_value` | Integer | Required          | `0`       | `DataControl` (Int)                        | Numeric quantity to add/subtract                                            |
| `offset_unit`  | String  | Required          | `"days"`  | `SelectControl`                            | `"days"`, `"weeks"`, `"months"`, `"years"`, `"hours"`                       |

### Operation 2: `diff`

| Key                | Type   | Optional/Required | Default       | Frontend Control  | Backend Interpretation                                  |
| ------------------ | ------ | ----------------- | ------------- | ----------------- | ------------------------------------------------------- |
| `diff_start_type`  | String | Required          | `"today"`     | `SelectControl`   | `"today"` -> `nowdate()`, `"doc_field"` -> lookup field |
| `diff_start_field` | String | Conditional       | `""`          | `ComboBoxControl` | Start field path                                        |
| `diff_end_type`    | String | Required          | `"doc_field"` | `SelectControl`   | `"today"` -> `nowdate()`, `"doc_field"` -> lookup field |
| `diff_end_field`   | String | Conditional       | `""`          | `ComboBoxControl` | End field path                                          |
| `diff_unit`        | String | Required          | `"days"`      | `SelectControl`   | `"days"`, `"months"`, `"years"`                         |

### Operation 3: `format`

| Key          | Type   | Optional/Required | Default        | Frontend Control  | Backend Interpretation                                   |
| ------------ | ------ | ----------------- | -------------- | ----------------- | -------------------------------------------------------- |
| `fmt_field`  | String | Required          | `""`           | `ComboBoxControl` | Target field path                                        |
| `fmt_config` | String | Required          | `"YYYY-MM-DD"` | `DataControl`     | Date format pattern passed to `frappe.utils.format_date` |

---

## 5. Supported Operations

| Capability Area                | Supported Operations                                  | Unsupported / Missing Operations                                               |
| ------------------------------ | ----------------------------------------------------- | ------------------------------------------------------------------------------ |
| **Current Date/Time**          | Today's date (`nowdate()`)                            | Current Datetime (`now_datetime()`), Current Time (`nowtime()`), UTC timestamp |
| **Field Values**               | Document field lookup (`doc.*`, `vars.*`, `row.*`)    | Dynamic resolver chaining, child table row date evaluation                     |
| **Arithmetic**                 | Add/Subtract scalar Days, Weeks, Months, Years, Hours | Add/Subtract Minutes, Seconds; Dynamic offset from variable/field              |
| **Differences**                | Difference in Days, Months, Years                     | Difference in Hours, Minutes, Seconds, Exact Durations                         |
| **Extraction**                 | None                                                  | Year, Month, Day, Weekday, Hour, Minute, Second, Quarter                       |
| **Normalization / Boundaries** | None                                                  | Start/End of Day, Week, Month, Quarter, Year                                   |
| **Timezone Conversions**       | None                                                  | Server-to-UTC, UTC-to-User, Specific Timezone Conversion                       |

---

## 6. Input and Output Types

### Input Types Accepted

- **UI Filtering:** `dateFieldOptions` in Vue components filter fields by `fieldtype`:
    - `DateTimeCalculateConfig`: `["Date", "Datetime", "Time"]`
    - `DateTimeDiffConfig`: `["Date", "Datetime", "Time", "Int", "Float", "Currency", "Percent", "Duration"]`
    - `DateTimeFormatConfig`: `["Date", "Datetime", "Time", "Data", "Text", ...]`
- **Backend Behavior:** Accepts strings (e.g. `"2026-01-31"`, `"2026-01-31 10:00:00"`), `datetime.date`, or `datetime.datetime` objects.

### Output Types Produced

- **`calculate`:** Returns an ISO string (e.g. `"2026-01-06"` or `"2026-01-31 15:00:00.000000"`).
- **`diff`:** Returns an Integer representing the difference (e.g., `10` days).
- **`format`:** Returns a formatted String (e.g., `"2026-01-01"` or `"01/01/2026"`).

### Type Discrepancies & Flaws

1. **Loss of Datetime Precision in `today`:** Selecting `base_type: "today"` always uses `frappe.utils.nowdate()`, stripping time components even if the offset unit is `"hours"`.
2. **Untyped String Outputs:** Date arithmetic returning strings can cause type conversion issues when chained into math or collection resolvers expecting Python `datetime` objects.

---

## 7. Timezone Behavior

1. **Server vs System vs User Timezone:** Native Frappe utilities rely on `frappe.utils.get_system_timezone()` (configured in System Settings). Current FlexiRule `nowdate()` execution uses system time without user timezone context.
2. **Timezone Awareness:** All calculations performed by `DateFormulaResolver` and `DateDiffResolver` operate on naive datetime strings. No timezone awareness or conversion logic exists in `value_resolver.py`.
3. **Missing Frappe Timezone APIs:** Native Frappe functions such as `get_datetime_in_timezone` and `convert_utc_to_system_timezone` are completely unutilized.

---

## 8. Frappe Integration

FlexiRule properly uses Frappe framework utility functions for base operations, but misses several key native functions:

| Concept             | Frappe Native Utility                        | FlexiRule Usage                        | Status  |
| ------------------- | -------------------------------------------- | -------------------------------------- | ------- |
| Add Offset          | `frappe.utils.add_to_date(date, **kwargs)`   | Used for weeks/months/years/hours      | Correct |
| Add Days            | `frappe.utils.add_days(date, days)`          | Used for days                          | Correct |
| Date Difference     | `frappe.utils.date_diff(end, start)`         | Used for days                          | Correct |
| Month Difference    | `frappe.utils.month_diff(end, start)`        | Used for months/years                  | Correct |
| Hour/Sec Diff       | `frappe.utils.time_diff_in_hours / seconds`  | **Not Used**                           | **Gap** |
| Period Boundaries   | `frappe.utils.get_first_day / get_last_day`  | **Not Used**                           | **Gap** |
| Datetime Formatting | `frappe.utils.format_datetime / format_time` | **Not Used** (only `format_date` used) | **Gap** |

---

## 9. Frontend / UX Configuration

1. **Validation Real-Time Feedback:** `DateTimeCalculateConfig.vue` provides real-time field validation messages if a selected field does not exist in the store metadata.
2. **UI Gap - Unit Mismatch in `diff`:** The UI for `diff` allows selecting `diff_unit: "days"`, `"months"`, or `"years"`. It does not expose `hours` or `minutes`, despite users needing hourly duration differences.
3. **UI Gap - Missing Operations Selector Options:** Component extraction and start/end period options are not present in `DateTimeResolver.vue`.

---

## 10. Backend Validation and Execution

1. **Loose Config Handling:** `ValueResolver.compile_resolver_config` provides safe defaults for missing keys (e.g., defaulting `offset_value` to `0`, `offset_unit` to `"days"`).
2. **Error Handling:** Null/empty base fields evaluate safely to `None` or `0` without throwing unhandled exceptions.
3. **Validation Service Gap:** `validation_service.py` checks basic structure but does not validate if `offset_unit` or `diff_unit` contain valid options.

---

## 11. Existing Test Coverage

Backend test coverage in `flexirule/ruleflow/tests/test_value_resolvers_complex.py` covers:

- `test_date_time_family_resolver`: Canonical family compile for `calculate`, `diff`, and `format`.
- `test_date_formula_resolver`: Direct class unit testing including leap years (`2024-02-28 + 1 day -> 2024-02-29`) and month-end boundary rollover (`2026-01-31 + 1 month -> 2026-02-28`).
- `test_date_diff_resolver`: Direct class unit testing for days, months, and years difference.

**Missing Test Cases:**

- Sub-hour arithmetic (minutes/seconds).
- Hourly time differences.
- Timezone conversions or DST transitions.
- Invalid format strings.

---

## 12. Missing or Difficult Capabilities

| Missing Capability             | Category  | Practical Impact                                                                    |
| ------------------------------ | --------- | ----------------------------------------------------------------------------------- |
| **Minutes & Seconds Offset**   | Essential | Cannot calculate SLA deadlines expressed in minutes (e.g. 30-min response SLA).     |
| **Hourly / Minute Difference** | Essential | Cannot calculate duration between two datetime fields in hours/minutes.             |
| **Component Extraction**       | Useful    | Cannot extract `year` or `month` to construct fiscal grouping keys or conditionals. |
| **Period Boundaries**          | Useful    | Cannot calculate `start_of_month` or `end_of_month` for scheduled accounting rules. |
| **Dynamic Offset Value**       | Essential | Offset value must be static integer; cannot use a field/variable as offset.         |
| **Timezone Conversion**        | Useful    | Cannot convert UTC timestamps from external integrations to user local time.        |

---

## 13. Architectural Assessment

A. **Is the current Date/Time resolver conceptually complete?**
No. While adequate for basic date math, it lacks essential time granularity (minutes, seconds, duration diffs) and period boundaries.

B. **Are there important missing capabilities?**
Yes:

- _Essential:_ Minutes/seconds arithmetic, hourly/minute duration diffs, dynamic field-based offsets.
- _Useful:_ Component extraction, period boundary normalization, timezone conversions.
- _Unnecessary:_ Complex calendar recurrence engines (which belong in dedicated rule triggers/processes).

C. **Is the current configuration model too small?**
Yes. The schema for `calculate` assumes `offset_value` is always a static integer and `base_type` is restricted to `"today"` vs `"doc_field"`.

D. **Is the current configuration model too large or redundant?**
No. The 3 existing operations are concise and non-overlapping.

E. **Is Date/Time correctly separated from other resolver families?**
Yes. It focuses on temporal math and formatting. Comparison operators (`<`, `>`, `between`) belong in the Condition Evaluator, where they are already handled properly.

F. **Is the current schema extensible?**
Yes. Because operations are keyed by `operation` (`"calculate"`, `"diff"`, `"format"`), new operations (e.g. `"extract"`, `"boundary"`, `"convert_tz"`) can be added cleanly without breaking existing configurations.

---

## 14. Improvement Opportunities

### Opportunity 1: Support Minutes & Seconds in Arithmetic and Time-Aware Base (`now`)

- **Current Behavior:** `offset_unit` in UI/backend only supports `days`, `weeks`, `months`, `years`, `hours`. `today` uses `nowdate()` (date only).
- **Problem:** SLA rules (e.g., "+30 minutes") cannot be configured.
- **Proposed Direction:** Add `minutes` and `seconds` to `offset_unit`. Support `base_type: "now"` using `frappe.utils.now_datetime()`.

### Opportunity 2: Enable Dynamic Offsets (Field / Variable as Offset)

- **Current Behavior:** `offset_value` is hardcoded as an integer.
- **Problem:** Cannot add $N$ days where $N$ comes from a document field (e.g., `doc.payment_terms_days`).
- **Proposed Direction:** Extend `calculate` config to accept `offset_type` (`"constant"` | `"field"`) and `offset_field`.

### Opportunity 3: Sub-Day Duration Differences in `diff`

- **Current Behavior:** `DateDiffResolver` only supports `days`, `months`, `years`.
- **Problem:** Cannot calculate time elapsed in hours or minutes.
- **Proposed Direction:** Add `hours`, `minutes`, and `seconds` to `diff_unit` using `frappe.utils.time_diff_in_hours` / `time_diff_in_seconds`.

### Opportunity 4: Component Extraction Operation (`extract`)

- **Proposed Direction:** Add operation `"extract"` with config `{ field, component }` where component is `year`, `month`, `day`, `weekday`, `hour`, `minute`.

### Opportunity 5: Period Boundary Operation (`boundary`)

- **Proposed Direction:** Add operation `"boundary"` with config `{ field, boundary_type }` where type is `start_of_day`, `end_of_day`, `start_of_month`, `end_of_month`, `start_of_year`, `end_of_year`.

---

## 15. Recommended Direction

Implement a **minimalist, non-breaking schema expansion** of the canonical `date_time` resolver family:

1. **Enhance `calculate` Operation:**
    - Add `"now"` to `base_type` options (`frappe.utils.now_datetime()`).
    - Add `"minutes"` and `"seconds"` to `offset_unit`.
    - Support `offset_type: "field"` with `offset_field` for dynamic offsets.

2. **Enhance `diff` Operation:**
    - Add `"hours"`, `"minutes"`, and `"seconds"` to `diff_unit`.

3. **Add `extract` Operation:**
    - Extract numeric components (`year`, `month`, `day`, `weekday`, `hour`, `minute`).

4. **Add `boundary` Operation:**
    - Period start/end boundaries using `frappe.utils.get_first_day` / `get_last_day`.

---

## 16. Backward Compatibility

- All existing configurations using `family: "date_time"` with operations `calculate`, `diff`, or `format` will remain 100% valid and unchanged.
- Backend defaults will fall back cleanly if new keys (`offset_type`, `boundary_type`) are omitted in older saved payloads.

---

## 17. Implementation Impact

- **Backend (`value_resolver.py`):** ~40-60 lines added to `DateFormulaResolver`, `DateDiffResolver`, and dispatch logic. Add `DateExtractResolver` and `DateBoundaryResolver`.
- **Frontend (`DateTimeResolver.vue` & sub-components):** Register 2 new operation components (`DateTimeExtractConfig.vue`, `DateTimeBoundaryConfig.vue`) and update options dropdowns.
- **Tests (`test_value_resolvers_complex.py`):** Add ~6 test cases covering new units, dynamic offsets, component extractions, and boundaries.

---

## 18. Open Questions

1. Should timezone conversion be a dedicated operation within `date_time` (e.g. `operation: "convert_tz"`), or should system/user timezone preferences be configured globally at the Rule level? _(Recommendation: Handle timezone conversion as an operation within `date_time` if explicit rule-level conversion is needed)._

---

## 19. Evidence / Source References

- `flexirule/ruleflow/core/value_resolver.py`: Lines 100-131 (`DateFormulaResolver`), Lines 179-204 (`DateDiffResolver`), Lines 825-845 (`compile_resolver_config` date_time dispatch).
- `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/DateTimeResolver.vue`: Lines 30-48 (`DATE_TIME_OPERATIONS` registry).
- `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/operations/DateTimeCalculateConfig.vue`: Lines 76-82 (`unitOptions`).
- `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/operations/DateTimeDiffConfig.vue`: Lines 75-79 (`diffUnitOptions`).
- `flexirule/ruleflow/tests/test_value_resolvers_complex.py`: Lines 41-160 (`test_date_time_family_resolver`, `test_date_formula_resolver`, `test_date_diff_resolver`).
- Frappe Framework Utility APIs: `frappe.utils.add_to_date`, `frappe.utils.time_diff_in_hours`, `frappe.utils.get_first_day`, `frappe.utils.get_last_day`.

---

## Final Decision & Conclusion

**Does the current Date/Time resolver provide the configuration necessary for the practical date/time requirements of FlexiRule?**

**No.** The current implementation provides a solid structural foundation, but its configuration model is too restrictive. It fails to support practical enterprise requirements such as minutes/seconds arithmetic, sub-day duration differences, dynamic field-based offsets, component extractions, and period boundary calculations.

A minimalist expansion of the existing `date_time` family (enhancing `calculate` and `diff`, while adding `extract` and `boundary` operations) will bring complete architectural parity with enterprise rule requirements while maintaining 100% backward compatibility.
