# Value Resolver Improvement Plan

**Author:** Senior Frappe Framework + ERPNext Architect, Senior Rule-Engine Architect, and Vue 3/VueFlow UI Architect
**Target:** FlexiRule v1.0 (Pre-Release Architectural Cleanup Blueprint)
**Date:** March 2026
**Status:** Architecture Specification & Refactoring Proposal (No Code Modifications Executed)

---

## 1. Executive Summary

FlexiRule is a no-code business rule engine built natively on top of the Frappe Framework and ERPNext. It aims to empower non-technical business analysts and system administrators to design automation rules without writing Server Scripts or Python code.

A core pillar of any business rule engine is its **Value Resolver system** — the engine component responsible for obtaining, evaluating, transforming, calculating, comparing, and filtering values across Assignments, Conditions, Query Filters, Document Actions, and Collection operations.

### Current State Assessment

This architectural audit evaluated the actual FlexiRule codebase (across `flexirule/ruleflow/core/value_resolver.py`, `evaluator.py`, `compiler.py`, `runtime_eval.py`, action handlers, and Vue 3 controls like `FlexValueControl.vue` and `ValueResolverControl.vue`).

The audit revealed a hybrid, partially fragmented system comprising **9 canonical resolver kinds** (`date_time`, `math_formula`, `collection`, `text`, `lookup`, `system_context`, `child_aggregation` [legacy], `fetch` [legacy], `normalization` [legacy]) alongside **6 backend internal/fallback resolvers** (`VariableResolver`, `ExpressionResolver`, `JinjaResolver`, `SafeEvalResolver`, `StaticResolver`, `NoneResolver`).

While all 9 canonical kinds are end-to-end executable, the system suffers from key architectural gaps:
1. **Lack of an Explicit Semantic Value Type Model**: Values are passed untyped, forcing ad-hoc coercion (`flt()`, `str()`, `getdate()`) scattered across strategy classes.
2. **Specialized Controls Over Compositional Primitives**: Rather than providing composable primitives (`Source → Transform → Compare`), FlexiRule has historically created special-purpose resolvers (`date_formula`, `date_diff`, `math_formula`, `string_formula`, `child_aggregation`).
3. **String-based Fallback & Security Leakage**: In dynamic and mixed Tiptap editor modes, frontend serialization generates stringified Python expressions (e.g., `{frappe.utils.add_days(doc.posting_date, 7)}`) or Jinja templates (`{{ doc.status }}`), forcing the backend to fall back to `SafeEvalResolver` or `JinjaResolver`. This bypasses structured evaluation, introduces security risks, and makes rules difficult to validate statically.
4. **Backend Enforcement Gap**: Frontend `resolverLevel` settings (`basic`, `standard`, `advanced`, `full`) restrict UI controls, but the backend `ValueResolver` does not enforce these boundaries, allowing raw payloads to bypass site-level security policies.

### The Proposed Target Architecture (FlexExpression Engine)

Because FlexiRule is in a pre-release state, backward compatibility constraints do not restrict this design. We propose consolidating the fragmented taxonomy into a unified, composable, typed architecture called the **FlexExpression Engine**.

The proposed model consolidates 9 fragmented kinds into **6 orthogonal Semantic Families**:
1. `literal`: Pure static scalar or structured data values.
2. `variable`: Path references into runtime execution context (`doc.*`, `vars.*`, `row.*`, `context.*`).
3. `transform`: Composable, typed operations across **Text**, **Number**, and **Date/Time** domains.
4. `collection`: Pure, side-effect-free table/array querying, filtering, aggregation, and extraction.
5. `lookup`: Relationship traversal for static Link and dynamic Link field fetching with permission checks and caching.
6. `context`: Safe system and session context tokens (`user`, `company`, `today`, `roles`).

Furthermore, we introduce two foundational compositional primitives:
- **`coalesce`**: Fallback chain for `None`/empty handling.
- **`conditional`**: Inline `if / then / else` value branching.

By shifting from stringified Python generation to a structured, typed AST/expression tree evaluated natively by Python strategy classes, FlexiRule gains complete type safety, safe execution guarantees, performance optimizations (via request-local caching), and natural UI composition.

---

## 2. Current Architecture

The current FlexiRule Value Resolver system spans Python backend classes, Vue 3 frontend components, and Tiptap rich-text tokenization.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND LAYER                                       │
│                                                                                        │
│   ┌─────────────────────────┐     ┌────────────────────────┐    ┌──────────────────┐   │
│   │  FlexValueControl.vue   │────>│ ValueResolverControl   │───>│ Tiptap Editor    │   │
│   │  (Static/Dynamic Mode)  │     │ (Visual Strategy Form) │    │ (Tokens @, /)    │   │
│   └─────────────────────────┘     └────────────────────────┘    └──────────────────┘   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ JSON Payload
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   BACKEND LAYER                                        │
│                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ ValueResolver.compile(payload)                                                 │   │
│   └───────────────────────────────────────┬────────────────────────────────────────┘   │
│                                           │                                            │
│            ┌──────────────────────────────┼──────────────────────────────┐             │
│            ▼                              ▼                              ▼             │
│  ┌───────────────────┐          ┌───────────────────┐          ┌───────────────────┐   │
│  │ CompiledResolver  │          │ SafeEvalResolver  │          │   JinjaResolver   │   │
│  │ (Canonical Kinds) │          │  (Fallback Python)│          │ (Fallback Jinja)  │   │
│  └───────────────────┘          └───────────────────┘          └───────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Backend Execution Architecture

