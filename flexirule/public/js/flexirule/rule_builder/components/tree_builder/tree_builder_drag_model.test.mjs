import assert from "node:assert/strict";
import { getSiblingDropIntent } from "./tree_builder_drag_model.mjs";

assert.deepEqual(getSiblingDropIntent("parent", 0, "before"), {
	targetId: "parent",
	position: 0,
	visualPosition: "before",
});
assert.deepEqual(getSiblingDropIntent("parent", 0, "after"), {
	targetId: "parent",
	position: 1,
	visualPosition: "after",
});
assert.deepEqual(getSiblingDropIntent("nested-group", 3, "before"), {
	targetId: "nested-group",
	position: 3,
	visualPosition: "before",
});
assert.deepEqual(getSiblingDropIntent("nested-group", 3, "after"), {
	targetId: "nested-group",
	position: 4,
	visualPosition: "after",
});
assert.equal(getSiblingDropIntent("", 0, "before"), null);
assert.equal(getSiblingDropIntent("parent", -1, "before"), null);
assert.equal(getSiblingDropIntent("parent", 1.5, "after"), null);
assert.equal(getSiblingDropIntent("parent", 0, "inside"), null);

console.log("tree builder drag model tests passed");
