import assert from "node:assert/strict";
import {
	createFilterLeaf,
	createFilterGroup,
	deserializeFilterPayload,
	serializeFilterTree,
	validateFilterTree,
} from "./filter_tree_adapter.js";

const leaf = (field, value, operator = "=") => [
	"Sales Order",
	field,
	operator,
	{ mode: "static", value },
];

// Test 1: Single leaf deserialization & serialization
{
	const tree = deserializeFilterPayload(leaf("status", "Open"), {
		defaultDoctype: "Sales Order",
	});
	assert.equal(tree.type, "group");
	assert.equal(tree.children.length, 1);
	assert.deepEqual(serializeFilterTree(tree), leaf("status", "Open"));
}

// Test 2: Nested groups and operator precedence
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

// Test 3: Mixed operator sequence parsing
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

// Test 4: Preserving FlexValue objects (including variable mode)
{
	const flexValue = { mode: "variable", value: "doc.status" };
	const tree = deserializeFilterPayload(["status", "=", flexValue], {
		defaultDoctype: "Sales Order",
	});
	assert.deepEqual(tree.children[0].value, flexValue);
	assert.deepEqual(serializeFilterTree(tree), ["Sales Order", "status", "=", flexValue]);
}

// Test 5: Validation of blank/incomplete leaf
{
	const tree = createFilterGroup({
		children: [createFilterLeaf({ doctype: "Sales Order" })],
	});
	const result = validateFilterTree(tree);
	assert.equal(result.valid, false);
	assert.equal(result.errors[0].code, "required");
	assert.throws(
		() => serializeFilterTree(tree),
		(error) => error.name === "FilterTreeValidationError"
	);
}

// Test 6: UI-only properties are stripped during serialization
{
	const tree = deserializeFilterPayload([
		["Sales Order", "customer", "=", { mode: "static", value: "CUST-1" }],
	]);
	tree.children[0].uiOnlyProperty = true;
	const payload = serializeFilterTree(tree);
	assert.equal(payload.length, 4);
	assert.equal(payload[0], "Sales Order");
	assert.equal(payload[1], "customer");
	assert.equal("uiOnlyProperty" in payload, false);
}

console.log("filter_tree_adapter tests passed");
