# Action Types Reference

FlexiRule provides a variety of action types, each represented as a node in the visual builder. These actions define the building blocks of your business logic.

## Control Flow Actions

| Action           | Purpose                                                        | Branches                 |
| :--------------- | :------------------------------------------------------------- | :----------------------- |
| **Entry Action** | The starting point of every rule. Holds trigger configuration. | `Next`                   |
| **Condition**    | Evaluates a Python expression to branch logic.                 | `True`, `False`          |
| **Loop**         | Iterates over a collection (e.g., child table).                | `For Each`, `After Last` |
| **Wait**         | Pauses execution for a specified duration.                     | `Next`                   |
| **Sub-Rule**     | Calls another rule as a subroutine.                            | `Next`                   |

## Data & Logic Actions

### **Process**

Executes reusable business logic defined in a `Process` DocType. This is the primary way to extend FlexiRule with custom Python code.

- **Inputs**: Defined by the Operation's `config_schema`.
- **Outputs**: Defined by the Operation's `output_schema`.
- **Mutation Logic**: Processes are designed to be side-effect free. They return results (data) or explicit **Mutation Intents**. The Rule Engine is responsible for applying these changes (e.g., updating a document field or context variable) based on the **Mutation Mode** selected by the rule designer.

### **Set Value**

Updates a field or variable using a Jinja template.

- **Targets**: `Current Document`, `Context Variable`, or `Reference Document`.
- **Mutation Modes**: `Set`, `Update` (for dicts), `Append` (for lists).

### **Query Records**

Retrieves data from the database.

- **Operations**: `Query List`, `Query Doc`, `Exist Record`, `Count`, `Sum`, `Average`, `Min`, `Max`, `Group By`.
- **Filters**: Visual filter builder with support for dynamic variable values.

### **Document Action**

Standard CRUD and social operations on DocTypes.

- **Operations**: `Create New`, `Update Existing`, `Delete Record`, `Create ToDo`, `Add Comment`.
- **Mappings**: Direct mapping of data to fields.

---

## Utility & Notification Actions

### **Notify**

Communicates with the user or external systems.

- **Channels**: `Toast`, `System Notification`, `Email`, `External Provider`.
- **Dynamic Content**: Uses Jinja templates for subjects and messages.

### **Stop**

The final node of a path.

- **Success**: Ends execution and marks the path as successful.
- **Error**: Aborts the current operation and raises a custom error message to the user.

### **Raise Error**

Immediately terminates the rule by throwing a Python exception. Used for strict validation where the process should not continue under any circumstances.

---

## Technical Details

### **Action Contracts**

Every action type is governed by a **Contract** defined in `flexirule/ruleflow/core/contracts.py`. This contract specifies:

- Required configuration fields.
- Available outgoing handles (True/False/Default).
- Allowed **Mutation Modes** (e.g., whether it can update the document).
- Expected **Return Types**.

### **Action Handlers**

The actual execution logic for each action type is implemented in a corresponding `ActionHandler` in `flexirule/ruleflow/core/action_handlers/`.