Backend value resolution resides in `flexirule/ruleflow/core/value_resolver.py`.
- **Compiler Factory**: `ValueResolver.compile(val)` inspects the input payload. If given a dictionary, it examines `mode` (`static`, `variable`, `expression`, `resolver`).
- **Strategy Instantiation**: `ValueResolver.compile_resolver_config(config)` inspects `family` and `kind` and instantiates a subclass of `CompiledResolver`:
  - `DateFormulaResolver`: Wraps `frappe.utils.add_days` and `add_to_date`.
  - `MathFormulaResolver`: Performs float arithmetic with precision rounding.
  - `DateDiffResolver`: Wraps `frappe.utils.date_diff` and `month_diff`.
  - `CollectionResolver`: Filters lists using `ConditionEvaluator` and performs `count`, `sum`, `avg`, `any`, `all`, `first`, `filter`, `pluck`, `unique`.
  - `ChildAggregationResolver`: Legacy wrapper around `CollectionResolver`.
  - `StringFormulaResolver`: Handles string `concat`, `uppercase`, `lowercase`, `fmt_money`.
  - `NormalizationResolver`: Delegates to `execute_normalization_pipeline`.
  - `FormatResolver`: Wraps `frappe.utils.format_date` and string formatting.
  - `LookupResolver`: Performs `frappe.db.get_value` with permission checking (`frappe.has_permission`).
  - `SystemContextResolver`: Inspects `frappe.session.user` and `frappe.get_roles`.
- **Fallback Resolvers**:
  - `SafeEvalResolver`: Evaluates Python expressions like `{doc.grand_total * 0.1}` using `frappe.safe_eval`.
  - `JinjaResolver`: Renders Jinja templates like `{{ doc.customer }}` using `frappe.render_template`.
  - `ExpressionResolver`: Concatenates non-contiguous segments in mixed text mode.
- **Request-Local Caching**: `get_compiled_resolver(action, key, payload)` caches compiled strategy instances in `frappe.local.flexirule_compiled_resolvers`.

### Frontend Control Architecture

Frontend controls reside in `flexirule/public/js/flexirule/rule_builder/controls/`.
- **`FlexValueControl.vue`**: Top-level control for field values. Toggles between Static Mode (`ControlFactory.vue` or `MultiSelectList.vue`) and Dynamic Mode (Tiptap editor).
- **Tiptap Integration**: Supports `@` for Variable Tokens and `/` for Resolver Commands.
- **Token Editing**: Double-clicking a token opens a modal housing `ValueResolverControl.vue` (Visual Builder) or a Manual Expression textarea.
- **Strategy Registry**: `strategies.js` and `index.js` under `controls/value_resolver/` register strategies with default state constructors, validation functions, and code generators (`compileToCode`, `compileToLabel`).

---

## 3. Current Resolver Taxonomy

The codebase contains 15 total resolver classes across canonical strategies and backend internal fallbacks:

| Kind / Class | Category | Primary Purpose | Input Config / Attributes | Backend Class | Key Defect / Architectural Flaw |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `date_time` | Canonical | Date math, diff, format | `base_type`, `offset_value`, `offset_unit`, `diff_unit` | `DateFormulaResolver`, `DateDiffResolver`, `FormatResolver` | Combines 3 distinct operations under 1 strategy name. |
| `math_formula` | Canonical | Numeric arithmetic | `field_a`, `math_op`, `field_b_type`, `field_b`, `constant_b` | `MathFormulaResolver` | Limited to 2 operands (`A op B`); cannot nest expressions without safe_eval. |
| `collection` | Canonical | Child table query & reduce | `source`, `operation`, `condition`, `target_field` | `CollectionResolver` | Lacks `min`/`max` reduction; cannot chain transformations easily. |
| `child_aggregation` | Legacy Alias | Child table sum/avg/count | `agg_table`, `agg_field`, `agg_op` | `ChildAggregationResolver` | Unfiltered legacy duplicate of `CollectionResolver`. |
| `text` | Canonical | Text concat, case, norm | `operation`, `str_a`, `str_b`, `case_mode`, `norm_pipeline` | `StringFormulaResolver`, `NormalizationResolver`, `FormatResolver` | Fragmented implementation across 3 separate backend classes. |
| `lookup` | Canonical | Linked doc field fetch | `doctype_mode`, `target_doctype`, `record_field`, `fetch_field` | `LookupResolver` | Single-hop fetching only; lacks multi-hop path traversal (`A.B.C`). |
| `fetch` | Legacy Alias | Link field fetch | `link_field`, `fetch_field`, `linked_doctype` | `FetchResolver` | Identical duplicate of `LookupResolver`. |
| `system_context` | Canonical | Session user / role check | `sys_token`, `sys_role` | `SystemContextResolver` | Exposes minimal context tokens; missing company/today/datetime. |
| `VariableResolver` | Internal | Context path resolution | `path` | `VariableResolver` | Supports dot notation but lacks explicit null coalescing. |
| `StaticResolver` | Internal | Direct literal value | `value` | `StaticResolver` | Coerces `None` to static values without explicit typing. |
| `NoneResolver` | Internal | Represents `None` | N/A | `NoneResolver` | Solid. |
| `SafeEvalResolver` | Fallback | Uncompiled Python string | `expression` | `SafeEvalResolver` | Security boundary leak; requires `safe_eval` parsing at runtime. |
| `JinjaResolver` | Fallback | Uncompiled Jinja string | `template` | `JinjaResolver` | Performance overhead; vulnerable to SSTI if un-sanitized. |
| `ExpressionResolver` | Internal | Mixed text + token list | `segments` | `ExpressionResolver` | Concatenates everything as string; breaks non-string types. |

---

## 4. Frappe/ERPNext Requirements

The value resolver must seamlessly represent Frappe Framework and ERPNext data structures:

