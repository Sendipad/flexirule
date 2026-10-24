import assert from "node:assert/strict";
import { stableStringify } from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/stable_serialization.mjs";
import { hasGraphStateChanged, shouldRecordExplicitGraphCommit } from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/graph_dirty_state.mjs";

const baselineSnapshot = [
	{
		id: "action-1",
		type: "process",
		data: {
			action_type: "Query Records",
			config: { limit: 20, fields: ["name", "customer"] },
		},
	},
];
const baseline = stableStringify(baselineSnapshot);

// Equivalent nested objects remain clean when only property insertion order changes.
const sameDataDifferentKeyOrder = [
	{
		data: { config: { fields: ["name", "customer"], limit: 20 }, action_type: "Query Records" },
		type: "process",
		id: "action-1",
	},
];
assert.equal(hasGraphStateChanged(baseline, sameDataDifferentKeyOrder), false);

// A real scalar change or an array-order change must remain dirty.
assert.equal(
	hasGraphStateChanged(baseline, [
		{
			id: "action-1",
			type: "process",
			data: {
				action_type: "Query Records",
				config: { fields: ["name", "customer"], limit: 50 },
			},
		},
	]),
	true
);
assert.equal(
	hasGraphStateChanged(baseline, [
		{
			id: "action-1",
			type: "process",
			data: {
				action_type: "Query Records",
				config: { fields: ["customer", "name"], limit: 20 },
			},
		},
	]),
	true
);
assert.equal(hasGraphStateChanged(null, sameDataDifferentKeyOrder), false);

// Explicit user commits are not suppressed just because the baseline is not ready yet.
assert.equal(
	shouldRecordExplicitGraphCommit({
		isReadOnly: false,
		initialState: null,
		currentSnapshot: sameDataDifferentKeyOrder,
	}),
	true
);

// No-op commits stay clean, while read-only rules can never be committed.
assert.equal(
	shouldRecordExplicitGraphCommit({
		isReadOnly: false,
		initialState: baseline,
		currentSnapshot: sameDataDifferentKeyOrder,
	}),
	false
);
assert.equal(
	shouldRecordExplicitGraphCommit({
		isReadOnly: true,
		initialState: baseline,
		currentSnapshot: sameDataDifferentKeyOrder,
	}),
	false
);

console.log("graph dirty-state tests passed");
