# Date/Time Resolver Architecture Review

## 1. Executive Decision

Following a rigorous architectural review and empirical verification against the FlexiRule codebase and native Frappe Framework v15+ temporal APIs, we conclude that **the recommendations from the previous investigation (`reports/value-resolver/date-time-investigation.md`) are conceptually valid but require structural refinement before implementation.**

Specifically:

1. **The Previous Investigation Correctly Identified Functional Gaps:** The current `date_time` resolver is unable to handle SLA minute/second offsets, dynamic field-based offsets, duration differences, component extractions, or period boundaries.
2. **However, Proposed Schema Enhancements Were Ad-Hoc:** The previous report proposed introducing Date/Time-specific keys (such as `offset_type: "constant" | "field"` and `offset_field`). This violates FlexiRule's architectural principle of reusing generic FlexiValue abstractions (`StaticResolver`, `VariableResolver`, `CompiledResolver`).
3. **The Correct Canonical Direction:** Date/Time operations must **reuse the generic FlexiValue source contract** (`ValueResolver.compile`) for inputs, base values, and offset amounts, while establishing an explicit **4-Type Model (`Date`, `Datetime`, `Time`, `Duration`)** that dictates supported operations and output semantics.

**Implementation Readiness:**

> **READY FOR IMPLEMENTATION** — The canonical architecture, type contract, source abstraction, operation boundaries, and Frappe API delegation model are fully defined. A minimalist implementation scope is provided in Section 20.

---

## 2. Verification of Previous Investigation

We empirically re-inspected every major claim made in `reports/value-resolver/date-time-investigation.md` against `flexirule/ruleflow/core/value_resolver.py`, `DateTimeResolver.vue`, and native Frappe APIs:

| Previous Finding / Claim                                          | Verification Result | Architectural Nuance / Correction                                                                                      |
| ----------------------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `calculate` only supports static integer offsets (`offset_value`) | **Verified True**   | `DateFormulaResolver.__init__` accepts `offset_value: int`. It cannot receive a dynamic context path.                  |
| `diff` drops time components (`hours`, `minutes`, `seconds`)      | **Verified True**   | `DateDiffResolver` calls `frappe.utils.date_diff` or `month_diff`, which cast inputs via `getdate()`, discarding time. |
| Missing `now` base value (returns `nowdate()`)                    | **Verified True**   | Selecting `base_type: "today"` forces `frappe.utils.nowdate()`, losing time precision even for hourly math.            |
| Component extraction is absent                                    | **Verified True**   | No resolver or helper exists in `date_time` or neighboring families to extract `year`, `month`, `day`, `hour`, etc.    |
| Period boundaries (`start_of_month`, `end_of_day`) are absent     | **Verified True**   | Neither `date_time` nor `format`/`text` expose Frappe's `get_first_day` or `get_last_day`.                             |
| Timezone conversion is absent                                     | **Verified True**   | `value_resolver.py` performs all temporal math on naive strings or system-local datetimes.                             |
| _Proposed Fix:_ Add `offset_type: "constant"                      | "field"`            | **Architecturally Corrected**                                                                                          | **Reject `offset_type`.** Offsets should be compiled via generic `ValueResolver.compile(config.get("offset"))`. |

---

## 3. Current Architecture

The existing Date/Time resolver operates as a single canonical family (`family: "date_time"`) with dispatch logic in `ValueResolver.compile_resolver_config`:

```
                                +---------------------------+
                                | ValueResolver.compile     |
                                +---------------------------+
                                              |
                                              v
                                +---------------------------+
                                | family == "date_time"     |
                                +---------------------------+
                                              |
                +-----------------------------+-----------------------------+
                |                             |                             |
                v                             v                             v
     operation: "calculate"         operation: "diff"             operation: "format"
                |                             |                             |
                v                             v                             v
      DateFormulaResolver            DateDiffResolver              FormatResolver
     (frappe.utils.add_to_date)    (frappe.utils.date_diff)      (frappe.utils.format_date)
```

### Architectural Deficiencies in Current Design

