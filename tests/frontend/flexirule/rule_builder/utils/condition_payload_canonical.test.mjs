import test from "node:test";
import assert from "node:assert/strict";

import {
	getConditionPayloadFromConfig,
	getConditionPayload,
	hasConditionPayload,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/condition_payload.js";
import { validateAgainstContract } from "../../../../../flexirule/public/js/flexirule/core/contracts.js";

test("condition_payload: recognizes direct canonical comparison node", () => {
	const canonical = {
		type: "comparison",
		operator: "eq",
		left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
		right: { mode: "static", value_type: "string", value: "Open" },
	};

	assert.deepEqual(getConditionPayloadFromConfig(canonical), canonical);
	assert.deepEqual(getConditionPayload({ config: canonical }), canonical);
	assert.equal(hasConditionPayload({ config: canonical }), true);
});

test("condition_payload: recognizes direct canonical group node", () => {
	const canonicalGroup = {
		type: "group",
		operator: "and",
		children: [
			{
				type: "comparison",
				operator: "eq",
				left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
			},
			{
				type: "comparison",
				operator: "gt",
				left: { mode: "variable", path: { scope: "doc", segments: ["grand_total"] } },
				right: { mode: "static", value_type: "decimal", value: "100" },
			},
		],
	};

	assert.deepEqual(getConditionPayloadFromConfig(canonicalGroup), canonicalGroup);
	assert.deepEqual(getConditionPayload({ config: canonicalGroup }), canonicalGroup);
	assert.equal(hasConditionPayload({ config: canonicalGroup }), true);
});

test("condition_payload: preserves backward compatibility for legacy shapes", () => {
	const legacyConfig = {
		condition: {
			op: "and",
			conditions: [{ left: { ref: "doc.status" }, op: "==", right: { value: "Open" } }],
		},
	};

	assert.deepEqual(getConditionPayloadFromConfig(legacyConfig), legacyConfig.condition);
	assert.deepEqual(getConditionPayload({ config: legacyConfig }), legacyConfig.condition);
	assert.equal(hasConditionPayload({ config: legacyConfig }), true);
});

test("condition_payload: preserves unknown root condition objects and non-empty unknown arrays", () => {
	const unknownRoot = {
		type: "unknown_custom_condition_v99",
		custom_field: "special_value",
	};

	assert.equal(getConditionPayloadFromConfig(unknownRoot), null);
	assert.equal(getConditionPayload({ config: unknownRoot, action_type: "Fetch Records" }), null);
	assert.deepEqual(
		getConditionPayload({ config: unknownRoot, action_type: "Condition" }),
		unknownRoot
	);
	assert.equal(hasConditionPayload({ config: unknownRoot, action_type: "Condition" }), true);

	const unknownArray = [
		{ custom_type: "foo", val: 1 },
		{ custom_type: "bar", val: 2 },
	];
	assert.equal(getConditionPayloadFromConfig(unknownArray), null);
	assert.deepEqual(
		getConditionPayload({ config: unknownArray, action_type: "Condition" }),
		unknownArray
	);

	// Distinguishes non-condition action configs (e.g. assignments)
	const assignmentConfig = {
		assignments: [{ target: "status", value: "Closed" }],
	};
	assert.equal(getConditionPayloadFromConfig(assignmentConfig), null);
	assert.equal(
		getConditionPayload({ config: { iterator: "doc.items" }, action_type: "Loop" }),
		null
	);
	assert.equal(
		getConditionPayload({
			config: { filters: [{ field: "status", value: "Open" }] },
			action_type: "Fetch Records",
		}),
		null
	);
	assert.equal(
		getConditionPayload({
			action_type: "Loop",
			config: { type: "group", operator: "and", children: [] },
		}),
		null
	);

	const malformed = '{"type":"comparison",';
	assert.equal(getConditionPayload({ config: malformed, action_type: "Fetch Records" }), null);
	assert.equal(getConditionPayload({ config: malformed, action_type: "Condition" }), malformed);

	// Genuinely empty object or null
	assert.equal(getConditionPayloadFromConfig({}), null);
	assert.equal(getConditionPayloadFromConfig(null), null);
});

test("condition_payload: validateAgainstContract accepts a direct canonical Condition root", () => {
	const nodeData = {
		action_type: "Condition",
		config: {
			type: "comparison",
			operator: "eq",
			left: { mode: "variable", path: { scope: "doc", segments: ["status"] } },
			right: { mode: "static", value_type: "string", value: "Open" },
		},
	};
	const result = validateAgainstContract(nodeData);
	assert.equal(result.valid, true, JSON.stringify(result.errors));
	assert.equal(
		result.errors.some((error) => error.includes("At least one condition is required")),
		false
	);
});
