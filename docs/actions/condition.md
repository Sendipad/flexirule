# Condition Action

The **Condition** action allows for branching execution logic based on the evaluation of a Python expression.

## Visual Builder

Conditions are built using the visual Condition Builder, which supports:

- **Hierarchical Grouping**: Combine conditions using `AND` and `OR` logic.
- **Drag-and-Drop**: Easily restructure logic by dragging conditions between groups.

## Execution

- **Compiled Logic**: Design-time JSON is compiled into an optimized Python string for runtime execution.
- **Branches**:
    - `True`: Followed if the condition evaluates to true.
    - `False`: Followed if the condition evaluates to false.

## Context Access

Conditions can access the current document (`doc`), the previous state (`old_doc`), and context variables (`vars`).
