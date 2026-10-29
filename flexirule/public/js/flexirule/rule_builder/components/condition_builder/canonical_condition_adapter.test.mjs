import test from "node:test";
import assert from "node:assert/strict";

import {
	normalizeFlexValue,
	normalizeConditionNode,
	hydrateToTreeBuilder,
	serializeToCanonicalAst,
} from "./canonical_condition_adapter.mjs";

test("normalizeFlexValue transforms string paths to variable FlexValue", () => {
	const result = normalizeFlexValue("doc.status");
	assert.deepEqual(result, { value_type: "variable", path: "doc.status" });
});

test("normalizeFlexValue transforms primitive static values to static FlexValue", () => {
	const result = normalizeFlexValue("Active");
	assert.deepEqual(result, { value_type: "static", value: "Active" });
});

test("normalizeConditionNode converts legacy == operator symbol to canonical eq ID", () => {
	const legacyNode = { field: "status", op: "==", value: "Draft" };
	const normalized = normalizeConditionNode(legacyNode);
	assert.equal(normalized.type, "comparison");
	assert.equal(normalized.op, "eq");
	assert.deepEqual(normalized.left, { value_type: "static", value: "status" });
	assert.deepEqual(normalized.right, { value_type: "static", value: "Draft" });
});

test("hydrateToTreeBuilder & serializeToCanonicalAst roundtrip preserves canonical structure and purges UI ids", () => {
	const canonicalAst = {
		type: "group",
		op: "and",
		children: [
			{
				type: "comparison",
				op: "gt",
				left: { value_type: "variable", path: "grand_total" },
				right: { value_type: "static", value: 1000 },
			},
			{
				type: "collection_predicate",
				quantifier: "any",
				collection: { value_type: "variable", path: "items" },
				alias: "item",
				where: {
					type: "group",
					op: "and",
					children: [
						{
							type: "comparison",
							op: "gte",
							left: { value_type: "variable", path: "item.qty" },
							right: { value_type: "static", value: 10 },
						},
					],
				},
			},
		],
	};

	// Hydrate to TreeBuilder UI state
	global.frappe = {
		utils: { get_random: () => "ui_id_" + Math.random().toString(36).substring(2) },
	};
	const uiTree = hydrateToTreeBuilder(canonicalAst);

	// Verify ephemeral UI ID is attached
	assert.ok(uiTree.id);

	// Serialize back to canonical AST
	const serialized = serializeToCanonicalAst(uiTree);

	assert.deepEqual(serialized, canonicalAst);
});
