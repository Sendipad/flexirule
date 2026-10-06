# Query Records Filter Tree — Production Implementation Plan

**Repository:** `Sendipad/flexirule`  
**Source branch reviewed:** `refactor/query-records`  
**Report path:** `reports/query-records/filter-tree-adapter-implementation-plan.md`  
**Scope:** Filter TreeBuilder / FilterLeaf data flow and the boundary between UI filter state and the Fetch Records backend query contract.

## 1. Executive decision

Do **not** make `TreeBuilder` or `FilterLeaf` directly own the backend filter representation.

Use a dedicated, explicit **Filter Tree Adapter / Serializer** between the interactive UI tree and the canonical Fetch Records backend filter structure.

Recommended architecture:

```
Interactive UI tree
  TreeBuilder
  TreeBuilderNode
  FilterLeaf / FilterGroup
          |
          v
  Filter Tree Adapter
  - normalize
  - validate
  - serialize
  - deserialize
          |
          v
Canonical Fetch Records filters
          |
          v
Backend Query Records
          |
          v
frappe.qb.get_query()
```

The UI model should remain optimized for editing. The backend representation should remain optimized for query execution and Frappe compatibility.

This avoids coupling the Vue tree to the exact representation accepted by the installed Frappe version and makes the Frappe compatibility layer the backend concern rather than a responsibility of the UI.

---

## 2. Source-code findings from `refactor/query-records`

### 2.1 TreeBuilder is already a generic UI tree editor

Current `TreeBuilder.vue`:

- owns a root group;
- supports `and` / `or`;
- creates leaf nodes through a supplied `leafFactory`;
- creates nested groups;
- supports removal and drag/drop;
- maintains stable UI node IDs;
- emits a cloned tree through `update:modelValue`;
- intentionally knows nothing about Fetch Records or Frappe query syntax.

This is the correct separation and should be preserved.

### 2.2 TreeBuilderNode is also correctly UI-oriented

`TreeBuilderNode.vue` recursively renders groups and leaves.

It needs:

- node identity;
- parent/child relationships;
- group operator;
- drag/drop state;
- add/remove actions.

It should **not** be changed to understand backend filter arrays.

### 2.3 QueryFilterTree currently combines two responsibilities

Current `QueryFilterTree.vue` contains both:

1. the UI tree state;
2. conversion between that tree and the external filter payload.

The current internal model is approximately:

```js
{
  id,
  type: "group",
  operator: "and" | "or",
  children: [
    {
      id,
      type: "leaf",
      doctype,
      field,
      operator,
      value
    }
  ]
}
```

The current serializer produces leaf arrays of the form:

```js
[doctype, field, operator, value];
```

and combines multiple children using logical operator strings:

```js
[[doctype, field, "=", value], "or", [doctype, field, "=", value]];
```

This is already evidence that an adapter boundary exists conceptually. The production improvement should be to make that boundary explicit and reusable rather than redesigning TreeBuilder around backend arrays.

### 2.4 FilterGroup requires a complete editable leaf model

Current `FilterGroup.vue` expects a row with:

- `doctype`
- `field`
- `operator`
- `value`

It also owns Frappe/FlexiRule-specific UI behavior such as:

- field navigation;
- operator selection;
- field-type-specific operators;
- nested-set operators;
- Between;
- Timespan;
- FlexValueControl;
- variable/resolver values;
- field validation.

Therefore the UI leaf must remain richer than a raw backend list item.

### 2.5 Backend compatibility already establishes an important constraint

Current `flexirule/ruleflow/utils/frappe_query_compat.py` detects whether the installed Frappe version supports:

- `ignore_permissions`;
- logical filter groups.

When logical filter groups are not supported natively, the compatibility layer converts nested logical filters into Frappe/PyPika `Criterion` objects.

This confirms that **logical filter representation belongs at the backend boundary**, not inside the Vue TreeBuilder.

The compatibility layer also explicitly handles simple filter leaves and rejects unsupported dotted fields for its legacy logical-filter fallback.

---

## 3. Production architecture

Introduce a dedicated module conceptually named:

```
filter_tree_adapter.js
```

or, preferably if the project already has a suitable query/filter utility location:

```
query_filter_adapter.js
```

The exact file location should be chosen after checking the existing frontend utility/composable organization.

It should expose four primary operations:

```js
normalizeFilterTree(value, context);
serializeFilterTree(tree, context);
deserializeFilterPayload(payload, context);
validateFilterTree(tree, context);
```

Optional helpers:

