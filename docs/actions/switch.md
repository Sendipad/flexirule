# Switch Action

The **Switch** action enables multi-path branching based on the value of an expression. It functions similarly to a `switch` statement in programming or a router in logic flows.

## Configuration

- **Expression**: A Python expression that evaluates to a value (e.g., `doc.status` or `vars.category`).
- **Cases**: A mapping of expected values to target Action IDs.
- **Default Path**: If no case matches the expression's value, execution follows the `next_step_if_false` (labeled as "Default" in the UI) path.

## Execution Logic

1. The engine evaluates the **Expression**.
2. It attempts to match the result against the defined **Cases** (using both raw value and string comparison).
3. If a match is found, it jumps to the corresponding action.
4. If no match is found, it follows the **Default** path.

## Use Cases

- **Document Routing**: Direct a document to different approval paths based on its status.
- **Category Handling**: Apply different logic based on a "Type" or "Category" field without nesting multiple `Condition` nodes.
- **Error Code Handling**: Branch execution based on the specific result of a `Process` or `Query` action.
