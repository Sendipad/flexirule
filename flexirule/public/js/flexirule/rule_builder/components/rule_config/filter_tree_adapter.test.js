import assert from "node:assert/strict";
import {
	deserializeFilterPayload,
	isFilterTreePayloadEquivalent,
	serializeFilterTree,
	validateFilterTree,
	createFilterGroup,
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

// UI Empty Group Test: Adding an empty group retains group in UI tree structure
{
	const emptyGroup = createFilterGroup({ operator: "and", children: [] });
	assert.equal(emptyGroup.type, "group");
	assert.equal(emptyGroup.children.length, 0);

	// Validation identifies empty child group as incomplete
	const rootTree = createFilterGroup({ operator: "and", children: [emptyGroup] });
	const validation = validateFilterTree(rootTree, { allowEmptyRoot: true });
	assert.equal(validation.valid, false);
	assert.equal(validation.errors[0].code, "empty_group");
}



{
	const tree = createFilterGroup({
		operator: "and",
		children: [createFilterGroup({ operator: "or", children: [] })],
	});
	assert.equal(
		isFilterTreePayloadEquivalent(tree, [], { defaultDoctype: "Sales Order" }),
		true
	);
	// A normalized parent payload must not force an explicit empty group out of
	// the interactive editor state.
	assert.equal(tree.children[0].type, "group");
	assert.equal(tree.children[0].children.length, 0);
}

{
	const leafNode = deserializeFilterPayload(leaf("status", "Open"), {
		defaultDoctype: "Sales Order",
	}).children[0];
	const tree = createFilterGroup({
		operator: "and",
		children: [
			createFilterGroup({ operator: "or", children: [leafNode] }),
		],
	});
	assert.equal(
		isFilterTreePayloadEquivalent(tree, leaf("status", "Open"), {
			defaultDoctype: "Sales Order",
		}),
		true
	);
	// Single-child groups remain structural editor nodes even though the
	// execution payload intentionally normalizes them away.
	assert.equal(tree.children[0].type, "group");
	assert.equal(tree.children[0].operator, "or");
	assert.equal(tree.children[0].children.length, 1);
}

console.log("filter_tree_adapter tests passed");
