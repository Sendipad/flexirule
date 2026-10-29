import assert from "node:assert/strict";
import {
	createGroup,
	createLeaf,
	findNode,
	findParent,
	findPath,
	normalizeTree,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/tree_builder/tree_builder_utils.mjs";
import {
	addCollection,
	addGroup,
	addLeaf,
	moveNode,
	moveUp,
	moveDown,
	removeNode,
	setOperator,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/tree_builder/tree_builder_commands.mjs";
import { validateTree } from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/tree_builder/tree_builder_validation.mjs";
import {
	deserializeQueryFilters,
	serializeQueryFilters,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/query_filter_serializer.mjs";

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

// Test tree builder moveUp and moveDown commands and boundary rules
const tbRoot = createGroup("and", []);
const leafA = addLeaf(tbRoot, tbRoot.id, { field: "a" });
const leafB = addLeaf(tbRoot, tbRoot.id, { field: "b" });
const leafC = addLeaf(tbRoot, tbRoot.id, { field: "c" });

assert.equal(tbRoot.children.length, 3);
assert.equal(tbRoot.children[0].id, leafA.id);
assert.equal(tbRoot.children[1].id, leafB.id);

// First item cannot move up
assert.equal(moveUp(tbRoot, leafA.id), false);

// Move middle item (leafB) up
assert.equal(moveUp(tbRoot, leafB.id), true);
assert.equal(tbRoot.children[0].id, leafB.id);
assert.equal(tbRoot.children[1].id, leafA.id);

// Move leafB down twice
assert.equal(moveDown(tbRoot, leafB.id), true);
assert.equal(tbRoot.children[1].id, leafB.id);
assert.equal(moveDown(tbRoot, leafB.id), true);
assert.equal(tbRoot.children[2].id, leafB.id);

// Last item cannot move down
assert.equal(moveDown(tbRoot, leafB.id), false);

// Test canEditRule resolution logic
function resolveCanEditRule(canEditRuleProp, frappeBoot) {
	if (canEditRuleProp !== null && canEditRuleProp !== undefined) {
		return Boolean(canEditRuleProp);
	}
	if (frappeBoot && frappeBoot.user) {
		return Boolean(frappeBoot.canWrite ?? true);
	}
	return false;
}

assert.equal(resolveCanEditRule(true, null), true, "Explicit canEditRule=true takes precedence");
assert.equal(resolveCanEditRule(false, { user: "Test", canWrite: true }), false, "Explicit canEditRule=false takes precedence");
assert.equal(resolveCanEditRule(null, { user: "Test", canWrite: true }), true, "Frappe canWrite resolves to true when omitted");
assert.equal(resolveCanEditRule(null, { user: "Test", canWrite: false }), false, "Frappe canWrite=false suppresses contextual edit");
assert.equal(resolveCanEditRule(null, null), false, "When canEditRule is omitted and frappe is absent, defaults to false");
editableFilters.children[0].field = "customer_group";
assert.deepEqual(serializeQueryFilters(editableFilters), [
	"Customer",
	"customer_group",
	"=",
	{ mode: "static", value: "" },
]);
