# Architecture & Design: Shared FlexValue Contract, Unified Resolver Registry, and Layered Execution Policies

**Document Status:** Formal Architecture & Design Specification (No Production Code Modified)
**Author:** Jules (FlexiRule Core Engineering)
**Target:** FlexiRule v15+ / Frappe Framework
**Scope:** Canonical FlexValue Unification, Resolver Registry Consolidation, Consumer Inventory & Policies, Migration & Equivalence Strategy
**Reference:** Aligns with `reports/canonical-condition-flexvalue-implementation-plan.md` and user architectural mandate.

---

## Executive Summary

FlexiRule currently operates with a bifurcated value evaluation architecture:
1. **Canonical Conditions:** Governed by `flexirule/ruleflow/core/flexvalue_contract.py` and `condition_contract.py`. Employs a strict, safe, AST-driven JSON representation (`static`, `variable`, `resolver`, `template`) strictly limited to pure, deterministic, non-database operations (`no_data_access`) with sealed operand validation.
2. **Action Handlers & Legacy Builders:** Governed by `flexirule/ruleflow/core/value_resolver.py`, `AssignmentHandler`, `QueryRecordsHandler`, and `ConditionCompiler`. Employs permissive, loosely typed payloads (`mode: "expression"`, raw Python expressions, Jinja template strings `{{ ... }}`, and direct database lookups).

Maintaining two competing value paradigms creates structural drift, security loopholes (e.g., UI-only resolver level gating), and high maintenance overhead.

This design establishes **one universal, context-independent FlexValue data model** coupled with **one authoritative resolver registry**. Operational context (conditions vs. assignments vs. query filters vs. record queries) is enforced via **layered validation and execution policies**, not separate data structures. Legacy payloads are migrated to canonical structures where semantically equivalent or routed through quarantine adapters when manual remediation is required.

---

## 1. Complete Consumer-to-Evaluator Dependency Map & Inventory

Every consumer of value configuration across the frontend UI, rule storage, and backend execution was audited. Below is the complete inventory:

### 1.1 Detailed Consumer Inventory Table

