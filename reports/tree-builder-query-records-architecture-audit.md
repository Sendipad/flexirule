# Tree Builder / Query Records Architecture Audit

**Repository:** Sendipad/flexirule  
**Audited branches:** refactor/tree-builder-generic-20261008, refactor/tree-builder-generic-20261009, refactor/query-records  
**Status:** Architecture audit only. No source implementation changes were made by this audit.

## 1. Executive conclusion

### Verdict: NOT READY FOR IMPLEMENTATION

The current Generic Tree Builder is not yet the single structural tree/state owner for Query Records.

The effective current architecture is:

    FetchRecordsConfig
        -> QueryFilterTree
           -> its own reactive tree
           -> filter_tree_adapter normalization/deserialization
           -> legacy serialization
        -> Generic TreeBuilder
           -> useTreeBuilder reactive root
           -> commands
           -> structural validation
        -> FilterLeaf
           -> legacy FilterGroup
              -> filter-row state
              -> field/operator/value logic
              -> validation

This violates the requested architecture.

The main defects are:

1. QueryFilterTree creates a separate reactive tree.
2. TreeBuilder creates another normalized reactive tree.
3. FilterLeaf is only a wrapper around the legacy FilterGroup editor.
4. filter_tree_adapter.js is a compatibility parser/normalizer/validator/serializer, not merely a backend boundary.
5. Generic TreeBuilder hardcodes group, scope, and leaf semantics.
6. Generic TreeBuilder exposes scope-specific context through getNodeContext().
7. Generic normalization silently converts unknown node types into leaves.
8. FetchRecordsConfig has stale relative imports after being moved one directory deeper.
9. The existing ControlRegistry/ControlFactory/FlexValueControl architecture is available and should be reused.
10. Historical representations should not automatically survive on these unmerged pre-release branches.

The correct direction is:

    FetchRecordsConfig
        -> QueryFilterTree
           -> composition/policy only
        -> Generic TreeBuilder
           -> ONE canonical tree state
        -> FilterLeaf
           -> ONE filter leaf
        -> ControlFactory / ControlRegistry / FlexValueControl
        -> ONE explicit Query Filter serializer
        -> Query Records backend contract

## 2. Current state ownership

### Action configuration

node.data.config remains the action configuration state. This is legitimate and should remain outside the generic tree engine.

### FetchRecordsConfig

FetchRecordsConfig creates localConfig with reactive(normalizeConfig(props.modelValue)). This is acceptable as configuration editing state, provided filters are delegated and it does not become a second tree engine.

### QueryFilterTree

QueryFilterTree creates a reactive tree from deserializeFilterPayload(props.modelValue). It then deep-watches, validates, serializes, replaces, clones, and exposes that tree.

Therefore QueryFilterTree is a tree state owner.

### Generic TreeBuilder

useTreeBuilder creates a second reactive root by normalizeTree(modelValue).

It independently watches, normalizes, clones, mutates, validates, and emits that tree.

Therefore:

    QueryFilterTree.tree
        -> TreeBuilder.root

are two distinct in-memory tree objects.

### FilterGroup

FilterLeaf currently renders FilterGroup with singleRow=true. FilterGroup itself contains filter-row state, field lookup, operator selection, value editing, navigation, and validation.

Thus each generic leaf is backed by another filter editor state machine.

## 3. Actual data flow

    node.data.config
      -> FetchRecordsConfig.localConfig
      -> QueryFilterTree.modelValue
      -> deserializeFilterPayload()
      -> QueryFilterTree.tree
      -> TreeBuilder v-model
      -> useTreeBuilder.normalizeTree()
      -> TreeBuilder.root
      -> tree_builder_commands / tree_builder_validation
      -> FilterLeaf
      -> FilterGroup
      -> FilterLeaf update
      -> QueryFilterTree.updateLeaf()
      -> validateFilterTree()
      -> serializeFilterTree()
      -> FetchRecordsConfig
      -> node.data.config

This is too many transformations.