```js
createFilterLeaf(context);
createFilterGroup(operator);
isFilterLeaf(node);
isFilterGroup(node);
```

The adapter should contain **no Vue template logic**.

It may use plain JavaScript objects and functions and should be independently testable.

---

## 4. Canonical UI model

The editor model should remain tree-shaped.

Recommended conceptual schema:

```js
{
  id: "stable-ui-id",
  type: "group",
  operator: "and",
  children: [
    {
      id: "stable-ui-id",
      type: "leaf",
      doctype: "Sales Order",
      field: "customer",
      operator: "=",
      value: {
        mode: "static",
        value: "CUST-0001"
      }
    }
  ]
}
```

### UI-only properties

The following must never be required by the backend:

- `id`
- `type`
- expansion state;
- selection state;
- drag state;
- temporary editor state;
- UI validation state.

These are editor concerns.

### Query semantics

The following are semantic query properties:

- DocType;
- field/path;
- operator;
- value;
- logical operator;
- nested grouping.

The adapter is responsible for converting these semantic properties into the canonical backend structure.

---

## 5. Canonical backend representation

The backend representation should be selected from the structures actually supported by the Fetch Records implementation and installed Frappe Query Builder.

Do **not** invent a third query language.

The preferred simple leaf representation remains list-based where supported:

```js
["fieldname", "=", value];
```

or the existing four-part representation where the DocType must travel with the leaf:

```js
["DocType", "fieldname", "=", value];
```

The exact canonical choice must be the one already accepted by the current Fetch Records backend. The adapter should normalize all UI leaves to that one representation before emitting configuration.

For logical groups, preserve the backend-supported nested representation rather than flattening expressions in the UI.

The important invariant is:

> TreeBuilder never needs to know which representation Frappe accepts.

---

## 6. Serialization rules

### 6.1 Leaf

A valid leaf:

```
doctype + field + operator + value
```

is serialized into the canonical backend leaf representation.

No UI-only properties may survive serialization.

### 6.2 Group

A group with no children:

- is invalid for execution;
- may exist temporarily while the user is editing;
- must be reported by validation rather than silently becoming a query.

A group with one child may serialize directly to that child if this is semantically equivalent in the backend contract.

A group with multiple children must preserve its logical operator.

### 6.3 Nested groups

Nested groups must retain their grouping semantics.

For example:

```
AND
├── status = Open
└── OR
    ├── priority = High
    └── priority = Medium
```

must never be flattened into:

```
status = Open
AND priority = High
OR priority = Medium
```

because that changes the meaning.

The adapter must preserve the tree's grouping boundaries.

### 6.4 Empty/incomplete leaves

A newly created leaf may temporarily contain:

```
field: ""
```

while the user is editing.

That is acceptable in the UI model.

It must not be emitted as an executable backend filter.

Validation should identify:

```
"A filter field is required."
```

rather than generating malformed backend criteria.

This is particularly important because the current blank-leaf bug originated from the distinction between a valid UI node and a complete query criterion.

---

## 7. Deserialization rules

The reverse adapter is equally important.

When existing configuration enters the editor:

```
backend filters
      |
      v
deserializeFilterPayload()
      |
      v
UI tree
```

Requirements:

1. Generate stable UI IDs.
2. Never use backend values as UI IDs.
3. Preserve AND/OR grouping.
4. Preserve DocType information.
5. Preserve FlexValue structures.
6. Preserve nested filter groups.
7. Preserve values without coercing their semantic type.
8. Normalize legacy accepted forms only at this boundary.

The editor should receive one predictable tree shape regardless of which accepted backend filter form was stored.

---

## 8. Legacy/accepted input compatibility

The adapter may accept more than one input representation when reading existing configuration.

For example:

```js
["status", "=", "Open"];
```

and:

```js
["Sales Order", "status", "=", "Open"];
```

may both be recognized if they are currently valid inputs.

However:

- only one canonical representation should be emitted;
- compatibility parsing must be isolated;
- new UI code must not branch on legacy representations.

This prevents legacy support from spreading into TreeBuilder and FilterGroup.

---

## 9. FlexValue integration

The adapter must treat filter values as opaque semantic values.

For example:

```js
{
  mode: "static",
  value: "Open"
}
```

or a variable/resolver/expression value must remain intact.

Do not convert FlexValue into a plain string merely because the backend ultimately resolves it.

The pipeline should be:

```
UI FlexValue
   ↓
serialized filter
   ↓
backend resolver/context handling
   ↓
query value
```

