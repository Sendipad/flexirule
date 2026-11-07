import test from "node:test";
import assert from "node:assert/strict";
import { resolveStaticPresentation } from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/static_presentation_policy.mjs";

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
	const res = resolveStaticPresentation({
		fieldType: "Data",
		context: { operator: "in" },
	});
	assert.equal(res.control, "multi-select");
	assert.equal(res.isMultiSelect, true);
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
