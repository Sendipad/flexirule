# FlexiRule Action Type Future-Proofing & Design

## Scalability Evaluation

The current FlexiRule architecture is extensible but not fully scalable for a high volume of action types or third-party plugins.

| Question | Answer | Reason |
|----------|--------|--------|
| **Can action types be added without touching multiple unrelated files?** | No | Requires touching backend handlers, contracts, DocType JSON, and frontend registry. |
| **Are there violations of Open/Closed Principle?** | Partial | The `HandlerRegistry` obeys it, but the `Rule Action` DocType and `globals.js` violate it. |
| **Is metadata duplicated?** | Yes | Duplicated in `contracts.py`, `contracts.js` fallbacks, and `rule_action.json`. |
| **Are frontend/backend contracts centralized?** | Partial | `contracts.py` is the source, but consumption is still manual in several places. |
| **Can third-party action plugins be added?** | No | Requires manual modification of core DocTypes and frontend files. |
| **Is action discovery automatic?** | No | Imports and registrations are manual. |
| **Is testing standardized?** | Yes | The strategy pattern makes unit testing individual handlers easy. |

## Architectural Weaknesses
1. **The Select Field Bottleneck:** The `action_type` field in `Rule Action` must be updated for every type. This prevents plugin-based actions.
2. **Hardcoded UI Imports:** The frontend bundle grows with every new action type because all config components are imported and registered globally.
3. **Implicit Validation:** Backend validation in `validation_service.py` often relies on `if action_type == '...'` blocks instead of polymorphic methods on the handler.

---

## Recommended Future-Proof Design

### 1. Backend: Automatic Discovery & Registry Improvements

**A. Plugin-Capable Discovery:**
Instead of manual imports in `__init__.py`, the `HandlerRegistry` should scan a designated namespace or use Frappe's `hooks.py` to find registered handlers.

```python
# hooks.py
flexirule_action_handlers = [
    "myapp.my_module.handlers.MyCustomHandler"
]
```

**B. Contract-Driven Validation:**
The `ActionHandler` base class should define the contract. This eliminates the central `contracts.py` file being a bottleneck.

```python
class MyHandler(ActionHandler):
    action_type = "My Action"
    def get_contract(self):
        return {
            "required_fields": ["config"],
            "css": {"icon": "fa fa-plug", "color": "#000"}
        }
```

**C. Decoupled DocType Options:**
Change `action_type` in `Rule Action` from a `Select` to a `Data` or `Link` field (to a virtual DocType) to allow dynamic registration of types without schema changes.

### 2. Frontend: Dynamic Component Loading

**A. Metadata-Driven Registry:**
The frontend should use Vite's dynamic imports to load configuration components on demand based on the `config_component` name received in the contract DTO.

```javascript
// Dynamic resolver
const getComponent = (name) => defineAsyncComponent(() => import(`./types/${name}.vue`));
```

**B. Composition API standard for Configs:**
Establish a strict interface (composable) for configuration components to reduce boilerplate and coupling.

```javascript
// useActionConfig.js
export function useActionConfig(props) {
    const { node, ruleStore } = props;
    const config = computed({
        get: () => node.data.config,
        set: (val) => {
             node.data.config = val;
             ruleStore.mark_dirty();
        }
    });
    return { config };
}
```

### 3. Unified Validation Bridge
Implement a system where backend validation rules can be exported as JSON Schema and consumed by the frontend (using `ajv` or similar) to ensure 100% consistency.

---

## Migration Strategy

### Step 1: Decentralize Contracts (Incremental)
- Allow `ActionHandler` classes to define their own contracts.
- Update `get_contract_dto` API to aggregate contracts from all registered handlers.
- **Risk:** Low. Backward compatible with `ACTION_TYPE_CONTRACT` dictionary.

### Step 2: Dynamic UI Loading
- Update `ConfigurationPanel.vue` to use `shallowRef` and dynamic imports.
- Stop registering all `*Config.vue` components in `globals.js`.
- **Risk:** Medium. Requires ensuring all components are in the expected directory for Vite to bundle them as chunks.

### Step 3: DocType Decoupling
- Change `Rule Action` `action_type` to an `Autocomplete` or `Data` field.
- Remove hardcoded options from JSON.
- **Risk:** High. Requires a patch to ensure existing rule actions maintain their types.

### Implementation Order:
1. Dynamic UI Loading (reduces bundle size).
2. Decentralize Contracts (enables discovery).
3. Discovery via Hooks (enables plugins).
4. DocType Decoupling (final separation).

---

## Conclusion

If FlexiRule wants to add a new Action Type six months from now, the goal should be:
1. Create a Python class (logic).
2. Create a Vue file (UI).
3. Register the Python class in `hooks.py`.
**Nothing else should break.** The builder should automatically see the new type, load its metadata, and render its UI component.
