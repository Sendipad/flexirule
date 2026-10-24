# Rule Builder visual layout persistence contract

## Authoritative state

`Rule.actions` is the source of truth for action existence, action type, labels,
configuration, and executable graph structure. `Rule.visual_data` is only a
supplement for layout metadata: positions, direction, edge layout metadata, and
UI layout preferences. Visual layout data must not create, resurrect, or
reconfigure an action that is absent from `Rule.actions`.

## Visual-only nodes are currently unsupported

Standalone visual-only nodes such as annotations, notes, or free-form labels are
not a supported persisted Rule Builder feature in the current contract. The
serializer may emit layout records for nodes in memory, but the loader only
applies those records to nodes reconstructed from authoritative action data.
Orphan visual records are deliberately ignored on load and must not be restored
as graph nodes.

This is intentional: the current persistence model has no dedicated storage
contract for visual-only node content, and restoring such nodes risks either
losing their content on reload or allowing visual records to influence the
executable graph.

If standalone visual-only nodes become a product requirement, implement them as
a separate, explicit schema with their own identity, content, lifecycle, and
round-trip tests. They must remain excluded from `Rule.actions`, action
validation, and execution topology. Do not add their content to ordinary action
records in `visual_data`.

## Regression expectations

- Existing action data and labels come from `Rule.actions`, not `visual_data`.
- Matching visual records can update layout but cannot overwrite action data.
- A stale visual record for a deleted action does not resurrect that action.
- An orphan visual-only record is ignored, consistent with the unsupported-feature
  decision above.