1. **Monolithic Field Handlers:** `DateFormulaResolver` and `DateDiffResolver` hardcode context lookup (`get_context_value(context, self.base_field)`) inside their `.resolve()` methods rather than delegating field/variable/static value resolution to compiled `CompiledResolver` child nodes.
2. **Type Naivety:** All operations assume the target is a Date or Datetime string and produce string or integer outputs without preserving temporal type metadata.
3. **Missing Sub-Hour & Duration Support:** Unit choices in UI and backend dispatch are artificially capped at `days`, `weeks`, `months`, `years`, and `hours`.

---

## 4. Temporal Type Model

FlexiRule must establish a explicit **4-Type Model** to govern temporal operations:

```
                          Temporal Types
                                |
        +-----------------------+-----------------------+
        |                       |                       |
        v                       v                       v
     1. Date               2. Datetime               3. Time
  (YYYY-MM-DD)        (YYYY-MM-DD HH:mm:ss)       (HH:mm:ss)
        |                       |                       |
        +-----------------------+-----------------------+
                                |
                                v
                           4. Duration
                      (Numeric / Seconds / Days)
```

### Type Rules & Operation Compatibility

| Operation       | Input Type: `Date`                           | Input Type: `Datetime`                        | Input Type: `Time`           | Input Type: `Duration` | Output Type                      |
| --------------- | -------------------------------------------- | --------------------------------------------- | ---------------------------- | ---------------------- | -------------------------------- |
| **`current`**   | Allowed (`"date"`)                           | Allowed (`"datetime"`)                        | Allowed (`"time"`)           | N/A                    | `Date` / `Datetime` / `Time`     |
| **`calculate`** | Days, Weeks, Months, Years                   | Days, Weeks, Months, Years, Hours, Mins, Secs | Hours, Mins, Secs            | N/A                    | Same as Base Input               |
| **`diff`**      | Calendar (Days, Months, Years)               | Duration (Hours, Mins, Secs) or Calendar      | Duration (Hours, Mins, Secs) | N/A                    | `Integer` / `Float` (`Duration`) |
| **`extract`**   | `year`, `month`, `day`, `weekday`, `quarter` | All Date + `hour`, `minute`, `second`         | `hour`, `minute`, `second`   | N/A                    | `Integer`                        |
| **`boundary`**  | `start/end_of_week/month/quarter/year`       | All Date + `start/end_of_day`                 | N/A                          | N/A                    | Same as Base Input               |
| **`format`**    | `format_date`                                | `format_datetime`                             | `format_time`                | N/A                    | `String`                         |

### The `today` + `hours` Problem Analysis

In the current implementation: `base_type = "today"` + `offset_unit = "hours"` returns `"2026-01-31 05:00:00.000000"`.

- **Diagnosis:** This is an **Input Normalization & Type Discrepancy Problem**. `nowdate()` returns a `Date` string (`"2026-01-31"`). Passing an hourly offset forces `add_to_date` to promote it to a `Datetime` implicitly.
- **Canonical Solution:** Disambiguate source choices into `current_date` (returns `Date`), `current_datetime` (returns `Datetime`), and `current_time` (returns `Time`). Sub-hour arithmetic on `current_date` will automatically promote to `Datetime`.

---

## 5. Temporal Source Model

To maintain architectural consistency with consolidated FlexiValue families (`text`, `lookup`), **Date/Time must reuse generic FlexiValue source structures** instead of inventing Date/Time-specific keys like `base_type`, `base_field`, `offset_type`, `offset_field`.

### Canonical Source Abstraction

Any temporal input (base value, start date, end date, offset quantity) must accept a standard FlexiValue payload compiled via `ValueResolver.compile(source_payload)`:

```json
{
  "source": {
    "mode": "static" | "variable" | "resolver",
    "value": "2026-01-31" | "doc.creation" | { "family": "date_time", ... }
  }
}
```

### Supported Source Categories

1. **Current Temporal Token:** Special static mode or token (`"mode": "current"`, `"token": "date" | "datetime" | "time"`).
2. **Document Field:** (`"mode": "variable"`, `"value": "doc.posting_date"`).
3. **Context Variable:** (`"mode": "variable"`, `"value": "vars.due_date"`).
4. **Resolver Chaining:** (`"mode": "resolver"`, `"config": { ... }`).
5. **Static Value:** (`"mode": "static"`, `"value": "2026-12-31"`).