| Consumer # | Frontend Component | Context & Role | Current Emitted Payload Shape | Persisted Location & Schema | Backend Evaluator / Consumer | Supported Modes | Current Validation Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `ConditionLeaf.vue` | Canonical condition comparison operands (both `left` and `right`) | Dual operands: `{ mode: "static"|"variable"|"resolver"|"template", ... }` | `Rule Action.config` (JSON AST) under `left` and `right` | `condition_evaluator.py` & `flexvalue_contract.py` (`validate_flex_value`) | `static`, `variable`, `resolver`, `template` | **Strict Backend**: Fails closed on any unapproved resolver, unknown scope, or type mismatch. UI-level AST normalization. |
| **2** | `CollectionPredicateGroup.vue` | Collection source path for collection predicates (`any`, `all`, `none`) | `{ mode: "variable", path: { scope, segments } }` or raw path | `Rule Action.config.source` | `condition_evaluator.py` | `variable` | **Strict Backend**: Verifies scope in allowed scopes, bounded segments, DocType table/list validation. |
| **3** | `SimpleCondition.vue` | Legacy condition builder RHS value against LHS field | `{ mode: "static"|"variable"|"resolver"|"expression", value, config }` | `Rule Action.config` or legacy `condition_json` | `ConditionCompiler._compile_operand_value` -> Python string -> `safe_eval` | `static`, `variable`, `resolver`, `expression` | **Permissive/Compiler**: Coerces payload into Python AST or string; allows raw expressions. |
| **4** | `AssignmentConfig.vue` | Target state mutation (`doc.*`, `vars.*`) operand | `{ mode: "static"|"variable"|"resolver"|"expression", value, config }` | `Rule Action.config.rows[].value` (also compiled to `value_template` / `value_path` / `value_literal`) | `AssignmentHandler.execute` -> `get_compiled_resolver` -> `ValueResolver.compile` | `static`, `variable`, `resolver`, `expression`, plus raw strings / Jinja | **Permissive Runtime**: No backend schema validation on `value`. Resolves via `ValueResolver`. Compiles to Jinja string on save. |
| **5** | `AssignmentConfig.vue` (Row Guard) | Optional row execution guard (`when_condition`) | Canonical AST `{ type: "comparison"|"group" }` OR legacy Python expr | `Rule Action.config.rows[].when_condition` | `AssignmentHandler` -> `evaluate_condition` OR `_evaluate_python_condition` | AST or raw expr | **Hybrid**: Detects canonical vs legacy; validates canonical via `validate_condition_node`. Rejects mixed formats. |
| **6** | `FilterGroup.vue` | Query filter builder (QueryRecords, fetch conditions) | `{ mode: "static"|"variable"|"resolver"|"expression", value }` (2 for `between`) | `Rule Action.config.filters` | `QueryRecordsHandler._fetch_records` -> `_normalize_filters_for_backend` | `static`, `variable`, `resolver`, `expression` | **Ad-hoc Sanitizer**: Recursively strips `mode` wrappers down to primitive values; resolves variables. |
| **7** | `FilterLeaf.vue` | Standalone query filter leaf editor | Single `{ mode, value }` or array of 2 for range operators | Embedded in FilterTree AST | Same as `FilterGroup.vue` | `static`, `variable`, `resolver`, `expression` | Pure validation in `query_filter_validation.mjs` checks presence/type. |
| **8** | `QueryRecordsConfig.vue` (DocType) | Dynamic target DocType resolution | `{ mode: "static"|"variable", value }` | `Rule Action.config.doctype_name` | `QueryRecordsHandler` | `static`, `variable` | Checks string or variable path to string. |
| **9** | `QueryRecordsConfig.vue` (DocName) | Single document target name (`Get latest Doc` / specific doc) | `{ mode: "static"|"variable"|"resolver", value }` | `Rule Action.config.docname` | `QueryRecordsHandler` | `static`, `variable`, `resolver` | Resolves via `_resolve_nested_primitive_value`. |
| **10** | `QueryRecordsConfig.vue` (Report Filters) | Frappe Report filter parameters | Dictionary of fieldname -> FlexValue payload | `Rule Action.config.report_filters` | `QueryRecordsHandler` -> Report engine | `static`, `variable`, `resolver` | Strips mode wrappers down to primitive dictionary. |
| **11** | `OutputFieldsEditor.vue` | QueryRecords custom computed / literal output fields | Row object with `row.value_spec` containing FlexValue payload | `Rule Action.config.output_fields[].value_spec` | `QueryRecordsHandler._compute_output_fields` -> `ValueResolver.compile` | `static`, `variable`, `resolver`, `expression` | Resolves dynamically for each row returned by query. |

---

## 2. Comparison: Canonical FlexValue vs. Legacy ValueResolver

The following matrix contrasts the architectural realities of the new canonical contract and the legacy resolver system:

| Architectural Dimension | Canonical FlexValue Contract (`flexvalue_contract.py`) | Legacy ValueResolver (`value_resolver.py` & Handlers) |
| :--- | :--- | :--- |
| **Wire Schema** | Strict discriminated union: `mode` in `{"static", "variable", "resolver", "template"}`. Exact keys enforced. | Polymorphic dict or primitive: checks `mode`, `kind`, `family`, `value`, or raw Python/Jinja strings. |
| **Resolver Specification** | Requires explicit `family` + `operation` + `config`. No flat string expressions. | Accepts `kind` (e.g. `math_formula`), `family` + `operation`, flat `expression`, or legacy aliases (`fmt_op`, `norm_op`). |
| **Resolver Extensibility** | Explicit central registry (`register_condition_resolver`). Fingerprinted schema. | Static class methods and nested conditional branches in `ValueResolver.compile_resolver_config`. |
| **Database Access** | Strictly prohibited (`permission_policy == "no_data_access"`). Enforced by registry. | Unrestricted (`LookupResolver` / `FetchResolver` execute arbitrary `frappe.db.get_value` queries). |
| **Text Interpolation** | Explicit `template` mode with bounded typed segments (`text` and scalar `value`). | `mode: "expression"` containing rich-text HTML/Tiptap tokens or Jinja string `{{ ... }}`. |
| **Runtime Execution** | Pure Python dictionary AST traversal; no `eval()`, `exec()`, or Jinja rendering. | Compiled OOP hierarchy (`CompiledResolver`, `SafeEvalResolver`, `JinjaResolver`, `MathFormulaResolver`). |
| **Security Boundary** | Enforced at compile-time and runtime in Python backend. | Security filtering (`RESOLVER_LEVEL_KIND_MAP`) exists **only in Vue frontend**; backend executes anything. |
| **Error Handling** | Structured `ConditionValidationError` and `ConditionEvaluationError` with precise JSON paths. | Silent fallbacks to `NoneResolver()`, empty strings, or unhandled runtime exceptions. |

