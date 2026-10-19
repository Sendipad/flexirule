import assert from "node:assert/strict";
import {
	applyContractDto,
	hasResolvedOutputSchema,
	validateAgainstContract,
	applyOutputPolicyDefaults,
	getEffectiveActionPolicy,
} from "./contracts.js";

// Mock Frappe global translation function if missing
if (typeof globalThis.__ === "undefined") {
	globalThis.__ = (str) => str;
}

// Initialize DTO fixture for contract unit tests
applyContractDto({
	action_type_contract: {
		"Entry Action": {
			produces_result: false,
			supports_return_schema: false,
			show_return_type: false,
		},
		Condition: {
			produces_result: false,
			supports_return_schema: false,
			show_return_type: false,
		},
		Assignment: {
			produces_result: false,
			supports_return_schema: false,
			show_return_type: false,
		},
		Stop: {
			produces_result: false,
			supports_return_schema: false,
			show_return_type: false,
			terminal: true,
		},
		"Query Records": {
			produces_result: true,
			supports_return_schema: true,
			show_return_type: false,
			allowed_return_types: ["List of Records", "List of Values"],
			operation_policies: {
				"Fetch Records": {
					supports_return_schema: true,
					show_return_type: false,
				},
				Exists: {
					supports_return_schema: false,
					show_return_type: false,
					allowed_return_types: ["Yes / No"],
				},
			},
		},
		"Document Action": {
			produces_result: true,
			supports_return_schema: true,
			show_return_type: true,
			allowed_return_types: ["Single Record", "Full Document", "Yes / No"],
			operation_policies: {
				"Create New": {
					supports_return_schema: true,
					show_return_type: true,
					allowed_return_types: ["Single Record", "Full Document"],
				},
				"Save Doc": {
					supports_return_schema: false,
					show_return_type: false,
					allowed_return_types: ["Yes / No"],
				},
			},
		},
		"Sub-Rule": {
			produces_result: true,
			supports_return_schema: true,
			show_return_type: true,
			allowed_return_types: ["Single Record", "List of Records", "Yes / No"],
		},
	},
	action_types_with_return_schema: ["Query Records", "Document Action", "Sub-Rule"],
});

// ── 1. Test hasResolvedOutputSchema ──────────────────────────────────────────

// Empty forms must return false
assert.equal(hasResolvedOutputSchema(null), false);
assert.equal(hasResolvedOutputSchema(undefined), false);
assert.equal(hasResolvedOutputSchema(""), false);
assert.equal(hasResolvedOutputSchema("[]"), false);
assert.equal(hasResolvedOutputSchema("{}"), false);
assert.equal(hasResolvedOutputSchema("null"), false);
assert.equal(hasResolvedOutputSchema([]), false);
assert.equal(hasResolvedOutputSchema({}), false);
assert.equal(hasResolvedOutputSchema({ fields: [] }), false);
assert.equal(hasResolvedOutputSchema({ properties: {} }), false);
assert.equal(hasResolvedOutputSchema(JSON.stringify({ fields: [] })), false);
assert.equal(hasResolvedOutputSchema(JSON.stringify({ properties: {} })), false);
assert.equal(hasResolvedOutputSchema([{ fieldname: "" }]), false);

// Populated forms must return true
assert.equal(hasResolvedOutputSchema([{ fieldname: "customer" }]), true);
assert.equal(hasResolvedOutputSchema(JSON.stringify([{ fieldname: "customer" }])), true);
assert.equal(hasResolvedOutputSchema({ fields: [{ fieldname: "customer" }] }), true);
assert.equal(
	hasResolvedOutputSchema(JSON.stringify({ fields: [{ fieldname: "customer" }] })),
	true
);
assert.equal(hasResolvedOutputSchema({ properties: { customer: { type: "string" } } }), true);
assert.equal(
	hasResolvedOutputSchema(
		JSON.stringify({ properties: { customer: { type: "string" } } })
	),
	true
);

// ── 2. Test Non-Result Actions (Entry Action, Condition, Assignment, Stop) ──

const nonResultActionTypes = ["Entry Action", "Condition", "Assignment", "Stop"];
for (const actionType of nonResultActionTypes) {
	const nodeData = {
		action_type: actionType,
		return_type: "List of Records",
		resolved_output_schema: "[]",
		return_variable: null,
		config: actionType === "Condition" ? JSON.stringify({ op: "and", conditions: [{ field: "name" }] }) : "{}",
	};

	const validation = validateAgainstContract(nodeData);
	assert.equal(
		validation.valid,
		true,
		`Non-result action ${actionType} with stale fields should be valid: ${validation.errors.join(", ")}`
	);
	assert.equal(
		validation.errors.some((e) => e.includes("Return Schema requires a Return Variable Name")),
		false
	);

	const changed = applyOutputPolicyDefaults(nodeData, { preserveUserChoices: true });
	assert.equal(nodeData.return_variable, null);
}

// ── 3. Test Schema-Capable Actions ──

// A schema-capable action with empty schema and hidden/unselected return type does NOT require return_variable
{
	const queryRecordsNode = {
		action_type: "Query Records",
		operation: "Fetch Records",
		return_type: "List of Records",
		resolved_output_schema: "[]",
		return_variable: null,
	};
	const res = validateAgainstContract(queryRecordsNode);
	assert.equal(
		res.errors.some((e) => e.includes("Return Schema requires a Return Variable Name")),
		false
	);
}

// A schema-capable action with genuinely populated schema requires return_variable
{
	const queryRecordsWithSchema = {
		action_type: "Query Records",
		operation: "Fetch Records",
		return_type: "List of Records",
		resolved_output_schema: JSON.stringify([{ fieldname: "name", label: "Name" }]),
		return_variable: null,
	};
	const res = validateAgainstContract(queryRecordsWithSchema);
	assert.equal(
		res.errors.some((e) => e.includes("Return Schema requires a Return Variable Name")),
		true
	);
}

// Document Action / Create New with visible return_type requires return_variable
{
	const docActionCreate = {
		action_type: "Document Action",
		operation: "Create New",
		return_type: "Single Record",
		resolved_output_schema: "[]",
		return_variable: null,
	};
	const res = validateAgainstContract(docActionCreate);
	assert.equal(
		res.errors.some((e) => e.includes("Return Schema requires a Return Variable Name")),
		true
	);
}

// ── 4. Test "Yes / No" Return Type ──

// Return type "Yes / No" does NOT require return_variable
{
	const nodeWithYesNo = {
		action_type: "Document Action",
		operation: "Save Doc",
		return_type: "Yes / No",
		resolved_output_schema: "[]",
		return_variable: null,
	};
	const res = validateAgainstContract(nodeWithYesNo);
	assert.equal(
		res.errors.some((e) => e.includes("Return Schema requires a Return Variable Name")),
		false
	);
}

// ── 5. Test Operation-Level Policy Overrides ──

{
	const queryExistsPolicy = getEffectiveActionPolicy("Query Records", { operation: "Exists" });
	assert.equal(queryExistsPolicy.supports_return_schema, false);
}

console.log("Contracts return schema unit tests passed!");