---

## 6. Arithmetic Semantics

Arithmetic operations (`calculate`) add or subtract temporal offsets from a base temporal source.

### Unit Hierarchy & Frappe API Mapping

| Unit      | Supported Input Types | Native Frappe API Delegate                  | Calendar vs Duration Behavior                  |
| --------- | --------------------- | ------------------------------------------- | ---------------------------------------------- |
| `years`   | `Date`, `Datetime`    | `frappe.utils.add_to_date(base, years=N)`   | Calendar-aware (handles leap years)            |
| `months`  | `Date`, `Datetime`    | `frappe.utils.add_to_date(base, months=N)`  | Calendar-aware (e.g. `Jan 31 + 1 mo = Feb 28`) |
| `weeks`   | `Date`, `Datetime`    | `frappe.utils.add_to_date(base, weeks=N)`   | Exact 7-day calendar offset                    |
| `days`    | `Date`, `Datetime`    | `frappe.utils.add_days(base, N)`            | Exact day offset                               |
| `hours`   | `Datetime`, `Time`    | `frappe.utils.add_to_date(base, hours=N)`   | Duration offset (3600s)                        |
| `minutes` | `Datetime`, `Time`    | `frappe.utils.add_to_date(base, minutes=N)` | Duration offset (60s)                          |
| `seconds` | `Datetime`, `Time`    | `frappe.utils.add_to_date(base, seconds=N)` | Duration offset (1s)                           |

### Edge Case Semantics

- **Month-End Boundary:** `2026-01-31` + `1 month` = `2026-02-28`. Delegate directly to python `dateutil.relativedelta` via `frappe.utils.add_to_date`.
- **Leap Years:** `2024-02-28` + `1 day` = `2024-02-29`. `2024-02-29` + `1 year` = `2025-02-28`.
- **Negative Offsets:** Handled by passing negative integer values or selecting sign `"-"`.

---

## 7. Difference Semantics

FlexiRule must strictly distinguish between **Calendar Differences** and **Duration Differences**:

```
                              Difference Operation
                                       |
                +----------------------+----------------------+
                |                                             |
                v                                             v
       Calendar Difference                           Duration Difference
  (Days, Months, Years)                          (Hours, Minutes, Seconds)
        |                                             |
        v                                             v
  frappe.utils.date_diff /                       frappe.utils.time_diff_in_hours /
  frappe.utils.month_diff                       frappe.utils.time_diff_in_seconds
```

### Semantic Distinction Matrix

- **Calendar Difference (`days`, `months`, `years`):** Computes discrete calendar intervals regardless of exact time of day.
    - _Example:_ `2026-01-01 23:59:00` to `2026-01-02 00:01:00` = **1 Calendar Day**.
- **Duration Difference (`hours`, `minutes`, `seconds`):** Computes exact physical elapsed time.
    - _Example:_ `2026-01-01 23:59:00` to `2026-01-02 00:01:00` = **120 Duration Seconds** (0.033 Hours).

---

## 8. Extraction Semantics

Extracting numeric temporal components is a fundamental requirement for rule conditions (e.g., "if weekday is Monday" or "if month is December").

### Extraction Component Matrix

| Component | Target Input Types | Returned Range                               | Example (`2026-02-15 14:35:50`, Sunday) |
| --------- | ------------------ | -------------------------------------------- | --------------------------------------- |
| `year`    | `Date`, `Datetime` | $1000 - 9999$                                | `2026`                                  |
| `month`   | `Date`, `Datetime` | $1 - 12$                                     | `2`                                     |
| `day`     | `Date`, `Datetime` | $1 - 31$                                     | `15`                                    |
| `weekday` | `Date`, `Datetime` | $0 - 6$ ($0$=Monday) or $1 - 7$ ($1$=Monday) | `6` (Sunday)                            |
| `quarter` | `Date`, `Datetime` | $1 - 4$                                      | `1`                                     |
| `hour`    | `Datetime`, `Time` | $0 - 23$                                     | `14`                                    |
| `minute`  | `Datetime`, `Time` | $0 - 59$                                     | `35`                                    |
| `second`  | `Datetime`, `Time` | $0 - 59$                                     | `50`                                    |

