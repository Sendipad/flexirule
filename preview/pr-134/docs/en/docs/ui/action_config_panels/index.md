# <no value>
# UI: Action Config Panels

## 📦 Encapsulating Action Logic

The Rule Builder uses a modular approach to action configuration. Instead of one massive form, it uses **Config Panels** that correspond to specific action types.

### Primary Config Panels

#### 1. `AssignmentConfig.vue`

- **Purpose**: Batch state mutation.
- **Architecture**: A `FlexiGrid` where each row represents a "Target Path" and a "Value Resolver."
- **Complexity**: It manages a list of mutations that are executed sequentially by the engine.

#### 2. `ConditionBuilder`

- **Purpose**: Visual logical branching.
- **Architecture**: A recursive component that builds nested groups of AND/OR conditions.
- **Output**: Generates a standardized JSON structure that the `ConditionCompiler` can turn into Python.

#### 3. `SwitchNodeConfig.vue`

- **Purpose**: Multi-path branching.
- **Architecture**: A dynamic list of cases where each case is a compiled condition.

#### 4. `LoopNodeConfig.vue`

- **Purpose**: Iteration over collections.
- **Architecture**: Configures the collection path and the alias variable to be used within the loop body.

---

## 🎨 Design Patterns for Extensibility

### Generic Component Strategy

Most panels are built using a common set of controls (`ComboBoxControl`, `FlexValueControl`). This ensures that the look and feel is consistent and that performance optimizations (like tippy.js popups) are shared.

### Metadata-Driven Metadata

For "Process" actions, the config panel is **entirely dynamic**.

- The frontend doesn't have a `ProcessConfig.vue`.
- Instead, it uses the `ControlFactory` to loop through the Process Operation's `config_schema` and render the required inputs.
- This is the ultimate form of **Low-Code UI**: The form creates itself from the code's documentation.

---

## 🚀 Scaling Future Action UIs

Because the system is metadata-driven, adding a new action UI usually just involves:

1. Defining the contract in the backend.
2. (Optional) Creating a specialized Vue component if the generic UI isn't sufficient.
3. Registering the component in the `ActionPopover`.
