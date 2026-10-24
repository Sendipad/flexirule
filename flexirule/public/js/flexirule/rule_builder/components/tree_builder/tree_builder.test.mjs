import assert from "node:assert/strict";
import {
	createGroup,
	createLeaf,
	findNode,
	findParent,
	findPath,
	normalizeTree,
} from "./tree_builder_utils.mjs";
import {
	addCollection,
	addGroup,
	addLeaf,
	moveNode,
	removeNode,
	setOperator,
} from "./tree_builder_commands.mjs";
import { validateTree } from "./tree_builder_validation.mjs";
import { useTreeBuilder } from "./useTreeBuilder.js";
import {
	deserializeQueryFilters,
	serializeQueryFilters,
} from "../rule_config/query_filters/query_filter_serializer.mjs";

const root = createGroup("and", []);
const group = addGroup(root, root.id, "or");
const leaf = addLeaf(root, group.id, { field: "qty", operator: ">", value: 10 });
assert.equal(findParent(root, leaf.id), group);
assert.deepEqual(
	findPath(root, leaf.id).map((node) => node.id),
	[root.id, group.id, leaf.id]
);
assert.equal(findNode(root, group.id).operator, "or");
assert.equal(validateTree(root).valid, true);
assert.equal(moveNode(root, leaf.id, root.id, 0), true);
assert.equal(findParent(root, leaf.id), root);

// A nested group can be promoted to the root as a sibling of existing groups.
const siblingGroup = addGroup(root, root.id, "and");
assert.equal(moveNode(root, group.id, root.id, root.children.length), true);
assert.equal(findParent(root, group.id), root);
assert.equal(root.children.at(-1).id, group.id);
assert.equal(findParent(root, siblingGroup.id), root);

assert.equal(moveNode(root, group.id, leaf.id), false);
assert.equal(setOperator(root, root.id, "or"), true);
assert.equal(root.operator, "or");
assert.ok(removeNode(root, leaf.id));

const canonical = normalizeTree({
	id: "root",
	type: "group",
	operator: "and",
	children: [{ id: "leaf-1", type: "leaf", field: "status", operator: "=", value: "Open" }],
});
assert.equal(canonical.children[0].type, "leaf");

assert.throws(() => normalizeTree({ type: "scope", children: [] }), /Unsupported tree node type/);

const bad = createGroup("xor", [createLeaf({ field: "x" })]);
assert.equal(validateTree(bad).valid, false);
assert.ok(validateTree(bad).errors.some((error) => error.code === "operator"));

const tooDeep = createGroup("and", [createGroup("or", [createLeaf({ field: "x" })])]);
const depthResult = validateTree(tooDeep, { maxDepth: 1 });
assert.equal(depthResult.valid, false);
assert.ok(depthResult.errors.some((error) => error.code === "max_depth"));

console.log("tree builder core tests passed");

const collectionRoot = createGroup("and", []);
const collection = addCollection(collectionRoot, collectionRoot.id, { name: "rows" });
const collectionGroup = addGroup(collectionRoot, collection.id, "or");
const collectionLeaf = addLeaf(collectionRoot, collection.id, {
	field: "status",
	operator: "=",
	value: "Open",
});
assert.equal(collection.type, "collection");
assert.equal(findParent(collectionRoot, collectionGroup.id), collection);
assert.equal(findParent(collectionRoot, collectionLeaf.id), collection);
assert.equal(validateTree(collectionRoot, { allowCollections: true }).valid, true);
const collectionsDisabled = validateTree(collectionRoot, { allowCollections: false });
assert.equal(collectionsDisabled.valid, false);
assert.ok(collectionsDisabled.errors.some((error) => error.code === "collections_disabled"));

const groupsDisabled = validateTree(
	createGroup("and", [createGroup("or", [createLeaf({ field: "x" })])]),
	{ allowGroups: false }
);
assert.equal(groupsDisabled.valid, false);
assert.ok(groupsDisabled.errors.some((error) => error.code === "groups_disabled"));

const editableFilters = deserializeQueryFilters([], { defaultDoctype: "Customer" });
editableFilters.children.push({
	id: "leaf-edit",
	type: "leaf",
	doctype: "Customer",
	field: "",
	operator: "=",
	value: { mode: "static", value: "" },
});
assert.deepEqual(serializeQueryFilters(editableFilters), [
	"Customer",
	"",
	"=",
	{ mode: "static", value: "" },
]);

// Transient new leaf and editing lifecycle tests in useTreeBuilder
const tb = useTreeBuilder({ modelValue: createGroup("and", []) });
const newLeaf = tb.addLeaf(tb.root.id, {
	field: "",
	operator: "=",
	value: { mode: "static", value: "" },
});
assert.ok(newLeaf?.id);
assert.equal(tb.editingNodeId.value, newLeaf.id);
assert.equal(tb.isTransientNew(newLeaf.id), true);

// Finishing editing clears transient new status and editing state
tb.finishEditing(newLeaf.id);
assert.equal(tb.editingNodeId.value, null);
assert.equal(tb.isTransientNew(newLeaf.id), false);

// Adding another leaf and removing it cleans up transient state
const secondLeaf = tb.addLeaf(tb.root.id, {
	field: "status",
	operator: "=",
	value: { mode: "static", value: "Open" },
});
assert.equal(tb.isTransientNew(secondLeaf.id), true);
tb.removeNode(secondLeaf.id);
assert.equal(tb.isTransientNew(secondLeaf.id), false);
assert.equal(tb.editingNodeId.value, null);

// Resetting root clears transient state
const thirdLeaf = tb.addLeaf(tb.root.id, { field: "status" });
assert.equal(tb.isTransientNew(thirdLeaf.id), true);
tb.reset(createGroup("and", []));
assert.equal(tb.isTransientNew(thirdLeaf.id), false);
editableFilters.children[0].field = "customer_group";
assert.deepEqual(serializeQueryFilters(editableFilters), [
	"Customer",
	"customer_group",
	"=",
	{ mode: "static", value: "" },
]);
