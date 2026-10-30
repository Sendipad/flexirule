# Resolved Output Schema Contract

The `Rule Action.resolved_output_schema` field describes metadata keys exposed to later actions through a return variable. Query Records generates this schema; other return-schema-enabled action types may supply it manually. A shared ES module at `flexirule/public/js/flexirule/utils/output_schema.js` owns canonicalization so action components and stores can reuse the same contract without coupling it to Vue global component registration.

## Canonical field shape

```json
{
  "label": "Reference Doctype",
  "fieldname": "reference_doctype",
  "fieldtype": "Select",
  "options": "DocType",
  "reqd": 0,
  "source": {
    "kind": "field",
    "fieldname": "voucher_type",
    "expression": "voucher_type as reference_doctype"
  }
}
```

- `fieldname` is the actual key in the action result. For aliased queries, it is the alias rather than the input field.
- `reqd` is always present in a canonical object and uses Frappe's DocField property name. It is normalized to integer `0` or `1`; absent values default to `0`. For fields backed by DocField metadata it reflects the source field's `reqd`; generated values such as aggregate results use `0`. This describes source metadata, not a promise that every row has a non-null value or that the key is guaranteed at runtime.
- `source` is always present as an object with a non-empty `kind`. It is provenance for tracing, debugging, and future UI features, and must not change execution or output-key validation. Its `fieldname` refers to the source expression, not necessarily the result key.
- Known source kinds include `field`, `child_field`, `child_table`, `system`, `aggregate`, `expression`, `report`, `result`, and `dynamic`. Manually authored fields use `manual` when their provenance was not otherwise specified. Legacy schemas or schemas whose lineage cannot be determined use `unknown`; consumers must not infer more provenance from this value.
- Additional source kinds and kind-specific properties may be added without changing the core field metadata. The source object is separate from FlexValue's value-resolution modes: `static`, `variable`, `resolver`, and `expression` answer how a value is resolved, whereas `source.kind` records where an output field came from. If a future source expression needs FlexValue editing features, store a nested `source.value_spec` using FlexValue's structure rather than reusing `source.kind` as a value mode.

For example, an aggregate uses the alias as its output `fieldname` and stores its lineage separately:

```json
{
  "label": "Totals",
  "fieldname": "totals",
  "fieldtype": "Int",
  "reqd": 0,
  "source": {
    "kind": "aggregate",
    "function": "count",
    "fieldname": "name",
    "expression": "count(name) as totals"
  }
}
```

## Compatibility

- Updated schema producers emit `reqd`, not `mandatory`.
- The frontend canonicalizer accepts old `mandatory` values, uses them only if `reqd` is absent, and removes the legacy key from normalized schemas.
- Source-less metadata is normalized with `source: {"kind": "unknown"}` at general load/save boundaries. The manual schema editor uses `source: {"kind": "manual"}` only when a field has no more specific provenance; existing source objects are preserved.
- The canonicalizer is imported as a normal reusable JS module. `rule_builder/globals.js` remains responsible for global Vue component registration rather than becoming a shared utility registry.
- Runtime return-key validation continues to examine result `fieldname` keys only; `reqd` and `source` do not change execution behavior.
