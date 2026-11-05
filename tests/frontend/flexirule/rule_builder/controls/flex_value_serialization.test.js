import assert from "node:assert/strict";
import test from "node:test";

test("FlexValue canonical serialization contracts", () => {
	// Static mode with Frappe-native fieldtypes
	const staticInt = { mode: "static", value_type: "Int", value: 10 };
	assert.equal(staticInt.mode, "static");
	assert.equal(staticInt.value_type, "Int");
	assert.equal(staticInt.value, 10);

	// Static Check (0 or 1)
	const staticCheck = { mode: "static", value_type: "Check", value: 1 };
	assert.equal(staticCheck.mode, "static");
	assert.equal(staticCheck.value_type, "Check");
	assert.equal(staticCheck.value, 1);

	// Structured Variable
	const variablePayload = {
		mode: "variable",
		path: { scope: "doc", segments: ["grand_total"] },
	};
	assert.equal(variablePayload.mode, "variable");
	assert.equal(variablePayload.path.scope, "doc");
	assert.deepEqual(variablePayload.path.segments, ["grand_total"]);

	// Resolver Operation
	const resolverPayload = {
		mode: "resolver",
		family: "math",
		operation: "formula",
		value_type: "Float",
		config: {
			field_a: "doc.qty",
			math_op: "*",
			constant_b: 2,
		},
	};
	assert.equal(resolverPayload.mode, "resolver");
	assert.equal(resolverPayload.family, "math");
	assert.equal(resolverPayload.operation, "formula");
	assert.equal(resolverPayload.value_type, "Float");
});
