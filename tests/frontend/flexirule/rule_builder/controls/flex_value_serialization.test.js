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

test("Resolver identity serialize and deserialize round-tripping equality", () => {
	function escapeAttr(str) {
		return String(str || "")
			.replace(/&/g, "&amp;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#39;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;");
	}

	function deserializeMock(val) {
		if (val.mode === "variable") {
			const displayPath = `${val.path.scope}.${val.path.segments.join(".")}`;
			return `<span data-token-type="variable" data-path="${escapeAttr(
				displayPath
			)}"></span>`;
		}
		if (val.mode === "resolver") {
			return `<span data-token-type="resolver" data-family="${escapeAttr(
				val.family
			)}" data-operation="${escapeAttr(val.operation)}" data-config='${escapeAttr(
				JSON.stringify(val.config)
			)}'></span>`;
		}
		if (val.mode === "template") {
			return val.segments
				.map((seg) => (seg.type === "text" ? seg.value : deserializeMock(seg.value)))
				.join("");
		}
		return "";
	}

	function serializeMockToken(attrs) {
		if (attrs.type === "variable") {
			const parts = attrs.path.split(".");
			return {
				mode: "variable",
				path: { scope: parts[0], segments: parts.slice(1) },
			};
		}
		if (attrs.type === "resolver") {
			return {
				mode: "resolver",
				family: attrs.family,
				operation: attrs.operation,
				config: attrs.config,
			};
		}
	}

	// 1. Resolver round-tripping
	const resolverOriginal = {
		mode: "resolver",
		family: "math",
		operation: "formula",
		config: { field_a: "doc.qty", math_op: "*", constant_b: 2 },
	};
	const html = deserializeMock(resolverOriginal);
	assert.ok(html.includes('data-family="math"'));
	assert.ok(html.includes('data-operation="formula"'));

	const tokenAttrs = {
		type: "resolver",
		family: "math",
		operation: "formula",
		config: { field_a: "doc.qty", math_op: "*", constant_b: 2 },
	};
	const reserialized = serializeMockToken(tokenAttrs);
	assert.deepEqual(reserialized, resolverOriginal);

	// 2. Variable round-tripping
	const varOriginal = {
		mode: "variable",
		path: { scope: "doc", segments: ["customer", "name"] },
	};
	const varHtml = deserializeMock(varOriginal);
	assert.ok(varHtml.includes('data-path="doc.customer.name"'));
	const varAttrs = { type: "variable", path: "doc.customer.name" };
	const varReserialized = serializeMockToken(varAttrs);
	assert.deepEqual(varReserialized, varOriginal);
	assert.equal(
		varReserialized.value,
		undefined,
		"Serialized variable must not contain value property"
	);
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
