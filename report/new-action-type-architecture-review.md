# FlexiRule Architecture Review: New Action Type Lifecycle

This report traces the complete lifecycle of an Action Type in FlexiRule, from definition to runtime execution.

## 1. Action Type Registration (The Contract)

The lifecycle begins in **`flexirule/ruleflow/core/contracts.py`**.

- **Required Action:** Add a new entry to the `ACTION_TYPE_CONTRACT` dictionary.
- **Payload Includes:**
    - `required_fields`: List of fields from `Rule Action` DocType that must be non-empty.
    - `has_next_true` / `has_next_false`: Boolean flags for flow branching.
    - `terminal`: Boolean flag (true if this action stops the rule).
    - `css`: Metadata for UI (icon, color).
    - `configurable`: Boolean (true if it needs a custom modal UI).
    - `config_component`: The name of the Vue component for configuration.

## 2. Backend Execution (The Handler)

Once defined, the engine needs to know how to execute it. This is handled by the Strategy Pattern in **`flexirule/ruleflow/core/action_handlers/`**.

- **Step A:** Create a new file (e.g., `my_action.py`).
- **Step B:** Inherit from `ActionHandler`.
- **Step C:** Implement `execute(self, action, context, engine)`.
    - Returns `(result, next_action_id)`.
- **Step D:** Register the handler in **`flexirule/ruleflow/core/action_handlers/__init__.py`** inside `HandlerRegistry._ensure_initialized`.

## 3. Frontend Definition (The UI Contract)

The frontend needs a fallback definition to render the node on the canvas before the API loads.

- **File:** **`flexirule/public/js/flexirule/core/contracts.js`**.
- **Action:** Add the same metadata to `DEFAULT_ACTION_TYPE_CONTRACT`.

## 4. Configuration UI (The Form)

If the action is `configurable: true`, you must provide a UI.

- **Step A:** Create a Vue component in **`flexirule/public/js/flexirule/rule_builder/components/rule_config/types/`**.
- **Step B:** Register this component in **`flexirule/public/js/flexirule/rule_builder/components/rule_config/ConfigurationPanel.vue`**.
    - Import the component.
    - Add to `componentRegistry`.
    - Add to `staticComponentMap`.

## 5. Persistence & Schema

Actions are stored in the `Rule Action` child table.

- **Fields:** Most actions use the `config` (Text Editor/JSON) field for type-specific data.
- **Validation:**
    - Frontend validation happens via `validateAgainstContract` in `contracts.js`.
    - Backend validation happens via `validation_service.py` (which uses the contract defined in step 1).

## Required vs. Optional Files

| File | Status | Purpose |
|------|--------|---------|
| `flexirule/ruleflow/core/contracts.py` | **Required** | Defines the core contract. |
| `flexirule/ruleflow/core/action_handlers/new_type.py` | **Required** | Implements execution logic. |
| `flexirule/public/js/flexirule/core/contracts.js` | **Required** | Frontend fallback/UI metadata. |
| `flexirule/public/js/flexirule/rule_builder/components/rule_config/types/NewConfig.vue` | Optional* | UI for configuration (Required if `configurable: true`). |
| `flexirule/ruleflow/doctype/rule_action/rule_action.json` | Optional | Only if the action requires a new dedicated field on the DB. |

## Sequence Diagram: Action Execution

1. `RuleEngine.execute(doc)`
2. `RuleEngine._execute_graph(context)`
3. `HandlerRegistry.get(action_type)` -> returns `MyHandler`
4. `MyHandler.execute(action, context, engine)`
5. `RuleEngine._post_process_action_result(action, result, context)`
6. `RuleEngine` looks up `next_id` and repeats.

## Areas Likely to Break

1. **Circular Imports:** When adding a new handler to `action_handlers/__init__.py`.
2. **Contract Mismatch:** If `contracts.py` (backend) and `contracts.js` (frontend) disagree on `required_fields`.
3. **Dirty State:** If the config component forgets to call `store.mark_dirty()` or updates global state during mount.
4. **Serialization:** If the `config` JSON contains non-serializable objects.
