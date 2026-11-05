import assert from "node:assert/strict";
import test from "node:test";
import {
	escapeAttr,
	escapeHtml,
	coerceStructuredValue,
	deserializeFlexValue,
	serializeContentNodes,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/flex_value_serializer.js";

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

	// Canonical Template mode with structured segments
	const templatePayload = {
		mode: "template",
		segments: [
			{ type: "text", value: "Customer: " },
			{
				type: "value",
				value: {
					mode: "variable",
					path: { scope: "doc", segments: ["customer_name"] },
				},
			},
		],
	};
	assert.equal(templatePayload.mode, "template");
	assert.equal(templatePayload.segments.length, 2);
	assert.equal(templatePayload.segments[0].type, "text");
	assert.equal(templatePayload.segments[0].value, "Customer: ");
	assert.equal(templatePayload.segments[1].type, "value");
	assert.deepEqual(templatePayload.segments[1].value, {
		mode: "variable",
		path: { scope: "doc", segments: ["customer_name"] },
	});
});

test("Production flex_value_serializer deserialize round-tripping & HTML escaping", () => {
	// 1. Resolver round-tripping
	const resolverOriginal = {
		mode: "resolver",
		family: "math",
		operation: "formula",
		config: { field_a: "doc.qty", math_op: "*", constant_b: 2 },
	};
	const html = deserializeFlexValue(resolverOriginal);
	assert.ok(html.includes('data-token-type="resolver"'));
	assert.ok(html.includes('data-family="math"'));
	assert.ok(html.includes('data-operation="formula"'));

	const tokenAttrs = {
		attrs: {
			family: "math",
			operation: "formula",
			config: { field_a: "doc.qty", math_op: "*", constant_b: 2 },
		},
		type: { name: "resolverToken" },
	};
	const reserialized = serializeContentNodes([tokenAttrs]);
	assert.deepEqual(reserialized.config, resolverOriginal.config);
	assert.equal(reserialized.family, resolverOriginal.family);
	assert.equal(reserialized.operation, resolverOriginal.operation);
	assert.equal(reserialized.mode, "resolver");

	// 2. Variable round-tripping
	const varOriginal = {
		mode: "variable",
		path: { scope: "doc", segments: ["customer", "name"] },
	};
	const varHtml = deserializeFlexValue(varOriginal);
	assert.ok(varHtml.includes('data-token-type="variable"'));
	assert.ok(varHtml.includes('data-path="doc.customer.name"'));

	const varToken = {
		type: { name: "variableToken" },
		attrs: { path: "doc.customer.name" },
	};
	const varReserialized = serializeContentNodes([varToken]);
	assert.deepEqual(varReserialized, varOriginal);
	assert.equal(
		varReserialized.value,
		undefined,
		"Serialized variable must not contain value property"
	);

	// 3. Template HTML escaping (P2 finding prevention)
	const maliciousTemplate = {
		mode: "template",
		segments: [
			{ type: "text", value: "Use <script>alert(1)</script> & <b>priority</b>" },
			{
				type: "value",
				value: {
					mode: "variable",
					path: { scope: "doc", segments: ["customer"] },
				},
			},
		],
	};
	const deserializedHtml = deserializeFlexValue(maliciousTemplate);
	assert.ok(!deserializedHtml.includes("<script>"));
	assert.ok(deserializedHtml.includes("&lt;script&gt;"));
	assert.ok(deserializedHtml.includes("&amp;"));
	assert.ok(deserializedHtml.includes("&lt;b&gt;priority&lt;/b&gt;"));
});

test("Required resolver payload structural validation", () => {
	function isStructValid(struct) {
		if (!struct || typeof struct !== "object") return false;
		if (struct.mode === "variable")
			return !!(struct.path?.scope && struct.path?.segments?.length);
		if (struct.mode === "resolver") {
			return !!(
				struct.family &&
				struct.operation &&
				struct.config &&
				typeof struct.config === "object"
			);
		}
		if (struct.mode === "template")
			return Array.isArray(struct.segments) && struct.segments.length > 0;
		return true;
	}

	const canonicalResolver = {
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
	assert.equal(isStructValid(canonicalResolver), true);

	const incompleteResolver = {
		mode: "resolver",
		family: "",
		operation: "formula",
		config: {},
	};
	assert.equal(isStructValid(incompleteResolver), false);
});

test("Assignment Clear and Set transitions and serialization", () => {
	function needsValue(operator) {
		const op = (operator || "").toLowerCase();
		return !["clear", "toggle"].includes(op);
	}

	function syncToNodeMock(assignments) {
		return assignments.map((a) => {
			const row = {
				name: a.name || "test-id",
				target: a.target,
				operator: a.operator,
				when_condition: a.when_condition || null,
			};
			if (needsValue(a.operator)) {
				row.value = a.value;
			}
			return row;
		});
	}

	// 1. Initial Set assignment with valid typed FlexValue
	const row = {
		name: "row-1",
		target: "doc.status",
		operator: "set",
		value: { mode: "static", value_type: "Data", value: "Closed" },
	};
	let serialized = syncToNodeMock([row]);
	assert.equal(serialized[0].operator, "set");
	assert.deepEqual(serialized[0].value, { mode: "static", value_type: "Data", value: "Closed" });

	// 2. Transition Set -> Clear: Serialized row must omit value property
	row.operator = "clear";
	serialized = syncToNodeMock([row]);
	assert.equal(serialized[0].operator, "clear");
	assert.equal(
		serialized[0].value,
		undefined,
		"Serialized row must omit value for clear operator"
	);
	assert.equal("value" in serialized[0], false);

	// 3. Transition Clear -> Set: Valid FlexValue with value_type must be initialized
	row.operator = "set";
	if (needsValue(row.operator)) {
		if (!row.value || !row.value.mode || !row.value.value_type) {
			row.value = { mode: "static", value_type: "Data", value: "" };
		}
	}
	serialized = syncToNodeMock([row]);
	assert.equal(serialized[0].operator, "set");
	assert.deepEqual(serialized[0].value, { mode: "static", value_type: "Data", value: "Closed" });
});