---

## 3. Proposed Shared FlexValue Data Model

The shared FlexValue schema defines **how values are structured**. It is context-independent: any valid FlexValue must conform to one of the four canonical modes.

```
                  ┌─────────────────────────────────────────┐
                  │           Shared FlexValue              │
                  │         (Discriminated Union)           │
                  └────────────────────┬────────────────────┘
                                       │
        ┌──────────────────┬───────────┴───────────┬──────────────────┐
        ▼                  ▼                       ▼                  ▼
┌───────────────┐  ┌───────────────┐       ┌───────────────┐  ┌───────────────┐
│     Mode:     │  │     Mode:     │       │     Mode:     │  │     Mode:     │
│   "static"    │  │  "variable"   │       │  "resolver"   │  │  "template"   │
└───────┬───────┘  └───────┬───────┘       └───────┬───────┘  └───────┬───────┘
        │                  │                       │                  │
        ▼                  ▼                       ▼                  ▼
  value_type:        path:                   family:            segments:
   string             scope                   operation          - type: text
   integer            segments                config:              value: "..."
   decimal                                     (schema-driven     - type: value
   boolean                                      nested values)     value: <FlexValue>
   null/date/...
  value: <typed>
```

### 3.1 Shared Schema Definitions

#### Mode 1: Static Literal (`static`)
```json
{
  "mode": "static",
  "value_type": "decimal",
  "value": "1500.50"
}
```
* **Permitted `value_type`s:** `string`, `integer`, `decimal`, `boolean`, `null`, `date`, `datetime`, `time`, `list`, `object`.
* **Rules:**
  - `decimal` values must be serialized as strings to eliminate binary IEEE-754 precision loss.
  - `boolean` values must be JSON booleans (`true`/`false`), never coerced to `1`/`0`.
  - `date`, `datetime`, `time` must be strict ISO-8601 strings.
  - No arbitrary non-JSON types.

#### Mode 2: Context Variable Reference (`variable`)
```json
{
  "mode": "variable",
  "path": {
    "scope": "doc",
    "segments": ["grand_total"]
  }
}
```
* **Rules:**
  - `scope` must be an approved identifier (e.g., `doc`, `old_doc`, `vars`, `item`, `loop`, `row`, `caller`, `rule`, `doctype`, or registered collection alias).
  - `segments` must be an array of bounded identifier strings (`[A-Za-z0-9_]+`). No dunder access (`__`), no method invocations.
  - Non-existent paths resolve to a sentinel `MISSING` state, not an automatic fallback.

#### Mode 3: Registered Resolver Operation (`resolver`)
```json
{
  "mode": "resolver",
  "family": "math",
  "operation": "calculate",
  "config": {
    "left": {
      "mode": "variable",
      "path": { "scope": "doc", "segments": ["rate"] }
    },
    "operator": "multiply",
    "right": {
      "mode": "static",
      "value_type": "integer",
      "value": 10
    },
    "precision": 2
  }
}
```
* **Rules:**
  - `family` and `operation` identify an operation in the Authoritative Resolver Registry.
  - `config` is strictly validated against the operation's JSON schema.
  - Any dynamic sub-parameter within `config` must recursively be a valid FlexValue node.

