# Value Resolver Improvement Plan

## 1. Executive Summary

FlexiRule is a Frappe/ERPNext-native no-code business rule engine designed to enable functional ERP users, systems administrators, and business analysts to automate document workflows, field mutations, validations, and record queries without writing custom Server Scripts. As FlexiRule approaches release-candidate (RC) maturity, a rigorous architectural review of its **Value Resolver** subsystem is necessary to ensure it meets production requirements for safety, composability, performance, and Frappe ORM alignment.

The primary objective of this review is not to turn FlexiRule into a programming language or general-purpose scripting environment. Instead, it defines a **minimal, composable, safe, and Frappe-native expression and value resolution model**.

### Critical Architectural Distinctions

A core architectural principle established in this report is the explicit separation of concerns across three distinct operational layers:

1. **Value Resolver (Value Production Layer)**:
   - *Role*: Resolves, calculates, formats, or transforms dynamic values into concrete runtime primitives or objects based on context (`doc`, `vars`, `row`, `session`).
   - *Scope*: Scalar values, document references, collection extractions, date calculations, string manipulations, and lookups.
   - *Consumers*: Consumed downstream by specific Action Types (e.g., Assignment, Condition, Records Query).

2. **Assignment Action Type (Mutation Layer)**:
   - *Role*: Defines batch state mutation semantics (`set`, `append`, `increment`, `multiply`, `clear`).
   - *Mechanism*: Consumes the Value Resolver to evaluate the operand, then applies the mutation operator to the target field or variable path.

3. **Condition Action Type (Predicate Evaluation Layer)**:
   - *Role*: Evaluates logical truth values to branch rule execution flow (`next_step_if_true` vs `next_step_if_false`).
   - *Mechanism*: Consumes the Value Resolver to obtain left and right operands, then evaluates comparison semantics (`==`, `>`, `in`, `contains`, `between`) using `ConditionEvaluator` / `ConditionCompiler`.

4. **Records Query → Query List → Query Filters (Database Query Layer)**:
   - *Role*: Constructs permission-aware ORM database queries (`frappe.get_list()`, `frappe.db.get_value()`, `frappe.get_all()`).
   - *Mechanism*: Consumes resolved primitive values to pass into Frappe SQL parameter bindings (`filters`, `or_filters`). Query Filters themselves are **not** a Value Resolver family; they are configuration structures within the Records Query Action Type that consume resolved values.

By maintaining strict boundaries between **Value Production**, **Predicate Evaluation**, and **Query Filter Construction**, FlexiRule avoids anti-patterns where query semantics leak into value resolvers or where scalar value resolvers attempt to execute database joins directly.

---

## 2. Current Architecture

FlexiRule's current value resolution infrastructure relies on a dual-layer strategy split between frontend Vue 3 controls and backend Python compilation/execution classes.

### Frontend Architecture
- **Control Entry Point**: `FlexValueControl.vue` acts as the universal input component. It supports distinct input modes: `static`, `variable`, `expression` (Tiptap tokenized editor), and `resolver` (opens `ValueResolverControl.vue`).
- **Resolver Dialog**: `ValueResolverControl.vue` provides a modal interface driven by `strategies.js` (`RESOLVER_STRATEGIES`), where individual UI components configure specific resolver parameters.
- **Family / Kind System**: Frontend operations are organized under semantic families (`text`, `date_time`, `collection`, `lookup`) and specific kinds (`math_formula`, `normalization`, `system_context`, `child_aggregation`, `fetch`).

### Backend Architecture
- **Registry & Compiler**: `flexirule.ruleflow.core.value_resolver.ValueResolver` provides static methods `compile()` and `compile_resolver_config()`. It converts serialized payload dictionaries into optimized `CompiledResolver` class instances.
- **Compiled Classes**: Classes derived from `CompiledResolver` implement `.resolve(context)`:
  - Core primitives: `StaticResolver`, `VariableResolver`, `NoneResolver`.
  - Strategy implementations: `DateFormulaResolver`, `MathFormulaResolver`, `DateDiffResolver`, `StringFormulaResolver`, `NormalizationResolver`, `FormatResolver`, `SystemContextResolver`, `LookupResolver`, `CollectionResolver`.
  - Fallbacks: `JinjaResolver`, `SafeEvalResolver`, `ExpressionResolver`.
- **Runtime Caching**: `get_compiled_resolver(action, key, value_payload)` caches compiled resolver graphs on `frappe.local.flexirule_compiled_resolvers` to eliminate compile-time overhead during repeated rule execution.

### Architectural Shortcomings Identified
1. **Redundant Strategies**: Legacy classes like `FetchResolver` and `ChildAggregationResolver` duplicate functionality now cleanly handled by `LookupResolver` and `CollectionResolver`.
2. **Artificial Composition Limits**: Resolver parameters (e.g., date offsets or math operands) rely heavily on raw field names (`base_field`, `field_a`, `field_b`) rather than accepting nested `FlexValue` configurations, preventing arbitrary composition (e.g., calculating a date offset based on a looked-up customer lead-time).
3. **Implicit Typing**: Values are passed as raw untyped Python primitives, leading to runtime coercion bugs when dates or numbers are formatted as strings prior to database query insertion.

