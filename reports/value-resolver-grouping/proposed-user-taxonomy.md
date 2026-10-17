# Proposed User Taxonomy & Mental Model Architecture

## 1. Core Principle: Domain First, Operation Second

The primary UX principle of FlexiRule's first public release is:

> **"Reduce the number of concepts visible to the user at the first level, while making each user-facing Component responsible for a cohesive group of related operations."**

Instead of forcing a non-technical Rule Designer or Business Analyst to choose an implementation strategy (`date_formula` vs `date_diff`, or `string_formula` vs `normalization`), the user makes two natural choices:

```
Step 1: What kind of value or data am I working with?  (Family Choice)
       ↓
Step 2: What operation do I want to perform?           (Operation Choice)
```

---

## 2. The 8 First-Release Value Families

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               FlexiRule Value Families                                  │
├─────────────────┬─────────────────┬─────────────────┬───────────────────────────────────┤
│ 1. Date & Time  │ 2. Text         │ 3. Number       │ 4. Collections & Tables           │
├─────────────────┼─────────────────┼─────────────────┼───────────────────────────────────┤
│ 5. Lookup       │ 6. System       │ 7. Conversion   │ 8. Conditional                    │
└─────────────────┴─────────────────┴─────────────────┴───────────────────────────────────┘
```

### Family 1: Date & Time (`date`)
- **Internal Family Name**: `date`
- **User-Facing Label**: Date & Time
- **Description**: Operations for calculating, comparing, and formatting dates and times.
- **Icon**: `lucide-calendar` or `fa fa-calendar`
- **Mental Model**: "I want to work with a date or timestamp."

### Family 2: Text (`text`)
- **Internal Family Name**: `text`
- **User-Facing Label**: Text
- **Description**: Operations for combining, cleaning, transforming, and formatting text.
- **Icon**: `lucide-type` or `fa fa-font`
- **Mental Model**: "I want to manipulate string values."

### Family 3: Number (`number`)
- **Internal Family Name**: `number`
- **User-Facing Label**: Number
- **Description**: Mathematical calculations, rounding, percentages, and currency formatting.
- **Icon**: `lucide-hash` or `fa fa-calculator`
- **Mental Model**: "I want to calculate or format a numeric or currency value."

### Family 4: Collections & Tables (`collection`)
- **Internal Family Name**: `collection`
- **User-Facing Label**: Collections & Tables
- **Description**: Querying, filtering, checking, extracting, and aggregating table rows and list variables.
- **Icon**: `lucide-table` or `fa fa-table`
- **Mental Model**: "I want to count, filter, or aggregate rows in a child table or list."

### Family 5: Lookup (`lookup`)
- **Internal Family Name**: `lookup`
- **User-Facing Label**: Lookup
- **Description**: Retrieving field values from linked documents or searching related records.
- **Icon**: `lucide-search` or `fa fa-search`
- **Mental Model**: "I want to fetch a value from a linked document or master record."

### Family 6: System & Context (`system`)
- **Internal Family Name**: `system`
- **User-Facing Label**: System & Context
- **Description**: Accessing runtime environment information such as current user, roles, and system dates.
- **Icon**: `lucide-cpu` or `fa fa-cog`
- **Mental Model**: "I want to know who is running this rule or what the current system date is."

### Family 7: Conversion (`conversion`)
- **Internal Family Name**: `conversion`
- **User-Facing Label**: Conversion
- **Description**: Explicitly converting values between data types (Text, Number, Date, Boolean).
- **Icon**: `lucide-arrow-right-left` or `fa fa-exchange`
- **Mental Model**: "I want to change the type of a value (e.g. string to number)."

### Family 8: Conditional (`conditional`)
- **Internal Family Name**: `conditional`
- **User-Facing Label**: Conditional
- **Description**: Inline logic for returning values based on conditions (If/Else, Coalesce).
- **Icon**: `lucide-git-branch` or `fa fa-code-fork`
- **Mental Model**: "I want to choose between two values based on a condition."

---

## 3. Detailed Operation Breakdown by Family

```
Date & Time
  ├── Calculate Date          (Offset date by days/weeks/months/years)
  ├── Difference Between      (Calculate days or hours between two dates)
  └── Format Date             (Format date to specific string representation)

Text
  ├── Combine Text            (Concatenate multiple text fields/strings)
  ├── Change Case             (Upper, lower, title case)
  ├── Clean & Normalize       (Trim whitespace, slugify, remove accents)
  └── Format Text             (Template string formatting)

Number
  ├── Calculate               (Addition, subtraction, multiplication, division)
  ├── Round                   (Round to N decimal places)
  ├── Format Money            (Format as currency with symbol and precision)
  └── Percentage              (Calculate percentage of a base amount)

Collections & Tables
  ├── Count                   (Count total or matching rows)
  ├── Any / All               (Check if any or all rows match condition)
  ├── First / Find            (Retrieve first row matching condition)
  ├── Filter                  (Extract sub-collection of matching rows)
  ├── Pluck                   (Extract array of specific column values)
  ├── Unique                  (Extract distinct column values)
  └── Aggregate (Sum/Avg)     (Calculate sum or average of numeric column)

Lookup
  ├── Get Linked Field        (Fetch single field value from linked document)
  └── Lookup Record           (Query record by key/value pair)

System & Context
  ├── Current User            (Email or ID of session user)
  ├── Role Check              (Boolean check if user has role)
  ├── Current Date / Time     (System today or now)
  └── Current Company         (Default session company)

Conversion
  ├── To Text                 (Cast value to String)
  ├── To Number               (Cast value to Float/Int)
  ├── To Date                 (Parse string to Date)
  └── To Boolean              (Cast value to True/False)

Conditional
  ├── If / Else               (Return Value A if true, else Value B)
  └── Coalesce                (Return first non-null value from list)
```

---

## 4. Rationale for Taxonomy Design

1. **Elimination of `fmt_money` Duplication**:
   By placing `format_money` exclusively inside **Number**, we eliminate the confusing presence of currency formatting in `string_formula`, `format`, and backend handlers. Currency is fundamentally a numeric presentation concept.

2. **Unification of Text Operations**:
   Concatenation, casing, normalization pipelines, and string formatting belong under **Text** (`TextResolver.vue`), ending the artificial separation between `StringFormulaResolver.vue` and `NormalizationResolver.vue`.

3. **Unified Table & Collection Experience**:
   Users working with child tables select **Collections & Tables**. Whether the backend executes a lightweight Python iteration or a direct child table SQL query is an internal implementation detail handled by the compiler dispatch layer.