#### Mode 4: Text Template Interpolation (`template`)
```json
{
  "mode": "template",
  "segments": [
    { "type": "text", "value": "Invoice " },
    {
      "type": "value",
      "value": {
        "mode": "variable",
        "path": { "scope": "doc", "segments": ["name"] }
      }
    },
    { "type": "text", "value": " is overdue." }
  ]
}
```
* **Rules:**
  - Replaces ambiguous `mode: "expression"` containing HTML/Tiptap tokens.
  - Segment types are restricted to `text` (literal string) and `value` (FlexValue scalar).
  - Evaluates via strict concatenation; value segments must resolve to scalars.

---

## 4. Context-Specific Validation & Execution Policies

While the data contract is shared, **consumer policies dictate what is permissible in a given context**.

```
                           ┌─────────────────────────┐
                           │    Shared FlexValue     │
                           └────────────┬────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│  Condition Policy   │      │  Assignment Policy  │      │ Query Filter Policy │
├─────────────────────┤      ├─────────────────────┤      ├─────────────────────┤
│ • Pure & read-only  │      │ • Pure + DB lookups │      │ • Pure literals     │
│ • No DB / side-eff  │      │ • DateTime/Math ops │      │ • Doc/vars context  │
│ • Exact type match  │      │ • Target type check │      │ • PyPika conversion │
│ • No template left  │      │ • Full templates ok │      │ • No DB resolvers   │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
```

### 4.1 Policy Comparison Matrix

| Policy Dimension | Condition Operand Policy | Assignment Value Policy | Query Filter Policy | QueryRecords Param Policy | Output Field Policy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Allowed Modes** | `static`, `variable`, `resolver`, `template` (RHS only) | `static`, `variable`, `resolver`, `template` | `static`, `variable`, `resolver` | `static`, `variable` (resolver for docname) | `static`, `variable`, `resolver`, `template` |
| **Permitted Resolver Capabilities** | `pure`, `deterministic`, `no_data_access` | `pure`, `deterministic`, `read_only_db` | `pure`, `deterministic` (evaluated before SQL build) | `pure`, `deterministic`, `read_only_db` | `pure`, `deterministic`, `read_only_db` |
| **Forbidden Operations** | Any operation accessing database (`lookup.*`, `fetch.*`) or system state | Direct side-effect operations | Database-dependent resolvers (circular query risk) | Free-form SQL or unrestrained expression strings | Mutations or unbounded collection aggregations |
| **Scope Allowlist** | `doc`, `old_doc`, `vars`, `item`, `loop`, `row`, collection aliases | `doc`, `vars`, `old_doc`, `caller`, `rule` | `doc`, `vars`, `item` | `doc`, `vars` | `row`, `doc`, `vars` |
| **Output Type Gating** | Strict compatibility with Operator and LHS Fieldtype | Coercible to target fieldtype (`doc.<field>` or `vars.<var>`) | Compatible with SQL column Fieldtype | Must resolve to valid DocType string or docname | Must match declared output field type |
| **Template Support** | String comparison RHS only | Full scalar and text concatenation | Disallowed (prevents SQL injection/syntax error) | Disallowed for `doctype_name` | Allowed for string output columns |

### 4.2 Individual Policy Specifications

#### 1. Condition Operand Policy (`ConditionValidationPolicy`)
* **Objective:** Guarantee that condition evaluation is side-effect-free, microsecond-fast, and cannot fail due to network/DB latency.
* **Rules:**
  - Evaluates using `validate_flex_value` from `flexvalue_contract.py`.
  - Resolvers must have `condition_operand_allowed: True` and `permission_policy: "no_data_access"`.
  - Type checking strictly validates left vs. right operands according to `OPERATOR_REGISTRY`.