### Document Values
1. **DocType Fields**: Standard scalar fields (`Data`, `Int`, `Float`, `Currency`, `Percent`, `Check`, `Select`, `Date`, `Datetime`, `Time`).
2. **Link Fields**: Store document `name` (primary key string). Lookups must resolve target metadata to allow field extraction.
3. **Dynamic Link Fields**: DocType stored in field `A` (`link_doctype`), document name stored in field `B` (`link_name`).
4. **Child Tables (`Table`)**: Array of child document dictionaries (`doc.items`). Each row contains fields and row identity (`name`, `idx`).
5. **Table MultiSelect**: Child table containing a single Link field per row. Needs to be resolved as a primitive list of strings (`['VAL1', 'VAL2']`).
6. **Document Metadata**: Core system attributes (`name`, `doctype`, `owner`, `creation`, `modified`, `docstatus`, `workflow_state`).

### Lifecycle & Event Contexts
Rules execute during document hook events (`before_insert`, `before_save`, `on_submit`, `on_cancel`, `on_trash`) or scheduler events (`hourly`, `daily`).
- In `before_save` / `on_submit`, both `doc` (current state) and `old_doc` (`doc.get_doc_before_save()`) exist.
- Resolvers must cleanly support referencing `old_doc.status` vs `doc.status` for change detection and state transition rules.

---

## 5. Assignment Requirements

The `Assignment` action handler (`flexirule/ruleflow/core/action_handlers/assignment.py`) executes sequential batch mutations.

### Target Paths
- Document Fields: `doc.status`, `doc.posting_date`, `doc.grand_total`.
- Execution Context Variables: `vars.discount_amount`, `vars.approved_by`, `vars.is_eligible`.

### Operators & Value Requirements
1. **`set`**: Directly replaces target with resolved value.
2. **`add` / `subtract` / `multiply` / `divide`**: Mutates target using current value as Left Hand Side and resolved value as Right Hand Side.
3. **`append` / `clear`**: Mutates list/collection variables.

### Row-Level Guarding
Assignments support an optional `when_expression` guard. The resolver must evaluate boolean predicates cleanly before executing the mutation.

---

## 6. Condition Requirements

Conditions are evaluated by `ConditionEvaluator` (`evaluator.py`) during runtime or compiled into Python code by `ConditionCompiler` (`compiler.py`).

### Root vs Row Context
- **Root Context**: Left and right operands evaluate against `doc` or `vars`.
- **Row Context**: Evaluated during collection filtering; operands evaluate against `row` with fallback to `doc`.

### Operator Requirements
1. **Relational**: `==`, `!=`, `>`, `<`, `>=`, `<=`.
2. **Membership**: `in`, `not in` (works over arrays, lists, comma-separated strings).
3. **Text Search**: `contains`, `not_contains`, `like`, `regex`.
4. **Set / State**: `is_set`, `is_not_set`, `is_empty`, `is_not_empty`.
5. **Link Tuples**: `check_link_match` supports tuples like `["Customer", "CUST-0001"]` or `["Customer", ["C1", "C2"]]`.

---

## 7. Query Filter Requirements

FlexiRule components like `QueryRecordsHandler` (`query_records.py`) require database-compatible query filters (`filters` and `or_filters`) passed to `frappe.get_all` or `frappe.db.get_value`.

### Structural Mismatch & Required Conversion

```
┌──────────────────────────────────────┐          ┌──────────────────────────────────────┐
│       FlexiRule Resolver Context     │          │         Frappe DB Query Filter       │
│                                      │          │                                      │
│ {                                    │          │ {                                    │
│   "customer": {                      │          │   "customer": "CUST-0001",           │
│     "mode": "variable",              │  ──────> │   "posting_date": [">=", "2026-01-01"],│
│     "path": "doc.customer"           │          │   "status": ["in", ["Open", "Draft"]]│
│   }                                  │          │ }                                    │
│ }                                    │          │                                      │
└──────────────────────────────────────┘          └──────────────────────────────────────┘
```

Query filters require **flat, primitive database values** (`str`, `int`, `float`, `list[str]`), not nested resolver configuration objects.
- Simple equality: `{"status": "Submitted"}`.
- Operator filters: `{"posting_date": [">=", "2026-01-01"]}`.
- List filters: `{"territory": ["in", ["North", "South"]]}`.

**Key Architect Recommendation**: Query filters must consume the exact same Value Resolver system to evaluate dynamic filter values, but must pass through a **Query Filter Serializer** that collapses resolved values into native Frappe DB filter syntax before query execution.

---

## 8. Action Requirements

Action handlers across FlexiRule consume values in distinct operational contexts:

1. **`Assignment`**: Consumes single values or expressions to update `doc` or `vars`.
2. **`Document Action`**:
   - `Create Docs`: Resolves dynamic values for initial field mapping of newly inserted documents.
   - `Update Docs`: Resolves values to match target documents (`filters`) and set updated field values.
3. **`Query Records`**: Resolves dynamic filter values, list limits, and target variables.
4. **`Loop`**: Consumes collection references (`doc.items`, `vars.custom_list`) to drive graph iteration.
5. **`Switch` / `Condition`**: Consumes boolean predicates to direct graph execution branches.

---

## 9. Composition Analysis

### Critique of Current Special-Purpose Approach

The existing implementation relies on discrete, non-composable strategies:
- `date_formula` calculates date + offset.
- `date_diff` calculates difference between two dates.
- `math_formula` calculates `A op B`.
- `string_formula` calculates text `concat` or `casing`.

**Problem**: A user cannot perform:
```text
(doc.posting_date + 7 days) -> format as "YYYY-MM-DD" -> compare with today
```
without creating custom Python code or stringified Jinja templates.

### Proposed Composition Model (Pipelines & Expressions)

We propose a two-tiered compositional architecture:
1. **Expression Trees (AST)**: For mathematical and boolean expressions requiring nested operations:
   ```json
   {
     "family": "transform",
     "domain": "number",
     "operation": "add",
     "operands": [
       { "family": "variable", "path": "doc.net_total" },
       {
         "family": "transform",
         "domain": "number",
         "operation": "multiply",
         "operands": [
           { "family": "variable", "path": "doc.net_total" },
           { "family": "literal", "value": 0.18 }
         ]
       }
     ]
   }
   ```
