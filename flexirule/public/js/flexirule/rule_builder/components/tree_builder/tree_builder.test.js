import assert from "node:assert/strict";
import {
	createGroup,
	createLeaf,
	findNode,
	findParent,
	findPath,
	normalizeTree,
} from "./tree_builder_utils.js";
import { addGroup, addLeaf, moveNode, removeNode, setOperator } from "./tree_builder_commands.js";
import { validateTree } from "./tree_builder_validation.js";

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
