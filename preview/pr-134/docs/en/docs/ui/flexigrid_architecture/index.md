# <no value>
# UI: FlexiGrid Architecture

## 📊 The Generic Collection Editor

`FlexiGrid.vue` is one of the most sophisticated components in FlexiRule. It is a **recursive, schema-aware collection editor** that mimics the power of Frappe's Child Tables but with enhanced flexibility for dynamic configuration.

---

## 🛠️ Key Architectural Features

### 1. Schema-Aware Rendering

The grid accepts a `df` (DocField) object that defines its columns. Each column is rendered via the `ControlFactory`, meaning a grid cell can be a simple text input, a complex `FlexValueControl`, or even another grid.

### 2. Recursive Potential

Because it uses the `ControlFactory`, the grid is naturally recursive. This is used in actions like **Assignment** where each row needs its own complex value configuration.

### 3. State Management & Normalization

The grid uses the `useFieldNormalization` composable. This allows for:

- **Dynamic Field States**: Making a cell required, hidden, or read-only based on the values of other cells in the same row.
- **Dependency Evaluation**: Triggering backend logic as the user types to update the schema of subsequent cells.

### 4. Advanced UX Primitives

- **Sticky Columns**: Essential for large configuration tables.
- **Resize Handles**: Allowing users to customize their workspace.
- **Multi-Selection**: Batch actions like "Delete Selected."

---

## 🏗️ Generalization of Configuration

FlexiGrid is used for:

- **Assignments**: Mapping values to fields.
- **Conditions**: Defining complex multi-row logical groups.
- **API Mappings**: Connecting local variables to external webhook parameters.

This **Standardization of Collection Editing** is what makes the FlexiRule builder feel cohesive despite handling very different types of actions.

---

## 🔮 Evolution into a Visual Builder Foundation

The FlexiGrid architecture is ideally suited to become the foundation for a **Data Mapper**:

- By adding "Source" and "Target" column types, it can become a visual integration tool.
- Its ability to handle nested structures makes it prepared for complex JSON mapping and transformation UIs.
