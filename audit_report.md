# FlexiRule Add Action Discovery & Search Architecture Audit

## 1. Add Action Flow

### Flow Trace

1.  **Trigger**: User clicks the `+` button on an edge (`AddNodeEdge.vue`).
2.  **Popover**: `ActionPopover.vue` is displayed at the click position.
3.  **Discovery**: User searches or browses for an action/operation.
4.  **Selection**: User selects an item, emitting a `select` event with a payload:
    ```json
    {
	"action_type": "Process",
	"operation": "create_invoice",
	"process_name": "Sales",
	"label": "Process: Create Invoice"
    }
    ```
5.  **Insertion**: `App.vue` receives `insertNodeOnEdge` and calls `graphStore.insert_node_on_edge`.
6.  **Graph Update**: `useGraphStore.js` creates a new node (via `get_default_node_data`), deletes the old edge, and creates two new edges (Source -> NewNode -> Target).
7.  **Auto-Config**: If the action is `Condition`, `Loop`, or `Switch`, `ruleStore.open_config` is triggered.
8.  **Layout**: `layoutGraph` is called to recalculate visual positions.

### Component Map

- **AddNodeEdge**: Edge component that renders the `+` trigger and holds the `ActionPopover`.
- **ActionPopover**: The search and selection UI.
- **ActionSelectorNode**: An alternative "in-graph" selector used when a selector node is explicitly added.
- **useGraphStore**: Pinia store managing the graph topology and node insertion logic.
- **useRuleStore**: Pinia store managing the underlying Rule JSON and synchronization with the backend.

### Data Flow

`User Click` -> `AddNodeEdge` -> `ActionPopover (discover)` -> `App.vue (emit)` -> `useGraphStore (execute)` -> `VueFlow (render)`

---

## 2. AddActionPopover (ActionPopover.vue) Analysis

### Search Architecture

The component uses a **local, weighted scoring engine** calculated on every keystroke.

- **Logic**: Uses `scoreText(text, query)` which returns 0-100.
    - Exact Match: 100
    - Prefix Match: 70
    - Word-Start Match: 60 (`" ${needle}"`)
    - Substring Match: 45
    - Acronym Match: 35 (e.g., "dq" matches "Document Query")
    - Multi-word coverage: 25
- **Scoped Search**: Supports `Scope: Operation` syntax via `parseScopedQuery`. If a query starts with `:` or includes `:`, it isolates the search to a specific Action Type.
- **Keyboard Navigation**: Managed via `selectedIndex` and `onKeydown`. Arrows move between items, skipping headers.
- **Selection Flow**: `selectItem` maps the search result back to the Action/Operation/Process schema and emits it.

### Features & Limitations

- **Strengths**: Instant response (no network round-trip), excellent acronym support for power users, intuitive scoped search.
- **Limitations**:
    - **Logic Fragmentation**: Search logic is duplicated and slightly different in `ActionSelectorNode.vue`.
    - **No Typo Tolerance**: Strictly substring or acronym based.
    - **Scalability**: Fetching all Process Operations into a single frontend registry may impact boot time as the library of processes grows.

---

## 3. Search Architecture (Backend vs Frontend)

### Current Implementation

- **Frontend**: Custom weighted matching. Strong on acronyms and scoped queries.
- **Backend**: `search_service.py` exists with `rapidfuzz` support. Strong on typo tolerance and global indexing.

### Comparison

| Feature             | Frontend (Current) | Backend (Search Service) |
| :------------------ | :----------------- | :----------------------- |
| **Typo Tolerance**  | Low (None)         | High (Fuzzy)             |
| **Acronym Support** | High               | Low                      |
| **Latency**         | 0ms                | 50-200ms                 |
| **Data Freshness**  | Boot-time DTO      | Real-time DB Query       |

---

## 4. Data Sources

- **Action Types**: Defined in `ACTION_TYPE_CONTRACT` via `CONTRACT_DTO`.
- **Native Operations**: Defined in `OPERATION_REGISTRY` / `OPERATION_CONTRACT`.
- **Process Operations**: Loaded via `PROCESS_REGISTRY` (DTO) with a fallback to `get_all_process_operations` API.
- **Clipboard**: Sourced from `localStorage` (`flexirule-clipboard`).

---

## 5. Process Architecture Integration

- **Discovery**: Process operations are flattened from the `PROCESS_REGISTRY`.
- **DTO Dependencies**: High dependency on a large contract DTO sent to the frontend.
- **Tradeoffs of First-Class Search**: Making Process Operations first-class searchable entities (competing with Action Types) would improve discovery speed but might clutter the UI if not ranked correctly. Currently, they are grouped separately.

---

## 6. ComboBoxControl Investigation

- **Reuse Potential**: Low to Moderate.
- **Gains**: Standardized keyboard handling, shared "Link" UI patterns.
- **Losses**: Scoped search syntax, custom header/category layouts, weighted acronym scoring.
- **Verdict**: `ActionPopover` is a specialized discovery tool; forcing it into a `ComboBoxControl` would likely result in more "hacky" slot code than the current dedicated component.

---

## 7. FlexValueControl Investigation

- **Comparison**: `FlexValueControl` uses `/` and `@` triggers for inline formula/variable selection.
- **Pattern Reuse**: The "metadata density" (showing description + icon + category) should be aligned, but the "popover" discovery pattern is more appropriate for adding nodes than the "type-to-trigger" pattern.

---

## 8. Clipboard / Paste Action

- **Storage**: JSON string in `localStorage`.
- **Flow**: `paste_on_edge` in `useGraphStore` handles ID remapping to prevent collisions.
- **Recommendation**: Keep "Paste Action" as a pinned top item. Do not make it a searchable entity unless it's a secondary discovery path.

---

## 9. Backend Search & Extensibility

- **Frappe Infrastructure**: Can leverage `frappe.search.link` or AwesomeBar ranking utilities.
- **Recommendation**: A backend-owned **Action Registry** is the superior architectural choice for:
    - AI-assisted discovery.
    - Usage-based ranking (global or user-specific).
    - Shared "Favorites" across devices.

---

## 10. Recommendations

### 1. Minimal Improvement Path

- **Actions**: Extract search logic to a shared composable; add "Paste" as a searchable keyword.
- **Complexity**: Low.
- **Risk**: Low.
- **Backward Compatibility**: 100%.

### 2. Recommended Architecture Path

- **Actions**: Implement a hybrid model. Keep core Action Types in frontend for instant access, but offload Process Operation search to a debounced backend API.
- **Complexity**: Medium.
- **Risk**: Minor UX flicker if network is slow.
- **Backward Compatibility**: Requires backend API update.

### 3. Long-term Architecture Path

- **Actions**: Full Backend Action Registry. All discovery goes through a unified "Action Search" API with AI ranking boosters and usage analytics.
- **Complexity**: High.
- **Risk**: High implementation cost; requires robust caching for performance.
- **Backward Compatibility**: Major architectural shift.
