import test from "node:test";
import assert from "node:assert/strict";

import {
	serializeConditionTree,
	deserializeConditionTree,
	toCanonicalFlexValue,
	findUnsupportedDiagnostics,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_adapter.mjs";

import { validateCanonicalCondition } from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_validation.mjs";

test("production_readiness: clearing optional Entry Condition persists explicit null", () => {
	const emptyTree = {
		id: "root",
		type: "group",
		operator: "and",
		children: [],
	};

	const serialized = serializeConditionTree(emptyTree);
	assert.equal(serialized, null);

	const validation = validateCanonicalCondition(emptyTree, { isMandatory: false });
	assert.equal(validation.valid, true);
	assert.equal(validation.errors.length, 0);
});

test("production_readiness: empty Condition Action fails validation to prevent save", () => {
	const emptyTree = {
		id: "root",
		type: "group",
		operator: "and",
		children: [],
	};

	const serialized = serializeConditionTree(emptyTree);
	assert.equal(serialized, null);

	const validation = validateCanonicalCondition(emptyTree, { isMandatory: true });
	assert.equal(validation.valid, false);
	assert.ok(validation.errors.some((err) => err.includes("cannot be empty")));
});

test("production_readiness: single-child root persists direct node; multi-child persists canonical group without UI properties", () => {
	const singleChildTree = {
		id: "root-ui-id",
		type: "group",
		operator: "and",
		_extraUiProp: true,
		children: [
			{
				id: "leaf-ui-id-1",
				type: "leaf",
				operator: "eq",
				left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
				right: { mode: "static", value_type: "string", value: "Submitted" },
			},
		],
	};

	const singlePayload = serializeConditionTree(singleChildTree);
	assert.deepEqual(singlePayload, {
		type: "comparison",
		operator: "eq",
		left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
		right: { mode: "static", value_type: "string", value: "Submitted" },
	});
	assert.equal("id" in singlePayload, false);
	assert.equal(singlePayload.type, "comparison");

	const multiChildTree = {
		id: "root-ui-id",
		type: "group",
		operator: "or",
		children: [
			{
				id: "leaf-1",
				type: "leaf",
				operator: "eq",
				left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
				right: { mode: "static", value_type: "string", value: "Submitted" },
			},
			{
				id: "leaf-2",
				type: "leaf",
				operator: "gt",
				left: { mode: "variable", path: { scope: "doc", segments: ["grand_total"] } },
				right: { mode: "static", value_type: "decimal", value: "5000" },
			},
		],
	};

	const multiPayload = serializeConditionTree(multiChildTree);
	assert.equal(multiPayload.type, "group");
	assert.equal(multiPayload.operator, "or");
	assert.equal(multiPayload.children.length, 2);
	assert.equal("id" in multiPayload, false);
	assert.equal("id" in multiPayload.children[0], false);
	assert.equal("id" in multiPayload.children[1], false);
});

test("production_readiness: collection predicate with 0, 1, and multiple children", () => {
	const col0Children = {
		id: "root",
		type: "group",
		operator: "and",
		children: [
			{
				id: "col-1",
				type: "collection",
				quantifier: "any",
				collection: "doc.items",
				alias: "row",
				children: [],
			},
		],
	};
	const val0 = validateCanonicalCondition(col0Children, { isMandatory: true });
	assert.equal(val0.valid, false);
	assert.ok(val0.errors.some((e) => e.includes("at least one condition")));

	const col1Child = {
		id: "root",
		type: "group",
		operator: "and",
		children: [
			{
				id: "col-1",
				type: "collection",
				quantifier: "all",
				collection: "doc.items",
				alias: "items_row",
				children: [
					{
						id: "leaf-item-1",
						type: "leaf",
						operator: "gt",
						left: { mode: "variable", path: { scope: "items_row", segments: ["qty"] } },
						right: { mode: "static", value_type: "integer", value: 10 },
					},
				],
			},
		],
	};
	const payload1 = serializeConditionTree(col1Child);
	assert.equal(payload1.type, "collection_predicate");
	assert.equal(payload1.quantifier, "all");
	assert.equal(payload1.as, "items_row");
	assert.equal(payload1.where.type, "comparison");
	assert.equal(payload1.where.operator, "gt");

	const col2Children = {
		id: "root",
		type: "group",
		operator: "and",
		children: [
			{
				id: "col-1",
				type: "collection",
				quantifier: "none",
				collection: "doc.items",
				alias: "items_row",
				children: [
					{
						id: "leaf-item-1",
						type: "leaf",
						operator: "gt",
						left: { mode: "variable", path: { scope: "items_row", segments: ["qty"] } },
						right: { mode: "static", value_type: "integer", value: 10 },
					},
					{
						id: "leaf-item-2",
						type: "leaf",
						operator: "eq",
						left: {
							mode: "variable",
							path: { scope: "items_row", segments: ["is_free"] },
						},
						right: { mode: "static", value_type: "boolean", value: true },
					},
				],
			},
		],
	};
	const payload2 = serializeConditionTree(col2Children);
	assert.equal(payload2.type, "collection_predicate");
	assert.equal(payload2.where.type, "group");
	assert.equal(payload2.where.children.length, 2);
});

test("production_readiness: strict FlexValue types preservation", () => {
	const dec = toCanonicalFlexValue("123.456", "Currency");
	assert.deepEqual(dec, {
		mode: "static",
		value_type: "decimal",
		value: "123.456",
	});

	const intVal = toCanonicalFlexValue(42, "Int");
	assert.deepEqual(intVal, {
		mode: "static",
		value_type: "integer",
		value: 42,
	});

	const boolVal = toCanonicalFlexValue(false, "Check");
	assert.deepEqual(boolVal, {
		mode: "static",
		value_type: "boolean",
		value: false,
	});

	const nullVal = toCanonicalFlexValue(null);
	assert.deepEqual(nullVal, {
		mode: "static",
		value_type: "null",
		value: null,
	});

	const dateVal = toCanonicalFlexValue("2026-11-03", "Date");
	assert.deepEqual(dateVal, {
		mode: "static",
		value_type: "date",
		value: "2026-11-03",
	});

	const linkTuple = toCanonicalFlexValue(["Item Group", "Raw Material"], "Link");
	assert.deepEqual(linkTuple, {
		mode: "static",
		value_type: "string",
		value: "Raw Material",
	});
});
