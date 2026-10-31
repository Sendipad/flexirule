import test from "node:test";
import assert from "node:assert/strict";

import {
	validateFlexValue,
	validateComparisonDomain,
	validateConditionTree,
} from "./canonical_condition_validator.mjs";

const operators = [
	{ id: "eq", arity: 2 },
	{ id: "gt", arity: 2 },
	{ id: "is_set", arity: 1 },
];

const variable = (value = "doc.status") => ({ mode: "variable", value });
const staticValue = (value = "Draft") => ({ mode: "static", value });

test("validator accepts valid variable and static operands", () => {
	assert.deepEqual(validateFlexValue(variable(), "Left operand"), []);
	assert.deepEqual(validateFlexValue(staticValue(), "Right operand"), []);
});

test("validator rejects missing operands and unknown operators", () => {
	assert.ok(validateComparisonDomain({ type: "comparison", op: "eq", left: variable() }, operators).length > 0);
	assert.match(validateComparisonDomain({ type: "comparison", op: "made_up", left: variable() }, operators)[0], /Unsupported condition operator/);
});

test("validator respects operator arity from backend contract", () => {
	assert.deepEqual(validateComparisonDomain({
		type: "comparison", op: "is_set", left: variable(),
	}, operators), []);
	assert.ok(validateComparisonDomain({
		type: "comparison", op: "eq", left: variable(), right: null,
	}, operators).length > 0);
});

test("empty optional root is allowed but mandatory empty root is rejected", () => {
	const empty = { type: "group", operator: "and", children: [] };
	assert.equal(validateConditionTree(empty, { operators, isMandatory: false }).isValid, true);
	assert.equal(validateConditionTree(empty, { operators, isMandatory: true }).isValid, false);
});

test("persisted groups require at least two children", () => {
	const group = {
		type: "group", operator: "and",
		children: [{ type: "leaf", domain: { type: "comparison", op: "is_set", left: variable() } }],
	};
	assert.equal(validateConditionTree(group, { operators }).isValid, false);
});

test("collection predicates require a variable source, safe alias, and nested condition", () => {
	const valid = {
		type: "collection", quantifier: "any",
		collection: variable("doc.items"), alias: "item",
		children: [{ type: "leaf", domain: { type: "comparison", op: "gt", left: variable("row.qty"), right: staticValue(0) } }],
	};
	assert.equal(validateConditionTree(valid, { operators }).isValid, true);
	assert.equal(validateConditionTree({ ...valid, alias: "doc" }, { operators }).isValid, false);
	assert.equal(validateConditionTree({ ...valid, collection: staticValue("items") }, { operators }).isValid, false);
	assert.equal(validateConditionTree({ ...valid, children: [] }, { operators }).isValid, false);
});

test("validation fails closed if the server contract is unavailable", () => {
	assert.equal(validateConditionTree({ type: "leaf", domain: {} }, { operators: [] }).isValid, false);
});