The adapter is responsible for structural serialization, not value resolution.

This keeps Value Resolver semantics outside the filter tree serializer.

---

## 10. Operators

The adapter should not maintain a second independent list of query operators.

Operator availability belongs to the existing field/operator capability logic.

The adapter should:

- preserve the selected operator;
- validate that an operator exists;
- preserve case/representation required by the backend contract;
- reject unsupported values during validation.

The UI can continue to derive field-specific operator options from the existing FilterGroup logic.

Future operator additions should therefore not require changes to the adapter unless serialization semantics change.

---

## 11. Fields and dotted references

Field references must remain strings at the semantic query layer.

Examples:

```
customer
customer.customer_name
items.item_code
items.qty
```

The adapter must not split these into unrelated frontend concepts merely because they contain dots.

The field navigator may provide the user-friendly navigation experience, but the selected backend field/path should remain the exact reference expected by the query backend.

This gives:

```
Display label
      ≠
Backend field reference
```

The UI may show:

```
Customer → Customer Name
```

while storing:

```
customer.customer_name
```

---

## 12. Validation boundary

Validation should exist at two levels.

### UI validation

Performed while editing:

- field selected;
- operator selected;
- required value supplied;
- valid field for selected DocType;
- valid field path;
- valid nested group;
- valid Between values;
- valid value control.

### Serialization validation

Performed before emitting executable configuration:

- no malformed leaf;
- no empty executable group;
- valid logical operator;
- valid leaf shape;
- valid backend field representation;
- valid operator;
- value structure remains serializable.

The adapter should return structured validation information where practical:

```js
{
  valid: false,
  errors: [
    {
      path: ["children", 0, "field"],
      code: "required",
      message: "A filter field is required."
    }
  ]
}
```

The existing user-facing validation messages can remain localized in the UI layer.

---

## 13. Emission strategy

Avoid a situation where both TreeBuilder and FetchRecordsConfig independently transform filters.

Recommended flow:

```
TreeBuilder
   ↓
UI tree
   ↓
QueryFilterTree
   ↓
adapter.serializeFilterTree()
   ↓
Fetch Records config.filters
```

The adapter should be the only code responsible for turning the tree into backend filter syntax.

Similarly:

```
config.filters
   ↓
adapter.deserializeFilterPayload()
   ↓
QueryFilterTree
   ↓
TreeBuilder
```

---

## 14. FetchRecordsConfig responsibility

`FetchRecordsConfig.vue` should remain responsible for:

- assembling the complete Fetch Records configuration;
- passing `filters` into QueryFilterTree;
- receiving serialized filters;
- emitting the complete action configuration;
- handling Fields;
- Order By;
- Group By;
- Limit;
- Offset;
- Distinct.

It should **not** understand individual tree nodes.

This is especially important as Fetch Records grows to support more query-builder features.

---

## 15. QueryFilterTree responsibility after refactor

`QueryFilterTree.vue` should become a thin integration layer:

1. receive `modelValue`;
2. deserialize it into a UI tree;
3. render TreeBuilder;
4. receive tree mutations;
5. validate;
6. serialize through the adapter;
7. emit the canonical filter payload.

It should not contain a growing collection of backend-format conditionals.

---

## 16. TreeBuilder responsibility

No Fetch Records-specific logic should be introduced into generic TreeBuilder.

TreeBuilder should continue to know only:

- group;
- leaf;
- children;
- logical group operator;
- node identity;
- add/remove/move.

This preserves TreeBuilder as a reusable component for:

- Conditions;
- Filters;
- future rule trees;
- other nested expression builders.

---

## 17. Backend responsibility

The backend remains authoritative for actual query execution.

The pipeline should be:

```
Fetch Records config
       ↓
backend handler
       ↓
frappe.qb.get_query()
       ↓
Frappe Query Builder
```

The existing compatibility layer remains responsible for Frappe-version differences, particularly logical filters and permission-related API differences.

Do not move backend compatibility logic into JavaScript.

---

## 18. Important distinction: adapter vs compatibility layer

These are two different layers.

### Frontend adapter

Solves:

> How does the interactive Vue tree become the Fetch Records filter payload?

### Backend compatibility layer

Solves:

> How does the Fetch Records filter payload execute correctly on the installed Frappe version?

Architecture:

```
Vue tree
   ↓
Frontend adapter
   ↓
FlexiRule canonical filter payload
   ↓
Fetch Records backend
   ↓
Frappe compatibility layer
   ↓
frappe.qb.get_query()
```