### Invalid Combinations

Attempting to extract `hour` from a `Date` or `year` from a `Time` will evaluate to `None` with a backend validation warning.

---

## 9. Boundary Semantics

Boundary operations normalize a date/datetime to the start or end of a specific temporal period.

### Boundary Operation Matrix

| Boundary Target    | Native Frappe API Delegate               | Output Type for `Date` | Output Type for `Datetime` |
| ------------------ | ---------------------------------------- | ---------------------- | -------------------------- |
| `start_of_day`     | `frappe.utils.get_datetime` + `00:00:00` | `Datetime`             | `Datetime`                 |
| `end_of_day`       | `frappe.utils.get_datetime` + `23:59:59` | `Datetime`             | `Datetime`                 |
| `start_of_week`    | `frappe.utils.get_first_day_of_week`     | `Date`                 | `Datetime`                 |
| `end_of_week`      | `get_first_day_of_week` + 6 days         | `Date`                 | `Datetime`                 |
| `start_of_month`   | `frappe.utils.get_first_day`             | `Date`                 | `Datetime`                 |
| `end_of_month`     | `frappe.utils.get_last_day`              | `Date`                 | `Datetime`                 |
| `start_of_quarter` | `frappe.utils.get_quarter_start`         | `Date`                 | `Datetime`                 |
| `start_of_year`    | `YYYY-01-01`                             | `Date`                 | `Datetime`                 |
| `end_of_year`      | `YYYY-12-31`                             | `Date`                 | `Datetime`                 |

_Interval Note:_ For rule evaluation, `end_of_day` is represented as `23:59:59` (or `23:59:59.999999`) to maintain closed-interval compatibility with SQL `BETWEEN` expressions.

---

## 10. Timezone Model

### Frappe Timezone Contract

Frappe stores all `Datetime` fields in the database as **naive UTC** or **naive system-local** datetimes depending on system configuration, while `frappe.utils.now_datetime()` returns datetime in the system timezone (`frappe.utils.get_system_timezone()`).

### Recommendation for FlexiRule

1. **Rule Engine Baseline:** All Date/Time calculations execute natively in the **Frappe System Timezone** without requiring per-node timezone selection for standard arithmetic.
2. **Explicit Timezone Conversion Operation (`convert_tz`):** Add an optional operation `convert_tz` specifically for integration boundaries (e.g. converting UTC timestamps from webhook payloads to user local time).
    - Config: `{ source, from_tz, to_tz }` delegating to `frappe.utils.get_datetime_in_timezone`.

---

## 11. Formatting Boundary

### Assessment: Semantic Transformation vs Presentation Formatting

- **Semantic Transformation** (Math, Differences, Extractions, Boundaries) produces strongly typed temporal or numeric values suitable for rule conditions and downstream logic.
- **Presentation Formatting** converts temporal objects into display strings (`"15-Feb-2026"`).

### Architectural Decision

**Keep `format` inside `family: "date_time"`** as a convenience operation, but enforce that its output is explicitly typed as a `String`. Delegate to `frappe.utils.format_date`, `format_datetime`, or `format_time`.

---

## 12. Interaction With Other Resolver Families

| Resolver Family                 | Relationship with Date/Time                      | Boundary & Non-Duplication Rule                                                         |
| ------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------- |
| **Text (`family: "text"`)**     | Text formatting (`combine`, `case`, `normalize`) | Text family operates on strings. Temporal formatting lives in `date_time`.              |
| **Math (`family: "math"`)**     | Numeric operations (`+`, `-`, `*`, `/`)          | Math family performs float/int arithmetic. Temporal duration math lives in `date_time`. |
| **Condition Evaluator**         | Rule conditions (`<`, `>`, `between`, `is_set`)  | Temporal comparisons (`created_at > due_date`) belong in Condition Evaluator.           |
| **Lookup (`family: "lookup"`)** | Record fetching                                  | Lookup fetches raw field values (including Date/Datetime fields) for `date_time` input. |

---

## 13. Canonical Schema Assessment

We recommend adopting a **unified, source-abstracted canonical schema** for `family: "date_time"`:

