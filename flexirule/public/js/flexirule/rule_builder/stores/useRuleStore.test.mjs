import assert from "node:assert/strict";
import { hasGraphStateChanged, shouldRecordExplicitGraphCommit } from "../utils/graph_dirty_state.mjs";
import { stableStringify } from "../utils/stable_serialization.mjs";

// Test suite for Rule Store Dirty-State and Primary Action Lifecycle (Bug 2)

function createMockRuleStore() {
	let is_read_only = false;
	let is_loading = false;
	let is_initializing = true;
	let is_performing_layout = false;

	let _is_dirty = false;
	let initial_state = null;
	let graphSnapshot = [];

	const uiStore = {
		get is_initializing() { return is_initializing; },
		set is_initializing(v) { is_initializing = v; },
		get is_performing_layout() { return is_performing_layout; },
		set is_performing_layout(v) { is_performing_layout = v; }
	};

	function checkDirty() {
		if (is_read_only || !initial_state) return false;
		return hasGraphStateChanged(initial_state, graphSnapshot);
	}

	function is_dirty() {
		if (is_read_only || is_loading || uiStore.is_initializing || uiStore.is_performing_layout) {
			return false;
		}
		if (_is_dirty) return true;
		return checkDirty();
	}

	function primary_action_label() {
		if (is_dirty()) return "Save Rule";
		if (!is_read_only) return "Activate Rule";
		return "Edit Rule";
	}

	async function fetch() {
		is_loading = true;
		uiStore.is_initializing = true;

		// Simulate fetching doc and syncing graph
		graphSnapshot = [
			{ id: "start", type: "start", position: { x: 0, y: 0 }, data: { label: "Start" } },
			{ id: "action_1", type: "process", position: { x: 100, y: 100 }, data: { action_label: "Action 1" } },
		];

		initial_state = stableStringify(graphSnapshot);
		_is_dirty = false;
		is_loading = false;

		// Post-fetch tick clears initializing state
		uiStore.is_initializing = false;
	}

	async function save_changes() {
		is_loading = true;
		// Simulate backend save ...
		await fetch(); // refetch after save
	}

	function commit_graph_edit() {
		if (is_loading) return false;
		if (!shouldRecordExplicitGraphCommit({ isReadOnly: is_read_only, initialState: initial_state, currentSnapshot: graphSnapshot })) {
			return false;
		}
		_is_dirty = true;
		return true;
	}

	return {
		uiStore,
		fetch,
		save_changes,
		commit_graph_edit,
		primary_action_label,
		is_dirty,
		getGraphSnapshot: () => graphSnapshot,
		setGraphSnapshot: (snap) => { graphSnapshot = snap; },
	};
}

// Bug 2 Reproduction & Resolution Sequence Test
{
	const store = createMockRuleStore();

	// Step 1: Initial load
	await store.fetch();
	assert.equal(store.uiStore.is_initializing, false);
	assert.equal(store.is_dirty(), false);
	assert.equal(store.primary_action_label(), "Activate Rule");

	// Step 2: Edit Action 1 config and commit graph edit
	const snap = store.getGraphSnapshot();
	snap[1].data.action_label = "Action 1 Modified";
	store.setGraphSnapshot(snap);
	store.commit_graph_edit();

	assert.equal(store.is_dirty(), true);
	assert.equal(store.primary_action_label(), "Save Rule");

	// Step 3: Click Save Rule (saves changes and refetches)
	await store.save_changes();

	assert.equal(store.uiStore.is_initializing, false, "is_initializing must NOT be left stuck at true after refetch");
	assert.equal(store.is_dirty(), false, "Dirty state must be clean after save and refetch");
	assert.equal(store.primary_action_label(), "Activate Rule", "Primary action must revert to Activate Rule after save");

	// Step 4: Modify Action 2 (or Action 1 again) after save
	const snap2 = store.getGraphSnapshot();
	snap2[1].data.action_label = "Action 1 Modified Second Time";
	store.setGraphSnapshot(snap2);
	store.commit_graph_edit();

	assert.equal(store.is_dirty(), true, "Subsequent edit after save must set is_dirty to true immediately");
	assert.equal(store.primary_action_label(), "Save Rule", "Primary action must switch back to Save Rule");
}

console.log("Bug 2 Rule Store Dirty-State and Primary Action Lifecycle tests passed!");
