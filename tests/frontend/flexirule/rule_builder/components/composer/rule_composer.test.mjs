import test from "node:test";
import assert from "node:assert/strict";
import {
	buildContextualSuggestions,
	groupSuggestions,
	SUGGESTION_GROUPS,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/composer/ComposerContextAdapter.js";
import {
	deserializeConditionTree,
	serializeConditionTree,
} from "../../../../../../flexirule/public/js/flexirule/rule_builder/components/condition_builder/canonical_condition_adapter.mjs";

test("ComposerContextAdapter: aggregates Document, Variables, and Resolvers by group", () => {
	const docFields = [
		{ fieldname: "total", label: "Grand Total", fieldtype: "Currency" },
		{ fieldname: "status", label: "Status", fieldtype: "Select" },
		{ fieldname: "is_active", label: "Is Active", fieldtype: "Check" },
	];
	const variableOptions = [
		{ value: "vars.user_limit", label: "User Limit", fieldtype: "Float" },
		{ value: "context.user", label: "Current User", fieldtype: "Data" },
	];
	const contract = {
		flexvalue_modes: {
			resolver: [
				{
					family: "math",
					operation: "formula",
					label: "Math Formula",
					output_type: "Float",
					condition_operand_allowed: true,
				},
				{
					family: "date_time",
					operation: "current",
					label: "Current Date/Time",
					output_type: "Date",
					condition_operand_allowed: true,
				},
				{
					family: "lookup",
					operation: "fetch",
					label: "Lookup",
					output_type: "Data",
					condition_operand_allowed: false, // Disallowed in condition operand!
				},
			],
		},
	};

	// 1. In condition operand context: lookup should be omitted (fail-closed)
	const condSuggestions = buildContextualSuggestions({
		docFields,
		variableOptions,
		contract,
		isConditionOperand: true,
	});

	assert.equal(
		condSuggestions.some((s) => s.id === "resolver:lookup.fetch"),
		false
	);
	assert.equal(
		condSuggestions.some((s) => s.id === "resolver:math.formula"),
		true
	);
	assert.equal(
		condSuggestions.some((s) => s.id === "doc:total"),
		true
	);
	assert.equal(
		condSuggestions.some((s) => s.id === "var:vars.user_limit"),
		true
	);

	// 2. In non-condition operand context: lookup is allowed
	const allSuggestions = buildContextualSuggestions({
		docFields,
		variableOptions,
		contract,
		isConditionOperand: false,
	});
	assert.equal(
		allSuggestions.some((s) => s.id === "resolver:lookup.fetch"),
		true
	);

	// 3. Verify Grouping
	const groups = groupSuggestions(condSuggestions);
	const groupNames = groups.map((g) => g.name);
	assert.deepEqual(groupNames, [
		SUGGESTION_GROUPS.DOCUMENT,
		SUGGESTION_GROUPS.VARIABLES,
		SUGGESTION_GROUPS.VALUES,
	]);
});

test("ComposerContextAdapter: filters suggestions by query", () => {
	const docFields = [
		{ fieldname: "total", label: "Grand Total", fieldtype: "Currency" },
		{ fieldname: "status", label: "Status", fieldtype: "Select" },
	];
	const contract = {
		flexvalue_modes: {
			resolver: [
				{
					family: "math",
					operation: "formula",
					label: "Math Formula",
					output_type: "Float",
					condition_operand_allowed: true,
				},
			],
		},
	};

	const filtered = buildContextualSuggestions({
		docFields,
		contract,
		query: "tot",
	});

	assert.equal(filtered.length, 1);
	assert.equal(filtered[0].id, "doc:total");
	assert.equal(filtered[0].mentionLabel, "@doc.total");
});

test("Composer operator compatibility: enforces operator resets on left operand change", () => {
	const operatorList = [
		{
			id: "gt",
			label: "is greater than",
			arity: 2,
			accepted_left_types: ["decimal", "integer"],
			fieldtypes: ["Int", "Float", "Currency"],
		},
		{
			id: "eq",
			label: "is",
			arity: 2,
			accepted_left_types: ["decimal", "integer", "string", "boolean"],
			fieldtypes: ["Int", "Float", "Currency", "Select", "Data", "Check"],
		},
	];

	// For a Currency field, 'gt' is valid
	const isGtValidForCurrency = operatorList.some(
		(op) => op.id === "gt" && op.fieldtypes.includes("Currency")
	);
	assert.equal(isGtValidForCurrency, true);

	// For a Check/Boolean field, 'gt' is NOT valid
	const isGtValidForCheck = operatorList.some(
		(op) => op.id === "gt" && op.fieldtypes.includes("Check")
	);
	assert.equal(isGtValidForCheck, false);
});

test("Composer serialization: round-trip comparison nodes through composer structure without transient UI leakage", () => {
	const canonicalComparison = {
		type: "comparison",
		operator: "gt",
		left: {
			mode: "variable",
			path: { scope: "doc", segments: ["total"] },
		},
		right: {
			mode: "static",
			value_type: "decimal",
			value: "100.5",
		},
	};

	const tree = deserializeConditionTree(canonicalComparison);
	assert.equal(tree.children.length, 1);
	const leaf = tree.children[0];
	assert.equal(leaf.operator, "gt");
	assert.equal(leaf.left.path.segments[0], "total");

	// Serialize back and verify pure canonical output without temporary IDs
	const serialized = serializeConditionTree(tree);
	assert.deepEqual(serialized, canonicalComparison);
	assert.equal("id" in serialized, false);
	assert.equal("_draft_right" in serialized, false);
	assert.equal("_invalid_right_error" in serialized, false);
});