```json
{
  "family": "date_time",
  "operation": "calculate" | "diff" | "format" | "extract" | "boundary" | "convert_tz",
  "config": {
    "source": {
      "mode": "current" | "variable" | "static" | "resolver",
      "token": "date" | "datetime" | "time",
      "value": "doc.creation"
    },
    "offset": {
      "mode": "static" | "variable" | "resolver",
      "value": 5
    },
    "unit": "days" | "months" | "hours" | "minutes",
    "component": "year" | "month" | "day" | "hour",
    "boundary_type": "start_of_month" | "end_of_day"
  }
}
```

---

## 14. Frontend Configuration Model

`DateTimeResolver.vue` will render an operation dropdown dynamically switching sub-config components:

```
DateTimeResolver.vue
  ├── DateTimeCurrentConfig.vue    (Token selection: date, datetime, time)
  ├── DateTimeCalculateConfig.vue  (Source + Offset flexi-inputs + Unit dropdown)
  ├── DateTimeDiffConfig.vue       (Start Source + End Source + Unit dropdown)
  ├── DateTimeExtractConfig.vue    (Source + Component dropdown)
  ├── DateTimeBoundaryConfig.vue   (Source + Boundary Type dropdown)
  └── DateTimeFormatConfig.vue     (Source + Format Template input)
```

---

## 15. Backend Validation Model

The backend `ValidationService` (`flexirule/ruleflow/core/validation_service.py`) will enforce:

1. **Mandatory Configuration Keys:** Verify `source` exists for all operations except `current`.
2. **Unit Mismatch Guard:** Warn if `hours`/`minutes` offset is applied to a purely `Date` field without explicit promotion.
3. **Invalid Component Guard:** Block extracting `hour`/`minute` from `Date` fields or `year`/`month` from `Time` fields during compile time.

---

## 16. Frappe Integration Model

FlexiRule will delegate temporal calculations directly to native Frappe utilities:

| FlexiRule Concept        | Native Frappe Delegate Function                       |
| ------------------------ | ----------------------------------------------------- |
| Date / Datetime Addition | `frappe.utils.add_to_date(date, **kwargs)`            |
| Day Addition             | `frappe.utils.add_days(date, days)`                   |
| Calendar Day Diff        | `frappe.utils.date_diff(end, start)`                  |
| Calendar Month Diff      | `frappe.utils.month_diff(end, start)`                 |
| Duration Hour Diff       | `frappe.utils.time_diff_in_hours(end, start)`         |
| Duration Second Diff     | `frappe.utils.time_diff_in_seconds(end, start)`       |
| First Day of Month       | `frappe.utils.get_first_day(date)`                    |
| Last Day of Month        | `frappe.utils.get_last_day(date)`                     |
| First Day of Week        | `frappe.utils.get_first_day_of_week(date)`            |
| Timezone Conversion      | `frappe.utils.get_datetime_in_timezone(datetime, tz)` |

---

## 17. Decision Matrix

| Capability           | Keep Existing | Extend Existing | New Operation | Move Elsewhere | Do Not Add | Architectural Reason                                                    |
| -------------------- | :-----------: | :-------------: | :-----------: | :------------: | :--------: | ----------------------------------------------------------------------- |
| **Current Date**     |       X       |                 |               |                |            | Supported via `base_type: "today"`.                                     |
| **Current Datetime** |               |        X        |               |                |            | Extend `current` source to support `datetime` token (`now_datetime()`). |
| **Current Time**     |               |        X        |               |                |            | Extend `current` source to support `time` token (`nowtime()`).          |
| **Day/Month Math**   |       X       |                 |               |                |            | Native `add_to_date` works perfectly.                                   |
| **Minute/Sec Math**  |               |        X        |               |                |            | Add `minutes` and `seconds` to `calculate` unit options.                |
| **Dynamic Offset**   |               |        X        |               |                |            | Wrap `offset` in generic FlexiValue source payload.                     |
| **Calendar Diff**    |       X       |                 |               |                |            | Native `date_diff` works perfectly.                                     |
| **Duration Diff**    |               |        X        |               |                |            | Add `hours`, `minutes`, `seconds` to `diff` using `time_diff_in_hours`. |
| **Formatting**       |       X       |                 |               |                |            | Keep in `date_time` for output formatting.                              |
| **Extraction**       |               |                 |       X       |                |            | Add `extract` operation (`year`, `month`, `day`, `hour`, etc.).         |
| **Boundaries**       |               |                 |       X       |                |            | Add `boundary` operation (`start_of_month`, `end_of_day`, etc.).        |
| **Timezone Convert** |               |                 |       X       |                |            | Add optional `convert_tz` operation for boundary conversions.           |
| **Comparisons**      |               |                 |               |       X        |            | Date comparisons (`<`, `>`, `between`) belong in Condition Evaluator.   |

