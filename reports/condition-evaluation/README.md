# Shared Specification — Canonical Condition v1 and FlexValue Wire Contract

**Target branch:** `plan/canonical-condition-evaluation-tasks-20261026` (PR #460)
**Primary specification:** PR #460
**Source review:** Current develop source fetched on 2026-10-26.  
**Task plans:** [Backend implementation plan](backend-implementation-plan.md) · [Frontend implementation plan](frontend-implementation-plan.md)

---

## 1. Objective and Scope Boundaries

This document freezes the canonical condition and FlexValue wire contract for FlexiRule.

### Scope Boundaries
- **Specification & Fixtures Only:** This task (Task 0) produces frozen documentation specifications and machine-readable contract fixtures in `flexirule/ruleflow/fixtures/condition_contract_fixtures.json`.
- **Zero Application Code Changes:** No runtime application code (`flexirule/ruleflow/core/*.py`), frontend Vue/JS components (`public/js/`), DocTypes, database schemas, migrations, or workflows are modified in Task 0.
- **Single Source of Truth:** PR #460 and `reports/condition-evaluation/README.md` serve as the single primary specification for all subsequent backend and frontend implementation tasks.

---

## 2. Frozen Public Wire Contract

### 2.1 Condition Envelope

A complete canonical condition payload is JSON-serializable and MUST use this envelope:

```json
{
  "schema": "flexirule.condition",
  "version": 1,
  "root": {
    "type": "group",
    "operator": "and",
    "children": [
      {
        "type": "comparison",
        "operator": "equals",
        "left": {
          "mode": "variable",
          "path": { "scope": "doc", "segments": ["status"] }
        },
        "right": {
          "mode": "static",
          "value_type": "string",
          "value": "Submitted"
        }
      }
    ]
  }
}
```

#### Envelope Rules
1. **Top-Level Only:** The `schema` and `version` fields appear exactly once at the top level of a complete condition. They MUST NOT be repeated on nested nodes.
2. **JSON AST Source of Truth:** The saved JSON AST is the sole authoritative source of truth. Generated Python code strings and persisted execution plans are NOT part of the contract and MUST NOT be saved.
3. **No Unneeded Version Bumps:** Implementation-level optimizations do not require schema version changes.
4. **Explicit Migration for Format Changes:** Any incompatible persisted format or semantic change requires an explicit versioning and migration RFC.
5. **Fail-Closed Verification:** Unknown schema identifiers (anything other than `"flexirule.condition"`) and unsupported versions (anything other than `1`) are rejected with actionable diagnostics. Implementation code MUST NEVER guess a format or silently reset a condition to an empty state.

---

### 2.2 Business-Oriented Operator Registry Contract

The canonical operator contract describes business comparison semantics rather than Python syntax or UI symbols. The backend owns the single authoritative operator registry.

#### Operator Table

| Canonical ID | Translatable Label | Arity | Supported Operand Value Types | Applicable Field Types | Missing / Null Semantics | Legacy Tokens / Mappings |
|---|---|---|---|---|---|---|
| `equals` | Equals | 2 | String, Integer, Decimal, Boolean, Null, Date, Datetime, Document Reference | All | Null == Null is True; missing path raises error | `==`, `=` (Deterministic) |
| `not_equals` | Does Not Equal | 2 | String, Integer, Decimal, Boolean, Null, Date, Datetime, Document Reference | All | Inverse of equals | `!=`, `<>` (Deterministic) |
| `greater_than` | Greater Than | 2 | Integer, Decimal, Date, Datetime, Time | Numeric, Date, Datetime, Time | Strict type match required; missing path raises error | `>` (Deterministic) |
| `less_than` | Less Than | 2 | Integer, Decimal, Date, Datetime, Time | Numeric, Date, Datetime, Time | Strict type match required; missing path raises error | `<` (Deterministic) |
| `greater_than_or_equals` | Greater Than or Equal | 2 | Integer, Decimal, Date, Datetime, Time | Numeric, Date, Datetime, Time | Strict type match required; missing path raises error | `>=` (Deterministic) |
| `less_than_or_equals` | Less Than or Equal | 2 | Integer, Decimal, Date, Datetime, Time | Numeric, Date, Datetime, Time | Strict type match required; missing path raises error | `<=` (Deterministic) |
| `is_one_of` | Is One Of | 2 | List (Right operand) | Select, Link, Data, Integer | Right operand must be a List; item type matching applied | `in` (Deterministic) |
| `is_not_one_of` | Is Not One Of | 2 | List (Right operand) | Select, Link, Data, Integer | Inverse of `is_one_of` | `not in`, `not_in` (Deterministic) |
| `contains_text` | Contains Text | 2 | String | Text, Data, Small Text, Code, JSON | Case-insensitive substring match; non-string raises error | N/A |
| `is_set` | Is Set | 1 | Any | All | Returns True if value is present, non-null, and non-empty string. Whitespace is considered set. Missing path returns False without error. | N/A |
| `is_not_set` | Is Not Set | 1 | Any | All | Inverse of `is_set`. Returns True for missing paths or nulls without error. | N/A |
| `is_empty` | Is Empty | 1 | String, List, Object | Text, Data, Table, JSON | Returns True if length is 0 or value is null/missing | N/A |
| `is_not_empty` | Is Not Empty | 1 | String, List, Object | Text, Data, Table, JSON | Inverse of `is_empty` | N/A |
| `is_submittable` | Is Submittable | 1 | Document Reference / DocType String | Link, Dynamic Link | Returns True if target DocType has `is_submittable = 1` | N/A |
| `has_field` | Has Field | 2 | String (Fieldname) | All DocTypes | Checks if target document/DocType contains specified field | N/A |

#### Legacy Token & Non-Canonical Token Decisions
1. **Deterministic Legacy Mappings:** `==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`, and `not_in` map deterministically to `equals`, `not_equals`, `greater_than`, `less_than`, `greater_than_or_equals`, `less_than_or_equals`, `is_one_of`, and `is_not_one_of` once legacy payload context is verified.
2. **Ambiguous Tokens Require Migration Diagnostics:** Tokens with ambiguous historical semantics (`like`, `not like`, `regex`, `has_changed`, `is`, `is not`) MUST NOT be auto-mapped. They produce an explicit migration diagnostic (`MIGRATE_NON_CANONICAL_OPERATOR_*`) requiring manual migration review.

---

### 2.3 FlexValue Union & Document Reference Semantics

Both left and right comparison operands use the identical FlexValue union.

#### FlexValue Union Variants
1. **Static (`mode: "static"`):** Carries explicit `value_type` and `value`. Supported scalar and structured value types:
   - `string`, `integer`, `decimal` (serialized as string to avoid FP loss), `boolean`, `null`, `date`, `datetime`, `time`, `list`, `object`.
   - `document_reference`: Explicitly typed document reference carrying `{ "doctype": "Customer", "name": "CUST-0001" }`.
2. **Variable (`mode: "variable"`):** Explicit path segment resolution with scope.
   - Canonical scopes: `doc`, `old_doc`, `vars`, `item`, `loop`, `row`, `caller`, `rule`, `doctype`, and locally declared collection aliases.
   - No implicit fallback searches across scopes in canonical mode.
3. **Resolver (`mode: "resolver"`):** Explicit resolver invocation.
   - Carries `family`, `operation`, and backend-validated `config`.
   - Resolvers default to `condition_operand_allowed = false` unless explicitly audited and permitted by backend capability policy.
   - Database lookup resolvers MUST NOT be enabled as condition operands without explicit permission and query-limit policies.
4. **Template (`mode: "template"`):** Structured text/value segments where value segments recursively contain valid FlexValue nodes.
   - Raw Jinja or Python expression strings are strictly forbidden.

#### Link & Document Reference Resolution
1. **Scalar Link Values:** Ordinary Link comparisons use scalar strings (`value_type: "string"`, e.g. `"CUST-0001"`). Target DocType constraints are verified against Frappe field metadata of the left operand.
2. **Explicitly Typed Document Reference:**
   ```json
   {
     "mode": "static",
     "value_type": "document_reference",
     "value": {
       "doctype": "Customer",
       "name": "CUST-0001"
     }
   }
   ```
   Both `doctype` and `name` are validated at runtime and during metadata checks.
3. **Two-Item Lists Are Strictly Lists:** A two-item list (e.g., `["Customer", "CUST-0001"]`) is NEVER interpreted as a Link tuple based on shape alone. It is evaluated strictly as a `list` unless a separate legacy migration adapter proves its legacy meaning using verified left-operand Link metadata.
4. **Resolver Output Contracts:** Resolvers returning document references MUST declare `value_type: "document_reference"` in their output contract.

---

### 2.4 Logical and Value Semantics

1. **Short-Circuit Logical Groups:**
   - Group nodes (`type: "group"`) evaluate children left-to-right with strict short-circuiting (`and` stops on first `false`/error; `or` stops on first `true`).
   - All child siblings in a group share the group's `operator`. Mixed logic MUST be represented via nested groups.
2. **Absent vs Empty/Malformed Condition Boundary:**

| Consumer Field State | Semantic Meaning | Evaluation Behavior |
|---|---|---|
| Field omitted / missing | Optional guard/filter absent | Unconditional execution (Pass / True) |
| Field explicitly `null` | Optional guard/filter absent | Unconditional execution (Pass / True) |
| Valid canonical condition payload | Active condition configured | Evaluated via canonical evaluator |
| Present condition with `children: []` | Invalid condition | Fails validation / Fails Closed (Error) |
| Blank or malformed payload string | Invalid condition | Fails validation / Fails Closed (Error) |
| Unknown schema or version | Invalid condition | Fails validation / Fails Closed (Error) |
| Malformed node or operator config | Invalid condition | Fails validation / Fails Closed (Error) |

3. **Value & Type Semantics:**
   - **Missing Path vs Null Value:** Unary `is_set` and `is_not_set` handle missing paths safely. All binary operators encountering a missing variable path raise a typed evaluation error (`ERR_MISSING_VARIABLE_PATH`).
   - **Empty String vs Whitespace:** Empty string (`""`) is considered unset (`is_set` -> False). Whitespace strings (e.g. `" "`) are considered set (`is_set` -> True).
   - **False vs Zero:** Boolean `false` and integer/decimal `0` are distinct types. Boolean `false` is NEVER coerced to numeric `0`.
   - **Fail-Closed Error Policy:** Evaluation errors (missing paths in binary comparisons, type mismatches, resolver execution errors) fail closed. An evaluation error is NEVER converted to an ordinary `false` or `true` result; it triggers lifecycle error handling while preserving distinct diagnostic codes.

---

## 3. Shared Static Contract Fixtures

Contract fixtures are stored in a single, machine-readable JSON file:
`flexirule/ruleflow/fixtures/condition_contract_fixtures.json`

### Fixture Schema Overview
Each fixture entry includes:
- `id`: Unique identifier
- `description`: Explanatory title
- `payload`: Condition or legacy payload
- `expected_status`: `"accept"`, `"reject"`, or `"migrate"`
- `expected_diagnostic_code`: Diagnostic string or `null` for clean accepted payloads
- `evaluation`: (Optional for accepted payloads) Context dictionary, expected outcome (`true`, `false`, or `"error"`), and expected diagnostic code on error.

Both Python backend unit tests and JavaScript frontend unit tests MUST consume this identical fixture file.

---

## 4. Reconciled Task Plans

- [Backend Implementation Plan](backend-implementation-plan.md)
- [Frontend Implementation Plan](frontend-implementation-plan.md)
