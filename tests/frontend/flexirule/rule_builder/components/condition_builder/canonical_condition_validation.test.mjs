import test from "node:test";
import assert from "node:assert/strict";

import { validateCanonicalCondition } from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_validation.mjs";

test("canonical_condition_validation: empty tree handling for mandatory vs optional", () => {
	const emptyTree = {
		id: "root",
		type: "group",
		operator: "and",
		children: [],
	};

	const optionalResult = validateCanonicalCondition(emptyTree, { isMandatory: false });
	assert.equal(optionalResult.valid, true);
	assert.equal(optionalResult.errors.length, 0);

	const mandatoryResult = validateCanonicalCondition(emptyTree, { isMandatory: true });
	assert.equal(mandatoryResult.valid, false);
	assert.ok(mandatoryResult.errors.some((e) => e.includes("empty")));
});

test("canonical_condition_validation: validates comparison operands and operator", () => {
	const invalidLeaf = {
		id: "root",
		type: "group",
		operator: "and",
		children: [
			{
				id: "leaf-1",
				type: "leaf",
				operator: "",
				left: null,
				right: null,
			},
		],
	};

	const result = validateCanonicalCondition(invalidLeaf, { isMandatory: true });
	assert.equal(result.valid, false);
	assert.ok(result.errors.some((e) => e.includes("operator is required")));
	assert.ok(result.errors.some((e) => e.includes("Left operand is required")));
});

test("canonical_condition_validation: unary operator does not require right operand", () => {
	const unaryTree = {
		id: "root",
		type: "group",
		operator: "and",
		children: [
			{
				id: "leaf-1",
				type: "leaf",
				operator: "is_set",
				left: {
					mode: "variable",
					path: { scope: "doc", segments: ["status"] },
				},
				right: null,
			},
		],
	};

	const result = validateCanonicalCondition(unaryTree, { isMandatory: true });
	assert.equal(result.valid, true);
	assert.equal(result.errors.length, 0);
});

test("canonical_condition_validation: validates nested group minimum children", () => {
	const singleChildGroup = {
		id: "root",
		type: "group",
		operator: "and",
		children: [
			{
				id: "group-1",
				type: "group",
				operator: "or",
				children: [
					{
						id: "leaf-1",
						type: "leaf",
						operator: "eq",
						left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
						right: { mode: "static", value_type: "string", value: "Open" },
					},
				],
			},
		],
	};

	const result = validateCanonicalCondition(singleChildGroup, { isMandatory: true });
	assert.equal(result.valid, false);
	assert.ok(result.errors.some((e) => e.includes("at least two conditions")));
});

test("canonical_condition_validation: validates collection predicate alias and where", () => {
	const invalidCollection = {
		id: "root",
		type: "group",
		operator: "and",
		children: [
			{
				id: "col-1",
				type: "collection",
				quantifier: "any",
				collection: "doc.items",
				alias: "bad__alias",
				children: [],
			},
		],
	};

	const result = validateCanonicalCondition(invalidCollection, { isMandatory: true });
	assert.equal(result.valid, false);
	assert.ok(result.errors.some((e) => e.includes("alias")));
	assert.ok(result.errors.some((e) => e.includes("at least one condition")));
});
