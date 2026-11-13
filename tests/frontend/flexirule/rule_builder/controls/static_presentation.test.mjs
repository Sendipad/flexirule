import test from "node:test";
import assert from "node:assert/strict";
import {
	isRemoteRecordFieldType,
	resolveStaticPresentation,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/static_presentation_policy.mjs";
import { ControlRegistry } from "../../../../../flexirule/public/js/flexirule/core/control_registry.js";

test("static_presentation: defaults according to field metadata", () => {
	const resData = resolveStaticPresentation({ fieldType: "Data" });
	assert.equal(resData.control, "input");

	const resSelect = resolveStaticPresentation({
		fieldType: "Select",
		fieldOptions: ["Open", "Closed"],
	});
	assert.equal(resSelect.control, "select");
	assert.deepEqual(resSelect.options, ["Open", "Closed"]);

	const resLink = resolveStaticPresentation({
		fieldType: "Link",
		referenceDoctype: "Customer",
	});
	assert.equal(resLink.control, "link");
	assert.equal(resLink.doctype, "Customer");
});

test("static_presentation: native fieldtypes preserve input control without destroying fieldtype", () => {
	const nativeTypes = [
		"Int",
		"Float",
		"Currency",
		"Percent",
		"Check",
		"Date",
		"Datetime",
		"Time",
	];
	for (const ft of nativeTypes) {
		const res = resolveStaticPresentation({ fieldType: ft });
		assert.equal(res.control, "input");
	}
});

test("static_presentation: operator-specific requirement overrides default fieldtype", () => {
	// For all membership comparisons (in, not_in), a list-capable input (multi-select) is provided
	const resSelect = resolveStaticPresentation({
		fieldType: "Select",
		fieldOptions: ["Draft", "Submitted"],
		context: { operator: "in" },
	});
	assert.equal(resSelect.control, "multi-select");
	assert.equal(resSelect.isMultiSelect, true);

	const resInt = resolveStaticPresentation({
		fieldType: "Int",
		context: { operator: "in" },
	});
	assert.equal(resInt.control, "multi-select");
	assert.equal(resInt.isMultiSelect, true);
});

test("static_presentation: auto configuration preserves supplied options and doctype", () => {
	const resAutoOpts = resolveStaticPresentation({
		fieldType: "Data",
		staticPresentation: { control: "auto", options: ["A", "B"] },
	});
	assert.equal(resAutoOpts.control, "select");
	assert.deepEqual(resAutoOpts.options, ["A", "B"]);

	const resAutoDoc = resolveStaticPresentation({
		fieldType: "Data",
		staticPresentation: { control: "auto", doctype: "Customer", filters: { is_active: 1 } },
	});
	assert.equal(resAutoDoc.control, "link");
	assert.equal(resAutoDoc.doctype, "Customer");
	assert.deepEqual(resAutoDoc.filters, { is_active: 1 });
});

test("static_presentation: explicit consumer override takes highest precedence", () => {
	const resExplicit = resolveStaticPresentation({
		fieldType: "Data",
		context: { operator: "eq" },
		staticPresentation: {
			control: "select",
			options: ["High", "Medium", "Low"],
		},
	});
	assert.equal(resExplicit.control, "select");
	assert.deepEqual(resExplicit.options, ["High", "Medium", "Low"]);

	// Explicit override via context
	const resContext = resolveStaticPresentation({
		fieldType: "Data",
		context: {
			operator: "eq",
			staticPresentation: {
				control: "link",
				doctype: "Supplier",
				filters: { status: "Active" },
			},
		},
	});
	assert.equal(resContext.control, "link");
	assert.equal(resContext.doctype, "Supplier");
	assert.deepEqual(resContext.filters, { status: "Active" });
});


test("static_presentation: Link equality resolves to LinkControl, not a Select using the DocType name", () => {
	const presentation = resolveStaticPresentation({
		fieldType: "Link",
		fieldOptions: "Customer",
		referenceDoctype: "Customer",
		context: { operator: "eq" },
	});
	assert.equal(presentation.control, "link");
	assert.equal(presentation.doctype, "Customer");
});

test("static_presentation: Link membership operators preserve the target DocType for remote multi-select", () => {
	for (const operator of ["in", "not_in"]) {
		const presentation = resolveStaticPresentation({
			fieldType: "Link",
			fieldOptions: "Customer",
			referenceDoctype: "Customer",
			context: { operator },
		});
		assert.equal(presentation.control, "multi-select");
		assert.equal(presentation.doctype, "Customer");
		assert.equal(presentation.isMultiSelect, true);
	}
});

test("static_presentation: Check uses its native control for equality", () => {
	const presentation = resolveStaticPresentation({
		fieldType: "Check",
		context: { operator: "eq" },
	});
	assert.equal(presentation.control, "input");
	assert.equal(presentation.isMultiSelect, false);
});


test("static_presentation: Check membership can choose multiple boolean values", () => {
	const presentation = resolveStaticPresentation({
		fieldType: "Check",
		fieldOptions: [
			[1, "Yes"],
			[0, "No"],
		],
		context: { operator: "in" },
	});
	assert.equal(presentation.control, "multi-select");
	assert.equal(presentation.isMultiSelect, true);
	assert.deepEqual(presentation.options, [[1, "Yes"], [0, "No"]]);
});


test("static_presentation: Dynamic Link retains its resolved target DocType for equality and membership", () => {
	const equality = resolveStaticPresentation({
		fieldType: "Dynamic Link",
		referenceDoctype: "Customer",
		context: { operator: "eq" },
	});
	assert.equal(equality.control, "link");
	assert.equal(equality.doctype, "Customer");

	const membership = resolveStaticPresentation({
		fieldType: "Dynamic Link",
		referenceDoctype: "Customer",
		context: { operator: "in" },
	});
	assert.equal(membership.control, "multi-select");
	assert.equal(membership.doctype, "Customer");
});


test("static_presentation: Check equality is routed to the native CheckControl", () => {
	const checked = ControlRegistry.resolve({ fieldtype: "Check" }, { modelValue: 1 });
	const unchecked = ControlRegistry.resolve({ fieldtype: "Check" }, { modelValue: 0 });

	assert.equal(checked.component, "CheckControl");
	assert.equal(checked.props.modelValue, true);
	assert.equal(unchecked.component, "CheckControl");
	assert.equal(unchecked.props.modelValue, false);
});


test("static_presentation: remote record fields are distinct from local MultiSelect", () => {
	assert.equal(isRemoteRecordFieldType("Link"), true);
	assert.equal(isRemoteRecordFieldType("Dynamic Link"), true);
	assert.equal(isRemoteRecordFieldType("MultiSelectList"), true);
	assert.equal(isRemoteRecordFieldType("MultiSelect"), false);
	assert.equal(isRemoteRecordFieldType("Select"), false);

	const local = resolveStaticPresentation({
		fieldType: "MultiSelect",
		fieldOptions: "Red\\nGreen\\nBlue",
		context: { operator: "in" },
	});
	assert.equal(local.control, "multi-select");
	assert.equal(local.isMultiSelect, true);
});