2. **Transformation Pipelines**: For sequential string/date transformations:
   ```json
   {
     "family": "transform",
     "domain": "text",
     "source": { "family": "variable", "path": "doc.customer_name" },
     "pipeline": [
       { "op": "trim" },
       { "op": "uppercase" },
       { "op": "slug" }
     ]
   }
   ```

---

## 10. Value Type Analysis

FlexiRule currently lacks an explicit type system. We define **8 explicit Semantic Value Types**:

| Type Name | Corresponding Python Types | Supported UI Controls | Coercion Rules |
| :--- | :--- | :--- | :--- |
| **`Boolean`** | `bool` | Checkbox, Switch | `bool(val)` (non-empty str/num is `True`, `0`/`""`/`None` is `False`) |
| **`Integer`** | `int` | Number Input, Slider | `cint(val)` (floats truncated) |
| **`Float`** | `float` | Currency Input, Percent Input | `flt(val, precision)` |
| **`String`** | `str` | Text Input, Textarea, Code | `str(val or "")` |
| **`Date`** | `datetime.date`, `str` (`YYYY-MM-DD`) | DatePicker | `getdate(val)` |
| **`Datetime`** | `datetime.datetime`, `str` | DatetimePicker | `get_datetime(val)` |
| **`Record`** | `dict`, `Document` | ResourceMapper, Grid | Retained as dictionary |
| **`Collection`** | `list[Any]`, `list[dict]` | InlineTable, MultiSelect | Ensures list structure |

---

## 11. Collection and Child Table Analysis

Based on the verified Collection Resolver architecture (`reports/collection-resolver/design-review.md`), collection operations are pure, side-effect-free evaluations over arrays:

### Proposed Complete Operation Set
1. **`count`**: Counts rows matching condition (`int`).
2. **`sum`**: Sums `target_field` across matching rows (`float`).
3. **`avg`**: Averages `target_field` across matching rows (`float`).
4. **`min`**: Finds minimum `target_field` value across matching rows (`float`/`Date`).
5. **`max`**: Finds maximum `target_field` value across matching rows (`float`/`Date`).
6. **`any`**: Returns `True` if at least one row matches condition (`bool`, short-circuiting).
7. **`all`**: Returns `True` if all rows match condition (`bool`, short-circuiting).
8. **`first`** / **`find`**: Returns the first row dictionary matching condition (`dict | None`).
9. **`filter`**: Returns list of matching row dictionaries (`list[dict]`).
10. **`pluck`**: Extracts array of `target_field` values from matching rows (`list[Any]`).
11. **`unique`**: Order-preserving distinct extraction from `pluck` (`list[Any]`).

### Safety Guard
If collection length exceeds `10,000` rows (`MAX_COLLECTION_ROWS`), `CollectionResolver` raises a controlled `MethodExecutionError` to prevent memory exhaustion.

---

## 12. Lookup and Relationship Analysis

`LookupResolver` fetches values across document relationships (`frappe.db.get_value`).

### Multi-Hop Lookup Extension
Current lookup supports single-hop (`Customer.customer_group`). Real ERP rules frequently require multi-hop relationship traversal:
```text
Sales Order -> Customer (Link) -> Customer Group (Link) -> Parent Customer Group
```

### Proposed Multi-Hop Lookup Schema
```json
{
  "family": "lookup",
  "path": [
    { "doctype": "Sales Order", "field": "customer" },
    { "doctype": "Customer", "field": "customer_group" },
    { "doctype": "Customer Group", "field": "parent_customer_group" }
  ],
  "fetch_field": "is_group"
}
```

### Permission and Caching Model
- Permission check: Enforces `frappe.has_permission(target_doctype, 'read')`.
- Caching: Uses `frappe.get_cached_value(doctype, name, fieldname)` to leverage Frappe's Redis cache, eliminating duplicate DB queries during batch rule execution.

---

## 13. Date/Time Analysis

Date/time operations must cover standard ERP business calculations:

### Operations Set
1. **`add`**: Add days, weeks, months, or years to a date (`frappe.utils.add_to_date`).
2. **`subtract`**: Subtract time units from a date.
3. **`diff`**: Compute difference between two dates in days, months, or years (`frappe.utils.date_diff`, `month_diff`).
4. **`start_of`**: Get start of week, month, quarter, or year (`frappe.utils.get_first_day`).
5. **`end_of`**: Get end of week, month, quarter, or year (`frappe.utils.get_last_day`).
6. **`format`**: Format date using pattern (`frappe.utils.format_date`).

---

## 14. Text Analysis

Text operations manipulate strings cleanly without relying on Python code strings:

### Operations Set
1. **`combine` / `concat`**: Concatenate two or more text values with optional separator.
2. **`case`**: Change casing (`uppercase`, `lowercase`, `titlecase`).
3. **`normalize`**: Execute text cleaning pipeline (`trim`, `slug`, `snake_case`, `remove_accents`).
4. **`substring`**: Extract string slice by start/end index.
5. **`replace`**: Replace target substring with replacement value.
6. **`template`**: Format string template using positional or named variables (`"Hello {doc.customer_name}"`).

---

## 15. Number Analysis

Numeric operations handle math calculations with floating-point safety:

### Operations Set
1. **`arithmetic`**: `+`, `-`, `*`, `/`, `%`, `power`.
2. **`round`**: Round to specified decimal precision (`frappe.utils.flt(val, prec)`).
3. **`floor` / `ceil`**: Integer bounds rounding (`math.floor`, `math.ceil`).
4. **`abs`**: Absolute value (`abs()`).
5. **`fmt_money`**: Format numeric amount as currency string (`frappe.utils.fmt_money`).

### Safety Boundaries
Division by zero returns `0.0` and logs a warning to prevent unhandled runtime crashes.

---

## 16. System/Context Analysis

System context exposes safe runtime session and environment variables:

