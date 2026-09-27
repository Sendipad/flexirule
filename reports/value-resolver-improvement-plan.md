# Value Resolver Improvement Plan

**Author:** Senior Frappe Framework + ERPNext Architect, Senior Rule-Engine Architect, and Vue 3/VueFlow UI Architect
**Target:** FlexiRule v1.0 (Pre-Release Architectural Cleanup Blueprint)
**Date:** March 2026
**Status:** Architecture Specification & Refactoring Proposal (No Code Modifications Executed)

---

## 1. Executive Summary

FlexiRule is a no-code business rule engine built natively on top of the Frappe Framework and ERPNext. It enables business analysts and system administrators to create automation rules without writing Server Scripts or Python code.

The **Value Resolver system** is the engine component responsible for obtaining, calculating, transforming, and producing values.

### Important Architectural Boundary Clarification

A primary finding of this architectural review is that **Assignments**, **Conditions**, and **Query Filters** are **NOT** Value Resolver families or resolver primitives:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              VALUE RESOLVER SYSTEM                              │
│                                                                                 │
│   Produces typed, resolved values or collection evaluation results              │
│   (literal, variable, transform, collection, lookup, context)                   │
└────────────────────────┬────────────────────────┬───────────────────────────────┘
                         │                        │
                         ▼                        ▼
