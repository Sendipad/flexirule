import test from "node:test";
import assert from "node:assert/strict";

import {
	deserializeConditionTree,
	serializeConditionTree,
	fieldExpressionToCanonicalVariable,
	canonicalVariableToFieldExpression,
	toCanonicalFlexValue,
	inferCanonicalValueType,
	findUnsupportedDiagnostics,
	isCanonicalConditionPayload,
	isLegacyConditionPayload,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_adapter.mjs";

test("canonical_condition_adapter: converts field expression to canonical variable FlexValue", () => {
	assert.deepEqual(fieldExpressionToCanonicalVariable("status"), {
		mode: "variable",
		path: { scope: "doc", segments: ["status"] },
	});

	assert.deepEqual(fieldExpressionToCanonicalVariable("doc.grand_total"), {
		mode: "variable",
		path: { scope: "doc", segments: ["grand_total"] },
	});

	assert.deepEqual(fieldExpressionToCanonicalVariable("vars.min_qty"), {
		mode: "variable",
		path: { scope: "vars", segments: ["min_qty"] },
	});

	assert.deepEqual(fieldExpressionToCanonicalVariable("item_row.amount"), {
		mode: "variable",
		path: { scope: "item_row", segments: ["amount"] },
	});

	assert.equal(
		canonicalVariableToFieldExpression({
			mode: "variable",
			path: { scope: "doc", segments: ["status"] },
		}),
		"doc.status"
	);
});

test("canonical_condition_adapter: toCanonicalFlexValue handles static types, decimals, ints and tuples", () => {
	const stringVal = toCanonicalFlexValue("hello");
	assert.deepEqual(stringVal, {
		mode: "static",
		value_type: "string",
		value: "hello",
	});

	const decimalVal = toCanonicalFlexValue(100.5, "Currency");
	assert.deepEqual(decimalVal, {
		mode: "static",
		value_type: "decimal",
		value: "100.5",
	});

	const intVal = toCanonicalFlexValue(42, "Int");
	assert.deepEqual(intVal, {
		mode: "static",
		value_type: "integer",
		value: 42,
	});

	const boolVal = toCanonicalFlexValue(true, "Check");
	assert.deepEqual(boolVal, {
		mode: "static",
		value_type: "Check",
		value: 1,
	});

	assert.deepEqual(
		toCanonicalFlexValue(
			{ mode: "static", value_type: "boolean", value: true },
			"Check",
			"eq"
		),
		{ mode: "static", value_type: "Check", value: 1 }
	);
	assert.deepEqual(
		toCanonicalFlexValue(
			{ mode: "static", value_type: "boolean", value: false },
			"Check",
			"eq"
		),
		{ mode: "static", value_type: "Check", value: 0 }
	);

	const tupleVal = toCanonicalFlexValue(["Customer", "Cust-001"], "Link");
	assert.deepEqual(tupleVal, {
		mode: "static",
		value_type: "string",
		value: "Cust-001",
	});
});

test("canonical_condition_adapter: round-trip single comparison (direct canonical node)", () => {
	const canonical = {
		type: "comparison",
		operator: "eq",
		left: {
			mode: "variable",
			path: { scope: "doc", segments: ["status"] },
		},
		right: {
			mode: "static",
			value_type: "string",
			value: "Open",
		},
	};

	assert.equal(isCanonicalConditionPayload(canonical), true);

	const tree = deserializeConditionTree(canonical);
	assert.equal(tree.type, "group");
	assert.equal(tree.children.length, 1);
	assert.equal(tree.children[0].type, "leaf");
	assert.equal(tree.children[0].operator, "eq");
	assert.ok(tree.children[0].id);

	const roundTrip = serializeConditionTree(tree);
	assert.deepEqual(roundTrip, canonical);
});

test("canonical_condition_adapter: round-trip unary operator has no right operand", () => {
	const canonical = {
		type: "comparison",
		operator: "is_set",
		left: {
			mode: "variable",
			path: { scope: "doc", segments: ["workflow_state"] },
		},
	};

	const tree = deserializeConditionTree(canonical);
	assert.equal(tree.children.length, 1);
	assert.equal(tree.children[0].operator, "is_set");

	const roundTrip = serializeConditionTree(tree);
	assert.deepEqual(roundTrip, canonical);
	assert.equal("right" in roundTrip, false);
});

test("canonical_condition_adapter: round-trip canonical group (AND / OR) with 2+ children", () => {
	const canonical = {
		type: "group",
		operator: "and",
		children: [
			{
				type: "comparison",
				operator: "eq",
				left: {
					mode: "variable",
					path: { scope: "doc", segments: ["status"] },
				},
				right: {
					mode: "static",
					value_type: "string",
					value: "Open",
				},
			},
			{
				type: "comparison",
				operator: "gt",
				left: {
					mode: "variable",
					path: { scope: "doc", segments: ["grand_total"] },
				},
				right: {
					mode: "static",
					value_type: "decimal",
					value: "100",
				},
			},
		],
	};

	const tree = deserializeConditionTree(canonical);
	assert.equal(tree.type, "group");
	assert.equal(tree.operator, "and");
	assert.equal(tree.children.length, 2);

	const roundTrip = serializeConditionTree(tree);
	assert.deepEqual(roundTrip, canonical);
});

test("canonical_condition_adapter: round-trip nested groups", () => {
	const canonical = {
		type: "group",
		operator: "and",
		children: [
			{
				type: "comparison",
				operator: "eq",
				left: {
					mode: "variable",
					path: { scope: "doc", segments: ["status"] },
				},
				right: {
					mode: "static",
					value_type: "string",
					value: "Active",
				},
			},
			{
				type: "group",
				operator: "or",
				children: [
					{
						type: "comparison",
						operator: "gt",
						left: {
							mode: "variable",
							path: { scope: "doc", segments: ["rate"] },
						},
						right: {
							mode: "static",
							value_type: "decimal",
							value: "50",
						},
					},
					{
						type: "comparison",
						operator: "lt",
						left: {
							mode: "variable",
							path: { scope: "doc", segments: ["discount"] },
						},
						right: {
							mode: "static",
							value_type: "decimal",
							value: "5",
						},
					},
				],
			},
		],
	};

	const tree = deserializeConditionTree(canonical);
	assert.equal(tree.children.length, 2);
	assert.equal(tree.children[1].type, "group");
	assert.equal(tree.children[1].operator, "or");

	const roundTrip = serializeConditionTree(tree);
	assert.deepEqual(roundTrip, canonical);
});

test("canonical_condition_adapter: round-trip collection predicate", () => {
	const canonical = {
		type: "collection_predicate",
		quantifier: "any",
		source: {
			scope: "doc",
			segments: ["items"],
		},
		as: "item_row",
		where: {
			type: "comparison",
			operator: "gt",
			left: {
				mode: "variable",
				path: {
					scope: "item_row",
					segments: ["amount"],
				},
			},
			right: {
				mode: "static",
				value_type: "decimal",
				value: "100",
			},
		},
	};

	const tree = deserializeConditionTree(canonical);
	assert.equal(tree.children.length, 1);
	const colNode = tree.children[0];
	assert.equal(colNode.type, "collection");
	assert.equal(colNode.quantifier, "any");
	assert.equal(colNode.alias, "item_row");
	assert.equal(colNode.collection, "doc.items");
	assert.equal(colNode.children.length, 1);

	const roundTrip = serializeConditionTree(tree);
	assert.deepEqual(roundTrip, canonical);
});

test("canonical_condition_adapter: empty tree serializes to null", () => {
	const emptyTree = {
		id: "root",
		type: "group",
		operator: "and",
		children: [],
	};
	assert.equal(serializeConditionTree(emptyTree), null);
	assert.equal(serializeConditionTree(null), null);
});

test("canonical_condition_adapter: converts legacy format safely and deterministically", () => {
	const legacy = {
		op: "and",
		conditions: [
			{
				left: { ref: "doc.status" },
				op: "==",
				right: { value: { mode: "static", value: "Open" } },
			},
			{
				left: { ref: "doc.grand_total" },
				op: ">",
				right: { value: 500 },
			},
		],
	};

	assert.equal(isLegacyConditionPayload(legacy), true);
	assert.equal(isCanonicalConditionPayload(legacy), false);

	const tree = deserializeConditionTree(legacy);
	assert.equal(tree.children.length, 2);
	assert.equal(tree.children[0].operator, "eq");
	assert.equal(tree.children[1].operator, "gt");

	const canonical = serializeConditionTree(tree);
	assert.deepEqual(canonical, {
		type: "group",
		operator: "and",
		children: [
			{
				type: "comparison",
				operator: "eq",
				left: {
					mode: "variable",
					path: { scope: "doc", segments: ["status"] },
				},
				right: {
					mode: "static",
					value_type: "string",
					value: "Open",
				},
			},
			{
				type: "comparison",
				operator: "gt",
				left: {
					mode: "variable",
					path: { scope: "doc", segments: ["grand_total"] },
				},
				right: {
					mode: "static",
					value_type: "integer",
					value: 500,
				},
			},
		],
	});
});

test("canonical_condition_adapter: preserves unsupported legacy conditions with diagnostics without data loss", () => {
	const legacyWithUnsupported = {
		op: "and",
		conditions: [
			{
				left: { ref: "doc.title" },
				op: "like",
				right: { value: "%test%" },
			},
		],
	};

	const tree = deserializeConditionTree(legacyWithUnsupported);
	const diagnostics = findUnsupportedDiagnostics(tree);
	assert.equal(diagnostics.length, 1);
	assert.match(diagnostics[0].reason, /Unsupported legacy operator 'like'/);

	const reserialized = serializeConditionTree(tree);
	assert.deepEqual(reserialized, {
		left: { ref: "doc.title" },
		op: "like",
		right: { value: "%test%" },
	});
});