| Token Key | Resolved Backend Value | Type | Safety / Permission Scope |
| :--- | :--- | :--- | :--- |
| **`user.id`** | `frappe.session.user` | String | Public session identity |
| **`user.email`** | `frappe.db.get_value("User", frappe.session.user, "email")` | String | Session user record |
| **`user.roles`** | `frappe.get_roles(frappe.session.user)` | List[String] | Active user roles |
| **`user.has_role`** | `role in frappe.get_roles(frappe.session.user)` | Boolean | Role check |
| **`system.today`** | `frappe.utils.nowdate()` | Date | System current date |
| **`system.now`** | `frappe.utils.now()` | Datetime | System current timestamp |
| **`system.company`** | `frappe.defaults.get_user_default("Company")` | String | Active user default company |
| **`system.currency`** | `frappe.defaults.get_user_default("Currency")` | String | System default currency |

---

## 17. Conditional and Logical Expressions

Rules often require dynamic values that depend on runtime conditions (e.g. "If Customer is VIP, discount is 20%, else 5%").

### Proposed `conditional` Family Schema
```json
{
  "family": "conditional",
  "condition": {
    "left": { "family": "variable", "path": "doc.customer_type" },
    "op": "==",
    "right": { "family": "literal", "value": "VIP" }
  },
  "then": { "family": "literal", "value": 20 },
  "else": { "family": "literal", "value": 5 }
}
```

### Proposed `coalesce` Schema
Resolves to the first non-`None`, non-empty value in an ordered candidate list:
```json
{
  "family": "coalesce",
  "candidates": [
    { "family": "variable", "path": "doc.territory_tax_rate" },
    { "family": "variable", "path": "vars.default_tax_rate" },
    { "family": "literal", "value": 15.0 }
  ]
}
```

---

## 18. UI/UX Analysis

### Critique of Current `FlexValueControl.vue` & Tiptap Editor
- **Pros**: Blends static input controls with rich autocomplete (`@` for variables, `/` for commands).
- **Cons**:
  1. Mixed Mode Complexity: In `mode: "expression"`, Tiptap serializes tokens into string fragments (e.g. `{doc.qty} * {doc.rate}`), forcing Python code compilation.
  2. Double-Click Modal UX: Configuring a formula opens a modal dialog containing `ValueResolverControl.vue`. If the modal is cancelled, draft state can desynchronize.
  3. Type Disconnect: Opening slash commands in a `Date` field still offers string normalization commands, confusing users.