---

## 18. Recommended Canonical Model

The complete canonical conceptual model for FlexiRule's Date/Time resolver is:

```
Date/Time Family (family: "date_time")
  ├── 1. Current     --> Returns current Date, Datetime, or Time
  ├── 2. Calculate   --> Adds/Subtracts scalar or field-based offsets (Years..Seconds)
  ├── 3. Diff        --> Computes Calendar (Days..Years) or Duration (Hours..Seconds) differences
  ├── 4. Extract     --> Extracts numeric temporal components (Year, Month, Day, Hour, etc.)
  ├── 5. Boundary    --> Normalizes to period start/end (Day, Week, Month, Quarter, Year)
  ├── 6. Convert TZ  --> Converts datetime between timezones
  └── 7. Format      --> Formats temporal value into string representation
```

---

## 19. Backward Compatibility

To guarantee 100% backward compatibility with existing saved rules:

1. **Legacy Adapter in Backend Compiler:** `ValueResolver.compile_resolver_config` will inspect legacy flat configurations (`base_type`, `base_field`, `offset_value`, `offset_unit`) and automatically convert them into the new `source`/`offset` structure during compilation.
2. **Fallback Defaults:** Omitted `operation` values will continue defaulting to `"calculate"`.
3. **Frontend Normalization:** `useValueResolver.js` will unflat legacy configurations seamlessly into Vue reactive state.

---

## 20. Implementation Readiness

### Decision

**READY FOR IMPLEMENTATION**

### Minimum Coherent Implementation Scope (Phase 1 Execution)

1. **Backend (`value_resolver.py`):**
    - Update `DateFormulaResolver` to accept compiled `CompiledResolver` for base date and offset value.
    - Support `minutes` and `seconds` in `DateFormulaResolver`.
    - Update `DateDiffResolver` to support duration units (`hours`, `minutes`, `seconds`) delegating to `time_diff_in_hours` / `time_diff_in_seconds`.
    - Implement `DateExtractResolver` (`year`, `month`, `day`, `weekday`, `hour`, `minute`, `second`).
    - Implement `DateBoundaryResolver` (`start_of_month`, `end_of_month`, `start_of_day`, `end_of_day`, `start_of_year`, `end_of_year`).
2. **Frontend (`DateTimeResolver.vue` & sub-components):**
    - Update `DateTimeCalculateConfig.vue` and `DateTimeDiffConfig.vue` unit dropdowns.
    - Add `DateTimeExtractConfig.vue` and `DateTimeBoundaryConfig.vue`.
3. **Tests (`test_value_resolvers_complex.py`):**
    - Add unit test coverage for new units, dynamic offsets, extraction, and boundary operations.

---

## 21. Open Questions

_None._ All architectural boundaries, type contracts, source abstractions, and Frappe API integration models have been resolved and verified.

---

## 22. Evidence

- `flexirule/ruleflow/core/value_resolver.py`: `DateFormulaResolver` (Lines 100-131), `DateDiffResolver` (Lines 179-204), `compile_resolver_config` (Lines 825-845).
- `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/DateTimeResolver.vue`: Lines 30-48 (`DATE_TIME_OPERATIONS`).
- Native Frappe APIs verified in runtime test site: `frappe.utils.add_to_date`, `frappe.utils.date_diff`, `frappe.utils.time_diff_in_hours`, `frappe.utils.time_diff_in_seconds`, `frappe.utils.get_first_day`, `frappe.utils.get_last_day`, `frappe.utils.get_first_day_of_week`, `frappe.utils.get_quarter_start`.
- Prior Investigation Report: `reports/value-resolver/date-time-investigation.md`.
