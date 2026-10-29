import assert from "node:assert/strict";
import { createGroup } from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/tree_builder/tree_builder_utils.mjs";
import {
	addLeaf,
	moveNodeDown,
	moveNodeUp,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/tree_builder/tree_builder_commands.mjs";
import { getInlinePresentation } from "../../../../../../flexirule/public/js/flexirule/rule_builder/controls/inline_presentation_policy.mjs";

// Global translation shim for node test runner environment
if (typeof globalThis.__ !== "function") {
	globalThis.__ = (str) => str;
}

// 1. Test moveNodeUp and moveNodeDown commands
const root = createGroup("and", []);
const leaf1 = addLeaf(root, root.id, { field: "a", operator: "=", value: 1 });
const leaf2 = addLeaf(root, root.id, { field: "b", operator: "=", value: 2 });
const leaf3 = addLeaf(root, root.id, { field: "c", operator: "=", value: 3 });

// Moving leaf1 up when it's at index 0 should fail
assert.equal(moveNodeUp(root, leaf1.id), false);

// Moving leaf2 up should swap leaf1 and leaf2 -> [leaf2, leaf1, leaf3]
assert.equal(moveNodeUp(root, leaf2.id), true);
assert.equal(root.children[0].id, leaf2.id);
assert.equal(root.children[1].id, leaf1.id);

// Moving leaf3 down when it's at index 2 (the end) should fail
assert.equal(moveNodeDown(root, leaf3.id), false);

// Moving leaf1 down should move it from index 1 to index 2 -> [leaf2, leaf3, leaf1]
assert.equal(moveNodeDown(root, leaf1.id), true);
assert.equal(root.children[2].id, leaf1.id);

// Moving leaf1 down now that it's at the end should fail
assert.equal(moveNodeDown(root, leaf1.id), false);

console.log("tree builder moveNodeUp and moveNodeDown unit tests passed");

// 2. Test GenericGrid row action menu builder model logic
function mockGetRowMenuActions(entry, totalRows, options = {}) {
	const {
		readOnly = false,
		showRowActions = true,
		availableRowActions = ["edit", "move", "remove"],
		selection = true,
		isEditing = false,
	} = options;

	if (readOnly || !showRowActions) return [];

	const presentation = getInlinePresentation({
		mode: "hybrid",
		isNew: false,
		isValid: true,
		isEditing,
		readOnly,
		hasSummary: true,
	});

	const items = [];

	if (availableRowActions.includes("edit")) {
		if (presentation.presentation === "summary" && presentation.canToggle) {
			items.push({ id: "edit", label: "Edit row", icon: "fa fa-pencil" });
		} else if (presentation.presentation === "editor") {
			items.push({ id: "finish", label: "Finish editing", icon: "fa fa-check" });
		}
	}

	if (selection) {
		items.push({ id: "select", label: "Select row", icon: "fa fa-mouse-pointer" });
	}

	if (availableRowActions.includes("move")) {
		items.push({
			id: "move-up",
			label: "Move row up",
			disabled: entry.index === 0,
		});
		items.push({
			id: "move-down",
			label: "Move row down",
			disabled: entry.index === totalRows - 1,
		});
	}

	if (availableRowActions.includes("remove")) {
		items.push({ id: "delete", label: "Remove row", danger: true });
	}

	return items;
}

// First row in 3-row grid
const row0Actions = mockGetRowMenuActions({ index: 0, key: "r1" }, 3);
assert.ok(row0Actions.some((a) => a.id === "edit"));
assert.ok(row0Actions.some((a) => a.id === "select"));
const moveUpRow0 = row0Actions.find((a) => a.id === "move-up");
assert.equal(moveUpRow0.disabled, true);
const moveDownRow0 = row0Actions.find((a) => a.id === "move-down");
assert.equal(moveDownRow0.disabled, false);

// Last row in 3-row grid
const row2Actions = mockGetRowMenuActions({ index: 2, key: "r3" }, 3);
const moveUpRow2 = row2Actions.find((a) => a.id === "move-up");
assert.equal(moveUpRow2.disabled, false);
const moveDownRow2 = row2Actions.find((a) => a.id === "move-down");
assert.equal(moveDownRow2.disabled, true);

// Editing state row
const editingRowActions = mockGetRowMenuActions({ index: 1, key: "r2" }, 3, { isEditing: true });
assert.ok(editingRowActions.some((a) => a.id === "finish"));

console.log("generic grid action menu model unit tests passed");