The redundant layers are QueryFilterTree.tree, FilterLeaf -> FilterGroup, adapter normalization, adapter structural validation, and historical compatibility parsing.

## 4. Generic Tree Builder analysis

### Correct responsibilities

The generic layer should own:

- tree state
- hierarchy
- group creation/removal
- leaf creation/removal
- movement/reordering
- nesting
- structural validation
- depth limits
- mutation commands
- operator policy mechanism
- rendering composition

The current extraction of commands, utilities, and validation is directionally good.

### Incorrect responsibilities

The generic layer must not know:

- Frappe
- DocTypes
- fields
- Query Records
- Query Filter syntax
- Value Resolver semantics
- legacy filter arrays
- Query-specific scope semantics

The current implementation makes scope generic through TreeBuilderScope, scopeFactory, allowScopes, validateScope, and getNodeContext().scopes.

That is too domain-specific.

### Unknown node behavior

normalizeTree() currently turns unknown node types into leaves. This is unsafe. An extension node must never silently change semantic type.

## 5. Maximum depth

The 20261009 branch correctly attempts to make maxDepth a structural invariant.

It affects:

- add leaf
- add group
- add scope
- move
- drag/drop
- validation

This is the right direction.

The final implementation must also protect every externally supplied/replaced subtree. Max depth should be a single structural policy rather than scattered checks.

## 6. Logical operators

groupOperators is already a good generic mechanism.

The generic layer should provide the mechanism while the consumer defines:

- allowed values
- labels
- optionally descriptions

Hardcoded AND/OR label semantics should be removed from the generic implementation.

The added operatorLabel mechanism is directionally correct.

## 7. Node visibility

visibleNode is a useful policy hook, but the current behavior means that hiding a container hides its entire subtree.

That is valid for “hide node and subtree”, but not for “hide wrapper while still rendering children”.

Do not add transparent-container complexity unless a real consumer requires it. Visibility must never mutate the canonical tree.

## 8. Scope and collection decision

The audit did not establish a current Query Records-independent need for generic scope semantics.

Recommendation:

- group = generic structural container
- leaf = generic terminal node
- leaf payload = consumer-owned

Do not hardcode collection/scope semantics into the generic core merely because the previous implementation created them.

If a future consumer actually needs custom container node types, introduce a formal node-definition/capability mechanism at that time.

## 9. Query Records analysis

Query Records supports several modes. The backend contract confirms Fetch Records is a Query Records operation using Frappe Query Builder.

QueryRecordsConfig also uses the existing FilterGroup for other modes such as Query List, Exist Record, and aggregation-related filters.

Therefore FilterGroup must not be deleted globally as part of this refactor.

The clean migration boundary is the Fetch Records nested tree editor.

## 10. FilterLeaf decision

**Classification: D/E — rewrite as a genuine domain leaf renderer.**

Current design:

    FilterLeaf
        -> FilterGroup(singleRow=true)

This is not a real leaf renderer. It is a legacy filter editor wrapped to look like a leaf.

The new FilterLeaf should represent one leaf:

    {
      id,
      type: "leaf",
      doctype,
      field,
      operator,
      value
    }

It may own:

- field metadata
- field picker
- operator policy
- value control
- field-specific validation

It must not own:

- children
- groups
- nesting
- movement
- tree mutation
- tree normalization
- tree serialization
- parent/child relationships

The Generic TreeBuilder owns structural remove/move behavior.

## 11. QueryFilterTree decision

**Classification: B — retain, but make it thin.**

QueryFilterTree is a useful Query Filter composition boundary.

It should configure:

- Generic TreeBuilder
- Query Filter operator policy
- max depth
- visibility policy when required
- FilterLeaf renderer
- domain validation

It should not:

- create a second reactive tree
- deep-watch a duplicate tree
- normalize the tree independently
- serialize every mutation
- maintain a second tree API

The current reactive tree in QueryFilterTree should be eliminated.

## 12. filter_tree_adapter decision

