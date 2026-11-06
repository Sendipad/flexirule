import test from "node:test";
import assert from "node:assert/strict";

import {
	getConditionPayloadFromConfig,
	getConditionPayload,
	hasConditionPayload,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/condition_payload.js";

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

	assert.deepEqual(getConditionPayloadFromConfig(unknownRoot), unknownRoot);
	assert.deepEqual(getConditionPayload({ config: unknownRoot }), unknownRoot);
	assert.equal(hasConditionPayload({ config: unknownRoot }), true);

	const unknownArray = [
		{ custom_type: "foo", val: 1 },
		{ custom_type: "bar", val: 2 },
	];
	assert.deepEqual(getConditionPayloadFromConfig(unknownArray), unknownArray);
	assert.deepEqual(getConditionPayload({ config: unknownArray }), unknownArray);

	// Distinguishes non-condition action configs (e.g. assignments)
	const assignmentConfig = {
		assignments: [{ target: "status", value: "Closed" }],
	};
	assert.equal(getConditionPayloadFromConfig(assignmentConfig), null);

	// Genuinely empty object or null
	assert.equal(getConditionPayloadFromConfig({}), null);
	assert.equal(getConditionPayloadFromConfig(null), null);
});
