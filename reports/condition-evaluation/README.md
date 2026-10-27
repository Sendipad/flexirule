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
1. **Top-Level Only:** The `schema` and `version` fields appear exactly once at the top level of a complete condition payload. They MUST NOT be repeated on nested nodes.
2. **JSON AST Source of Truth:** The saved JSON AST is the sole authoritative source of truth. Generated Python code strings and persisted execution plans are NOT part of the contract and MUST NOT be saved.
3. **No Unneeded Version Bumps:** Implementation-level optimizations do not require schema version changes.
4. **Explicit Migration for Format Changes:** Any incompatible persisted format or semantic change requires an explicit versioning and migration decision.
5. **Fail-Closed Verification:** Unknown schema identifiers (anything other than `"flexirule.condition"`) and unsupported versions (anything other than `1`) are rejected with actionable diagnostics. Implementation code MUST NEVER guess a format or silently reset a condition to an empty state.

---

### 2.2 Canonical AST Node Types

The canonical AST contains exactly three node types under `root` or within nested child structures:

#### 1. Group Node (`type: "group"`)
- `type`: `"group"`
- `operator`: `"and"` | `"or"`
- `children`: Array of non-empty child nodes (`comparison`, `group`, or `collection_predicate`).
- **Rules:** Siblings within a group share the same logical `operator`. Mixed logic MUST be represented using explicitly nested groups. Children array MUST NOT be empty in saved canonical JSON. Child evaluation order is preserved left-to-right.

#### 2. Comparison Node (`type: "comparison"`)
- `type`: `"comparison"`
- `operator`: Stable canonical operator ID from the registry (e.g., `"equals"`, `"greater_than"`, `"is_set"`).
- `left`: Valid FlexValue object.
- `right`: Valid FlexValue object (omitted ONLY when operator arity is 1, e.g., `"is_set"`, `"is_empty"`).

#### 3. Collection Predicate Node (`type: "collection_predicate"`)
- `type`: `"collection_predicate"`
- `quantifier`: `"any"` | `"all"` | `"none"`
- `source`: FlexValue variable reference pointing to a list/child-table (e.g., `{ "mode": "variable", "path": { "scope": "doc", "segments": ["items"] } }`).
- `as`: Valid string row alias scoped strictly to this predicate and its nested descendants (e.g., `"item_row"`).
- `where`: Valid nested condition node (`comparison` or `group`) evaluated against each row.
- **Safety Limit:** Collection iteration reuses the shared constant limit of 10,000 rows. Reaching or exceeding 10,000 rows without finding a terminal result halts evaluation with a typed resource limit error (`ERR_COLLECTION_ROW_GUARD_EXCEEDED`). Collections MUST NEVER be silently truncated.

---

### 2.3 Business-Oriented Operator Registry Contract

The canonical operator contract describes business comparison semantics rather than Python syntax or UI symbols. The backend owns the single authoritative operator registry.

#### Authoritative Operator Table

| Canonical ID | Translatable Label | Arity | Supported Operand Value Types | Applicable Field Types | Missing / Null Semantics |
|---|---|---|---|---|---|
| `equals` | Equals | 2 | String, Integer, Decimal, Boolean, Null, Date, Datetime, Document Reference | All | Null == Null is True; missing path in binary op raises `ERR_MISSING_VARIABLE_PATH` |
| `not_equals` | Does Not Equal | 2 | String, Integer, Decimal, Boolean, Null, Date, Datetime, Document Reference | All | Inverse of `equals` |
| `greater_than` | Greater Than | 2 | Integer, Decimal, Date, Datetime, Time | Numeric, Date, Datetime, Time | Strict type match required; missing path raises `ERR_MISSING_VARIABLE_PATH` |
| `less_than` | Less Than | 2 | Integer, Decimal, Date, Datetime, Time | Numeric, Date, Datetime, Time | Strict type match required; missing path raises `ERR_MISSING_VARIABLE_PATH` |
| `greater_than_or_equals` | Greater Than or Equal | 2 | Integer, Decimal, Date, Datetime, Time | Numeric, Date, Datetime, Time | Strict type match required; missing path raises `ERR_MISSING_VARIABLE_PATH` |
| `less_than_or_equals` | Less Than or Equal | 2 | Integer, Decimal, Date, Datetime, Time | Numeric, Date, Datetime, Time | Strict type match required; missing path raises `ERR_MISSING_VARIABLE_PATH` |
| `is_one_of` | Is One Of | 2 | List (Right operand) | Select, Link, Data, Integer | Right operand must be a List; item type matching applied |
| `is_not_one_of` | Is Not One Of | 2 | List (Right operand) | Select, Link, Data, Integer | Inverse of `is_one_of` |
| `contains_text` | Contains Text | 2 | String | Text, Data, Small Text, Code, JSON | Case-insensitive literal substring match; non-string raises type error |
| `is_set` | Is Set | 1 | Any | All | Returns True if value is present, non-null, and non-empty string. Whitespace strings are considered set. Missing path returns False without error. |
| `is_not_set` | Is Not Set | 1 | Any | All | Inverse of `is_set`. Returns True for missing paths or nulls without error. |
| `is_empty` | Is Empty | 1 | String, List, Object | Text, Data, Table, JSON | Returns True if length/count is 0 or value is null/missing |
| `is_not_empty` | Is Not Empty | 1 | String, List, Object | Text, Data, Table, JSON | Inverse of `is_empty` |
| `is_submittable` | Is Submittable | 1 | Document Reference / DocType String | Link, Dynamic Link | Returns True if target DocType has `is_submittable = 1` |
| `has_field` | Has Field | 2 | String (Fieldname) | All DocTypes | Checks if target document/DocType contains specified field |