Neither layer should absorb the other's responsibilities.

---

## 19. Testing strategy

The adapter should have focused unit tests before changing TreeBuilder behavior.

### Required serialization tests

1. Empty root group.
2. One leaf.
3. Multiple AND leaves.
4. Multiple OR leaves.
5. Nested AND/OR.
6. Deep nested groups.
7. Four-part leaf with DocType.
8. Three-part leaf without DocType.
9. Static FlexValue.
10. Variable FlexValue.
11. Resolver/expression FlexValue.
12. Dotted Link field.
13. Dotted child field.
14. Empty field.
15. Empty group.
16. Unsupported logical operator.
17. Malformed leaf.

### Required deserialization tests

For every supported backend representation:

```
backend → UI tree → backend
```

must preserve query semantics.

The strongest test is semantic round-trip equality rather than object identity.

UI-generated IDs must not affect round-trip comparison.

### Component tests

Verify:

- Add Filter creates a complete editable leaf;
- field/operator/value controls render immediately;
- nested groups retain their operator;
- changing AND to OR changes serialized output;
- deleting a leaf updates serialized filters;
- moving a node does not corrupt grouping;
- invalid filters fail validation.

### Regression tests

Verify existing Fetch Records behavior for:

- Fields;
- Order By;
- Group By;
- Limit;
- Offset;
- Distinct;
- Refresh Schema;
- Link fields;
- child fields.

---

## 20. Performance requirements

Do not serialize the entire tree on every keystroke if this becomes expensive for large trees.

The first implementation may continue using Vue's deep watcher because current trees are expected to be small.

However, the adapter should be pure and cheap enough to call repeatedly.

Avoid:

- API calls during serialization;
- schema fetches during serialization;
- field metadata traversal unrelated to the changed node;
- repeated deep cloning of the entire rule document;
- generating new IDs during every serialization;
- asynchronous serialization.

Schema metadata should be resolved outside the adapter.

---

## 21. Reactivity requirements

The adapter must never mutate the source tree during:

- serialization;
- deserialization;
- validation.

Use immutable/clone semantics where necessary.

This is particularly important because TreeBuilder uses a reactive root and emits deep-cloned values.

The adapter should therefore behave as a pure boundary:

```
input → output
```

with no hidden Vue mutations.

---

## 22. Error handling

Malformed persisted configuration must not crash the rule-builder UI.

The adapter should:

1. attempt to parse;
2. normalize recognized forms;
3. preserve as much valid structure as possible;
4. report invalid nodes;
5. allow the editor to display and repair them.

Do not silently turn malformed filters into an unrestricted query.

An invalid filter configuration must never result in:

```
filters = []
```

and accidentally mean "return all records".

This is a critical production safety invariant.

---

## 23. Security boundary

The frontend adapter must never be treated as a security boundary.

It can validate structure for UX, but:

- permissions;
- field permissions;
- DocType permissions;
- `ignore_permissions`;
- query safety;
- Frappe capability compatibility

remain backend responsibilities.

The backend must validate and enforce them regardless of what the Vue UI sends.

---

## 24. Migration strategy

Because FlexiRule is pre-RC and backward compatibility is not a major constraint, do not introduce a complicated migration framework.

Recommended approach:

### Phase 1

Keep current accepted payloads.

### Phase 2

Introduce the adapter and normalize input.

### Phase 3

Make the adapter the sole serializer.

### Phase 4

Remove duplicate serialization code from QueryFilterTree.

### Phase 5

Add focused tests.

If a legacy representation is no longer needed before RC, it may be removed rather than permanently supported.

---

## 25. Implementation phases

### Phase A — Contract inventory

Before changing code:

- inventory every current filter payload shape;
- inspect Fetch Records backend parsing;
- inspect `frappe.qb.get_query` invocation;
- inventory tests;
- document supported logical nesting;
- document 3-part vs 4-part leaf forms;
- document FlexValue handling.

**Deliverable:** one canonical serialization contract.

### Phase B — Adapter

Create the pure adapter.

Implement:

- normalize;
- create leaf/group;
- deserialize;
- serialize;
- validate.

No UI redesign.

### Phase C — QueryFilterTree integration

Replace local parsing/serialization logic with adapter calls.

Keep TreeBuilder unchanged.

### Phase D — Validation integration

Ensure incomplete UI nodes are allowed during editing but cannot become executable filters.

### Phase E — Regression tests

Add adapter tests and QueryFilterTree-focused tests.

