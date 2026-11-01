import assert from "node:assert/strict";
import {
	getDirtyConfigDraftEntries,
	getOrCreateConfigDraftEntry,
	isConfigDraftEntryDirty,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/config_draft_session.js";
import { stableStringify } from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/stable_serialization.mjs";

function createNode(id, data = {}) {
	return { id, type: "action", label: id, data: { action_type: "Assignment", ...data } };
}

// Returning to an action restores the exact draft from this editing session.
{
	const entries = new Map();
	const sourceA = createNode("action-a", { value: "original-a" });
	const sourceB = createNode("action-b", { value: "original-b" });
	const draftA = getOrCreateConfigDraftEntry(entries, sourceA);
	draftA.initialDraftState = stableStringify(draftA.draftNode.data);
	draftA.draftNode.data.value = "unsaved-a";

	const draftB = getOrCreateConfigDraftEntry(entries, sourceB);
	draftB.initialDraftState = stableStringify(draftB.draftNode.data);
	draftB.draftNode.data.value = "unsaved-b";

	assert.strictEqual(getOrCreateConfigDraftEntry(entries, sourceA), draftA);
	assert.equal(draftA.draftNode.data.value, "unsaved-a");
	assert.equal(draftB.draftNode.data.value, "unsaved-b");
	assert.equal(isConfigDraftEntryDirty(draftA), true);
	assert.equal(isConfigDraftEntryDirty(draftB), true);
	assert.deepEqual(
		getDirtyConfigDraftEntries(entries)
			.map((entry) => entry.nodeId)
			.sort(),
		["action-a", "action-b"]
	);
	assert.deepEqual(
		getDirtyConfigDraftEntries(entries, "action-a").map((entry) => entry.nodeId),
		["action-b"]
	);
}

// A source node replaced without data changes can safely rebind to its new identity.
{
	const entries = new Map();
	const source = createNode("action-a", { value: "original" });
	const entry = getOrCreateConfigDraftEntry(entries, source);
	entry.initialDraftState = stableStringify(entry.draftNode.data);
	entry.draftNode.data.value = "edited";
	const replacement = createNode("action-a", { value: "original" });

	assert.strictEqual(getOrCreateConfigDraftEntry(entries, replacement), entry);
	assert.strictEqual(entry.sourceNode, replacement);
	assert.equal(entry.isStale, false);
	assert.equal(entry.draftNode.data.value, "edited");
}

// A concurrent source-data change preserves the user's edits but marks them stale.
{
	const entries = new Map();
	const source = createNode("action-a", { value: "original" });
	const entry = getOrCreateConfigDraftEntry(entries, source);
	entry.initialDraftState = stableStringify(entry.draftNode.data);
	entry.draftNode.data.value = "unsaved-local-value";
	const replacement = createNode("action-a", { value: "changed-elsewhere" });

	assert.strictEqual(getOrCreateConfigDraftEntry(entries, replacement), entry);
	assert.equal(entry.isStale, true);
	assert.strictEqual(entry.sourceNode, source);
	assert.equal(entry.draftNode.data.value, "unsaved-local-value");
}

// A clean draft follows a newer graph value instead of retaining stale data.
{
	const entries = new Map();
	const source = createNode("action-a", { value: "original" });
	const entry = getOrCreateConfigDraftEntry(entries, source);
	entry.initialDraftState = stableStringify(entry.draftNode.data);
	const replacement = createNode("action-a", { value: "changed-elsewhere" });
	const refreshed = getOrCreateConfigDraftEntry(entries, replacement);

	assert.notStrictEqual(refreshed, entry);
	assert.strictEqual(entries.get("action-a"), refreshed);
	assert.equal(refreshed.draftNode.data.value, "changed-elsewhere");
	assert.equal(isConfigDraftEntryDirty(refreshed), false);
}

// eslint-disable-next-line no-console
console.log("Config draft session tests passed");
