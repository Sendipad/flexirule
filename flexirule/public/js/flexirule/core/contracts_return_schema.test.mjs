import assert from "node:assert/strict";
import {
	applyContractDto,
	hasResolvedOutputSchema,
	validateAgainstContract,
	applyOutputPolicyDefaults,
	getEffectiveActionPolicy,
	requiresReturnVariable,
} from "./contracts_policy.mjs";

// Mock Frappe global translation function if missing
if (typeof globalThis.__ === "undefined") {
	globalThis.__ = (str) => str;
}

// Initialize DTO fixture matching realistic backend Process, Query Records, and Document Action policies
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
				"Exist Record": {
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
			allowed_mutations: ["Set Doc Field", "Update Doc Field"],
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
		Process: {
			produces_result: true,
			supports_return_schema: true,
			show_return_type: true,
		},
	},
	process_operation_registry_v2: {
		"Validation Process": {
			validate_role: {
				policy: {
					allowed_mutations: ["Set Context Variable", "Update Context Variable"],
					allowed_return_types: ["Yes / No"],
					default_return_type: "Yes / No",
					require_return_type: false,
					require_return_variable: false,
					supports_return_schema: false,
				},
			},
			calculate_tax: {
				policy: {
					allowed_mutations: ["Set Context Variable", "Update Context Variable"],
					allowed_return_types: ["Single Record"],
					require_return_variable: true,
					supports_return_schema: true,
				},
			},
		},
	},
	action_types_with_return_schema: ["Query Records", "Document Action", "Sub-Rule", "Process"],
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
	hasResolvedOutputSchema(JSON.stringify({ properties: { customer: { type: "string" } } })),
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
		config:
			actionType === "Condition"
				? JSON.stringify({ op: "and", conditions: [{ field: "name" }] })
				: "{}",
	};

	assert.equal(requiresReturnVariable(nodeData), false);
	const validation = validateAgainstContract(nodeData);
	assert.equal(
		validation.valid,
		true,
		`Non-result action ${actionType} with stale fields should be valid: ${validation.errors.join(
			", "
		)}`
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
	assert.equal(requiresReturnVariable(queryRecordsNode, { operation: "Fetch Records" }), false);
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
	assert.equal(
		requiresReturnVariable(queryRecordsWithSchema, { operation: "Fetch Records" }),
		true
	);
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
	assert.equal(requiresReturnVariable(docActionCreate, { operation: "Create New" }), true);
	const res = validateAgainstContract(docActionCreate);
	assert.equal(
		res.errors.some((e) => e.includes("Return Schema requires a Return Variable Name")),
		true
	);
}

// ── 4. Test "Yes / No" Return Type & Operation-Level Policy Overrides ──

// Return type "Yes / No" does NOT require return_variable
{
	const nodeWithYesNo = {
		action_type: "Document Action",
		operation: "Save Doc",
		return_type: "Yes / No",
		resolved_output_schema: "[]",
		return_variable: null,
	};
	assert.equal(requiresReturnVariable(nodeWithYesNo, { operation: "Save Doc" }), false);
	const res = validateAgainstContract(nodeWithYesNo);
	assert.equal(
		res.errors.some((e) => e.includes("Return Schema requires a Return Variable Name")),
		false
	);
}

{
	const queryExistsPolicy = getEffectiveActionPolicy("Query Records", {
		operation: "Exist Record",
	});
	assert.equal(queryExistsPolicy.supports_return_schema, false);
}

// ── 7. Test Public Module Export Surface ──
import * as contractsFacade from "./contracts_policy.mjs";
assert.equal(typeof contractsFacade.getAllowedReturnTypeOptions, "function");
assert.equal(typeof contractsFacade.getAllowedMutationModeOptions, "function");
assert.equal(typeof contractsFacade.getFieldLabel, "function");
assert.equal(typeof contractsFacade.getOperationOptions, "function");
assert.equal(typeof contractsFacade.getTriggerTypeContract, "function");
assert.equal(typeof contractsFacade.shouldShowReturnType, "function");
assert.equal(typeof contractsFacade.isReturnTypeMandatory, "function");
assert.equal(typeof contractsFacade.getActionFeatureFlags, "function");
assert.equal(typeof contractsFacade.getNodeStatus, "function");

// ── 5. Test Process contract_v2 Policies ──

// Process with validate_role (Yes / No return type) does NOT require return_variable
{
	const processValidateRole = {
		action_type: "Process",
		process_name: "Validation Process",
		operation: "validate_role",
		return_type: "Yes / No",
		resolved_output_schema: "[]",
		return_variable: null,
	};
	const ctx = { processName: "Validation Process", operation: "validate_role" };
	assert.equal(requiresReturnVariable(processValidateRole, ctx), false);
	const res = validateAgainstContract(processValidateRole);
	assert.equal(
		res.errors.some((e) => e.includes("Return Schema requires a Return Variable Name")),
		false
	);
}

// Process with calculate_tax (requires_return_variable = true) requires return_variable
{
	const processCalculateTax = {
		action_type: "Process",
		process_name: "Validation Process",
		operation: "calculate_tax",
		return_type: "Single Record",
		resolved_output_schema: "[]",
		return_variable: null,
	};
	const ctx = { processName: "Validation Process", operation: "calculate_tax" };
	assert.equal(requiresReturnVariable(processCalculateTax, ctx), true);
	const res = validateAgainstContract(processCalculateTax);
	assert.equal(
		res.errors.some((e) => e.includes("Return Variable Name is required")),
		true
	);
}

// ── 6. Test Mutation Mode Requirements ──

// Supported mutation mode requires return_variable
{
	const docActionMutation = {
		action_type: "Document Action",
		operation: "Create New",
		mutation_mode: "Set Doc Field",
		return_variable: null,
	};
	const ctx = { operation: "Create New" };
	assert.equal(requiresReturnVariable(docActionMutation, ctx), true);
}

// Unsupported/stale mutation mode on an action with empty allowed_mutations does NOT require return_variable
{
	const entryActionWithStaleMutation = {
		action_type: "Entry Action",
		mutation_mode: "Set Doc Field",
		return_variable: null,
	};
	assert.equal(requiresReturnVariable(entryActionWithStaleMutation), false);
	const res = validateAgainstContract(entryActionWithStaleMutation);
	assert.equal(
		res.errors.some((e) => e.includes("Mutation Mode requires a Return Variable Name")),
		false
	);
}

console.log("Contracts return schema unit tests passed!");
