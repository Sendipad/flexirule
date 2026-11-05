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
	assert.equal(
		"value" in variablePayload,
		false,
		"value property must not exist on variable payload"
	);
	assert.deepEqual(Object.keys(variablePayload).sort(), ["mode", "path"]);

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

	// Template Mode with Mixed Text and Dynamic Values
	const templatePayload = {
		mode: "template",
		segments: [
			{ type: "text", value: "Order " },
			{
				type: "value",
				value: {
					mode: "variable",
					path: { scope: "doc", segments: ["name"] },
				},
			},
			{ type: "text", value: " processed" },
		],
	};
	assert.equal(templatePayload.mode, "template");
	assert.equal(templatePayload.segments.length, 3);
	assert.equal(templatePayload.segments[0].type, "text");
	assert.equal(templatePayload.segments[0].value, "Order ");
	assert.equal(templatePayload.segments[1].type, "value");
	assert.equal(templatePayload.segments[1].value.mode, "variable");
	assert.deepEqual(templatePayload.segments[1].value.path, { scope: "doc", segments: ["name"] });
});

import {
	deserializeFlexValue,
	unescapeAttr,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/flex_value_helpers.mjs";

test("Resolver identity serialize -> deserialize -> serialize equality", () => {
	const original = {
		mode: "resolver",
		family: "math",
		operation: "formula",
		value_type: "Float",
		config: {
			field_a: "doc.price",
			math_op: "*",
			constant_b: 1.15,
		},
	};

	// Call the actual deserializer used by FlexValueControl
	const deserializedHtml = deserializeFlexValue(original, "Float");

	// Verify HTML attributes contain family, operation, and value_type
	assert.match(deserializedHtml, /data-family="math"/);
	assert.match(deserializedHtml, /data-operation="formula"/);
	assert.match(deserializedHtml, /data-value-type="Float"/);

	// Simulate node parsing matching FlexValueControl's ResolverToken.parseHTML
	const familyMatch = deserializedHtml.match(/data-family="([^"]*)"/);
	const opMatch = deserializedHtml.match(/data-operation="([^"]*)"/);
	const vtMatch = deserializedHtml.match(/data-value-type="([^"]*)"/);
	const cfgMatch = deserializedHtml.match(/data-config='([^']*)'/);

	const parsedAttrs = {
		family: familyMatch ? familyMatch[1] : "",
		operation: opMatch ? opMatch[1] : "",
		value_type: vtMatch ? vtMatch[1] : "",
		config: cfgMatch ? JSON.parse(unescapeAttr(cfgMatch[1])) : null,
	};

	// Reserialized from parsed node attrs
	const reserialized = {
		mode: "resolver",
		family: parsedAttrs.family,
		operation: parsedAttrs.operation,
		value_type: parsedAttrs.value_type,
		config: parsedAttrs.config,
	};

	assert.deepEqual(
		reserialized,
		original,
		"Resolver identity must be strictly preserved across roundtrip"
	);
});

test("Template mode deserialization unpacks into tokens and text", () => {
	const templatePayload = {
		mode: "template",
		segments: [
			{ type: "text", value: "Order " },
			{
				type: "value",
				value: {
					mode: "variable",
					path: { scope: "doc", segments: ["name"] },
				},
			},
			{ type: "text", value: " created" },
		],
	};

	const deserialized = deserializeFlexValue(templatePayload, "Data");
	assert.match(deserialized, /^Order /);
	assert.match(deserialized, /data-token-type="variable"/);
	assert.match(deserialized, /data-path="doc\.name"/);
	assert.match(deserialized, / created$/);
});