#### 2. Assignment Value Policy (`AssignmentValidationPolicy`)
* **Objective:** Ensure predictable mutations of document fields and workflow context variables.
* **Rules:**
  - Permits `lookup` family resolvers (e.g. fetching `customer_group` from `Customer` based on `doc.customer`).
  - Target compatibility: Validates that the static or inferred resolver output type matches the target DocType field.
  - Injects current target value into context as `value` for incremental transformations (e.g., text normalization).
  - Fully supports `template` mode for formatting complex strings.

#### 3. Query Filter Policy (`QueryFilterValidationPolicy`)
* **Objective:** Safe extraction of filter parameters for SQL query generation.
* **Rules:**
  - Resolvers must be resolvable *before* the SQL query is dispatched; DB-dependent lookups in filter values are rejected to avoid N+1 query cascades and circular dependencies.
  - Strips FlexValue nodes to raw Python primitives acceptable by PyPika / Frappe DB query builder.
  - Range operators (`between`) require a 2-element tuple of scalar FlexValues.

#### 4. QueryRecords Config Policy (`QueryRecordsValidationPolicy`)
* **Objective:** Dynamic document name and criteria resolution.
* **Rules:**
  - `doctype_name`: Limited to `static` string or `variable` pointing to a string field (e.g., `doc.reference_type`).
  - `docname`: Accepts `static`, `variable`, or `lookup` resolver.
  - Parameters for Script Reports: Serialized down to clean JSON primitives.

#### 5. Output Fields Policy (`OutputFieldsValidationPolicy`)
* **Objective:** Real-time projection and computation of records fetched by `QueryRecords`.
* **Rules:**
  - Evaluated per record row; exposes `row` scope representing the current fetched database record.
  - Permits `math`, `text`, `date_time`, and `lookup` resolvers.
  - Inferred resolver output type must match the declared column `fieldtype`.

---

## 5. Authoritative Unified Resolver Registry Architecture

The current architecture has two places defining resolver behavior:
- `flexvalue_contract.py`: `CONDITION_RESOLVER_REGISTRY` (currently empty in base repo; strict signature).
- `value_resolver.py`: Class-based `ValueResolver.compile_resolver_config()` (implements 9 families).

### 5.1 Unified Registry Design

We unify these into **one central Authoritative Resolver Registry**:

```python
@dataclass(frozen=True)
class ResolverDefinition:
    family: str
    operation: str
    label: str
    output_type: str
    config_schema: dict[str, Any]
    capabilities: frozenset[str]  # {"pure", "deterministic", "read_only_db", "side_effect"}
    permission_policy: str        # "no_data_access", "read_record", "system"
    condition_operand_allowed: bool
    allowed_contexts: frozenset[str] # {"condition", "assignment", "filter", "output_field"}
    validate_config: Callable[[dict, str, set[str], int, int], None]
    resolve: Callable[[dict, dict], Any]
```

### 5.2 Canonical Resolver Family & Capability Matrix

Every existing resolver in `value_resolver.py` is mapped into this unified registry:

| Canonical Family | Canonical Operation | Capabilities | Permission Policy | Condition Allowed? | Assignment Allowed? | Query Filter Allowed? | Output Field Allowed? | Underlying Implementation |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **`math`** | `calculate` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `MathFormulaResolver` |
| **`date_time`** | `current` | `system`, `read_only` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `DateCurrentResolver` |
| **`date_time`** | `calculate` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `DateFormulaResolver` |
| **`date_time`** | `diff` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `DateDiffResolver` |
| **`date_time`** | `extract` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `DateExtractResolver` |
| **`date_time`** | `boundary` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `DateBoundaryResolver` |
| **`date_time`** | `format` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `FormatResolver` |
| **`text`** | `combine` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `StringFormulaResolver` |
| **`text`** | `case` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | String upper/lower |
| **`text`** | `normalize` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `NormalizationResolver` |
| **`text`** | `format` | `pure`, `deterministic` | `no_data_access` | **Yes** | **Yes** | **Yes** | **Yes** | `FormatResolver` |
| **`collection`** | `count` / `sum` / `avg` | `pure`, `in_memory` | `no_data_access` | **Yes** | **Yes** | **No** | **Yes** | `CollectionResolver` |
| **`collection`** | `filter` / `pluck` / `find` | `pure`, `in_memory` | `no_data_access` | **Yes** | **Yes** | **No** | **Yes** | `CollectionResolver` |
| **`lookup`** | `fetch` / `get_value` | `read_only_db`, `external` | `read_record` | **NO** | **Yes** | **NO** | **Yes** | `LookupResolver` |
| **`system_context`** | `get_user` / `get_role` | `system`, `read_only` | `system` | **Yes** | **Yes** | **Yes** | **Yes** | `SystemContextResolver` |

