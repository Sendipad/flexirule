# Fetch Records Field Selection and Result Shapes — Design

**Base:** `feat/fetch-records-mode`  
**Working branch:** `feat/fetch-records-field-selection-20261011`  
**Status:** Design/implementation specification; no production compatibility requirement for experimental Fetch Records payloads.

## Goal

Expose the field-selection capabilities of the installed Frappe `frappe.qb.get_query()` API through an understandable visual builder. The UI should author semantic configuration, not SQL fragments, and should serialize to the native `fields` shape only at the adapter boundary.

## Result modes

Use a single required `result_shape` enum, with a deterministic default:

1. **Document names** (default): return `[{"name": "…"}, …]`. Hide field-selection and expression controls. Configure the native query to select only `name`.
2. **Whole documents**: return parent DocType fields with child-table fields embedded as arrays. Use native `fields="*"` for parent fields and structured child selections (or the exact supported native equivalent); do not fetch every child field implicitly unless that is explicitly the selected whole-document behavior.
3. **Selected fields — flat rows**: select configured fields and expressions, with each result row a flat dict. Linked fields use dot notation and aliases where needed. Child-table dot notation can multiply parent rows.
4. **Selected fields — embedded child tables**: parent fields and child-table selections are represented as a structured field selection, e.g. `{"items": ["item_code", "qty"]}`, allowing Frappe to return child rows nested under their parent.
5. **Flattened rows**: explicitly select fields from parent/link/child tables into a flat row set. Clearly explain that selecting child fields with dot notation may duplicate parent values across child rows and does not return nested child arrays.

Do not confuse modes 3 and 5: selected flat fields is a deliberate projection over a parent result, while flattened rows explicitly signals join/row-expansion semantics for child-table selections. If the implementation finds these are semantically identical in the installed Frappe version, consolidate them rather than maintaining duplicate modes with no behavioral distinction.

## Field selection model

Use a discriminated, semantic field specification; do not store SQL strings as the primary editable representation:

- `kind: "field"`: `field_path`, optional `alias`.
- `kind: "function"`: `function`, typed `arguments`, required/optional `alias` depending on function and output mode.
- Child selections: `kind: "child_table"`, `fieldname`, and nested child field specs.
- Wildcard selection is a mode-level choice, not an ordinary field row.

The backend adapter compiles semantic specifications to the native `fields` forms accepted by `frappe.qb.get_query()` (strings, function dictionaries, and child-table dictionaries). Validation rejects unknown field paths, invalid child table fieldnames, duplicate output aliases, unsupported functions, invalid arity, and malformed arguments before query execution.

## Visual builder

- Field rows have a navigable DocType field picker, path display, optional editable alias, and remove/reorder actions.
- Selecting a Link field permits choosing a target field via dot notation and clearly labels the path as a linked-document field.
- Selecting a Table field offers an explicit **Embed child rows** action and a nested child-field editor. A separate **Flatten child rows** choice selects dot-notation fields and warns about row multiplication.
- Expression rows choose from an allowlisted function catalog, then show function-specific typed argument pickers and alias. Do not expose arbitrary function names or raw SQL entry as the normal path.
- Provide a read-only result-shape preview and concise examples that update with the selected mode.
- Hide field/expression controls in Document names mode; reveal them for the other modes. Whole documents should guide users through parent and child selections without requiring manual expression syntax.
- Reuse FlexiRule's field navigation, ControlFactory, translation functions, and existing query-filter tree where they fit. New controls are appropriate where existing controls cannot express nested field specs or typed function arguments cleanly.

## Function catalog

Start from functions confirmed by the target Frappe version and its tests/docs, not merely the supplied illustrative list. Include the demonstrated aggregation functions (`COUNT`, `SUM`, `AVG`, `MAX`, `MIN`) and scalar functions (`ABS`, `IFNULL`, `CONCAT`, `EXTRACT`, `NOW`) only where native support is verified. Represent function names in canonical uppercase internally. Arguments are field references, string/numeric literals, or special typed arguments (e.g. EXTRACT unit); do not accept arbitrary raw SQL through a text input. Treat `COUNT('*')` specially and test the exact native syntax. Enforce alias requirements where the result key would otherwise be unstable or ambiguous.

## Contract and runtime requirements

- Inspect and update the Fetch Records serializer, backend validator, runtime field compiler, and result-consumer contract together. The UI alone is not sufficient: each selected result shape must be emitted and consumed as documented.
- Keep native query construction delegated to `frappe.qb.get_query()`; do not implement custom SQL generation for these functions, linked fields, or child-table nesting.
- Preserve existing filters, sort, grouping, limit/offset, distinct, and permission behavior unless a result shape makes a combination invalid; report such incompatibilities in UI validation.
- No migration/backward-compatibility layer is required for experimental Fetch Records configurations. Use one canonical new schema and add tests for it.
- Validate selected field paths and function specs server-side. Client-side field metadata is for usability, not a security boundary.
- Keep the existing Query List, Query Doc, and other Query Records modes unchanged.

## Required tests

1. Default shape selects `name` only and returns dictionaries keyed by `name`.
2. Whole-document selection includes expected parent fields and nested child rows.
3. Flat projection preserves aliases and linked-document paths.
4. Embedded child selection returns nested arrays and does not duplicate parent rows.
5. Flattened child selection documents/asserts row expansion.
6. Each supported function's native field payload and output alias are correct, including function arity and special arguments.
7. Unknown functions, malformed arguments, invalid paths, duplicate aliases, and invalid child fields fail validation before query execution.
8. Filters, sorting, limit/offset, distinct, permissions, and grouping are regression-tested against each result mode where supported.
9. Empty/incomplete field rows remain editable in the UI but cannot be serialized as valid executable selections.
10. Existing non-Fetch Records Query Records modes remain unaffected.

## Acceptance criteria

- Result shape is explicit, visible, and defaults to Document names.
- Field controls are hidden for Document names mode.
- Aliases and allowlisted functions are configurable graphically.
- Linked fields, embedded child fields, and flattened child fields have distinct, understandable behavior.
- Frontend and backend share a documented canonical schema; there is no silent fallback to a second legacy field schema.
- Tests assert both serialized native field payloads and actual result structure on the installed Frappe version.
