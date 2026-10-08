# Generic Tree Builder

The Tree Builder is a generic hierarchical/context engine. It owns structure, not domain semantics.

## Layers

- `tree_builder_utils.js`: framework-independent tree algorithms.
- `tree_builder_commands.js`: pure mutations for add/remove/move/replace/operator.
- `tree_builder_validation.js`: structural validation with optional domain callbacks.
- `useTreeBuilder.js`: Vue 3 reactive state, controlled synchronization, UI state, drag/drop and inherited scope context.
- `TreeBuilder.vue`: generic controlled UI.
- `TreeBuilderNode.vue`: recursive dispatcher.
- `TreeBuilderGroup.vue`, `TreeBuilderScope.vue`, `TreeBuilderLeaf.vue`: presentation boundaries.

## Model

```js
{
  id: "root",
  type: "group",
  operator: "and",
  children: [
    { id: "a", type: "leaf", ...domainPayload },
    {
      id: "items",
      type: "scope",
      scope: { type: "collection", key: "items" },
      children: [...]
    }
  ]
}
```

UI state is kept outside persisted nodes. `getNodeContext(nodeId)` derives inherited scopes from ancestry.

## Controlled usage

```vue
<TreeBuilder v-model="tree" :leaf-factory="createLeaf" />
```

Consumers own the canonical serializable tree. Domain layers interpret leaf payloads and scope metadata.

## Scope

A scope is a context boundary, not a logical group. Nested scopes are returned in ancestry order:

```js
{ scopes: [
  { type: "collection", key: "items" },
  { type: "collection", key: "taxes" }
] }
```

This allows Fetch Records or Condition Builder composables to resolve field/navigation semantics without coupling them to Tree Builder.
