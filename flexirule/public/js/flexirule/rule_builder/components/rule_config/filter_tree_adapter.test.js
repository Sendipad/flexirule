import assert from "node:assert/strict";
import {
	createFilterLeaf,
	deserializeFilterPayload,
	serializeFilterTree,
	validateFilterTree,
} from "./filter_tree_adapter.js";

{
	const blank = createFilterLeaf({ doctype: "Sales Order", createId: () => "leaf-1" });
	assert.equal(blank.field, "");
	assert.equal(blank.operator, "=");
	assert.deepEqual(blank.value, { mode: "static", value: "" });

	const result = validateFilterTree(deserializeFilterPayload({ type: "group", operator: "and", children: [blank] }));
	assert.equal(result.valid, false);
	assert.equal(result.errors[0].code, "required");
}

const leaf = (field, value, operator = "=") => [
	"Sales Order",
	field,
	operator,
	{ mode: "static", value },
];

{
	const tree = deserializeFilterPayload(leaf("status", "Open"), {
		defaultDoctype: "Sales Order",
	});
	assert.equal(tree.type, "group");
	assert.equal(tree.children.length, 1);
	assert.deepEqual(serializeFilterTree(tree), leaf("status", "Open"));
}

{
	const payload = [
		leaf("status", "Open"),
		"and",
		[leaf("priority", "High"), "or", leaf("priority", "Medium")],
	];
	const tree = deserializeFilterPayload(payload);
	assert.equal(tree.operator, "and");
	assert.equal(tree.children[1].type, "group");
	assert.equal(tree.children[1].operator, "or");
	assert.deepEqual(serializeFilterTree(tree), payload);
}

{
	const tree = deserializeFilterPayload([
		leaf("status", "Open"),
		"or",
		leaf("status", "Closed"),
		"and",
		leaf("enabled", 1),
	]);
	assert.equal(tree.operator, "and");
	assert.equal(tree.children[0].operator, "or");
	assert.deepEqual(serializeFilterTree(tree), [
		[leaf("status", "Open"), "or", leaf("status", "Closed")],
		"and",
		leaf("enabled", 1),
	]);
}

{
	const flexValue = { mode: "variable", value: "doc.status" };
	const tree = deserializeFilterPayload(["status", "=", flexValue], {
		defaultDoctype: "Sales Order",
	});
	assert.deepEqual(tree.children[0].value, flexValue);
}

{
	const tree = deserializeFilterPayload([
		["Sales Order", "", "=", { mode: "static", value: "" }],
	]);
	const result = validateFilterTree(tree);
	assert.equal(result.valid, false);
	assert.equal(result.errors[0].code, "required");
	assert.throws(
		() => serializeFilterTree(tree),
		(error) => error.name === "FilterTreeValidationError"
	);
}

{
	const tree = deserializeFilterPayload([
		["Sales Order", "customer", "=", { mode: "static", value: "CUST-1" }],
	]);
	tree.children[0].uiOnly = true;
	const payload = serializeFilterTree(tree);
	assert.equal(payload.length, 4);
	assert.equal(payload[0], "Sales Order");
	assert.equal("uiOnly" in payload[0], false);
}

console.log("filter_tree_adapter tests passed");
