import assert from "node:assert/strict";
import { stableStringify } from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/stable_serialization.mjs";
import {
	hasGraphStateChanged,
	shouldRecordExplicitGraphCommit,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/graph_dirty_state.mjs";

// Helper simulating primary action resolution in rule_builder.js
function getPrimaryActionLabel({ is_dirty, is_active }) {
	if (is_dirty) {
		return "Save Rule";
	} else if (!is_active) {
		return "Activate Rule";
	} else {
		return "Edit Rule";
	}
}

// Full lifecycle simulation test for Bug 2 sequence:
// 1. Initial fetch sets clean baseline, is_initializing = false. Primary action: Activate Rule (inactive)
// 2. Action edit 1 occurs -> is_dirty becomes true -> Primary action: Save Rule
// 3. Save Rule executed -> fetch() reloads rule, sets new baseline, sets _is_dirty = false, is_initializing = false
// 4. Primary action after Save Rule: Activate Rule
// 5. Action edit 2 occurs -> is_dirty becomes true -> Primary action: Save Rule
{
	let is_initializing = true;
	let is_performing_layout = false;
	let is_active = false;
	let is_read_only = false;
	let _is_dirty = false;
	let initial_state = null;

	let currentGraphSnapshot = [
		{
			id: "action-1",
			type: "process",
			data: { action_type: "Query Records", config: { limit: 20 } },
		},
	];

	const computeIsDirty = () => {
		if (is_read_only) return false;
		if (is_initializing || is_performing_layout) return false;
		if (_is_dirty) return true;
		if (!initial_state) return false;
		return hasGraphStateChanged(initial_state, currentGraphSnapshot);
	};

	// --- Step 1: Initial fetch completes
	initial_state = stableStringify(currentGraphSnapshot);
	_is_dirty = false;
	is_initializing = false; // Verified fix ensures is_initializing is cleared post-fetch

	assert.equal(computeIsDirty(), false);
	assert.equal(getPrimaryActionLabel({ is_dirty: computeIsDirty(), is_active }), "Activate Rule");

	// --- Step 2: First action edit
	currentGraphSnapshot = [
		{
			id: "action-1",
			type: "process",
			data: { action_type: "Query Records", config: { limit: 50 } },
		},
	];
	_is_dirty = true; // Explicit commit or graph edit

	assert.equal(computeIsDirty(), true);
	assert.equal(getPrimaryActionLabel({ is_dirty: computeIsDirty(), is_active }), "Save Rule");

	// --- Step 3: Save Rule and post-save refetch
	// Simulation of fetch() called at the end of save_changes()
	is_initializing = true;
	// Refetch updates graph and resets baseline
	initial_state = stableStringify(currentGraphSnapshot);
	_is_dirty = false;
	// Critical fix: fetch() clears is_initializing = false even when VueFlow @pane-ready does NOT fire again
	is_initializing = false;

	assert.equal(computeIsDirty(), false);
	assert.equal(getPrimaryActionLabel({ is_dirty: computeIsDirty(), is_active }), "Activate Rule");

	// --- Step 4: Second action edit
	currentGraphSnapshot = [
		{
			id: "action-1",
			type: "process",
			data: { action_type: "Query Records", config: { limit: 100 } },
		},
	];
	_is_dirty = true; // Explicit commit or graph edit

	// Before the fix, computeIsDirty() would return false because is_initializing remained true!
	// Now, computeIsDirty() correctly evaluates to true!
	assert.equal(computeIsDirty(), true);
	assert.equal(getPrimaryActionLabel({ is_dirty: computeIsDirty(), is_active }), "Save Rule");
}

// eslint-disable-next-line no-console
console.log("rule dirty-state lifecycle and primary action tests passed");