---

## 6. Legacy Payload Conversion, Compatibility Adapter, & Migration Strategy

To guarantee that existing rules, assignments, and query configs do not break, migration must distinguish between **lossless semantic conversions** and **ambiguous payloads requiring manual remediation**.

### 6.1 Payload Classification Taxonomy

```
                          ┌──────────────────────────┐
                          │ Incoming FlexValue Input │
                          └─────────────┬────────────┘
                                        │
           ┌────────────────────────────┴────────────────────────────┐
           ▼                                                         ▼
┌─────────────────────┐                                   ┌─────────────────────┐
│  Lossless Canonical │                                   │  Ambiguous / Unsafe │
│      Candidate      │                                   │       Payload       │
└──────────┬──────────┘                                   └──────────┬──────────┘
           │                                                         │
     Auto-Migrate                                              Quarantine
           │                                                         │
  • mode: "static" -> typed static                          • Raw Python math strings
  • mode: "variable" -> scope+segments                      • Arbitrary safe_eval blocks
  • mode: "expression" (pure text+tokens) -> template       • Unparseable Jinja logic
  • legacy kind -> canonical family+operation               • Direct DB mutations
```

### 6.2 Lossless Conversions (Auto-Migrated)

#### Case 1: Legacy Text Token Mixed Content -> Canonical Template
* **Legacy Payload:**
  ```json
  {
    "mode": "expression",
    "value": [
      { "type": "text", "value": "Customer: " },
      { "type": "variableToken", "attrs": { "path": "doc.customer_name" } },
      { "type": "text", "value": " has balance " },
      { "type": "variableToken", "attrs": { "path": "doc.outstanding_amount" } }
    ]
  }
  ```
* **Converted Canonical Payload:**
  ```json
  {
    "mode": "template",
    "segments": [
      { "type": "text", "value": "Customer: " },
      {
        "type": "value",
        "value": {
          "mode": "variable",
          "path": { "scope": "doc", "segments": ["customer_name"] }
        }
      },
      { "type": "text", "value": " has balance " },
      {
        "type": "value",
        "value": {
          "mode": "variable",
          "path": { "scope": "doc", "segments": ["outstanding_amount"] }
        }
      }
    ]
  }
  ```

#### Case 2: Legacy Flat `kind: "math_formula"` -> Canonical `family: "math"`
* **Legacy Payload:**
  ```json
  {
    "mode": "resolver",
    "config": {
      "kind": "math_formula",
      "field_a": "doc.qty",
      "math_op": "*",
      "field_b_type": "constant",
      "constant_b": 2.5,
      "precision": 2
    }
  }
  ```
* **Converted Canonical Payload:**
  ```json
  {
    "mode": "resolver",
    "family": "math",
    "operation": "calculate",
    "config": {
      "left": {
        "mode": "variable",
        "path": { "scope": "doc", "segments": ["qty"] }
      },
      "operator": "multiply",
      "right": {
        "mode": "static",
        "value_type": "decimal",
        "value": "2.5"
      },
      "precision": 2
    }
  }
  ```

#### Case 3: Legacy String Context References -> Canonical Variable
* **Legacy Payload:** `"doc.customer.customer_group"` or `{"mode": "variable", "value": "doc.status"}`
* **Converted Canonical Payload:**
  ```json
  {
    "mode": "variable",
    "path": {
      "scope": "doc",
      "segments": ["customer", "customer_group"]
    }
  }
  ```

