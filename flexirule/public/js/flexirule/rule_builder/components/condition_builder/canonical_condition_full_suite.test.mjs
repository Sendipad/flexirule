import test from "node:test";
import assert from "node:assert/strict";

import {
	normalizeFlexValue,
	normalizeConditionNode,
	hydrateToTreeBuilder,
	serializeToCanonicalAst,
} from "./canonical_condition_adapter.mjs";

import {
	validateFlexValue,
	validateComparisonDomain,
	validateConditionTree,
} from "./canonical_condition_validator.mjs";

import { resetContractCache } from "./condition_contract_client.mjs";

test("Adapter: Hydrating and serializing a single comparison AST", () => {
	const ast = {
		type: "comparison",
		op: "eq",
		left: { value_type: "variable", path: "doc.status" },
		right: { value_type: "static", value: "Submitted" },
	};

	global.frappe = { utils: { get_random: () => "test_id_1" } };
	const uiTree = hydrateToTreeBuilder(ast);

	assert.equal(uiTree.type, "leaf");
	assert.deepEqual(uiTree.domain, ast);

	const serialized = serializeToCanonicalAst(uiTree);
	assert.deepEqual(serialized, ast);
});

test("Adapter: Hydrating and serializing nested AND/OR groups", () => {
	const ast = {
		type: "group",
		op: "or",
		children: [
			{
				type: "comparison",
				op: "eq",
				left: { value_type: "variable", path: "doc.docstatus" },
				right: { value_type: "static", value: 1 },
			},
			{
				type: "group",
				op: "and",
				children: [
					{
						type: "comparison",
						op: "gt",
						left: { value_type: "variable", path: "doc.grand_total" },
						right: { value_type: "static", value: 5000 },
					},
				],
			},
		],
	};

	global.frappe = { utils: { get_random: () => "test_id_group" } };
	const uiTree = hydrateToTreeBuilder(ast);

	assert.equal(uiTree.type, "group");
	assert.equal(uiTree.operator, "or");
	assert.equal(uiTree.children.length, 2);

	const serialized = serializeToCanonicalAst(uiTree);
	assert.deepEqual(serialized, ast);
});

test("Adapter: Legacy payload normalization", () => {
	const legacyPayload = {
		op: "and",
		conditions: [
			{ field: "doc.grand_total", op: ">", value: 100 },
			{ field: "status", op: "!=", value: "Cancelled" },
		],
	};

	const normalized = normalizeConditionNode(legacyPayload);
	assert.equal(normalized.type, "group");
	assert.equal(normalized.op, "and");
	assert.equal(normalized.children[0].op, "gt");
	assert.deepEqual(normalized.children[0].left, { value_type: "variable", path: "doc.grand_total" });
	assert.equal(normalized.children[1].op, "ne");
});

test("Adapter: Ephemeral IDs never appear in serialized canonical JSON", () => {
	const uiTree = {
		id: "ephemeral_group_123",
		type: "group",
		operator: "and",
		children: [
			{
				id: "ephemeral_leaf_456",
				type: "leaf",
				domain: {
					type: "comparison",
					op: "is_set",
					left: { value_type: "variable", path: "doc.customer" },
				},
			},
		],
	};

	const serialized = serializeToCanonicalAst(uiTree);
	assert.strictEqual(serialized.id, undefined);
	assert.strictEqual(serialized.children[0].id, undefined);
	assert.deepEqual(serialized, {
		type: "group",
		op: "and",
		children: [
			{
				type: "comparison",
				op: "is_set",
				left: { value_type: "variable", path: "doc.customer" },
			},
		],
	});
});

test("Validator: Unary vs Binary operator validation", () => {
	const operators = [
		{ id: "eq", label: "Equals", arity: 2 },
		{ id: "is_set", label: "Is set", arity: 1 },
	];

	// Valid unary
	const validUnary = {
		type: "comparison",
		op: "is_set",
		left: { value_type: "variable", path: "doc.name" },
	};
	assert.deepEqual(validateComparisonDomain(validUnary, operators), []);

	// Incomplete binary (missing right)
	const incompleteBinary = {
		type: "comparison",
		op: "eq",
		left: { value_type: "variable", path: "doc.name" },
		right: null,
	};
	const binaryErrors = validateComparisonDomain(incompleteBinary, operators);
	assert.ok(binaryErrors.length > 0);
});

test("Validator: Mandatory empty tree validation", () => {
	const emptyTree = { type: "group", operator: "and", children: [] };
	const res = validateConditionTree(emptyTree, { isMandatory: true });
	assert.equal(res.isValid, false);
	assert.ok(res.errors.length > 0);
});