#### Exhaustive Legacy Operator Classification Matrix

| Legacy Token | Classification | Canonical Target / Action | Diagnostic Code |
|---|---|---|---|
| `==` | Deterministic Mapping | `equals` | `MIGRATE_LEGACY_TOKEN` |
| `!=` | Deterministic Mapping | `not_equals` | `MIGRATE_LEGACY_TOKEN` |
| `>` | Deterministic Mapping | `greater_than` | `MIGRATE_LEGACY_TOKEN` |
| `<` | Deterministic Mapping | `less_than` | `MIGRATE_LEGACY_TOKEN` |
| `>=` | Deterministic Mapping | `greater_than_or_equals` | `MIGRATE_LEGACY_TOKEN` |
| `<=` | Deterministic Mapping | `less_than_or_equals` | `MIGRATE_LEGACY_TOKEN` |
| `in` | Deterministic Mapping | `is_one_of` | `MIGRATE_LEGACY_TOKEN` |
| `not in`, `not_in` | Deterministic Mapping | `is_not_one_of` | `MIGRATE_LEGACY_TOKEN` |
| `=` | Unverified Alias (Manual Review) | Requires context verification | `MIGRATE_NON_CANONICAL_OPERATOR_ASSIGNMENT_EQUAL` |
| `<>` | Unverified Alias (Manual Review) | Requires context verification | `MIGRATE_NON_CANONICAL_OPERATOR_ANGLE_BRACKETS` |
| `like`, `not like` | Ambiguous / Manual Review | SQL wildcard semantics differ from canonical literal text | `MIGRATE_NON_CANONICAL_OPERATOR_LIKE` |
| `regex` | Prohibited in v1 | Regex patterns not supported in v1 canonical AST | `MIGRATE_NON_CANONICAL_OPERATOR_REGEX` |
| `contains` | Context Conversion | Historical compiler `contains` is case-sensitive Python `in`. Convert to `contains_text` only if case-insensitivity is accepted or flagged for review. | `MIGRATE_LEGACY_CONTAINS` |
| `not_contains` | Context Conversion | Inverse of legacy `contains` | `MIGRATE_LEGACY_NOT_CONTAINS` |
| `length_eq`, `length_gt`, `length_gte`, `length_lt`, `length_lte` | Unclassified Legacy | Length comparisons require string/collection length resolver or manual migration review | `MIGRATE_LEGACY_LENGTH_OPERATOR` |
| `has_changed` | Prohibited in v1 | Historical benchmark disparity; requires explicit state tracking resolver in v2 | `MIGRATE_NON_CANONICAL_OPERATOR_HAS_CHANGED` |
| `is`, `is not` | Prohibited in v1 | Python identity operators strictly forbidden | `MIGRATE_NON_CANONICAL_OPERATOR_IDENTITY` |

---

### 2.4 FlexValue Union & Document Reference Semantics

Both left and right comparison operands use the identical FlexValue union structure.

#### FlexValue Union Variants
1. **Static (`mode: "static"`):** Carries explicit `value_type` and `value`.
   - Supported value types: `string`, `integer`, `decimal` (serialized as string to avoid floating-point loss), `boolean`, `null`, `date`, `datetime`, `time`, `list`, `object`, `document_reference`.
