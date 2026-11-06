import test from "node:test";
import assert from "node:assert/strict";

import { normalizeConditionContract } from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_contract_normalization.mjs";
import { validateCanonicalCondition } from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_validation.mjs";
import {
	toCanonicalFlexValue,
	deserializeConditionTree,
	serializeConditionTree,
	fieldExpressionToCanonicalVariable,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_adapter.mjs";

test("Workflow: Left-to-right authoring and contract normalization", () => {
	const rawContract = {
		api_version: "1",
		semantics_version: 1,
		node_types: {
			group: { required_keys: ["type", "operator", "children"], operators: ["and", "or"] },
			comparison: { required_keys: ["type", "operator", "left"] },
			collection_predicate: { required_keys: ["type", "quantifier", "source", "as", "where"] },
		},
		flexvalue_modes: {
			static: ["string", "integer", "decimal", "boolean", "null", "date", "datetime", "time", "list"],
			variable: { scopes: ["doc", "old_doc", "vars", "caller", "rule", "doctype"] },
			resolver: {},
			template: {},
		},
		operators: [
			{
				id: "eq",
				label: "is",
				arity: 2,
				accepted_left_types: ["string", "integer", "decimal", "boolean", "null", "date", "datetime", "time", "list", "object"],
				accepted_right_types: ["string", "integer", "decimal", "boolean", "null", "date", "datetime", "time", "list", "object"],
			},
			{
				id: "gt",
				label: "is greater than",
				arity: 2,
				accepted_left_types: ["integer", "decimal", "date", "datetime", "time"],
				accepted_right_types: ["integer", "decimal", "date", "datetime", "time"],
				fieldtypes: ["Int", "Float", "Currency", "Percent", "Date", "Datetime", "Time"],
			},
			{
				id: "in",
				label: "is one of",
				arity: 2,
				accepted_left_types: ["string", "integer", "decimal", "boolean", "null"],
				accepted_right_types: ["list"],
			},
			{
				id: "is_set",
				label: "is set",
				arity: 1,
				accepted_left_types: ["string", "integer", "decimal", "boolean", "null", "date", "datetime", "time", "list", "object"],
			},
		],
		fieldtype_value_types: {
			Data: ["string"],
			Int: ["integer"],
			Float: ["integer", "decimal"],
			Currency: ["integer", "decimal"],
		},
		limits: { condition_depth: 16, condition_nodes: 128 },
	};

	const contract = normalizeConditionContract(rawContract);
	assert.ok(contract, "Contract must normalize successfully");

	// 1. Backend operator labels are conversational
	assert.equal(contract.operators.eq.label, "is");
	assert.equal(contract.operators.gt.label, "is greater than");
	assert.equal(contract.operators.in.label, "is one of");
	assert.equal(contract.operators.is_set.label, "is set");

	// 2. Draft state: blank left operand fails validation
	const blankLeftTree = {
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
	let res = validateCanonicalCondition(blankLeftTree, { isMandatory: true, contract });
	assert.equal(res.valid, false);
	assert.ok(res.errors.some((e) => e.includes("choose a value source")));

	// 3. Left operand selected: selecting doc.grand_total converts to canonical variable
	const leftVar = fieldExpressionToCanonicalVariable("doc.grand_total");
	assert.deepEqual(leftVar, {
		mode: "variable",
		path: { scope: "doc", segments: ["grand_total"] },
	});

	// 4. Operator selection: binary operator initializes empty right value without implicit 0
	const emptyRightNumeric = {
		mode: "static",
		value_type: "decimal",
		value: "",
	};
	assert.equal(emptyRightNumeric.value, "");
	assert.notEqual(emptyRightNumeric.value, 0, "Must not implicitly default to 0");

	// 5. Membership operator: initializes canonical empty list []
	const emptyMembershipRight = {
		mode: "static",
		value_type: "list",
		value: [],
	};
	assert.deepEqual(emptyMembershipRight.value, []);
	assert.equal(emptyMembershipRight.value_type, "list");

	// 6. Unary operator: serializes without right operand
	const unaryNode = {
		id: "leaf-unary",
		type: "leaf",
		operator: "is_set",
		left: leftVar,
		right: null,
	};
	const serializedUnary = serializeConditionTree(
		{ id: "root", type: "group", children: [unaryNode] },
		contract.operators
	);
	assert.equal(serializedUnary.operator, "is_set");
	assert.equal("right" in serializedUnary, false, "Unary comparison must not have right key");

	// 7. Dynamic right operand: supports variable and resolver
	const dynamicRightVar = {
		mode: "variable",
		path: { scope: "vars", segments: ["limit_total"] },
	};
	const validBinaryComparison = {
		type: "comparison",
		operator: "gt",
		left: leftVar,
		right: dynamicRightVar,
	};
	const validTree = { id: "root", type: "group", children: [validBinaryComparison] };
	const finalRes = validateCanonicalCondition(validTree, { isMandatory: true, contract });
	assert.equal(finalRes.valid, true);
	assert.equal(finalRes.errors.length, 0);
});
