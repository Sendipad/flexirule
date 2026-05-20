---
title: "User Guide (Conditions)"
weight: 30
---

# User Guide: Building Logic with the Condition Builder

The Condition Builder is your primary tool for defining "When" logic in FlexiRule. Whether you are deciding if a rule should run at all or branching a workflow based on a field value, the interface remains consistent and powerful.

## 1. Creating Your First Condition

A condition consists of three parts:

1.  **Source (Left)**: What field or variable are you checking? (e.g., `doc.status`)
2.  **Operator**: How are you comparing it? (e.g., `equals`, `is set`, `greater than`)
3.  **Target (Right)**: What are you comparing it against? (e.g., a literal value like `"Open"`, or another field)

### Step-by-Step

1.  Click the **+ Condition** button.
2.  **Select Source**: Click the first box to pick a field from the current document (`doc`) or previous state (`old_doc`).
3.  **Pick Operator**: The list of operators changes automatically based on the field type. For example, you'll see "Contains" for text but "Between" or "After" for dates.
4.  **Enter Value**: Type a value, or click the `@` icon to pick another field or variable.

---

## 2. Organizing Logic with Groups (AND/OR)

Sometimes a single check isn't enough. You might need logic like:
_"If the status is Open AND (Priority is High OR the Customer is VIP)."_

### Using Groups

1.  Click **+ Group**. A new nested box appears.
2.  **Toggle Logic**: Click the **AND** or **OR** button at the top of the group.
    - **AND**: All conditions inside must be true.
    - **OR**: Only one needs to be true.
3.  **Add Sub-conditions**: Click the buttons _inside_ the group box to add conditions specifically to that container.

---

## 3. Working with Child Tables (Collections)

FlexiRule makes it easy to check conditions against lists of items (like Sales Invoice Items).

### The Collection Node

Click **+ Collection** to create a specialized loop checker.

1.  **Collection Path**: Pick the child table (e.g., `doc.items`).
2.  **Alias**: By default, this is `row`. It represents a single row in the table.
3.  **Quantifier**:
    - **Any**: True if at least one row matches.
    - **All**: True only if every single row matches.
    - **None**: True if no rows match.
4.  **Criteria**: Use the sub-builder inside the collection node to define what you are looking for in each row (e.g., `row.qty > 10`).

---

## 4. Drag-and-Drop Organization

Don't worry if you build things in the wrong order. You can easily reorganize your logic:

- **Move**: Grab the drag handle (⠿) on the left of any condition or group and move it.
- **Nesting**: Drag a condition into an existing group to include it in that group's logic.
- **Reordering**: Move conditions up or down to change the visual flow (and execution order).

---

## 5. Advanced: Field Comparisons (doc vs old_doc)

One of the most powerful uses for conditions is detecting changes.

- **Trigger Level**: Use `doc.status != old_doc.status` to make a rule run ONLY when the status field is actually modified.
- **Previous Value**: Check if a value _was_ something specific: `old_doc.status == "Draft"`.

---

## Best Practices

- **Keep it Simple**: If a condition group gets too deep (more than 3 levels), consider splitting the logic into multiple rules or sub-rules.
- **Use Clear Aliases**: When using collection nodes, use descriptive aliases like `item` or `entry` instead of just `row` if you have nested collections.
- **Check for "Is Set"**: Before comparing values of optional fields, it's often safer to first check if the field `is set`.
- **Naming**: If a condition action is complex, give the node a descriptive label (e.g., "Check VIP Eligibility") so it's easy to understand the graph at a glance.