**Classification: D/E — replace/minimize.**

The current adapter performs:

- ID generation
- group creation
- leaf creation
- legacy value normalization
- tuple detection
- legacy sequence parsing
- deserialization
- normalization
- structural validation
- serialization

That is a second filter-tree framework, not a simple backend boundary.

The only legitimate remaining boundary is:

    canonical UI tree
        <-> Query Records backend filter representation

If historical representations are not required by the active backend contract, delete their parsing.

Because these branches are unmerged, compatibility with the previous refactor is not a requirement.

## 13. Canonical model

Recommended canonical in-memory model:

    {
      "id": "root",
      "type": "group",
      "operator": "and",
      "children": [
        {
          "id": "filter-1",
          "type": "leaf",
          "doctype": "Sales Order",
          "field": "status",
          "operator": "=",
          "value": {
            "mode": "static",
            "value": "Open"
          }
        }
      ]
    }

The Generic TreeBuilder should treat leaf payload after id/type as opaque.

It knows structure, not Query Filter meaning.

The backend boundary should be:

    canonical UI tree
        -> Query Filter serializer
        -> Query Records backend contract

and, when loading persisted data:

    backend contract
        -> Query Filter deserializer
        -> canonical UI tree

There must not be several intermediate filter-tree representations.

## 14. Responsibility matrix

| Responsibility | Generic TreeBuilder | QueryFilterTree | FilterLeaf | FetchRecordsConfig | Backend boundary |
|---|---:|---:|---:|---:|---:|
| Tree state | YES | NO | NO | NO | NO |
| Tree mutations | YES | NO | NO | NO | NO |
| Group creation | YES | policy | NO | NO | NO |
| Leaf creation | YES | policy | NO | NO | NO |
| Movement/reordering | YES | policy | NO | NO | NO |
| Nesting | YES | policy | NO | NO | NO |
| Max depth | YES | config | NO | NO | NO |
| Structural validation | YES | domain policy | NO | NO | NO |
| Group operators | mechanism | policy | NO | NO | NO |
| Operator labels | mechanism | policy | filter labels | NO | NO |
| Node visibility | mechanism | policy | NO | NO | NO |
| Leaf rendering | framework | configures | YES | NO | NO |
| Field selection | NO | NO | YES | NO | NO |
| Filter operator | NO | policy | YES | NO | NO |
| Filter value | NO | NO | YES | NO | NO |
| Value Resolver | NO | NO | YES | NO | NO |
| Query configuration | NO | NO | NO | YES | NO |
| Backend serialization | NO | NO | NO | NO | YES, if required |

## 15. Existing FlexiRule architecture

The existing frontend already provides the required mechanisms.

### ControlRegistry

core/control_registry.js maps field definitions to registered controls including ComboBoxControl, SelectControl, CheckControl, MultiSelectList, FlexValueControl, and others.

### ControlFactory

rule_builder/controls/ControlFactory.vue resolves controls through ControlRegistry.

Where a field definition naturally determines its control, this should be preferred over a new control-resolution mechanism.

### FlexValueControl

FlexValueControl.vue is already the structured value/resolver integration point.

FilterLeaf should reuse it rather than creating another resolver abstraction.

### useControlContext

useControlContext.js provides dependent-field resolution for Dynamic Link and MultiSelectList. Reuse it.

### useNavigableFields

useNavigableFields.js is the existing Query Records-oriented field-navigation composable. It belongs in Query Records/domain UI, not Generic TreeBuilder.

### useActionConfig

useActionConfig.js already owns action configuration concerns such as reference DocType, metadata, variables, config synchronization, and dirty state.

## 16. Build-error root cause

### FetchRecordsConfig imports

FetchRecordsConfig was moved from:

rule_builder/components/rule_config/types/FetchRecordsConfig.vue

to:

rule_builder/components/rule_config/types/query_records/FetchRecordsConfig.vue

but imports remained at the old relative depth:

