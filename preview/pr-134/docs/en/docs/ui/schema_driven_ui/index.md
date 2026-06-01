# <no value>
# UI: Schema-Driven UI

## 🎨 The Philosophy: Metadata as UI

FlexiRule uses a **Schema-Driven Rendering** approach. The frontend does not "know" what an action's configuration looks like; it asks the backend for the "Contract."

### The Rendering Pipeline

1. **Action Selected**: User adds a "Process" action.
2. **Contract Fetch**: Frontend calls `get_contract_dto(process_name, operation)`.
3. **Schema Parsing**: The backend returns a JSON Schema of the required inputs.
4. **Dynamic Generation**: The `ControlFactory` interprets the schema and renders the appropriate Vue components.

---

## 🧩 Reusable Field Abstractions

The UI is built on a library of **Polymorphic Controls**:

- **`ComboBoxControl`**: Handles Links, Autocompletes, and "DocField" selection.
- **`MultiSelectList`**: Manages collections and multi-select tags.
- **`FlexValueControl`**: The "King" of controls—a multi-modal input that switches between static values, variable tokens, and advanced resolver builders.

---

## ⚡ FlexValueControl: The Multi-Modal Editor

This is a critical low-code primitive. It uses **Tiptap (ProseMirror)** to allow users to mix:

- **Plain Text**: Just typing.
- **@Variables**: Searching for context variables via a mention-style popup.
- ** /Resolvers**: Accessing a visual builder for Formulas, Math, and Formatting.

This turns a simple input into a **Visual Programming Interface**.

---

## 🏗️ Extensible Action Panels

Action configurations are not hardcoded forms. They are collections of fields defined in the action's contract.

- This allows a developer to add a new "Process" with 10 different input parameters, and the Rule Builder will **automatically** show the correct form with validation, without the developer writing a single line of JavaScript.

---

## 🔮 Visual Programming Concepts

FlexiRule's UI architecture is the foundation for a **Visual Builder**:

- **Polymorphic Configuration**: The same grid component used for "Assignment" can be reused for "API Parameters."
- **Recursive Rendering**: The `FlexiGrid` can contain a `ControlFactory`, which can contain another `FlexiGrid`, enabling infinite structural depth.