### Phase F — Full Fetch Records validation

Verify complete configuration behavior:

```
Filters
Fields
Order By
Group By
Limit
Offset
Distinct
```

including combinations.

### Phase G — CI

Run:

- frontend lint;
- frontend build;
- relevant unit tests;
- existing backend Fetch Records tests;
- full application test suite if CI capacity permits.

---

## 26. Definition of done

The implementation is production-ready when all of the following are true:

- TreeBuilder remains backend-agnostic.
- FilterLeaf remains optimized for interactive editing.
- One adapter owns filter serialization/deserialization.
- No duplicate filter serialization exists in FetchRecordsConfig.
- Nested AND/OR semantics are preserved.
- UI-only IDs never reach the backend.
- FlexValue structures are preserved.
- Link and child-table field paths remain exact backend references.
- Invalid filters cannot silently become an unrestricted query.
- Backend permission enforcement remains backend-only.
- Frappe compatibility remains backend-only.
- Adapter unit tests cover every supported filter shape.
- Existing Fetch Records tests remain green.
- Frontend lint/build pass.
- No backend query behavior is changed as part of the frontend adapter refactor unless a separate backend requirement is explicitly identified.

---

## 27. Recommended final ownership model

| Responsibility                     | Component / Layer           |
| ---------------------------------- | --------------------------- |
| Interactive tree                   | TreeBuilder                 |
| Recursive node rendering           | TreeBuilderNode             |
| Filter field/operator/value editor | FilterGroup / FilterLeaf UI |
| Filter UI state                    | QueryFilterTree             |
| Tree ↔ backend conversion          | Filter Tree Adapter         |
| Complete action configuration      | FetchRecordsConfig          |
| Query execution                    | Fetch Records backend       |
| Frappe API/version compatibility   | `frappe_query_compat.py`    |
| Permissions/security               | Backend / Frappe            |

The key design rule is:

> **The TreeBuilder should model the user's intent as a tree. The adapter should model how that intent is serialized for the backend. Neither side should be forced to become the other.**

---

### 27. Recommended final ownership model

The ownership model should explicitly reflect the FilterLeaf extraction and stable navigation state:

| Responsibility                   | Component / Layer                      |
| -------------------------------- | -------------------------------------- |
| Interactive tree                 | TreeBuilder                            |
| Recursive node rendering         | TreeBuilderNode                        |
| One filter leaf editor           | FilterLeaf                             |
| Field navigation for one leaf    | FilterLeaf → useNavigableFields        |
| Field picker UI                  | ComboBoxControl                        |
| Legacy flat filter collection    | FilterGroup, only where still required |
| Filter UI tree integration       | QueryFilterTree                        |
| Tree ↔ backend conversion        | Filter Tree Adapter                    |
| Complete action configuration    | FetchRecordsConfig                     |
| Query execution                  | Fetch Records backend                  |
| Frappe API/version compatibility | `frappe_query_compat.py`               |
| Permissions/security             | Backend / Frappe                       |

`FilterGroup.vue` must not become a second navigation implementation. The long-term Query Filter Tree path should use `FilterLeaf.vue` for individual filter editing and stable navigation state.

### 27.1 Migration sequence for FilterGroup → FilterLeaf

Do not rewrite all filter behavior at once. Extract incrementally:

1. Preserve the existing row data shape and operator/value behavior.
2. Move one complete filter row into `FilterLeaf.vue`.
3. Move the field picker and its navigation behavior with the row.
4. Replace index-based navigation state with one `useNavigableFields()` instance per leaf.
5. Verify Link and child-table navigation.
6. Switch QueryFilterTree to render `FilterLeaf.vue` through the existing tree structure.
7. Keep `FilterGroup.vue` available for legacy consumers until repository-wide usage confirms it is no longer required.
8. Remove duplicated field-discovery/navigation code only after all consumers have migrated.

This staged approach prevents the UI extraction from becoming a simultaneous query-contract refactor.

### 28. Explicit non-goals

## 28. Explicit non-goals

This implementation must not:

- rewrite TreeBuilder around backend arrays;
- make FilterLeaf know about `frappe.qb`;
- duplicate Frappe's query parser in JavaScript;
- introduce a second query language;
- move permission logic to the frontend;
- resolve variables/resolvers in the frontend adapter;
- redesign Fields/Order By/Group By as part of the filter adapter;
- change the backend compatibility layer merely to accommodate the UI.

This plan is specifically a **filter-tree representation and boundary refactor**.