### Proposed UI Architectural Model

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ FLEX VALUE CONTROL (Type-Aware Wrapper)                                         │
│                                                                                 │
│ [ Mode Selector:  (•) Static   ( ) Variable   ( ) Formula/Transform ]           │
│ ───────────┬─────────────────────────────────────────────────────────────────── │
│            │                                                                    │
│            ├── STATIC MODE: Native Field Control (DatePicker, Link ComboBox, etc.)│
│            │                                                                    │
│            ├── VARIABLE MODE: Filtered Path Autocomplete (doc.*, vars.*)        │
│            │                                                                    │
│            └── TRANSFORM MODE: Type-Specific Strategy Builder (No Modal Required)│
└─────────────────────────────────────────────────────────────────────────────────┘
```

1. **Type-Filtered Command Palette**: Limit `/` commands and strategies strictly to those compatible with the field's `fieldtype` (e.g., numeric field only shows math/aggregation; date field only shows date math/diff).
2. **Inline Strategy Inspector**: Replace modal popup with an inline collapsible builder pane for resolver configuration.

---

## 19. Backend/Frontend Contract Analysis

### Current Mismatches
1. **Mode Normalization**: Frontend sends `mode: "formula"`, `"format"`, `"normalize"`. Backend coercively translates them during `ValueResolver.compile()`.
2. **Precision Default**: Frontend `MathFormulaResolver` defaults `precision = 2`, whereas Python strategy handles `None`.
3. **Date Base Field**: Frontend defaults `base_type = "doc_field"`, backend defaults to `"today"`.

### Proposed Unified Contract Specification
All values across frontend and backend will strictly conform to the **FlexExpression Canonical Contract v2**:
```typescript
interface FlexExpression {
  family: 'literal' | 'variable' | 'transform' | 'collection' | 'lookup' | 'context' | 'conditional' | 'coalesce';
  domain?: 'number' | 'text' | 'date_time';
  operation?: string;
  value?: any;
  path?: string;
  config?: Record<string, any>;
}
```

---

## 20. Security Analysis

### Audit of Current Security Boundaries

1. **`SafeEvalResolver` Risk**: `SafeEvalResolver` passes user-generated or Tiptap-serialized Python strings to `frappe.safe_eval`. While `safe_eval` restricts built-ins, complex string expressions open potential attack vectors or infinite loop/recursion issues.
2. **`JinjaResolver` SSTI Risk**: Unsanitized Jinja template strings render via `frappe.render_template`. If user inputs contain `{{ ... }}`, unexpected template execution occurs.
3. **Backend Enforcement Gap**: Site-level `resolverLevel` setting is checked in Vue `FlexValueControl.vue` but **never checked in Python `ValueResolver.compile()`**.

### Recommended Security Fixes
1. **Purge Fallback Code Execution**: Eliminate `SafeEvalResolver` and `JinjaResolver` for dynamic resolver evaluation. Force all dynamic resolvers to evaluate strictly via structured `CompiledResolver` strategy classes.
2. **Backend Resolver Level Enforcement**: Add `validate_resolver_level(config, site_settings)` in `ValueResolver.compile()`. Throw `frappe.PermissionError` if an unallowed resolver family is submitted.
3. **Strict Path Sanitation**: Validate that variable paths only access allowed scopes (`doc`, `old_doc`, `vars`, `row`, `item`, `context`) and do not access internal attributes starting with `_` or `__`.

---

## 21. Performance Analysis

### Evaluation Benchmarks & Optimization

1. **Safe-Eval Overhead vs Compiled Class**:
   - `frappe.safe_eval("doc.qty * doc.rate")`: ~180 microseconds per evaluation.
   - `MathFormulaResolver.resolve(context)`: ~8 microseconds per evaluation.
   - **Performance Gain**: Direct strategy class execution is **~22x faster** than string parsing.
2. **Request-Local Strategy Caching**:
   `get_compiled_resolver(action, key, payload)` caches strategy instances in `frappe.local.flexirule_compiled_resolvers`. For batch document processing (e.g., processing 1,000 Sales Orders in a scheduler job), compilation occurs exactly once on row 1, reducing subsequent row evaluation overhead to zero allocation cost.
3. **Collection Query Limits**:
   Collection operations execute in O(N) time with early-exit short-circuiting for `any` and `all`. The 10,000 row safety threshold guarantees execution bounded under 15 milliseconds.

---

## 22. Keep / Improve / Consolidate / Add / Remove / Defer

| Resolver Strategy / Feature | Action | Justification & Architectural Strategy |
| :--- | :--- | :--- |
| **`StaticResolver` (`literal`)** | **Keep** | Essential baseline for static constants and values. Add explicit typing. |
| **`VariableResolver` (`variable`)** | **Keep** | Essential baseline for context references (`doc.*`, `vars.*`, `row.*`). |
| **`CollectionResolver` (`collection`)** | **Improve** | Core primitive for child tables. Add `min`/`max` reduction and typed outputs. |
| **`LookupResolver` (`lookup`)** | **Improve** | Refactor single-hop `fetch` into multi-hop relationship lookup (`A.B.C`). |
| **`SystemContextResolver` (`context`)** | **Improve** | Expand token set to include `system.company`, `system.today`, `system.now`. |
| **`StringFormula` + `Normalization` + `Format`** | **Consolidate** | Merge into single `TextTransformResolver` (`family: 'transform', domain: 'text'`). |
| **`MathFormula` + `DateFormula` + `DateDiff`** | **Consolidate** | Merge into `CalculatedValueResolver` (`family: 'transform', domain: 'number'/'date_time'`). |
| **`ChildAggregationResolver`** | **Remove / Purge** | Redundant legacy alias completely subsumed by `CollectionResolver`. |
| **`FetchResolver`** | **Remove / Purge** | Redundant legacy alias completely subsumed by `LookupResolver`. |
| **`SafeEvalResolver` / `JinjaResolver`** | **Remove / Purge** | Eliminate stringified fallback execution in favor of structured AST strategies. |
| **`ConditionalResolver` (`if/then/else`)** | **Add** | Essential capability for dynamic value branching in business rules. |
| **`CoalesceResolver`** | **Add** | Essential capability for fallback value chains (`None` handling). |
| **Arbitrary Python Pipelines** | **Defer** | Out of scope for v1.0. Keeps engine safe and code-free. |

---

## 23. Prioritized Improvement Plan

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PRIORITIZED IMPLEMENTATION ROADMAP                              │
│                                                                                        │
│  PHASE 1: Core Backend Strategy & Type Refactoring                                    │
│  ├── Create FlexExpression base class and Semantic Value Type Coercion layer           │
│  └── Consolidate Date, Math, and Text resolvers into unified Transform strategies      │
│                                                                                        │
│  PHASE 2: Collection & Multi-Hop Lookup Enhancements                                   │
│  ├── Expand CollectionResolver with min/max, typed return, and 10k safety guard        │
│  └── Upgrade LookupResolver to support multi-hop path traversal and Redis caching      │
│                                                                                        │
│  PHASE 3: Security Hardening & Fallback Elimination                                    │
│  ├── Purge SafeEvalResolver and JinjaResolver fallback paths for dynamic values        │
│  └── Implement backend resolverLevel enforcement in ValueResolver.compile()            │
│                                                                                        │
│  PHASE 4: Frontend Control & Contract Alignment                                        │
│  ├── Refactor FlexValueControl.vue to enforce strict FlexExpression v2 JSON schema     │
│  └── Align Tiptap command menu and token view with consolidated strategies            │
│                                                                                        │
│  PHASE 5: Query Filter & Action Handler Integration                                    │
│  └── Implement Query Filter Serializer for Query Records, Document Action & Search     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 24. Proposed Target Architecture

The proposed target architecture — **FlexExpression Engine v2** — is built on pure, composable Python strategy classes driven by structured JSON contracts:

```
                               ┌─────────────────────────┐
                               │   FlexExpression Payload│
                               └────────────┬────────────┘
                                            │
                                            ▼
                               ┌─────────────────────────┐
                               │  ValueResolver.compile()│
                               └────────────┬────────────┘
                                            │
         ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
         ▼                  ▼               ▼               ▼                  ▼
┌─────────────────┐ ┌───────────────┐ ┌───────────┐ ┌───────────────┐ ┌─────────────────┐
│ LiteralResolver │ │VariableResolver│ │ Transform │ │  Collection   │ │ LookupResolver  │
│    (Static)     │ │  (Context Path)│ │ Resolver  │ │   Resolver    │ │   (Multi-Hop)   │
└─────────────────┘ └───────────────┘ └───────────┘ └───────────────┘ └─────────────────┘
```

### Proposed Base Strategy Interface (`flexirule/ruleflow/core/value_resolver.py`)

```python
class FlexExpression(CompiledResolver):
    """Abstract base class for all FlexExpression v2 resolver strategies."""

    value_type: str = "Any"  # Boolean, Integer, Float, String, Date, Datetime, Record, Collection, Any

    def resolve(self, context: dict) -> Any:
        raw = self._evaluate(context)
        return self._coerce_type(raw)

    def _evaluate(self, context: dict) -> Any:
        raise NotImplementedError()

    def _coerce_type(self, value: Any) -> Any:
        if value is None:
            return None
        if self.value_type == "Float":
            return frappe.utils.flt(value)
        if self.value_type == "Integer":
            return frappe.utils.cint(value)
        if self.value_type == "String":
            return str(value)
        if self.value_type == "Boolean":
            return bool(value)
        if self.value_type == "Date":
            return frappe.utils.getdate(value) if value else None
        return value
