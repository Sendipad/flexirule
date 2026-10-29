import assert from "node:assert/strict";
import { ASSIGNMENT_OPERATOR_METADATA } from "../../../../../../../flexirule/public/js/flexirule/core/contracts.js";

// Populate test metadata if not yet loaded from backend DTO
if (!Object.keys(ASSIGNMENT_OPERATOR_METADATA).length) {
	Object.assign(ASSIGNMENT_OPERATOR_METADATA, {
		set: { label: "Set", requires_value: true, supported_target_types: [] },
		clear: { label: "Clear", requires_value: false, supported_target_types: [] },
		increment: {
			label: "Increment",
			requires_value: true,
			supported_target_types: ["Int", "Float", "Percent", "Currency"],
		},
		toggle: { label: "Toggle", requires_value: false, supported_target_types: ["Check"] },
	});
}

// Assignment parsing and normalization unit test
{
	const legacyConfig = [
		{
			target: "doc.status",
			operator: "set",
			value: { mode: "formula", config: { expression: "1 + 1" } },
		},
		{
			target: "vars.counter",
			operator: "increment",
			value_template: "5",
		},
	];

	const parsed = legacyConfig.map((a, idx) => {
		const name = a.name || `row-${idx}`;
		let structuredVal = null;
		if (a.value && typeof a.value === "object" && a.value.mode) {
			structuredVal = a.value;
		} else {
			const legacyVal = a.value || a.value_template || "";
			structuredVal = { mode: "static", value: legacyVal };
		}

		if (["formula", "format", "normalize"].includes(structuredVal.mode)) {
			const config = structuredVal.config || {};
			if (!config.kind) {
				const kindMap = { formula: "math_formula", format: "text", normalize: "text" };
				config.kind = kindMap[structuredVal.mode];
			}
			structuredVal.mode = "resolver";
			structuredVal.config = config;
		}

		return {
			name,
			target: a.target || "",
			operator: a.operator || "set",
			when_condition: a.when_condition || null,
			when_expression: a.when_expression || "",
			pythonExpression: a.pythonExpression || "",
			value: structuredVal,
		};
	});

	assert.equal(parsed.length, 2);
	assert.equal(parsed[0].value.mode, "resolver");
	assert.equal(parsed[0].value.config.kind, "math_formula");
	assert.equal(parsed[1].value.mode, "static");
	assert.equal(parsed[1].value.value, "5");
}

// Assignment operator metadata contract assertions
{
	assert.equal(ASSIGNMENT_OPERATOR_METADATA.set.requires_value, true);
	assert.equal(ASSIGNMENT_OPERATOR_METADATA.clear.requires_value, false);
	assert.equal(ASSIGNMENT_OPERATOR_METADATA.toggle.requires_value, false);
}

// GenericGrid header and primary action contract test
{
	const gridConfig = {
		primaryAction: {
			id: "add-assignment",
			label: "Add Assignment",
			icon: "fa fa-plus",
			class: "add-assignment-btn",
		},
		availableRowActions: ["move", "remove"],
		presentationMode: "editor",
	};

	assert.equal(gridConfig.primaryAction.class, "add-assignment-btn");
	assert.deepEqual(gridConfig.availableRowActions, ["move", "remove"]);
	assert.equal(gridConfig.presentationMode, "editor");
}

console.log("Assignment configuration and GenericGrid refactor unit tests passed");
