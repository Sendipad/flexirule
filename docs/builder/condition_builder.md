---
title: "Condition Builder"
weight: 20
---

# Condition Builder UI (Frontend)

The Condition Builder is a specialized Vue 3 workspace designed to let users author complex business logic through a structured, visual interface.

Looking for how to use it? See the [Condition Builder User Guide](user_guide_conditions.md).

## Recursive Component Architecture

The builder uses a hierarchical structure where components call each other recursively to support infinite nesting of logic.

### 1. `ConditionBuilder.vue`

The root component that manages the top-level state and provides action methods (Add Condition, Add Group, Add Collection) to all child components via Vue's `provide/inject` pattern.

### 2. `ConditionNode.vue`

A recursive dispatcher. It looks at the type of data node (Group, Collection, or Simple Condition) and renders the appropriate sub-component.

### 3. `ConditionGroupUI.vue`

Handles `AND`/`OR` logical groupings. It renders a list of `ConditionNode` components, creating the recursive link. This component allows for infinite nesting of logic.

### 4. `CollectionUI.vue`

A specialized interface for evaluating logic across child tables. It allows users to pick a collection (e.g., `doc.items`), define an alias (e.g., `item`), and then uses `ConditionGroupUI` to define the sub-logic for that collection.

### 5. `SimpleCondition.vue`

The leaf node component where actual comparisons are defined. It includes:

- **Context Picker**: To select fields from `doc`, `old_doc`, or loop aliases.
- **Operator Dropdown**: Dynamically filtered based on the selected field's type (e.g., showing "Contains" for strings but ">" for numbers).
- **Value Input**: Uses `FlexStructuredValueControl` to allow both literal values and dynamic expressions.

---

## State Management & Synchronization

- **JSON AST**: The builder maintains a single reactive JSON object representing the entire logic tree.
- **UUIDs**: Every node in the tree is assigned a unique ID upon creation. This is critical for the **Drag-and-Drop** system to track nodes as they are moved between groups.
- **Reactivity**: Any change in a leaf node (e.g., changing an operator) bubbles up through the reactive state, which the parent `RuleConfigModal` then syncs to the Rule DocType.

## Logical Grouping & Operators

FlexiRule supports sophisticated logical grouping to handle complex business requirements.

### The AND/OR Toggle

Each group (including the root) has a logical operator toggle.

- **AND**: All conditions within the group must evaluate to True.
- **OR**: At least one condition within the group must evaluate to True.

### Infinite Nesting

By clicking "Group", users can create a nested logical container. This allows for logic like:
`(Status == "Open" AND (Priority == "High" OR Priority == "Urgent"))`

### Local Logical Operators (In-Group Joining)

Inside a group, every node (except the last one) can specify how it joins with the _next_ node. While the group has a "Default" operator, individual conditions can override this for fine-grained control, although standard best practice is to use nested groups for clarity.

## Drag-and-Drop System

The builder implements a custom drag-and-drop layer to allow reordering and re-grouping conditions. This is the primary way to organize logic without deleting and recreating nodes.

### Moving Conditions Between Groups

Users can grab any condition or entire group by its drag handle and move it:

- **Reordering**: Dragging a node up or down within the same group.
- **Nesting**: Dragging a node into a different group or collection.
- **Promoting**: Dragging a node out of a nested group back to a parent level.

### Technical Implementation & Safety

- **UUID-Based Tracking**: Every node has a unique `id`. The `moveNode(fromGroup, fromIndex, toGroup, toIndex)` method uses these IDs to safely splice nodes out of their source array and into their target destination.
- **AST Integrity**: When a node is moved, its entire subtree in the JSON AST is moved with it. The `ConditionCompiler` then automatically handles the structural change upon the next save, regenerating the Python expression based on the new hierarchy.
- **Illegal Move Prevention**: The system includes a recursive `isDescendantOf(parent, targetId)` check. This prevents a user from accidentally dropping a parent group into one of its own children, which would cause a circular reference and crash the builder.
- **Visual Feedback**: Real-time "drop zone" highlighting shows exactly where a node will land.
- **Smooth Transitions**: Uses Vue's `<TransitionGroup>` to animate nodes as they are added, removed, or moved.

## Keyboard Shortcuts & Accessibility

- **Focus Management**: When a new condition is added, focus is automatically shifted to the field picker.
- **ARIA Labels**: All icon buttons include descriptive ARIA labels for screen readers.
- **Standard Controls**: Uses standard HTML input types where possible to ensure native browser accessibility features work as expected.