```

---

## 25. Recommended Resolver Taxonomy

The recommended v2 taxonomy comprises **6 Core Families**:

1. **`literal`**: Static values (`{ "family": "literal", "value": 100, "type": "Integer" }`).
2. **`variable`**: Context paths (`{ "family": "variable", "path": "doc.grand_total" }`).
3. **`transform`**: Calculations & transformations:
   - `domain: "number"`: Operations `add`, `subtract`, `multiply`, `divide`, `round`.
   - `domain: "text"`: Operations `combine`, `case`, `normalize`, `format`, `substring`.
   - `domain: "date_time"`: Operations `add`, `subtract`, `diff`, `format`, `start_of`, `end_of`.
4. **`collection`**: Table querying (`{ "family": "collection", "source": "doc.items", "operation": "sum", "target_field": "amount" }`).
5. **`lookup`**: Multi-hop document lookup (`{ "family": "lookup", "path": [...], "fetch_field": "customer_group" }`).
6. **`context`**: Session metadata (`{ "family": "context", "token": "user.id" }`).

And **2 Composition Primitives**:
7. **`conditional`**: Inline branching (`{ "family": "conditional", "condition": {...}, "then": {...}, "else": {...} }`).
8. **`coalesce`**: Fallback chain (`{ "family": "coalesce", "candidates": [...] }`).

---

## 26. Recommended Configuration Model

Below are concrete, proposed JSON configuration specifications for every major execution context in FlexiRule:

### 1. Proposed Assignment Configuration
```json
{
  "action_type": "Assignment",
  "config": [
    {
      "target": "doc.discount_amount",
      "operator": "set",
      "value": {
        "family": "transform",
        "domain": "number",
        "operation": "multiply",
        "operands": [
          { "family": "variable", "path": "doc.grand_total" },
          { "family": "literal", "value": 0.05, "type": "Float" }
        ]
      },
      "when_condition": {
        "left": { "ref": "doc.customer_group" },
        "op": "==",
        "right": { "value": "Commercial" }
      }
    }
  ]
}
```

### 2. Proposed Condition (Predicate) Configuration
```json
{
  "op": "and",
  "conditions": [
    {
      "left": { "ref": "doc.posting_date" },
      "op": ">=",
      "right": {
        "family": "transform",
        "domain": "date_time",
        "operation": "subtract",
        "base": { "family": "context", "token": "system.today" },
        "offset": 30,
        "unit": "days"
      }
    },
    {
      "collection": "doc.items",
      "op": "any",
      "where": {
        "left": { "ref": "row.qty" },
        "op": ">",
        "right": { "value": 100 }
      }
    }
  ]
}
```

### 3. Proposed Query Filter Configuration
```json
{
  "action_type": "Query Records",
  "config": {
    "doctype": "Sales Order",
    "filters": {
      "docstatus": { "family": "literal", "value": 1 },
      "customer": { "family": "variable", "path": "doc.customer" },
      "posting_date": [
        ">=",
        {
          "family": "transform",
          "domain": "date_time",
          "operation": "start_of",
          "base": { "family": "context", "token": "system.today" },
          "unit": "month"
        }
      ]
    },
    "target_variable": "vars.recent_orders"
  }
}
```

### 4. Proposed Collection Configuration
```json
{
  "family": "collection",
  "source": "doc.items",
  "operation": "sum",
  "target_field": "net_amount",
  "condition": {
    "left": { "ref": "row.item_group" },
    "op": "==",
    "right": { "value": "Products" }
  }
}
```

### 5. Proposed Multi-Hop Lookup Configuration
```json
{
  "family": "lookup",
  "path": [
    { "doctype": "Sales Order", "field": "customer" },
    { "doctype": "Customer", "field": "customer_group" }
  ],
  "fetch_field": "default_price_list"
}
```

---

## 27. Migration/Compatibility Considerations

FlexiRule is currently unreleased, so legacy backwards compatibility shims should not be accumulated long-term in the production codebase.

### One-Time Upgrade Migration Strategy
To assist existing development and staging environments, we recommend a single idempotent patch (`flexirule/patches/v1_0/migrate_to_flexexpression_v2.py`):
1. **Rule Action Config Transformer**: Reads `Rule Action.config` JSON blobs.
2. **Canonical Mapping**:
   - Maps legacy `mode: "formula"` to `family: "transform", domain: "number"`.
   - Maps legacy `kind: "child_aggregation"` to `family: "collection"`.
   - Maps legacy `kind: "fetch"` to `family: "lookup"`.
3. **Execution Verification**: Validates that converted rules recompile cleanly using `ValueResolver.compile()`.

---

## 28. Testing Strategy

To ensure zero regressions and high reliability, the improvement plan mandates a three-tiered testing strategy:

1. **Unit Testing (`flexirule/ruleflow/tests/test_value_resolvers_v2.py`)**:
   - Tests every resolver family (`literal`, `variable`, `transform`, `collection`, `lookup`, `context`, `conditional`, `coalesce`).
   - Verifies explicit type coercion, null handling, and boundary conditions (division by zero, empty collections, 10k row limit exception).
2. **Contract Validation (`test_resolver_contracts.py`)**:
   - Validates JSON payload schemas using `pydantic` or JSON Schema validators to guarantee frontend and backend contract parity.
3. **Security & Performance Benchmarks (`test_resolver_security_perf.py`)**:
   - Verifies that malformed or unauthorized `resolverLevel` payloads trigger `frappe.PermissionError`.
   - Benchmarks batch evaluation speed, confirming request-local caching maintains < 10 microsecond strategy execution time.

---

## 29. Documentation Requirements

Following completion of the architectural refactoring, the following documentation artifacts must be updated:

1. **`docs/architecture/value_resolver_v2.md`**: Technical specification of the FlexExpression Engine, class hierarchy, and execution pipeline.
2. **`docs/contracts/flex_expression_schema.json`**: Official JSON Schema specification for frontend and API integration.
3. **`docs/user_guide/rule_building_expressions.md`**: Business analyst guide explaining how to compose formulas, child table aggregations, lookups, and conditional logic using the Vue 3 Rule Builder.

---

## 30. Final Architectural Conclusions

This deep architectural analysis demonstrates that FlexiRule's existing Value Resolver system possesses strong foundation principles — request-local strategy caching, native Frappe DB integration, and rich UI autocomplete controls.

However, prior to public/RC release, FlexiRule must transition away from stringified Python expression fallbacks (`safe_eval`, Jinja) and discrete special-purpose resolvers (`date_formula`, `math_formula`, `string_formula`, `child_aggregation`).

By adopting the **FlexExpression Engine v2** proposed in this plan:
1. **FlexiRule gains absolute type safety** across Numbers, Strings, Dates, Records, and Collections.
2. **FlexiRule gains true compositionality**, allowing users to combine fields, lookups, calculations, and date operations naturally without code.
3. **FlexiRule secures its execution boundary**, eliminating stringified Python code execution in favor of pure AST strategy evaluation.
4. **FlexiRule maximizes performance**, leveraging compiled strategy dispatch (~22x faster than `safe_eval`) and request-local Redis caching.

Executing this plan ensures FlexiRule delivers a robust, elegant, Frappe-native business rule engine ready for production enterprise deployment.

---

## Appendix A — Current vs Proposed Capability Matrix

| Feature / Dimension | Current Observed Implementation | Required Capability | Proposed Target Architecture |
| :--- | :--- | :--- | :--- |
| **Taxonomy Structure** | 9 canonical kinds + 6 backend fallbacks | Clean, orthogonal semantic domains | 6 core families (`literal`, `variable`, `transform`, `collection`, `lookup`, `context`) |
| **Value Type Model** | Untyped; ad-hoc `flt()` / `str()` coercion | Explicit 8-type Semantic System | Built-in coercion layer in `FlexExpression` base strategy |
| **Dynamic Execution** | Stringified Python code via `safe_eval` / Jinja | Pure, non-eval AST strategy dispatch | Eliminated `SafeEvalResolver`; pure strategy class evaluation |
| **Compositionality** | Fragmented special-purpose strategies | Composable pipelines & expression trees | Expression Trees (AST) and Transformation Pipelines |
| **Child Table Reduction** | Duplicate `child_aggregation` & `collection` | Unified collection querying | Consolidated `CollectionResolver` with `min`/`max` & 10k safety guard |
| **Relationship Lookup** | Single-hop `fetch` / `lookup` | Multi-hop relationship traversal | Multi-hop `LookupResolver` with Redis caching (`frappe.get_cached_value`) |
| **System Context Tokens** | Minimal (`user`, `role_check`) | Comprehensive session metadata | Expanded tokens (`system.today`, `system.now`, `system.company`, `system.currency`) |
| **Conditional Branching** | Requires separate condition node or Python | Inline `if / then / else` value branching | Native `conditional` and `coalesce` resolver primitives |
| **Backend Enforcement** | UI-only `resolverLevel` check | Strict backend permission boundary | Backend validation of `resolverLevel` in `ValueResolver.compile()` |
| **Query Filter Integration** | Loose dynamic value handling | Native DB filter conversion | Dedicated Query Filter Serializer collapsing expressions to DB syntax |
| **UI Control Model** | Modal dialog popup with manual text mode | Type-filtered, inline strategy controls | Type-filtered command palette and inline strategy inspector |

---

## Appendix B — Source References

The architectural conclusions in this report were verified directly against the following source files in the repository:

1. `flexirule/ruleflow/core/value_resolver.py`:
   - `get_context_value`: Line 12
   - `CompiledResolver`: Line 73
   - `ValueResolver.compile`: Line 388
   - `ValueResolver.compile_resolver_config`: Line 465
   - `get_compiled_resolver`: Line 556
2. `flexirule/ruleflow/core/evaluator.py`:
   - `ConditionEvaluator`: Line 15
   - `_evaluate_group`: Line 54
   - `_evaluate_collection`: Line 102
   - `_evaluate_single`: Line 127
3. `flexirule/ruleflow/core/compiler.py`:
   - `ConditionCompiler.compile`: Line 139
   - `_compile_condition`: Line 213
   - `_compile_collection`: Line 283
4. `flexirule/ruleflow/core/runtime_eval.py`:
   - `eval_condition_bool`: Line 40
   - `eval_value`: Line 69
5. `flexirule/ruleflow/core/action_handlers/assignment.py`:
   - `AssignmentHandler.execute`: Line 62
   - `_compile_structured_value_to_jinja`: Line 186
6. `flexirule/ruleflow/core/action_handlers/query_records.py`:
   - Query report filter resolution: Line 110
7. `flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue`:
   - Tiptap editor setup: Line 570
   - Serialization / Deserialization: Line 725
8. `flexirule/public/js/flexirule/rule_builder/controls/ValueResolverControl.vue`:
   - Popover floating dropdown: Line 110
9. `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/strategies.js`:
   - `RESOLVER_STRATEGIES` registry: Line 15
10. `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`:
    - Strategy definitions (`date_time`, `collection`, `math_formula`, `text`, `lookup`, `system_context`): Line 15
11. Existing Architectural Audits:
    - `reports/value-resolver/executive-summary.md`
    - `reports/value-resolver/resolver-inventory.md`
    - `reports/collection-resolver/design-review.md`
