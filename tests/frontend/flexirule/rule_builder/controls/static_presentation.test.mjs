import test from "node:test";
import assert from "node:assert/strict";
import {
	isRemoteRecordFieldType,
	resolveDynamicLinkDoctype,
	resolveStaticPresentation,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/static_presentation_policy.mjs";

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
		const res = resolveStaticPresentation({
			fieldType: ft,
			// CanonicalConditionLeaf passes the current parent DocType for field resolution.
			// That context must not make a non-Link field render as LinkControl.
			referenceDoctype: "Sales Invoice",
			context: { operator: "eq" },
		});
		assert.equal(res.control, "input", ft + " must retain its native control");
		assert.equal(res.isLink, false, ft + " must not be inferred as a Link");
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
	assert.deepEqual(presentation.options, [
		[1, "Yes"],
		[0, "No"],
	]);
});

test("static_presentation: Select keeps its options control when options are a newline-separated string", () => {
	const options = "Draft\nSubmitted\nCancelled";
	const presentation = resolveStaticPresentation({
		fieldType: "Select",
		fieldOptions: options,
		referenceDoctype: options,
		context: { operator: "eq" },
	});
	assert.equal(presentation.control, "select");
	assert.equal(presentation.isLink, false);
	assert.equal(presentation.options, options);
});

test("static_presentation: Select membership stays multi-select despite a truthy options string", () => {
	const options = "Draft\nSubmitted";
	const presentation = resolveStaticPresentation({
		fieldType: "Select",
		fieldOptions: options,
		referenceDoctype: options,
		context: { operator: "in" },
	});
	assert.equal(presentation.control, "multi-select");
	assert.equal(presentation.isLink, false);
});


test("static_presentation: remote record fieldtypes are distinct from local MultiSelect choices", () => {
	assert.equal(isRemoteRecordFieldType("Link"), true);
	assert.equal(isRemoteRecordFieldType("Dynamic Link"), true);
	assert.equal(isRemoteRecordFieldType("MultiSelectList"), true);
	assert.equal(isRemoteRecordFieldType("MultiSelect"), false);
	assert.equal(isRemoteRecordFieldType("Select"), false);

	const localMultiSelect = resolveStaticPresentation({
		fieldType: "MultiSelect",
		fieldOptions: "Red\nGreen\nBlue",
		context: { operator: "eq" },
	});
	assert.equal(localMultiSelect.control, "multi-select");
	assert.equal(localMultiSelect.isLink, false);
});

test("static_presentation: Dynamic Link resolves its target from the controlling field value", () => {
	assert.equal(
		resolveDynamicLinkDoctype({
			options: "party_type",
			context: { doc: { party_type: "Customer" } },
		}),
		"Customer"
	);
	assert.equal(
		resolveDynamicLinkDoctype({
			options: "party_type",
			context: {
				controlContext: {
					getFieldValue: () => ({ mode: "static", value: "Supplier" }),
				},
			},
		}),
		"Supplier"
	);
	assert.equal(
		resolveDynamicLinkDoctype({
			options: "party_type",
			context: {},
		}),
		"",
		"an unresolved controlling field must not be mistaken for a DocType"
	);
});