### 6.3 Ambiguous Payloads (Quarantine & Actionable Diagnostic)

Certain legacy configurations cannot be transformed losslessly without guessing author intent:
1. **Manual Python Expression Strings:** E.g., `{ "mode": "resolver", "value": "doc.base_amount * (1 - doc.discount_pct / 100)" }` with `config: null`.
   - *Risk:* Converting this into a template concatenates strings; compiling into nested math resolvers requires full Python AST decompilation.
   - *Policy:* Quarantine under a legacy execution wrapper for existing saved rules. Block saving of new rules containing this payload with a descriptive validation error:
     `"Free-form Python expressions are deprecated. Please use the visual Math Formula resolver."`
2. **Arbitrary Jinja Code Blocks:** E.g., `{% if doc.grand_total > 1000 %}VIP{% endif %}`.
   - *Policy:* Allowed only in actions that explicitly support template scripting (e.g. `NotifyHandler`), never in conditions or numeric assignments.
3. **Unchecked DB Lookups in Conditions:** E.g., attempting to use a `lookup` resolver inside a condition operand.
   - *Policy:* Fails validation at save-time:
     `"Resolver 'lookup.fetch' is not permitted in condition operands (violates 'no_data_access' policy)."`

---

## 7. Semantic Equivalence & Verification Scenarios

To prove that unifying the contract causes zero behavioral regressions, the following semantic test suites are established:

### Test Scenario Matrix

| ID | Category | Fixture / Payload | Input Context | Expected Evaluation Output | Failure Mode to Guard Against |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEQ-01** | Decimal Math | Canonical `math.calculate` multiplying `doc.rate` (10.05) by `qty` (3) | `doc = {"rate": Decimal("10.05"), "qty": 3}` | `Decimal("30.15")` | Floating-point rounding artifact (`30.149999999999995`) |
| **SEQ-02** | Date Boundary | Canonical `date_time.boundary` (`start_of_month`) | `doc = {"posting_date": "2026-11-15"}` | `"2026-11-01"` | Timezone drift or datetime format corruption |
| **SEQ-03** | Text Template | Canonical `template` with multiple variables and null handling | `doc = {"prefix": "INV-", "num": 101, "suffix": None}` | `"INV-101"` | Outputting literal string `"None"` or `"null"` |
| **SEQ-04** | Variable Scope | Canonical `variable` resolving nested child row variable | `row = {"item_code": "ITEM-A"}, doc = {"name": "SO-01"}` | `"ITEM-A"` | Accidentally falling back to `doc.item_code` |
| **SEQ-05** | Condition Guard | Canonical comparison: `left` (doc.total) `gte` `right` (static 100) | `doc = {"total": 150}` | `True` | Incompatible type coercion error |
| **SEQ-06** | DB Lookup in Action | Canonical `lookup.fetch` in Assignment value | `doc = {"customer": "CUST-001"}` (mocked DB returns `Group A`) | `"Group A"` | Permission denied or caching stale database values |
| **SEQ-07** | Condition DB Ban | Canonical `lookup.fetch` placed in Condition operand | Valid DB context | Validation Exception (`resolver_not_allowed`) | Silently querying database inside hot rule condition loop |

---

## 8. Risk Assessment & Controls

| Risk | Impact | Likelihood | Mitigation & Control |
| :--- | :--- | :---: | :--- |
| **1. UI Disconnect** | Users authoring expressions in `FlexValueControl.vue` emit incompatible shapes | Medium | `FlexValueControl.vue` refactored to emit canonical `template` and structured `resolver` nodes natively. |
| **2. Breaking Existing Saved Assignments** | Deployed rules fail on site upgrade due to strict validation | High | Phased rollout: Runtime compatibility adapter in `ValueResolver` handles legacy shapes; migrations run via `bench migrate`. |
| **3. Performance Overhead** | Schema validation adds latency to high-frequency rule execution | Low | Plan caching via LRU: `prepare_condition` and `get_action_plan` validate once at load/cache time; execution uses compiled tuples/callables. |
| **4. Inadvertent DB Query in Hot Loops** | Action resolvers leak into condition evaluation causing DB thrashing | Medium | Strict static capability check: `permission_policy == "no_data_access"` is verified at compile-time and strictly barred from condition execution. |

