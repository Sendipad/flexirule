import assert from "node:assert/strict";
import {
	deserializeFilterPayload,
	serializeFilterTree,
	validateFilterTree,
} from "./filter_tree_adapter.js";

const leaf = (field, value, operator = "=") => [
	"Sales Order",
	field,
	operator,
	typeof value === "object" && value !== null && "mode" in value
		? value
		: { mode: "static", value },
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
}

{
	const tree = deserializeFilterPayload([
		["Sales Order", "customer", "=", { mode: "static", value: "CUST-1" }],
	]);
	tree.children[0].uiOnly = true;
	const payload = serializeFilterTree(tree);
	assert.equal(payload.length, 4);
	assert.equal(payload[0], "Sales Order");
	assert.equal("uiOnly" in payload, false);
}

// Empty editor groups must never become executable nested filter arrays.
{
	const tree = deserializeFilterPayload([
		leaf("status", "Open"),
		"and",
		{
			type: "group",
			operator: "or",
			children: [],
		},
	]);
	assert.equal(tree.children.length, 2);
	assert.equal(tree.children[1].type, "group");
	assert.deepEqual(serializeFilterTree(tree), leaf("status", "Open"));
}

// Integration Test: Single Authoritative Tree State Sync
{
	const rawPayload = [
		["Journal Entry", "is_system_generated", "=", { mode: "static", value: "0" }],
		"and",
		["Journal Entry", "naming_series", "=", { mode: "static", value: "ACC-JV-.YYYY.-" }],
	];
	const tree = deserializeFilterPayload(rawPayload, { defaultDoctype: "Journal Entry" });
	assert.equal(tree.children.length, 2);
	assert.equal(tree.children[0].field, "is_system_generated");
	assert.equal(tree.children[1].field, "naming_series");

	// Mutate node directly in tree
	tree.children[0].value = { mode: "static", value: "1" };
	const serialized = serializeFilterTree(tree, { defaultDoctype: "Journal Entry" });
	assert.equal(serialized[0][3].value, "1");
}


// Regression: the root AND must contain a sibling leaf and a nested OR group.
{
	const payload = [
		[
			"Journal Entry",
			"title",
			"is",
			{ mode: "static", value: "set" },
		],
		"and",
		[
			["Journal Entry", "is_system_generated", "=", { mode: "static", value: "0" }],
			"or",
			[
				"Journal Entry",
				"naming_series",
				"=",
				{ mode: "static", value: "ACC-JV-.YYYY.-" },
			],
		],
	];
	const tree = deserializeFilterPayload(payload);

	assert.equal(tree.operator, "and");
	assert.equal(tree.children.length, 2);
	assert.equal(tree.children[0].type, "leaf");
	assert.equal(tree.children[0].field, "title");
	assert.equal(tree.children[1].type, "group");
	assert.equal(tree.children[1].operator, "or");
	assert.equal(tree.children[1].children.length, 2);
	assert.equal(tree.children[1].children[0].field, "is_system_generated");
	assert.equal(tree.children[1].children[1].field, "naming_series");
	assert.deepEqual(serializeFilterTree(tree), payload);
}

console.log("filter_tree_adapter tests passed");