┌────────────────────────────────┐       ┌────────────────────────────────────────┐
│     CONDITION EVALUATION       │       │         ASSIGNMENT RULE ACTION         │
│                                │       │                                        │
│  Evaluates operands using      │       │  Applies resolved values to target     │
│  comparison operators          │       │  document fields or context variables  │
└────────────────────────────────┘       └────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    QUERY RECORDS / QUERY LIST RULE ACTION                       │
│                                                                                 │
│   Serializes resolved dynamic filter values into native Frappe DB query filters │
└─────────────────────────────────────────────────────────────────────────────────┘
```

1. **Assignments (`AssignmentHandler`)**: Downstream consumer. Manages target paths (`doc.status`, `vars.total`), mutation operators (`set`, `add`), and execution guards (`when_expression`). It consumes Value Resolver expressions for its input operands.
2. **Conditions (`ConditionEvaluator` / `ConditionCompiler`)**: Downstream consumer. Evaluates comparison operators (`==`, `!=`, `>`, `<`, `in`, `contains`) over left and right operands. It consumes resolved values to produce boolean decision logic.
3. **Query Filters (`QueryRecordsHandler`)**: Downstream consumer. Configures database query filters (`filters`, `or_filters`) for `Query Records` / `Query List`. It consumes Value Resolver expressions to resolve dynamic filter values before converting them into native Frappe database query arguments.

### Current State Assessment

Deep source inspection across `flexirule/ruleflow/core/value_resolver.py`, `evaluator.py`, `compiler.py`, `runtime_eval.py`, action handlers, and Vue 3 components (`FlexValueControl.vue`, `ValueResolverControl.vue`) reveals a fragmented taxonomy of **9 canonical resolver kinds** (`date_time`, `math_formula`, `collection`, `text`, `lookup`, `system_context`, `child_aggregation` [legacy], `fetch` [legacy], `normalization` [legacy]) alongside **6 backend internal/fallback resolvers** (`VariableResolver`, `ExpressionResolver`, `JinjaResolver`, `SafeEvalResolver`, `StaticResolver`, `NoneResolver`).

The current architecture is fragmented because it uses operation-specific resolver classes with rigid, non-composable schemas (e.g., `field_a`, `field_b`, `base_field`, `fmt_field`, `norm_field`, `record_field`). This indicates the absence of a **generic expression composition model**.

Furthermore, in dynamic and mixed Tiptap editor modes, frontend serialization generates stringified Python expressions (e.g., `{frappe.utils.add_days(doc.posting_date, 7)}`), forcing the backend to fall back to `SafeEvalResolver` or `JinjaResolver`.

### Proposed Target Architecture

FlexiRule is pre-release software. We do not need to preserve obsolete architecture, legacy modes, or old stored data for backward compatibility.

We propose consolidating the fragmented taxonomy into a **small, coherent, typed, composable Value Resolver architecture** comprising **6 Core Value Families**:
1. **`literal`**: Static data values.
2. **`variable`**: Path references into runtime context (`doc.*`, `vars.*`, `row.*`, `context.*`).
3. **`transform`**: Composable, typed operations across **Text**, **Number**, and **Date/Time** domains.
4. **`collection`**: Pure, side-effect-free table/array querying, filtering, aggregation, and extraction.
5. **`lookup`**: Relationship traversal across Link fields with permission checks and Redis caching.
6. **`context`**: Safe system and session context tokens (`user.id`, `system.today`, `system.company`).

And **2 Composition Primitives**:
- **`coalesce`**: Fallback chain for `None`/empty handling.
- **`conditional`**: Inline `if / then / else` value branching.

By shifting from stringified Python generation to pure, structured AST/expression trees evaluated natively by Python strategy classes, FlexiRule gains complete type safety, safe execution guarantees, performance optimizations, and natural UI composition.

---

## 2. Current Architecture

The current FlexiRule Value Resolver system spans Python backend classes, Vue 3 frontend components, and Tiptap rich-text tokenization.

### Source Evidence Breakdown

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

#### Backend Compiler & Runtime (`value_resolver.py`)
- **Factory Entry Point**: `ValueResolver.compile(val)` inspects the input payload. If given a dictionary, it examines `mode` (`static`, `variable`, `expression`, `resolver`).
- **Strategy Selection**: `ValueResolver.compile_resolver_config(config)` inspects `family` and `kind` and instantiates a subclass of `CompiledResolver`:
  - `DateFormulaResolver`: Wraps `frappe.utils.add_days` and `add_to_date`.
  - `MathFormulaResolver`: Performs float arithmetic with precision rounding over `field_a` and `field_b`/`constant_b`.
  - `DateDiffResolver`: Wraps `frappe.utils.date_diff` and `month_diff`.
  - `CollectionResolver`: Filters lists using `ConditionEvaluator` and performs `count`, `sum`, `avg`, `any`, `all`, `first`, `filter`, `pluck`, `unique`.
  - `ChildAggregationResolver`: Legacy duplicate around `CollectionResolver`.
  - `StringFormulaResolver`: Handles string `concat`, `uppercase`, `lowercase`, `fmt_money`.
  - `NormalizationResolver`: Delegates to `execute_normalization_pipeline`.
  - `FormatResolver`: Wraps `frappe.utils.format_date` and string formatting.
  - `LookupResolver`: Performs `frappe.db.get_value` with permission checking (`frappe.has_permission`).
  - `SystemContextResolver`: Inspects `frappe.session.user` and `frappe.get_roles`.
- **Fallback Resolvers**:
  - `SafeEvalResolver`: Evaluates string expressions like `{doc.grand_total * 0.1}` using `frappe.safe_eval`.
  - `JinjaResolver`: Renders Jinja templates like `{{ doc.customer }}` using `frappe.render_template`.
  - `ExpressionResolver`: Concatenates non-contiguous segments in mixed text mode.
- **Request-Local Caching**: `get_compiled_resolver(action, key, payload)` caches compiled strategy instances in `frappe.local.flexirule_compiled_resolvers`.

#### Frontend Control Architecture (`FlexValueControl.vue`, `ValueResolverControl.vue`)
- **`FlexValueControl.vue`**: Top-level control for field values. Toggles between Static Mode (`ControlFactory.vue` or `MultiSelectList.vue`) and Dynamic Mode (Tiptap editor).
- **Tiptap Integration**: Supports `@` for Variable Tokens and `/` for Resolver Commands.
- **Token Editing**: Double-clicking a token opens a modal housing `ValueResolverControl.vue` (Visual Builder) or a Manual Expression textarea.
- **Strategy Registry**: `strategies.js` and `index.js` under `controls/value_resolver/` register strategies with default state constructors, validation functions, and code generators (`compileToCode`, `compileToLabel`).

---

## 3. Current Resolver Taxonomy

The codebase contains 15 total resolver classes across canonical strategies and backend internal fallbacks:

| Kind / Class | Category | Primary Purpose | Input Config / Attributes | Backend Class | Architectural Flaw / Failure Point |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `date_time` | Canonical | Date math, diff, format | `base_type`, `offset_value`, `offset_unit`, `diff_unit` | `DateFormulaResolver`, `DateDiffResolver`, `FormatResolver` | Combines 3 distinct operations under 1 strategy name. |
| `math_formula` | Canonical | Numeric arithmetic | `field_a`, `math_op`, `field_b_type`, `field_b`, `constant_b` | `MathFormulaResolver` | Rigid 2-operand schema (`A op B`); cannot nest calculations without `safe_eval`. |
| `collection` | Canonical | Child table query & reduce | `source`, `operation`, `condition`, `target_field` | `CollectionResolver` | Lacks `min`/`max` reduction; cannot chain transformations easily. |
| `child_aggregation` | Legacy Alias | Child table sum/avg/count | `agg_table`, `agg_field`, `agg_op` | `ChildAggregationResolver` | Unfiltered legacy duplicate of `CollectionResolver`. |
| `text` | Canonical | Text concat, case, norm | `operation`, `str_a`, `str_b`, `case_mode`, `norm_pipeline` | `StringFormulaResolver`, `NormalizationResolver`, `FormatResolver` | Fragmented implementation across 3 separate backend classes. |
| `lookup` | Canonical | Linked doc field fetch | `doctype_mode`, `target_doctype`, `record_field`, `fetch_field` | `LookupResolver` | Single-hop fetching only; lacks multi-hop path traversal (`A.B.C`). |
| `fetch` | Legacy Alias | Link field fetch | `link_field`, `fetch_field`, `linked_doctype` | `FetchResolver` | Identical duplicate of `LookupResolver`. |
| `system_context` | Canonical | Session user / role check | `sys_token`, `sys_role` | `SystemContextResolver` | Exposes minimal context tokens; missing company/today/datetime. |
| `VariableResolver` | Internal | Context path resolution | `path` | `VariableResolver` | Supports dot notation but lacks explicit null coalescing. |
| `StaticResolver` | Internal | Direct literal value | `value` | `StaticResolver` | Coerces `None` to static values without explicit typing. |
| `NoneResolver` | Internal | Represents `None` | N/A | `NoneResolver` | Sound baseline. |
| `SafeEvalResolver` | Fallback | Uncompiled Python string | `expression` | `SafeEvalResolver` | Security boundary leak; requires `safe_eval` parsing at runtime. |
| `JinjaResolver` | Fallback | Uncompiled Jinja string | `template` | `JinjaResolver` | Performance overhead; vulnerable to SSTI if un-sanitized. |
| `ExpressionResolver` | Internal | Mixed text + token list | `segments` | `ExpressionResolver` | Concatenates everything as string; breaks non-string types. |

---

## 4. Frappe/ERPNext Requirements

The value resolver must represent Frappe Framework and ERPNext data structures natively:

### Document Values
1. **DocType Fields**: Standard scalar fields (`Data`, `Int`, `Float`, `Currency`, `Percent`, `Check`, `Select`, `Date`, `Datetime`, `Time`).
2. **Link Fields**: Store document `name` (primary key string). Lookups must resolve target metadata to allow field extraction.
3. **Dynamic Link Fields**: DocType stored in field `A` (`link_doctype`), document name stored in field `B` (`link_name`).
4. **Child Tables (`Table`)**: Array of child document dictionaries (`doc.items`). Each row contains fields and row identity (`name`, `idx`).
5. **Table MultiSelect**: Child table containing a single Link field per row. Needs to be resolved as a primitive list of strings (`['VAL1', 'VAL2']`).
6. **Document Metadata**: Core system attributes (`name`, `doctype`, `owner`, `creation`, `modified`, `docstatus`, `workflow_state`).

### Lifecycle & Event Contexts
Rules execute during document hook events (`before_insert`, `before_save`, `on_submit`, `on_cancel`, `on_trash`) or scheduler events (`hourly`, `daily`).
- In `before_save` / `on_submit`, both `doc` (current state) and `old_doc` (`doc.get_doc_before_save()`) exist in context.
- Resolvers must support referencing `old_doc.status` vs `doc.status` for change detection and state transition rules.

---

## 5. Assignment Requirements (Integration Boundary)

The `Assignment` action handler (`flexirule/ruleflow/core/action_handlers/assignment.py`) executes batch state mutations.

### Assignment Fields Consuming Value Resolver
1. **Target Path (`target`)**: Path string (`doc.status`, `vars.total_amount`).
2. **Mutation Operator (`operator`)**: `set`, `add`, `subtract`, `multiply`, `divide`, `append`, `clear`.
3. **Value Payload (`value`)**: Consumes Value Resolver expressions. `AssignmentHandler` invokes `get_compiled_resolver(action, f"assign_{idx}", assignment.get("value"))` to resolve operand values.
4. **Row Guard (`when_expression`)**: Optional condition/predicate guard evaluated before applying mutation.

### Type Conversion Boundary
`AssignmentHandler._set_value()` applies the resolved value to `doc` or `vars`.
- `Value Resolver` is responsible for producing a clean, typed value.
- `Assignment Action` is responsible for setting the target field or context variable.

---

## 6. Condition Requirements (Integration Boundary)

Conditions are evaluated by `ConditionEvaluator` (`evaluator.py`) during runtime or compiled into Python code by `ConditionCompiler` (`compiler.py`).

### Condition Structure
- **Left Operand (`left`)**: Consumes a Value Resolver expression (`{ "ref": "doc.grand_total" }` or `{ "family": "transform", ... }`).
- **Operator (`op`)**: Comparison operator (`==`, `!=`, `>`, `<`, `>=`, `<=`, `in`, `not in`, `contains`, `is_set`, `is_not_set`, `is_empty`, `is_not_empty`).
- **Right Operand (`right`)**: Consumes a Value Resolver expression.
- **Link Tuples**: `check_link_match(lhs, rhs, op)` supports tuple values like `["Customer", "CUST-0001"]`.

### Context Scoping
- **Root Context**: Left and right operands resolve against `doc` or `vars`.
- **Row Context**: When evaluating collection filters (`_evaluate_collection`), `ConditionEvaluator` sets `row` scope context (`row.qty`).

---

## 7. Query Filter Requirements (Integration Boundary)

Query filters in `QueryRecordsHandler` (`query_records.py`) configure database query arguments (`filters`, `or_filters`) passed to `frappe.get_list` or `frappe.db.get_value`.

### End-to-End Execution Trace
```
┌──────────────────────────────────────┐          ┌──────────────────────────────────────┐
│       FlexiRule Resolver Context     │          │         Frappe DB Query Filter       │
│                                      │          │                                      │
│ {                                    │          │ [                                    │
│   "customer": {                      │  ──────> │   ["customer", "=", "CUST-0001"],    │
│     "mode": "variable",              │          │   ["posting_date", ">=", "2026-01-01"]│
│     "path": "doc.customer"           │          │ ]                                    │
│   }                                  │          │                                      │
│ }                                    │          │                                      │
└──────────────────────────────────────┘          └──────────────────────────────────────┘
```

1. **Resolution Phase**: `QueryRecordsHandler._resolve_filters_with_context()` traverses the filter payload and invokes `get_compiled_resolver()` on dynamic value objects.
2. **Normalization Phase**: `QueryRecordsHandler._normalize_filters_for_backend()` converts the resolved dictionary or tuple structure into flat Frappe filter tuples: `[doctype, field, operator, value]`.
3. **Database Execution**: The normalized filter array is passed directly to `frappe.get_list(reference_doctype, filters=filters)`.

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

## 9. Composition Analysis (Proving True Composability)

To evaluate whether the architecture supports true composition, we trace three representative real-world examples in the current implementation vs the proposed architecture:

### Example A — Scalar Transformation
**Use Case**: `doc.amount → number calculation → round → assignment`

- **Current Implementation**:
  - *Payload*: `MathFormulaResolver` schema: `{ "field_a": "doc.amount", "math_op": "*", "field_b_type": "constant", "constant_b": 1.18, "precision": 2 }`.
  - *Backend Compilation*: Instantiates `MathFormulaResolver`.
  - *Runtime Flow*: `MathFormulaResolver.resolve()` computes `flt(val_a * 1.18, precision)`.
  - *Breakage / Limit*: Single-step math works, but if the user needs `(doc.amount + doc.shipping) * 1.18 -> round`, the rigid `field_a / field_b` schema fails. The frontend is forced to generate a raw string expression `{frappe.utils.flt((doc.amount + doc.shipping) * 1.18, 2)}` for `SafeEvalResolver`.
- **Proposed Architecture**:
  - *Payload*: Nested `transform` AST:
    ```json
    {
      "family": "transform",
      "domain": "number",
      "operation": "round",
      "precision": 2,
      "operands": [
        {
          "family": "transform",
          "domain": "number",
          "operation": "multiply",
          "operands": [
            {
              "family": "transform",
              "domain": "number",
              "operation": "add",
              "operands": [
                { "family": "variable", "path": "doc.amount" },
                { "family": "variable", "path": "doc.shipping" }
              ]
            },
            { "family": "literal", "value": 1.18 }
          ]
        }
      ]
    }
    ```
  - *Fix*: Replaces `SafeEvalResolver` with nested strategy evaluation, preserving structured execution.

---

### Example B — Lookup + Transformation
**Use Case**: `doc.customer → lookup customer → customer_group → text transformation → assignment`

- **Current Implementation**:
  - *Payload*: User attempts to configure `lookup` + `text` transform.
  - *Current Flaw*: `LookupResolver` only fetches a single field string from DB (`frappe.db.get_value("Customer", doc.customer, "customer_group")`). It cannot pipe that output directly into `NormalizationResolver` without writing a custom Python expression string or storing intermediate results in a `vars` variable.
- **Proposed Architecture**:
  - *Payload*:
    ```json
    {
      "family": "transform",
      "domain": "text",
      "operation": "normalize",
      "pipeline": ["trim", "uppercase"],
      "source": {
        "family": "lookup",
        "target_doctype": "Customer",
        "record_field": "doc.customer",
        "fetch_field": "customer_group"
      }
    }
    ```
  - *Fix*: The `source` property of any `transform` strategy accepts any inner `FlexExpression` (including `lookup`), enabling seamless composition.

---

### Example C — Collection Pipeline
**Use Case**: `doc.items → filter (qty > 10) → pluck (amount) → sum → compare`

- **Current Implementation**:
  - *Payload*: `CollectionResolver` config: `{ "kind": "collection", "source": "doc.items", "operation": "sum", "target_field": "amount", "condition": { "left": { "ref": "row.qty" }, "op": ">", "right": { "value": 10 } } }`.
  - *Backend Compilation*: Instantiates `CollectionResolver`.
  - *Runtime Flow*: Evaluates `CollectionResolver.resolve()`, which iterates over `doc.items`, filters rows matching `row.qty > 10`, extracts `row.amount`, and computes `sum()`.
  - *Analysis*: `CollectionResolver` already supports inline filtering + plucking + aggregation in a single pass. However, if the user wants to take that sum and round or format it before assignment, composition breaks because `CollectionResolver` cannot be nested inside `FormatResolver`.
- **Proposed Architecture**:
  - *Payload*:
    ```json
    {
      "family": "transform",
      "domain": "number",
      "operation": "round",
      "precision": 2,
      "operands": [
        {
          "family": "collection",
          "source": "doc.items",
          "operation": "sum",
          "target_field": "amount",
          "condition": {
            "left": { "ref": "row.qty" },
            "op": ">",
            "right": { "value": 10 }
          }
        }
      ]
    }
    ```
  - *Fix*: Wraps collection aggregations cleanly inside numeric or text transformations.

---

## 10. Collection Architecture Analysis

Collections represent arrays of dictionaries (`doc.items`, `vars.custom_list`).

### Collection Pipeline Conceptualization

```
Collection Source (doc.items)
       │
       ▼
  Filter Row Predicate (row.qty > 10)
       │
       ▼
  Project / Pluck Field (row.amount)
       │
       ▼
  Aggregate Reduction (sum / avg / min / max / count)