- ../../../controls/ControlFactory.vue
- ../../../controls/ComboBoxControl.vue
- ../../../controls/MultiSelectList.vue
- ../../../composables/useNavigableFields

The actual canonical locations are:

- rule_builder/controls/ControlFactory.vue
- rule_builder/controls/ComboBoxControl.vue
- rule_builder/controls/MultiSelectList.vue
- rule_builder/composables/useNavigableFields.js

Therefore the resolution failures are direct consequences of the move without adjusting the import root.

This is a symptom, not the architectural fix.

### frappe-vue-style error

The error about reading outputs from frappe-vue-style should be treated as secondary until the module-resolution failures are removed.

Correct order:

1. resolve module graph
2. rebuild
3. see whether outputs error remains
4. only then investigate plugin behavior

## 17. Directory structure

Responsibility-based target:

    rule_builder/
      components/
        tree_builder/
          TreeBuilder.vue
          TreeBuilderNode.vue
          TreeBuilderGroup.vue
          useTreeBuilder.js
          tree_builder_utils.js
          tree_builder_commands.js
          tree_builder_validation.js
          tree_builder_types.js

        rule_config/
          query_filters/
            QueryFilterTree.vue
            FilterLeaf.vue
            query_filter_serializer.js
            query_filter_policy.js

          types/
            QueryRecordsConfig.vue
            query_records/
              FetchRecordsConfig.vue

The exact serializer/policy filenames may change if an existing FlexiRule pattern is preferable.

The important rule is responsibility, not historical filename placement.

## 18. File classification

| File | Decision | Reason |
|---|---|---|
| FilterLeaf.vue | D/E | Keep concept, rewrite as one domain leaf |
| QueryFilterTree.vue | B | Keep as thin composition; remove duplicate state |
| filter_tree_adapter.js | D/E | Replace with minimal backend boundary if required |
| filter_tree_adapter.test.js | B/D | Rewrite around public serialization contract |
| FetchRecordsConfig.vue | A/B | Keep; delegate filters and own Query Records config |
| QueryRecordsConfig.vue | A/B | Keep as top-level mode configuration |
| FilterGroup.vue | A | Retain for existing non-Fetch-Records consumers |

## 19. Redundant layers

### Redundant 1
QueryFilterTree.tree — Generic TreeBuilder already owns the tree.

### Redundant 2
FilterLeaf -> FilterGroup — a leaf renderer must not mount a filter tree/editor.

### Redundant 3
normalizeFilterTree() — Generic TreeBuilder should normalize the canonical model.

### Redundant 4
validateFilterTree() — Generic TreeBuilder should own structure; Query Filter validates leaf/domain semantics.

### Redundant 5
Historical compatibility parsing — keep only if the active backend/persistence contract requires it.

## 20. Target QueryFilterTree composition

Conceptually:

    QueryFilterTree
        -> receives modelValue
        -> supplies Query Filter policy
        -> supplies FilterLeaf renderer
        -> Generic TreeBuilder

There must be no intermediary reactive tree.

The invariant is:

    TreeBuilder state == QueryFilterTree filter state

## 21. Target FilterLeaf

Conceptually:

    FilterLeaf
      -> field picker
      -> operator picker
      -> FlexValueControl / ControlFactory
      -> domain validation

It receives one canonical leaf and emits one updated leaf.

It does not know about siblings, parent groups, children, drag/drop, tree serialization, or tree normalization.

## 22. Testing strategy

### Generic TreeBuilder

Test:

- add leaf
- add group
- remove
- move/reorder
- circular move prevention
- operator policy
- max depth
- externally supplied too-deep trees
- replacement validation
- visibility policy if public behavior

### QueryFilterTree

Test composition:

- canonical model reaches TreeBuilder
- FilterLeaf receives canonical leaf
- operator policy
- max depth policy
- visibility policy

Do not test duplicate internal state.

### FilterLeaf

Test:

- field selection
- operator selection
- field-dependent operator changes
- value control
- static values
- variable/resolver values
- Between/multi-value semantics
- Dynamic Link/MultiSelect dependencies
- validation

