import assert from "node:assert/strict";
import {
	createGroup,
	createLeaf,
	createScope,
	findNode,
	findParent,
	findPath,
	normalizeTree,
} from "./tree_builder_utils.js";
import {
	addGroup,
	addLeaf,
	addScope,
	moveNode,
	removeNode,
	setOperator,
} from "./tree_builder_commands.js";
import { validateTree } from "./tree_builder_validation.js";

const root = createGroup("and", []);
const scope = addScope(root, root.id, { type: "collection", key: "items" });
const leaf = addLeaf(root, scope.id, { field: "qty", operator: ">", value: 10 });
const nested = addGroup(root, scope.id, "or");
addLeaf(root, nested.id, { field: "warehouse", operator: "=", value: "WH-01" });
assert.equal(findParent(root, leaf.id), scope);
assert.deepEqual(
	findPath(root, leaf.id).map((n) => n.id),
	[root.id, scope.id, leaf.id]
);
assert.equal(findNode(root, nested.id).operator, "or");
assert.equal(validateTree(root).valid, true);

assert.equal(moveNode(root, leaf.id, root.id, 0), true);
assert.equal(findParent(root, leaf.id), root);
assert.equal(moveNode(root, scope.id, leaf.id), false);
assert.equal(setOperator(root, root.id, "or"), true);
assert.equal(root.operator, "or");
assert.ok(removeNode(root, leaf.id));

const legacy = normalizeTree({
	type: "group",
	operator: "and",
	children: [
		{
			type: "scope",
			scope: { type: "collection", key: "items" },
			children: [{ type: "leaf", field: "qty" }],
		},
	],
});
assert.equal(validateTree(legacy).valid, true);

const bad = createGroup("xor", [createLeaf({ field: "x" })]);
assert.equal(validateTree(bad).valid, false);
assert.ok(validateTree(bad).errors.some((e) => e.code === "operator"));
console.log("tree builder core tests passed");
