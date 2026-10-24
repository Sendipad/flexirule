# Rule Builder persistence contract

## Action-backed graph nodes

`doc.actions` is the authoritative persisted representation of Rule actions and their configuration. `Rule.visual_data` is auxiliary layout state: node positions/directions, edge presentation metadata, and UI layout preferences. It must not duplicate action configuration or restore deleted action records.

## Standalone visual-only nodes are not currently supported

Annotations, sticky notes, and other standalone visual-only nodes are not a supported persisted Rule Builder feature. The contract is deliberately strict:

- The visual-layout serializer omits nodes explicitly marked `is_visual_only` and edges attached to them.
- The Rule save path rejects a graph containing an explicitly marked visual-only node. It must not silently turn such a node into a default `Process` action.
- During graph hydration, visual records without a corresponding node reconstructed from persisted Rule actions are ignored. They are not restored as actions or annotations.

If standalone annotations or other visual-only nodes become a product feature, they need a separate, versioned persistence contract for identity, type, content, and layout. That feature must keep visual-only records out of action validation and execution and must include a complete save/reload round-trip test. Do not relax the current behavior by restoring orphan records alone.

## Workspace route guard

The Frappe `Workspace.show_page` guard only skips a page lookup when workspace pages are loaded, the selected page list is well-formed, and the requested page is absent from that list. Valid pages delegate to Frappe's original method. The guard does not catch errors raised by the original method; unrelated navigation failures must remain visible to Cypress.