2. **Variable (`mode: "variable"`):** Explicit path segment resolution with scope.
   - Canonical scopes: `doc`, `old_doc`, `vars`, `item`, `loop`, `row`, `caller`, `rule`, `doctype`, and locally declared collection aliases.
   - Fallback searches across scopes are strictly forbidden in canonical mode.
3. **Resolver (`mode: "resolver"`):** Explicit resolver invocation.
   - Carries `family`, `operation`, and backend-validated `config`.
   - Resolvers default to `condition_operand_allowed = false` unless explicitly audited and permitted by backend capability policy.
   - Database lookup resolvers MUST NOT be enabled as condition operands without explicit permission and query-limit policies.
4. **Template (`mode: "template"`):** Structured text/value segments where value segments recursively contain valid FlexValue nodes.
   - Raw Jinja or Python expression strings are strictly forbidden.

#### Link & Document Reference Comparison Rules
1. **Scalar Link Values:** Ordinary Link comparisons use scalar strings (`value_type: "string"`, e.g. `"CUST-0001"`). Scalar Link values are compared against typed document references by matching document `name`.
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
3. **DocType Compatibility Check:** When comparing a scalar Link field or typed reference, the `doctype` specified in the reference MUST be compatible with the target DocType metadata of the left operand field. Mismatched target DocTypes fail validation (`ERR_LINK_DOCTYPES_INCOMPATIBLE`).
4. **No Implicit Database Query:** Comparison of typed document references performs string/metadata matching only and DOES NOT execute database queries to verify existence unless an explicit lookup resolver is configured.
5. **Two-Item Lists Are Strictly Lists:** A two-item list (e.g., `["Customer", "CUST-0001"]`) is NEVER interpreted as a Link tuple based on shape alone. It is evaluated strictly as a `list` unless a separate legacy migration adapter proves its legacy meaning using verified left-operand Link metadata.
6. **Resolver Output Contracts:** Resolvers returning document references MUST declare `value_type: "document_reference"` in their output contract.

---

### 2.5 Logical and Value Semantics

1. **Short-Circuit Logical Groups:**
   - Group nodes (`type: "group"`) evaluate children left-to-right with strict short-circuiting (`and` halts on first `false` or evaluation error; `or` halts on first `true`).
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
   - **Empty String vs Whitespace:** Empty string (`""`) is considered unset (`is_set` -> False). Whitespace strings (e.g., `" "`) are considered set (`is_set` -> True).
   - **Empty Collection / Object:** Empty lists (`[]`) and empty dicts (`{}`) return True for `is_empty` and False for `is_not_empty`.
   - **False vs Zero:** Boolean `false` and integer/decimal `0` are distinct types. Boolean `false` is NEVER coerced to numeric `0`.
   - **Fail-Closed Error Policy:** Evaluation errors (missing paths in binary comparisons, type mismatches, resolver execution errors) fail closed. An evaluation error is NEVER converted to an ordinary `false` or `true` result; it triggers lifecycle error handling while preserving distinct diagnostic codes.

---

## 3. Server-Owned Metadata Contract (DTO)

The backend exposes a versioned contract DTO endpoint (`flexirule.ruleflow.api.get_condition_contract_dto`) that publishes authoritative capabilities to the frontend builder.

### Contract DTO Response Structure
```json
{
  "schema": "flexirule.condition_dto",
  "version": 1,
  "operators": [
    {
      "id": "equals",
      "label": "Equals",
      "arity": 2,
      "supported_value_types": ["string", "integer", "decimal", "boolean", "null", "date", "datetime", "document_reference"],
      "field_types": ["Data", "Select", "Int", "Float", "Currency", "Check", "Date", "Datetime", "Link"]
    }
  ],
  "scopes": ["doc", "old_doc", "vars", "item", "loop", "row", "caller", "rule", "doctype"],
  "resolvers": [
    {
      "family": "date",
      "operation": "add_days",
      "condition_operand_allowed": true,
      "output_type": "date"
    }
  ],
  "limits": {
    "max_collection_rows": 10000,
    "max_ast_depth": 20,
    "max_node_count": 100
  }
}
```

The frontend MUST consume this DTO to populate UI controls rather than hardcoding static operator options or resolver capabilities.

---

## 4. Shared Static Contract Fixtures

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

## 5. Reconciled Task Plans

- [Backend Implementation Plan](backend-implementation-plan.md)
- [Frontend Implementation Plan](frontend-implementation-plan.md)