---

## 3. Current Resolver Taxonomy

The codebase currently maintains fifteen (15) resolver strategies/classes across backend execution and frontend registration:

| Canonical Kind / Family | Frontend Component | Backend Strategy Class | Config Mode / Strategy | Current Status |
| :--- | :--- | :--- | :--- | :--- |
| `date_time.calculate` | `DateTimeCalculateConfig.vue` | `DateFormulaResolver` | `kind: "date_formula"` / `family: "date_time"` | Active |
| `date_time.diff` | `DateTimeDiffConfig.vue` | `DateDiffResolver` | `kind: "date_diff"` / `family: "date_time"` | Active |
| `date_time.format` | `DateTimeFormatConfig.vue` | `FormatResolver` | `kind: "format"` / `family: "date_time"` | Active |
| `math_formula` | `MathFormulaResolver.vue` | `MathFormulaResolver` | `kind: "math_formula"` | Active |
| `text.combine` | `TextTransformResolver.vue` | `StringFormulaResolver` | `kind: "string_formula"` / `family: "text"` | Active |
| `text.case` | `TextTransformResolver.vue` | `StringFormulaResolver` / `NormalizationResolver` | `family: "text"` | Active |
| `text.normalize` | `TextTransformResolver.vue` | `NormalizationResolver` | `kind: "normalization"` / `family: "text"` | Active |
| `text.format` | `TextTransformResolver.vue` | `FormatResolver` | `kind: "format"` / `family: "text"` | Active |
| `collection` | `CollectionResolver.vue` | `CollectionResolver` | `kind: "collection"` / `family: "collection"` | Active |
| `child_aggregation` | `AggregationResolver.vue` | `ChildAggregationResolver` | `kind: "child_aggregation"` | Legacy Alias (maps to `CollectionResolver`) |
| `lookup` | `LookupResolver.vue` | `LookupResolver` | `kind: "lookup"` / `family: "lookup"` | Active |
| `fetch` | `FetchResolver.vue` | `FetchResolver` | `kind: "fetch"` | Legacy Alias (inherits `LookupResolver`) |
| `system_context` | `SystemContextResolver.vue` | `SystemContextResolver` | `kind: "system_context"` | Active |
| `variable` | `@` Mentions in Tiptap | `VariableResolver` | `mode: "variable"` | Core Primitive |
| `static` | Static Controls | `StaticResolver` | `mode: "static"` | Core Primitive |

---

## 4. Value Resolver Usage Map

Tracing actual consumers across the codebase establishes how Value Resolver payloads are integrated into execution routines.

### 4.1 Assignment Action Type
- **Consumer**: `AssignmentHandler` (`flexirule/ruleflow/core/action_handlers/assignment.py`).
- **Configuration Path**: `action.config` → Array of row objects `[{ target, operator, value, when_expression }]`.
- **Value Resolver Role**: Operands defined in `assignment.value` are compiled via `get_compiled_resolver(action, f"assign_{idx}", assignment.get("value"))` and evaluated using `resolver.resolve(context_copy)`.
- **Target Use Cases**:
  - Setting document status (`doc.status = "Submitted"`).
  - Calculating dynamic due dates (`doc.due_date = posting_date + 30 days`).
  - Aggregating child table totals (`doc.total_amount = sum(items.amount)`).
  - Fetching defaults from linked entities (`doc.territory = Customer.territory`).

### 4.2 Condition Action Type
- **Consumer**: `ConditionHandler` (`flexirule/ruleflow/core/action_handlers/condition.py`) & `ConditionEvaluator` (`flexirule/ruleflow/core/evaluator.py`).
- **Configuration Path**: `action.config` → JSON condition structure / `compiled_expression`.
- **Value Resolver Role**: In rule conditions and entry conditions, left-hand operands and right-hand operands consume `get_context_value` or dynamic resolver payloads before applying logical operators (`==`, `>`, `in`, `contains`).
- **Target Use Cases**:
  - Comparing totals (`doc.grand_total > 10000`).
  - Checking customer credit terms (`doc.posting_date > doc.credit_limit_date`).
  - Child row predicate checks (`any(items.qty > 50)`).

### 4.3 Records Query → Query List
- **Consumer**: `QueryRecordsHandler` (`flexirule/ruleflow/core/action_handlers/query_records.py`).
- **Configuration Path**: `action.config` → `filters`, `or_filters`.
- **Value Resolver Role**: Filter values specified in `QueryRecordsConfig` pass through `_resolve_filters_with_context()`, which delegates to `_resolve_value_expression_with_context()`. Dynamic resolver payloads or variable references are compiled and resolved into scalar primitives or primitive lists.
- **Target Use Cases**:
  - Dynamic date range filtering (`posting_date >= today - 30 days`).
  - User-scoped queries (`owner == current_user`).
  - Linked record matching (`customer == doc.customer`).

