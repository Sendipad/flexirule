import assert from "node:assert/strict";
import { test } from "node:test";
import { isConsoleRegressionMessage } from "../../../../../cypress/support/regression_guards.mjs";

test("isConsoleRegressionMessage detects known grid and schema regressions", () => {
	assert.equal(
		isConsoleRegressionMessage("Error: Could not find grid field 'target_field'"),
		true
	);
	assert.equal(
		isConsoleRegressionMessage(
			"TypeError: Cannot set property hasResolvedOutputSchema of undefined"
		),
		true
	);
	assert.equal(isConsoleRegressionMessage("grid field 'options' not found in row"), true);
});

test("isConsoleRegressionMessage rejects unrelated console messages", () => {
	assert.equal(isConsoleRegressionMessage("Server responded with 404"), false);
	assert.equal(isConsoleRegressionMessage("Navigated to /app/rule"), false);
	assert.equal(isConsoleRegressionMessage("show_page event fired"), false);
	assert.equal(isConsoleRegressionMessage(null), false);
	assert.equal(isConsoleRegressionMessage(undefined), false);
});
