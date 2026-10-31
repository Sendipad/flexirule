import test from "node:test";
import assert from "node:assert/strict";

import {
	normalizeFlexValue,
	normalizeConditionNode,
	hydrateToTreeBuilder,
	serializeToCanonicalAst,
} from "./canonical_condition_adapter.mjs";

const operators = [
	{ id: "eq", arity: 2 },
	{ id: "gt", arity: 2 },
	{ id: "is_set", arity: 1 },
];

global.frappe = { utils: { get_random: () => "test-id" } };

test("canonical comparison round-trips with backend operator and FlexValue fields", () => {
	const ast = {
		type: "group",
		operator: "and",
		children: [
			{
				type: "comparison",
				operator: "eq",
				left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
				right: { mode: "static", value_type: "string", value: "Submitted" },
			},
			{
				type: "comparison",
				operator: "gt",
				left: { mode: "variable", path: { scope: "doc", segments: ["grand_total"] } },
				right: { mode: "static", value_type: "integer", value: 100 },
			},
		],
	};
	const ui = hydrateToTreeBuilder(ast);
	const serialized = serializeToCanonicalAst(ui, { operators });
	assert.deepEqual(serialized, ast);
	assert.equal(serialized.children[0].operator, "eq");
	assert.equal("op" in serialized.children[0], false);
});

test("collection source and single nested predicate use the canonical collection contract", () => {
	const ast = {
		type: "collection_predicate",
		quantifier: "any",
		source: { mode: "variable", path: { scope: "doc", segments: ["items"] } },
		as: "item",
		where: {
			type: "comparison",
			operator: "gt",
			left: { mode: "variable", path: { scope: "row", segments: ["qty"] } },
			right: { mode: "static", value_type: "integer", value: 0 },
		},
	};
	const ui = hydrateToTreeBuilder(ast);
	assert.equal(ui.type, "collection");
	const serialized = serializeToCanonicalAst(ui, { operators });
	assert.deepEqual(serialized, ast);
	assert.equal(serialized.source.path.scope, "doc");
	assert.deepEqual(serialized.source.path.segments, ["items"]);
});

test("legacy persisted condition data is normalized into canonical keys for migration", () => {
	const migrated = normalizeConditionNode({
		op: "and",
		conditions: [
			{ field: "doc.grand_total", op: ">", value: 100 },
			{ field: "status", op: "!=", value: "Cancelled" },
		],
	});
	assert.deepEqual(migrated, {
		type: "group",
		operator: "and",
		children: [
			{
				type: "comparison",
				operator: "gt",
				left: { mode: "variable", path: { scope: "doc", segments: ["grand_total"] } },
				right: { mode: "static", value_type: "integer", value: 100 },
			},
			{
				type: "comparison",
				operator: "ne",
				left: { mode: "static", value_type: "string", value: "status" },
				right: { mode: "static", value_type: "string", value: "Cancelled" },
			},
		],
	});
});

test("unsupported canonical node types fail instead of becoming an empty tree", () => {
	assert.throws(() => hydrateToTreeBuilder({ type: "expression", value: "True" }), /Unsupported canonical condition node type/);
});

test("serializer requires the authoritative operator contract", () => {
	const ui = { type: "leaf", domain: { type: "comparison", op: "custom", left: { mode: "static", value: "x" } } };
	assert.throws(() => serializeToCanonicalAst(ui, { operators }), /Unsupported canonical condition operator/);
});

test("legacy FlexValue values are converted to strict canonical modes", () => {
	assert.deepEqual(normalizeFlexValue("doc.status"), {
		mode: "variable",
		path: { scope: "doc", segments: ["status"] },
	});
	assert.deepEqual(normalizeFlexValue("Active"), {
		mode: "static",
		value_type: "string",
		value: "Active",
	});
});