### 4.4 Other Consumers
- **Document Action (`document_action.py`)**: Resolves field value maps when creating or updating secondary documents.
- **Notify Action (`simple_actions.py`)**: Resolves dynamic recipient email addresses and templated message bodies.
- **Sub-Rule Action (`sub_rule.py`)**: Resolves input mapping payloads passed into child sub-rules.

---

## 5. Target Use-Case Inventory

| Resolver Family | Operation | Frontend Component | Backend Strategy | Consumer | Action Type | Target Use Case | Expected Value | Current Status | Gap |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `date_time` | `calculate` | `DateTimeCalculateConfig` | `DateFormulaResolver` | `AssignmentHandler` | `Assignment` | Calculate due date (`posting_date + payment_terms`) | `Date` string | Implemented | Cannot take dynamic offset variable |
| `date_time` | `diff` | `DateTimeDiffConfig` | `DateDiffResolver` | `ConditionHandler` | `Condition` | Overdue days check (`today - posting_date > 30`) | `Integer` | Implemented | None |
| `collection` | `sum` | `CollectionResolver` | `CollectionResolver` | `AssignmentHandler` | `Assignment` | Sales Order child items total sum | `Float` / `Currency` | Implemented | Cannot filter child rows before sum in single UI step cleanly |
| `collection` | `count` | `CollectionResolver` | `CollectionResolver` | `ConditionHandler` | `Condition` | Stock reorder check (`count(items) > 10`) | `Integer` | Implemented | None |
| `lookup` | `static` | `LookupResolver` | `LookupResolver` | `AssignmentHandler` | `Assignment` | Customer territory lookup (`doc.customer` → `Customer.territory`) | `Data` / `Link` | Implemented | Requires single step lookup; nested link traversal not supported |
| `lookup` | `dynamic` | `LookupResolver` | `LookupResolver` | `AssignmentHandler` | `Assignment` | Dynamic Link lookup (`party_type` + `party` → `credit_limit`) | `Float` | Implemented | None |
| `text` | `combine` | `TextTransformResolver` | `StringFormulaResolver` | `AssignmentHandler` | `Assignment` | Full name generation (`first_name` + `last_name`) | `Data` | Implemented | Fixed 2-string concat; needs multi-item join |
| `text` | `normalize` | `TextTransformResolver` | `NormalizationResolver` | `AssignmentHandler` | `Assignment` | Clean SKU or search term | `Data` | Implemented | Pipeline selection UI is disconnected from backend profiles |
| `system_context`| `user` | `SystemContextResolver` | `SystemContextResolver` | `QueryRecordsHandler` | `Query Records` | Filter records owned by current session user | `Link` (User) | Implemented | None |

---

## 6. Frappe/ERPNext Requirements

ERPNext business rules operate against Frappe's specific document lifecycle and ORM query model. A production-ready value resolver must align with:

1. **DocField Types & Metadata**:
   - `Link` & `Dynamic Link`: Require scalar string document keys (`name`). Lookups must handle missing or deleted linked documents gracefully without throwing Python `AttributeError`.
   - `Table` & `Table MultiSelect`: Represented as lists of dicts (`doc.items`). Collection resolvers must iterate natively over child table rows.
   - `Currency` / `Float` / `Int` / `Percent`: Require precision handling via `frappe.utils.flt()` and `frappe.utils.cint()`.
   - `Date` / `Datetime` / `Time`: Require standard ISO string formatting (`YYYY-MM-DD`) compatible with MariaDB/PostgreSQL column types.

2. **Permission Awareness**:
   - Out-of-the-box, value lookups on linked DocTypes (`LookupResolver`) or record queries (`QueryRecordsHandler`) must respect session permissions via `frappe.has_permission()`.
   - Admin bypasses (`ignore_permissions`) must be restricted to explicitly authorized contexts backed by audit logs.

3. **Savepoint & Transaction Safety**:
   - Value resolvers must remain strictly **side-effect-free**. A value resolver must NEVER write to the database or mutate document state during execution. State mutations are reserved exclusively for Action Handlers (`AssignmentHandler`, `DocumentActionHandler`).

---

## 7. Assignment Requirements

The `Assignment` Action Type mutates target document fields or execution context variables (`vars.*`).

### Core Requirements
- **Type Coercion & Validation**: Value Resolvers must produce values matching the target field's `fieldtype`. For example, assigning a string to a `Float` field must safely convert using `flt()`.
- **Supported Assignment Operators**:
  - `set`: Assigns resolved value directly.
  - `append`: Appends resolved item to a list or child table.
  - `increment` / `decrement`: Adds/subtracts numeric resolver output.
  - `clear`: Sets target path to `None` or `[]`.
- **Benchmark ERP Scenarios**:
  - *Scenario A (Payment Terms)*: `doc.due_date = DateFormulaResolver(base=doc.posting_date, offset=doc.credit_days)`.
  - *Scenario B (Grand Total)*: `doc.grand_total = CollectionResolver(source=doc.items, operation=sum, target_field=amount)`.
  - *Scenario C (Default Territory)*: `doc.territory = LookupResolver(doctype=Customer, record=doc.customer, fetch=territory)`.