### Serializer

Test only:

    canonical tree <-> active backend representation

Delete compatibility tests if compatibility is intentionally removed.

## 23. Compatibility decision

These branches are pre-release and unmerged.

Preferred policy:

    DELETE obsolete representation
    DELETE duplicate state
    DELETE redundant adapters
    REBUILD around one canonical model

Do not introduce:

    old model -> wrapper -> adapter -> generic model -> compatibility layer

Only compatibility required by the active persisted/backend contract should survive.

## 24. Implementation phases

Implementation should begin only after this audit is accepted.

### Phase 1 — Canonical generic model
Define and test one tree model. Remove generic scope semantics that are not genuinely generic.

### Phase 2 — Single state owner
Remove QueryFilterTree duplicate reactive state. Generic TreeBuilder becomes the tree state owner.

### Phase 3 — Real FilterLeaf
Rewrite FilterLeaf as a one-row domain component. Stop using FilterGroup as its implementation.

### Phase 4 — Serialization boundary
Confirm the active Query Records backend contract and replace the current adapter with one minimal serializer/deserializer if required.

### Phase 5 — QueryFilterTree composition
Configure TreeBuilder with Query Filter policy and renderer only.

### Phase 6 — FetchRecordsConfig integration
Keep FetchRecordsConfig focused on Query Records configuration and delegate filters.

### Phase 7 — Tests/build
Run generic tree, Query Filter, serializer, Fetch Records, lint/build, and targeted UI tests. Investigate frappe-vue-style only after module resolution succeeds.

## 25. Critical acceptance criteria

The implementation must not be considered successful merely because the build passes.

All must be demonstrable:

1. One canonical in-memory tree model.
2. One tree state owner.
3. One tree mutation owner.
4. FilterLeaf contains no tree structure.
5. FilterLeaf does not wrap FilterGroup for Fetch Records.
6. QueryFilterTree contains no second tree state.
7. FetchRecordsConfig does not manipulate tree internals.
8. Generic TreeBuilder contains no Query Records knowledge.
9. Generic TreeBuilder contains no Frappe knowledge.
10. Generic TreeBuilder does not hardcode Query Filter operators.
11. Scope/collection semantics are not hardcoded into generic core without a demonstrated generic requirement.
12. Legacy serialization is removed unless required by the active backend contract.
13. One explicit backend serialization boundary exists.
14. No redundant tree normalization remains.
15. No duplicated group/leaf/scope models remain.
16. Existing ControlRegistry/ControlFactory/FlexValueControl/composables are reused.
17. Build imports reference canonical locations.
18. Tests validate public contracts rather than obsolete implementation details.
19. Max depth applies to external trees, add, move, drag/drop, and validation.
20. Operator values/labels are consumer policy.
21. Visibility is a deliberate composition policy and never mutates canonical state.

## 26. Final architectural decision

The Generic TreeBuilder extraction is a useful foundation, but it is not yet the final architecture.

The correct next step is not to patch the current import errors or add more compatibility wrappers.

The correct next step is to simplify:

    DELETE duplicate QueryFilterTree state
    DELETE FilterLeaf -> FilterGroup tree delegation
    DELETE redundant filter-tree normalization
    DELETE obsolete adapter compatibility
    DELETE hardcoded generic scope semantics unless a real generic consumer requires them

Then rebuild around:

    FetchRecordsConfig
        -> QueryFilterTree (composition/policy)
        -> Generic TreeBuilder (ONE tree state owner)
        -> FilterLeaf (ONE leaf editor)
        -> ControlFactory / ControlRegistry / FlexValueControl
        -> Query Filter serializer
        -> Query Records backend contract

The architecture is acceptable only when Generic Tree Builder owns structure/state/mutations, Query Records owns domain semantics, there is one canonical tree model, one state owner, one mutation owner, one explicit backend serialization boundary, and no hidden legacy tree/serialization layer remains.