---

## 9. Phased Implementation Roadmap & Affected Files

The recommended implementation is structured in 5 controlled phases:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Authoritative Resolver Registry Foundation                        │
│ - Unify CONDITION_RESOLVER_REGISTRY and ValueResolver into registry.py    │
│ - Implement capability flags & permission policies                         │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│ Phase 2: Layered Validation Policies Implementation                         │
│ - Implement Condition, Assignment, Filter, and OutputField policies        │
│ - Add context validators in flexirule/ruleflow/core/policies/              │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│ Phase 3: Legacy Compatibility & Migration Adapters                         │
│ - Implement payload normalizer (expression -> template, kind -> family)   │
│ - Implement safe quarantine for legacy unparseable Python expressions     │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│ Phase 4: Frontend FlexValueControl & Builders Alignment                    │
│ - Update FlexValueControl.vue to emit canonical template & resolver AST   │
│ - Update AssignmentConfig.vue and FilterGroup.vue to consume policies      │
└─────────────────────────────────────┬──────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼──────────────────────────────────────┐
│ Phase 5: Verification, Benchmarks & Deprecation Finalization               │
│ - Execute full Cypress reboot test suite & Python test suite               │
│ - Benchmark condition evaluation latency (<25µs requirement)               │
└────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Affected Files Matrix

| File Path | Component / Layer | Nature of Change |
| :--- | :--- | :--- |
| `flexirule/ruleflow/core/flexvalue_contract.py` | Shared Value Contract | Centralize schema definitions for `static`, `variable`, `resolver`, `template`. |
| `flexirule/ruleflow/core/resolver_registry.py` *(New)* | Authoritative Registry | Single source of truth for all 9 resolver families, operations, schemas, and capabilities. |
| `flexirule/ruleflow/core/value_resolver.py` | Runtime Resolver Engine | Refactor `ValueResolver.compile` to delegate to `resolver_registry.py`; maintain legacy compatibility layer. |
| `flexirule/ruleflow/core/policies/` *(New)* | Context Policies | Implement `ConditionPolicy`, `AssignmentPolicy`, `QueryFilterPolicy`, `OutputFieldPolicy`. |
| `flexirule/ruleflow/core/action_handlers/assignment.py` | Assignment Execution | Replace ad-hoc Jinja serialization with canonical `AssignmentPolicy` validation and execution. |
| `flexirule/ruleflow/core/action_handlers/query_records.py` | QueryRecords Handler | Standardize filter and output field resolution on canonical FlexValue. |
| `flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue` | Frontend Control | Emit canonical `template` mode instead of `expression`; emit canonical `family`+`operation` for resolvers. |
| `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/AssignmentConfig.vue` | Frontend Action Config | Consume `AssignmentPolicy` metadata; remove legacy manual formula fallback. |
| `flexirule/ruleflow/tests/test_shared_flexvalue_contract.py` *(New)* | Backend Test Suite | Comprehensive unit and semantic equivalence tests for all modes and policies. |

---

## 10. Conclusion & Final Recommendation

The proposed architecture delivers the user's objective: **One shared FlexValue data model, one authoritative resolver registry, and explicit context-specific validation and execution policies.**

- **No Competing Formats:** All consumers speak the same JSON AST.
- **Strict Condition Security:** Conditions remain 100% read-only, deterministic, and isolated from database operations.
- **Rich Action Power:** Actions retain full access to database lookups, date/time arithmetic, and rich text templates.
- **Zero Disruption Migration:** Lossless legacy payloads convert seamlessly; unsupported payloads are cleanly quarantined with actionable feedback.