```

### Analysis of `ChildAggregationResolver`
Source inspection shows `ChildAggregationResolver` (`value_resolver.py:317`) is an older, unfiltered wrapper that instantiates `CollectionResolver(source=self.agg_table, operation=self.agg_op, target_field=self.agg_field)`. It lacks condition filtering support.

**Architectural Decision**: `ChildAggregationResolver` is a redundant legacy duplicate and will be **removed**. All collection operations will execute via `CollectionResolver`.

---

## 11. Lookup and Relationship Analysis

`LookupResolver` fetches values across document relationships using `frappe.db.get_value`.

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

## 12. Date/Time Analysis

Date/time operations handle standard ERP business calculations:

### Operations Set
1. **`add`**: Add days, weeks, months, or years to a date (`frappe.utils.add_to_date`).
2. **`subtract`**: Subtract time units from a date.
3. **`diff`**: Compute difference between two dates in days, months, or years (`frappe.utils.date_diff`, `month_diff`).
4. **`start_of`**: Get start of week, month, quarter, or year (`frappe.utils.get_first_day`).
5. **`end_of`**: Get end of week, month, quarter, or year (`frappe.utils.get_last_day`).
6. **`format`**: Format date using pattern (`frappe.utils.format_date`).

---

## 13. Text Analysis

Text operations manipulate strings cleanly without relying on Python code strings:

### Operations Set
1. **`combine` / `concat`**: Concatenate two or more text values with optional separator.
2. **`case`**: Change casing (`uppercase`, `lowercase`, `titlecase`).
3. **`normalize`**: Execute text cleaning pipeline (`trim`, `slug`, `snake_case`).
4. **`substring`**: Extract string slice by start/end index.
5. **`replace`**: Replace target substring with replacement value.
6. **`template`**: Format string template using positional or named variables (`"Hello {doc.customer_name}"`).

---

## 14. Number Analysis

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

## 15. System/Context Analysis

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

## 16. Conditional and Logical Expressions

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

## 17. UI/UX Analysis

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

## 18. Backend/Frontend Contract Analysis

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

## 19. Type System Re-Evaluation

The type system must bridge **Runtime Value Types** and **Frappe DocField Types**:

| Frappe DocField Fieldtype | Semantic Runtime Value Type | Supported Resolver Operations |
| :--- | :--- | :--- |
| `Data`, `Text`, `Long Text`, `Select` | **`String`** | `concat`, `uppercase`, `lowercase`, `trim`, `slug`, `replace` |
| `Int` | **`Integer`** | `add`, `subtract`, `multiply`, `divide`, `abs` |
| `Float`, `Currency`, `Percent` | **`Float`** | `add`, `subtract`, `multiply`, `divide`, `round`, `fmt_money` |
| `Check` | **`Boolean`** | Logical comparisons, `conditional` |
| `Date` | **`Date`** | `add_days`, `add_to_date`, `date_diff`, `start_of`, `end_of` |
| `Datetime` | **`Datetime`** | `add_to_date`, `diff`, `format_date` |
| `Link`, `Dynamic Link` | **`String` / `Reference`** | `lookup` |
| `Table` | **`Collection[Record]`** | `count`, `sum`, `avg`, `min`, `max`, `any`, `all`, `first`, `filter`, `pluck` |
| `Table MultiSelect` | **`Collection[String]`** | `count`, `any`, `all`, `filter` |

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

### Strategy Dispatch Optimization & Request-Local Caching

1. **Direct Strategy Dispatch vs String Parsing**: Direct Python strategy execution (`MathFormulaResolver.resolve(context)`) eliminates AST parsing overhead incurred by `frappe.safe_eval`.
2. **Request-Local Strategy Caching**:
   `get_compiled_resolver(action, key, payload)` caches strategy instances in `frappe.local.flexirule_compiled_resolvers`. For batch document processing (e.g., processing 1,000 Sales Orders in a scheduler job), compilation occurs exactly once on row 1, reducing subsequent row evaluation overhead to zero allocation cost.
3. **Collection Query Limits**:
   Collection operations execute in O(N) time with early-exit short-circuiting for `any` and `all`. The 10,000 row safety threshold guarantees execution bounded under reasonable memory limits.

---

## 22. Feature Justification & Classification

Every proposed addition or refactoring is evaluated against actual source code evidence:

1. **`conditional` (`if/then/else`)**: **Justified (Add)**. Source evidence: `AssignmentHandler` currently relies on raw Python strings or Jinja for conditional assignment values.
2. **`coalesce`**: **Justified (Add)**. Source evidence: Handlers frequently fall back across `doc.field`, `vars.field`, or static default values when primary fields are `None`.
3. **Multi-Hop Lookup**: **Justified (Improve)**. Source evidence: Single-hop `LookupResolver` forces users to create intermediate variables for nested link fields (`SO -> Customer -> Group`).
4. **`min` / `max` Collection Reduction**: **Justified (Improve)**. Source evidence: `CollectionResolver` already supports `sum`, `avg`, `count`; adding `min`/`max` completes standard aggregation set.
5. **`substring` / `replace` / `floor` / `ceil` / `abs`**: **Deferred**. No immediate source evidence requiring them in v1 core; defer to avoid feature creep.

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
   - `domain: "text"`: Operations `combine`, `case`, `normalize`, `format`.
   - `domain: "date_time"`: Operations `add`, `subtract`, `diff`, `format`, `start_of`, `end_of`.
4. **`collection`**: Table querying (`{ "family": "collection", "source": "doc.items", "operation": "sum", "target_field": "amount" }`).
5. **`lookup`**: Multi-hop document lookup (`{ "family": "lookup", "path": [...], "fetch_field": "customer_group" }`).
6. **`context`**: Session metadata (`{ "family": "context", "token": "user.id" }`).

And **2 Composition Primitives**:
7. **`conditional`**: Inline branching (`{ "family": "conditional", "condition": {...}, "then": {...}, "else": {...} }`).
8. **`coalesce`**: Fallback chain (`{ "family": "coalesce", "candidates": [...] }`).

---

## 26. Recommended Configuration Model

Below are concrete JSON configuration specifications for every major execution context in FlexiRule:

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

## 27. Direct Pre-Release Cleanup Strategy

FlexiRule is currently unreleased. We do not preserve obsolete resolver payloads, legacy modes, or old stored data for backward compatibility. The architecture will be consolidated cleanly before public release.

---

## 28. Testing Strategy

1. **Unit Testing (`flexirule/ruleflow/tests/test_value_resolvers_v2.py`)**:
   - Tests every resolver family (`literal`, `variable`, `transform`, `collection`, `lookup`, `context`, `conditional`, `coalesce`).
   - Verifies explicit type coercion, null handling, and boundary conditions (division by zero, empty collections, 10k row limit exception).
2. **Contract Validation (`test_resolver_contracts.py`)**:
   - Validates JSON payload schemas using `pydantic` or JSON Schema validators to guarantee frontend and backend contract parity.
3. **Security Benchmarks (`test_resolver_security.py`)**:
   - Verifies that malformed or unauthorized `resolverLevel` payloads trigger `frappe.PermissionError`.

---

## 29. Documentation Requirements

1. **`docs/architecture/value_resolver_v2.md`**: Technical specification of the FlexExpression Engine, class hierarchy, and execution pipeline.
2. **`docs/contracts/flex_expression_schema.json`**: Official JSON Schema specification for frontend and API integration.
3. **`docs/user_guide/rule_building_expressions.md`**: Business analyst guide explaining how to compose formulas, child table aggregations, lookups, and conditional logic using the Vue 3 Rule Builder.

---

## 30. Final Decision Table

The decision table below summarizes the disposition for every existing and proposed resolver concept:

| Concept | Current Source Evidence | Architectural Role | Keep | Consolidate | Remove | Defer |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **`static` / `literal`** | `StaticResolver` (`value_resolver.py:84`) | Value Source | **X** | | | |
| **`variable`** | `VariableResolver` (`value_resolver.py:93`) | Value Source | **X** | | | |
| **`date_time` (`DateFormula`)** | `DateFormulaResolver` (`value_resolver.py:102`) | Value Transform | | **X** | | |
| **`date_time` (`DateDiff`)** | `DateDiffResolver` (`value_resolver.py:195`) | Value Transform | | **X** | | |
| **`math_formula`** | `MathFormulaResolver` (`value_resolver.py:144`) | Value Transform | | **X** | | |
| **`string_formula`** | `StringFormulaResolver` (`value_resolver.py:348`) | Value Transform | | **X** | | |
| **`normalization`** | `NormalizationResolver` (`value_resolver.py:382`) | Value Transform | | **X** | | |
| **`format`** | `FormatResolver` (`value_resolver.py:417`) | Value Transform | | **X** | | |
| **`collection`** | `CollectionResolver` (`value_resolver.py:236`) | Collection Pipeline | **X** | | | |
| **`child_aggregation`** | `ChildAggregationResolver` (`value_resolver.py:317`) | Legacy Collection Duplicate | | | **X** | |
| **`lookup`** | `LookupResolver` (`value_resolver.py:460`) | Relationship Traversal | **X** | | | |
| **`fetch`** | `FetchResolver` (`value_resolver.py:532`) | Legacy Lookup Duplicate | | | **X** | |
| **`system_context`** | `SystemContextResolver` (`value_resolver.py:444`) | Context Source | **X** | | | |
| **`SafeEvalResolver`** | `SafeEvalResolver` (`value_resolver.py:560`) | Uncompiled Python Fallback | | | **X** | |
| **`JinjaResolver`** | `JinjaResolver` (`value_resolver.py:542`) | Uncompiled Jinja Fallback | | | **X** | |
| **`ExpressionResolver`** | `ExpressionResolver` (`value_resolver.py:575`) | Mixed Text Concatenator | | **X** | | |
| **`conditional` (`if/then/else`)**| Missing; users forced into `safe_eval` | Value Primitive | **X** | | | |
| **`coalesce`** | Missing; ad-hoc fallback handling in handlers | Value Primitive | **X** | | | |
| **Multi-Hop Lookup** | `LookupResolver` single-hop limit | Relationship Traversal | **X** | | | |
| **`min` / `max` Reduction** | Missing from `CollectionResolver` | Collection Pipeline | **X** | | | |
| **`substring` / `replace` / `abs`**| Generic string/math functions | Deferred Operations | | | | **X** |

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
   - Query Records filter resolution & normalization: Line 572
7. `flexirule/public/js/flexirule/rule_builder/controls/FlexValueControl.vue`:
   - Tiptap editor setup: Line 570
   - Serialization / Deserialization: Line 725
8. `flexirule/public/js/flexirule/rule_builder/controls/ValueResolverControl.vue`:
   - Popover floating dropdown: Line 110
9. `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/strategies.js`:
   - `RESOLVER_STRATEGIES` registry: Line 15
10. `flexirule/public/js/flexirule/rule_builder/controls/value_resolver/index.js`:
    - Strategy definitions (`date_time`, `collection`, `math_formula`, `text`, `lookup`, `system_context`): Line 15
