import assert from "node:assert/strict";
import {
	regenerateNodeIds,
	useTreeBuilderActions,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/tree_builder/useTreeBuilderActions.js";

// 1. Test regenerateNodeIds
const nodeWithChildren = {
	id: "original-parent",
	type: "group",
	children: [
		{ id: "child-1", type: "leaf", field: "status" },
		{ id: "child-2", type: "leaf", field: "amount" },
	],
};

const cloned = JSON.parse(JSON.stringify(nodeWithChildren));
regenerateNodeIds(cloned);
assert.notEqual(cloned.id, "original-parent");
assert.notEqual(cloned.children[0].id, "child-1");
assert.notEqual(cloned.children[1].id, "child-2");

// 2. Test useTreeBuilderActions
let removeCalledWith = null;
let addLeafCalledWith = null;

const fakeTreeApi = {
	root: { id: "root", children: [] },
	removeNode(id) {
		removeCalledWith = id;
	},
	addLeaf(parentId) {
		addLeafCalledWith = parentId;
	},
	setEditing() {},
	finishEditing() {},
	selectNode() {},
};

let guardChecked = false;
const beforeRemove = (nodeId) => {
	guardChecked = true;
	return nodeId !== "protected-node";
};

const actions = useTreeBuilderActions({
	treeApi: fakeTreeApi,
	readOnly: false,
	beforeRemove,
});

const leafContext = {
	node: { id: "leaf-1", type: "leaf" },
	parent: { id: "root", children: [] },
	index: 0,
	isEditing: false,
	hasSummarySlot: true,
	canToggle: true,
	canFinishEditing: false,
};

const list = actions.getNodeActionList(leafContext);
assert.ok(list.length >= 4, "Should have edit, select, insert, duplicate, remove");

// Test guarded removal
await actions.removeCommand.execute({ node: { id: "leaf-1" } });
assert.equal(guardChecked, true);
assert.equal(removeCalledWith, "leaf-1");

// Test blocked removal
guardChecked = false;
removeCalledWith = null;
await actions.removeCommand.execute({ node: { id: "protected-node" } });
assert.equal(guardChecked, true);
assert.equal(removeCalledWith, null, "Protected node must not be removed");

console.log("useTreeBuilderActions unit tests passed");