---

## 8. Condition Requirements

The `Condition` Action Type and rule entry conditions evaluate logical predicates.

### Core Requirements
- **Operand Value Resolution**: Conditions use Value Resolver to obtain the left operand (`left_value`) and right operand (`right_value`).
- **Predicate Evaluation Separation**: Comparison semantics (`==`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not in`, `between`, `is set`, `is not set`) are evaluated by `ConditionEvaluator`, NOT by the Value Resolver.
- **Benchmark ERP Scenarios**:
  - *Scenario A (Credit Limit Check)*: `Condition(left=doc.grand_total, operator=">", right=LookupResolver(doctype=Customer, record=doc.customer, fetch=credit_limit))`.
  - *Scenario B (Item Quantity Threshold)*: `Condition(left=CollectionResolver(source=doc.items, operation=count, condition=[qty > 100]), operator=">", right=0)`.

---

## 9. Records Query / Query List / Query Filter Requirements

The `Records Query` Action Type (specifically the `Query List` operation) constructs database queries.

### Core Requirements
- **Filter Value Resolution**: Filter values may be resolved dynamically using `ValueResolver` (e.g., filtering `posting_date >= DateFormulaResolver(today - 30 days)`).
- **Query Filter Semantics**: Query Filters format resolved values into Frappe ORM filter tuples: `[doctype, field, operator, value]`.
- **SQL Injection Safety**: Values produced by Value Resolvers are passed as parameterized arguments to `frappe.get_list(filters=...)` or `frappe.db.sql(query, filters)`, preventing SQL injection vulnerabilities.
- **Benchmark ERP Scenarios**:
  - *Scenario A (Unpaid Invoices)*: `QueryList(doctype="Sales Invoice", filters=[["customer", "=", doc.customer], ["outstanding_amount", ">", 0]])`.
  - *Scenario B (Recent Activity)*: `QueryList(doctype="Stock Ledger Entry", filters=[["posting_date", ">=", DateFormulaResolver(today - 7 days)]])`.

---

## 10. Action Requirements

Other FlexiRule actions consume Value Resolvers to supply parameters:
- **Notify Action**: Resolves recipient lists (`LookupResolver` → `Customer.email_id`) and dynamic subject lines (`StringFormulaResolver`).
- **Document Action**: Resolves field value maps when auto-creating stock entries or journal vouchers.
- **Sub-Rule Action**: Resolves parameter dictionaries passed into reusable sub-rules.

---

## 11. Composition Analysis

Current FlexiRule resolvers have artificial composition boundaries:
- **Current Limitation**: A math resolver allows adding `field_a` and `field_b` (or a static constant). It cannot accept a nested `LookupResolver` as `field_b`.
- **Target Composition Model**: All resolver inputs should accept a nested `FlexValue` structure (`static`, `variable`, or `resolver`).
- **Example Composition Chain**:
  ```
  DateFormulaResolver
    ├── base_date: doc.posting_date
    └── offset_days: LookupResolver
                        ├── doctype: "Customer"
                        ├── record: doc.customer
                        └── fetch_field: "credit_days"
  ```
- **Architectural Solution**: Refactor resolver constructors to recursively compile input payloads using `ValueResolver.compile()`.

---

## 12. Value Type Analysis

FlexiRule requires a semantic value type model to enforce UI compatibility, prevent runtime exceptions, and provide intelligent field filtering.

### Semantic Value Types
1. **Scalar Types**:
   - `Text` / `String`: Raw text, codes, identifiers.
   - `Number` (`Integer`, `Float`, `Currency`, `Percent`): Numeric values.
   - `Boolean`: `True` / `False`.
   - `Date` / `Datetime` / `Time`: Temporal values.
2. **Reference Types**:
   - `Document Reference`: Unique document ID (`name`).
   - `DocType Reference`: Name of a DocType.
3. **Complex / Collection Types**:
   - `Collection` / `List`: Array of objects (child rows) or array of primitives.
   - `Object` / `Dict`: Key-value mappings (e.g., full document snapshot).

---

## 13. Collection and Child Table Analysis

Child table operations represent a major requirement in ERPNext (e.g., `Sales Order Item`, `Purchase Invoice Item`).

### Supported Collection Operations
- `count`: Number of rows matching optional condition.
- `sum`: Total sum of a numeric field across matching rows.
- `avg`: Average of a numeric field across matching rows.
- `min` / `max`: Minimum/maximum value in matching rows.
- `filter`: Returns array of child row objects matching condition.
- `pluck`: Extracts array of field values from child rows.
- `unique`: Extracts distinct field values from child rows.
- `any` / `all` / `first`: Boolean/row extraction predicates.

### Performance Safeguards
- **Max Collection Rows**: `MAX_COLLECTION_ROWS = 10000` enforced in `CollectionResolver` to prevent memory exhaustion DoS during large loop evaluations.

---

## 14. Lookup and Relationship Analysis

Cross-document lookups enable rules to fetch data across entity boundaries.

### Lookup Capabilities
- **Static Lookup**: Fetches field from a fixed DocType (e.g., `Customer.territory` where `name = doc.customer`).
- **Dynamic Lookup**: Resolves target DocType dynamically from another field (e.g., `party_type` + `party` → `party_name`).
- **Permission Boundary**: Enforces `frappe.has_permission(target_doctype, "read")` unless running under authorized admin context.
- **Cache Optimization**: Employs `frappe.get_cached_value()` to eliminate redundant SQL reads for repeated lookups within the same request lifecycle.

---

## 15. Date/Time Analysis

Date and time manipulation is critical for payment schedules, SLAs, and SLA breach tracking.

### Operations
1. `calculate`: Adds/subtracts days, weeks, months, or years from a base date (`nowdate()` or document date field).
2. `diff`: Computes integer difference between two dates in days, months, or years.
3. `format`: Formats date objects into custom display strings using `frappe.utils.format_date()`.

### Key Distinction
- Date **calculation** produces a valid ISO date object/string (`YYYY-MM-DD`).
- Date **formatting** produces a localized display string (`15-Aug-2026`). Formatting should be used ONLY for notifications/text display, NEVER for database query filters or date math operands.

---

## 16. Text Analysis

Text operations cover string formatting, slugification, casing, and template interpolation.

### Operations
1. `combine`: Concatenates two or more text values with optional delimiters.
2. `case`: Uppercase, lowercase, title case, slugify, or snake_case conversion.
3. `normalize`: Executes registered text normalization pipelines (`trim`, `strip_accents`, `clean_spaces`).
4. `format`: Formats strings or money amounts via template interpolation.

---

## 17. Number Analysis

Numeric calculations handle pricing, discounts, tax computations, and inventory thresholds.

### Operations
1. `math`: Basic arithmetic (`+`, `-`, `*`, `/`) with precision rounding (`precision`).
2. `round`: Rounds float values to specified decimal places or nearest integer.
3. `abs`: Computes absolute value of numeric inputs.

### Division by Zero Protection
`MathFormulaResolver` explicitly guards against division by zero:
```python
if self.math_op == "/":
    res = val_a / val_b if val_b != 0.0 else 0.0
```

---

## 18. System/Context Analysis

Rules frequently require session-level context or execution metadata.

### Exposed System Tokens
- `current_user`: Returns `frappe.session.user`.
- `user_roles`: Returns role list for current user via `frappe.get_roles()`.
- `has_role`: Evaluates boolean role check (`sys_role in user_roles`).
- `current_company`: Resolves default company from session defaults or `doc.company`.
- `today`: Returns `frappe.utils.nowdate()`.
- `now`: Returns `frappe.utils.now_datetime()`.

---

## 19. Conditional and Logical Expressions

In certain assignment or calculation scenarios, a value must be derived conditionally:
- **Coalesce / Fallback**: `coalesce(doc.shipping_address, doc.billing_address)`. Returns first non-null value.
- **Ternary Value**: `if doc.is_preferred_customer then 0.15 else 0.05`. Selects value based on condition.

These conditional value selectors belong inside the **Value Resolver** as value-producing primitives, distinct from the `Condition` Action Type which routes execution flow.

---

## 20. UI/UX Analysis

The frontend UI must provide intuitive, context-aware configuration controls:
- **Type Filtering**: `ValueResolverControl.vue` should filter available resolver strategies based on the target field's `fieldtype` (e.g., hiding string normalization when editing a `Date` field).
- **Inline Preview**: Display human-readable generated labels (e.g., `Date: posting_date + 30 days`) inside control badges.
- **Consumer-Specific UX**:
  - `Assignment`: Contextualized to target field type.
  - `Condition`: Highlights comparison operators and operand pickers.
  - `Query Filters`: Presents field-operator-value grid layout.

---

## 21. Backend/Frontend Contract Analysis

Serialization contracts between Vue 3 and Python must remain strict and unambiguous.

### Canonical FlexValue Payload Contract
```json
{
  "mode": "resolver",
  "family": "date_time",
  "operation": "calculate",
  "config": {
    "base_type": "doc_field",
    "base_field": "posting_date",
    "offset_value": 30,
    "offset_unit": "days",
    "offset_sign": "+"
  }
}
```

### Legacy Normalization
Backend `ValueResolver.compile_resolver_config()` automatically translates legacy payloads (`kind: "fetch"`, `kind: "child_aggregation"`, `kind: "date_formula"`) into canonical family/operation structures, preserving backward compatibility during migration.

---

## 22. Security Analysis

Security is paramount in no-code rule engines to prevent privilege escalation or Remote Code Execution (RCE).

### Security Boundaries
1. **No Unrestricted Code Execution**: Disable raw Jinja template rendering or unrestricted `eval()` in standard user modes.
2. **Safe Expression Evaluation**: Safe evaluation uses restricted globals, allowing only whitelist utilities (`frappe.utils.flt`, `frappe.utils.add_days`, `getdate`).
3. **Protected System Paths**: `AssignmentHandler` blocks mutation of system paths:
   ```python
   forbidden_prefixes = ("meta.", "frappe.", "rule.", "caller.")
   ```
4. **Read Permission Checking**: `LookupResolver` and `QueryRecordsHandler` enforce standard Frappe Document read permissions unless explicitly bypassed by a System Manager with a logged audit reason.

---

## 23. Performance Analysis

To maintain sub-millisecond rule execution overhead in high-throughput ERP environments:
- **Compiled Resolver Graphs**: `ValueResolver.compile()` parses configuration dictionaries once and outputs pure Python class instances (`CompiledResolver`).
- **Request-Local Caching**: `get_compiled_resolver()` caches compiled graphs in `frappe.local.flexirule_compiled_resolvers`, eliminating re-parsing during loops or bulk operations.
- **ORM Cache Utilization**: `LookupResolver` leverages `frappe.get_cached_value()` to eliminate duplicate database SELECT queries.
- **Collection Safeguards**: `MAX_COLLECTION_ROWS = 10000` bounds memory consumption during child table iterations.

---

## 24. Keep / Improve / Consolidate / Add / Remove / Defer

Every resolver strategy is classified below:

| Resolver Strategy / Feature | Classification | Action Required |
| :--- | :--- | :--- |
| `DateFormulaResolver` (`date_time.calculate`) | **Improve** | Generalize offset parameters to accept dynamic nested `FlexValue` inputs. |
| `DateDiffResolver` (`date_time.diff`) | **Keep** | Retain existing implementation; robust and fully tested. |
| `MathFormulaResolver` | **Improve** | Support nested resolver inputs for `field_b` and multi-operand arithmetic. |
| `StringFormulaResolver` (`text.combine`) | **Improve** | Generalize from 2-string concat to array string join with configurable separator. |
| `NormalizationResolver` | **Improve** | Align UI pipeline selection directly with backend `normalization.py` pipeline steps. |
| `FormatResolver` | **Keep** | Retain for string formatting and date/currency display generation. |
| `CollectionResolver` | **Consolidate** | Retain as single source of truth for child table operations; deprecate `ChildAggregationResolver`. |
| `LookupResolver` | **Consolidate** | Retain as unified lookup strategy; deprecate `FetchResolver` legacy alias. |
| `SystemContextResolver` | **Improve** | Add `current_company` token support. |
| `CoalesceResolver` / `TernaryResolver` | **Add** | Add fallback and conditional value selector resolvers. |
| Raw `SafeEvalResolver` in standard UI | **Remove** | Remove raw python expression input from standard UI mode; restrict to system manager advanced mode. |
| Complex AST Math Engine | **Defer** | Defer full mathematical AST parser to post-v1 releases. |

---

## 25. Prioritized Improvement Plan

### P0 — Required for Core Architecture (Release Candidate Critical)
1. **Consolidate Legacy Strategies**: Formally replace `FetchResolver` and `ChildAggregationResolver` with `LookupResolver` and `CollectionResolver`.
2. **Recursive Input Composition**: Refactor strategy constructors to compile nested `FlexValue` payloads using `ValueResolver.compile()`.
3. **Strict Parameterized Queries**: Ensure all `QueryRecordsHandler` filter values resolve to clean primitive types before ORM parameter binding.

### P1 — Required for Strong ERP Usability
1. **Coalesce & Ternary Resolvers**: Add `coalesce` (first non-null value) and `if-then-else` conditional value resolvers.
2. **Type-Aware UI Control**: Filter available resolver strategies in `FlexValueControl.vue` based on target DocField metadata.
3. **Session Company Context**: Add `current_company` token to `SystemContextResolver`.

### P2 — Valuable Extension
1. **Multi-String Join**: Expand string combination to join arbitrary text arrays with custom delimiters.
2. **Array Traversal in Lookups**: Support dot-notation link traversal (e.g., `doc.customer.territory.manager`).

### P3 — Future / Deferred
1. **Full AST Math Engine**: Complex algebraic formula parsing.
2. **External REST API Value Fetching**: Resolving values via third-party HTTP endpoints.

---

## 26. Proposed Target Architecture

The target architecture simplifies value resolution into six (6) core strategy families operating under unified compilation contracts:

```
FlexValue (Payload)
    │
    ├── Mode: Static / Variable / Expression
    │
    └── Mode: Resolver (Family / Operation)
           │
           ├── Family: date_time   (calculate, diff, format)
           ├── Family: math        (arithmetic, round, abs)
           ├── Family: text        (combine, case, normalize, format)
           ├── Family: collection  (count, sum, avg, min, max, filter, pluck, unique)
           ├── Family: lookup      (static_link, dynamic_link)
           └── Family: context     (user, company, today, now, role_check)
```

### Execution Flow
```
Action Handler (e.g., AssignmentHandler)
    │
    ├── 1. Fetch action plan row
    ├── 2. Pass operand payload to get_compiled_resolver()
    ├── 3. Execute resolver.resolve(context) → returns primitive
    └── 4. Apply action operator (e.g., set, increment) to target path
```

---

## 27. Recommended Resolver Taxonomy

The recommended final taxonomy consolidates existing fragmented strategies into six clean families:

1. `date_time`:
   - `calculate`: Add/subtract offset from base date.
   - `diff`: Calculate difference between two dates.
   - `format`: Format date for text display.
2. `math`:
   - `calculate`: Arithmetic operations (`+`, `-`, `*`, `/`).
   - `round`: Precision rounding.
3. `text`:
   - `combine`: Concatenate / join string values.
   - `case`: Case conversion (upper, lower, title, slug, snake).
   - `normalize`: Clean whitespace and special characters.
   - `format`: String/money template formatting.
4. `collection`:
   - `aggregate`: `sum`, `avg`, `min`, `max`, `count`.
   - `extract`: `pluck`, `unique`, `first`, `filter`.
5. `lookup`:
   - `record_value`: Fetch field value from linked record (static or dynamic link).
6. `context`:
   - `system_token`: Access session defaults (`user`, `company`, `today`, `now`, `role_check`).

---

## 28. Recommended Configuration Model

### Unified JSON Schema for Value Resolvers
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "mode": {
      "type": "string",
      "enum": ["static", "variable", "expression", "resolver"]
    },
    "family": {
      "type": "string",
      "enum": ["date_time", "math", "text", "collection", "lookup", "context", "logical"]
    },
    "operation": { "type": "string" },
    "config": {
      "type": "object",
      "additionalProperties": true
    }
  },
  "required": ["mode"]
}
```

---

## 29. Migration/Compatibility Considerations

1. **Zero Downtime Migration**: Existing legacy payload keys (`kind: "fetch"`, `kind: "child_aggregation"`, `kind: "date_formula"`) are transparently mapped to canonical `family`/`operation` structures inside `ValueResolver.compile_resolver_config()`.
2. **Database Patches**: Existing rule document configurations in MariaDB require no immediate schema breaking changes because backend compiler normalization bridges legacy shapes seamlessly.
3. **Deprecation Timeline**: Legacy aliases (`FetchResolver`, `ChildAggregationResolver`) will be formally deprecated in v1.1 following the v1.0 RC release.

---

## 30. Testing Strategy

1. **Unit Tests (`test_value_resolver_core.py`)**:
   - Verify all compiled strategy classes against mock execution contexts.
   - Test division by zero, null dates, missing linked documents, and empty collections.
2. **Complex Flow Tests (`test_value_resolvers_complex.py`)**:
   - Test nested resolver compositions (e.g., math formula containing child aggregation).
3. **Action Integration Tests (`test_assignment_resolver.py`, `test_query_records_filters.py`)**:
   - Test end-to-end execution of `AssignmentHandler`, `ConditionHandler`, and `QueryRecordsHandler` using resolved dynamic values.
4. **Security & Boundary Tests (`test_permissions.py`)**:
   - Verify `LookupResolver` throws `PermissionError` when non-admin session lacks read rights.

---

## 31. Documentation Requirements

1. **Developer Guide**: Document `CompiledResolver` interface and registration pattern for custom strategy extensions.
2. **User Guide / Desk Manual**: Provide visual examples for common ERPNext rule configurations (due date calculations, credit limit checks, child table total aggregations).
3. **Tooltips & Helper Text**: Embedded inline guidance inside `FlexValueControl.vue` and `ValueResolverControl.vue`.

---

## 32. Final Architectural Conclusions

The review confirms that FlexiRule's fundamental value resolution architecture is **conceptually sound, highly efficient, and properly aligned with Frappe Framework ORM principles**.

By enforcing strict boundaries between:
- **Value Resolver** (producing primitive values/objects),
- **Assignment Action Type** (executing batch field mutations),
- **Condition Action Type** (evaluating boolean predicates), and
- **Records Query / Query List** (building ORM database queries),

FlexiRule achieves excellent clarity and safety. Implementing the recommended consolidation of legacy strategies, adding recursive input composition, and formalizing semantic value typing will ensure FlexiRule achieves full **Release Candidate (RC) quality**.

---

## Appendix A — Current vs Proposed Capability Matrix

| Capability | Current Status | Proposed Target | Primary Consumer | Action Type / Operation | Architectural Gap | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Date Formula Calculation | Implemented | Improved | `AssignmentHandler` | `Assignment` | Offset cannot accept dynamic variable input | P1 |
| Date Difference Calculation | Implemented | Kept | `ConditionHandler` | `Condition` | None | P0 |
| Math Formula Arithmetic | Implemented | Improved | `AssignmentHandler` | `Assignment` | Operands restricted to field names / static constants | P1 |
| Text Concatenation | Implemented | Improved | `AssignmentHandler` | `Assignment` | Fixed 2-string limit | P2 |
| String Normalization | Implemented | Improved | `AssignmentHandler` | `Assignment` | UI selection disconnected from backend pipeline | P1 |
| String / Date Formatting | Implemented | Kept | `NotifyHandler` | `Notify` | None | P0 |
| Linked Record Lookup | Implemented | Consolidated | `AssignmentHandler` | `Assignment` | Legacy `FetchResolver` duplicate exists | P0 |
| Child Table Aggregation | Implemented | Consolidated | `AssignmentHandler` | `Assignment` | Legacy `ChildAggregationResolver` duplicate exists | P0 |
| Collection Filtering / Pluck | Implemented | Kept | `AssignmentHandler` | `Assignment` | None | P0 |
| Session System Context | Implemented | Improved | `QueryRecordsHandler` | `Query Records` | Missing `current_company` token | P1 |
| Coalesce / Fallback Value | Missing | Added | `AssignmentHandler` | `Assignment` | Cannot select first non-null value | P1 |
| Conditional Ternary Value | Missing | Added | `AssignmentHandler` | `Assignment` | Cannot evaluate if-then-else value in assignment | P1 |

---

## Appendix B — Value Resolver Consumer Matrix

| Value Resolver Capability | Assignment Action Type | Condition Action Type | Records Query → Query List | Shared Primitive? | Consumer-Specific Logic? | Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `VariableResolver` | Yes (operand) | Yes (operand) | Yes (filter value) | Yes | No | **Keep** as shared primitive. |
| `DateFormulaResolver` | Yes (due dates) | Yes (date checks) | Yes (date filters) | Yes | No | **Improve** to accept dynamic offsets. |
| `MathFormulaResolver` | Yes (totals) | Yes (thresholds) | Yes (range filters) | Yes | No | **Improve** to accept nested inputs. |
| `LookupResolver` | Yes (defaults) | Yes (credit checks) | Yes (relational filters) | Yes | No | **Consolidate** with legacy `fetch`. |
| `CollectionResolver` | Yes (aggregates) | Yes (row counts) | No | Yes | No | **Consolidate** with legacy `child_aggregation`. |
| `SystemContextResolver` | Yes (user audit) | Yes (role checks) | Yes (owner filters) | Yes | No | **Improve** with company token. |
| `ConditionEvaluator` | No (Row guard) | Yes (Predicate) | No | No | Yes (Condition Action) | **Keep Separate** in Condition subsystem. |
| Query Filter Formatting | No | No | Yes (ORM filters) | No | Yes (Query List) | **Keep Separate** in Query Records handler. |

---

## Appendix C — Target Use-Case Matrix

| Resolver | Target Use Case | Benchmark Example Rule | Consumer | Required Input | Expected Output | Current Status | Gap |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `date_time.calculate` | Due Date Offset | Set Sales Invoice due date = posting date + payment terms | `Assignment` | `base_date`, `offset_value` | `Date` string | Implemented | Offset must accept variable |
| `date_time.diff` | Overdue Aging | Overdue days check = today - posting date | `Condition` | `start_date`, `end_date` | `Integer` | Implemented | None |
| `lookup.record_value` | Customer Territory | Set Sales Order territory = Customer.territory | `Assignment` | `doctype`, `record_id`, `field` | `Link` string | Implemented | Direct lookup only; no chain |
| `collection.sum` | SO Grand Total | Set SO total = sum(items.amount) | `Assignment` | `child_table`, `target_field` | `Float` | Implemented | None |
| `collection.count` | Item Count Check | Verify order item count > 0 | `Condition` | `child_table`, `condition` | `Integer` | Implemented | None |
| `system_context` | User Filter | Query tasks where owner == current user | `Query List` | `sys_token: "user"` | `Link` (User) | Implemented | None |
| `coalesce` | Address Fallback | Shipping address = coalesce(shipping, billing) | `Assignment` | `value_list` | Primitive | Missing | Need `CoalesceResolver` |

---

## Appendix D — Source References

### Backend Modules
- `flexirule/ruleflow/core/value_resolver.py`: Unified compiler & runtime registry for `CompiledResolver` classes.
- `flexirule/ruleflow/core/action_handlers/assignment.py`: `AssignmentHandler` executing batch state mutations.
- `flexirule/ruleflow/core/action_handlers/condition.py`: `ConditionHandler` evaluating boolean condition expressions.
- `flexirule/ruleflow/core/action_handlers/query_records.py`: `QueryRecordsHandler` handling ORM queries and filter resolution.
- `flexirule/ruleflow/core/evaluator.py`: `ConditionEvaluator` implementing safe python condition checks.

### Frontend Components
- `flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue`: Universal dynamic value input component.
- `flexirule/public/js/flexirule/rule_builder/controls/ValueResolverControl.vue`: Resolver strategy configuration dialog.
- `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/strategies.js`: Strategy registration registry.
- `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/CollectionResolver.vue`: Vue component for child table collection operations.
- `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/components/LookupResolver.vue`: Vue component for cross-document lookups.

### Test Suites
- `flexirule/ruleflow/tests/test_value_resolver_core.py`: Unit tests for core resolvers.
- `flexirule/ruleflow/tests/test_assignment_resolver.py`: Integration tests for assignment value resolution.
- `flexirule/ruleflow/tests/test_value_resolvers_complex.py`: Integration tests for complex formulas and aggregations.
- `flexirule/ruleflow/tests/test_query_records_filters.py`: Integration tests for query filter value resolution.
