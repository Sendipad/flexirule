import assert from "node:assert/strict";
import { isFilterLeafValid, validateFilterLeaf } from "./query_filter_validation.mjs";
import {
	formatSingleValue,
	formatFilterSummary,
	resolveFilterFieldDef,
} from "./filter_summary_formatter.mjs";

// Global mock for translation __
if (typeof globalThis.__ !== "function") {
	globalThis.__ = (str, args) => {
		if (!args || !args.length) return str;
		return str.replace(/\{(\d+)\}/g, (_, index) => args[index] ?? "");
	};
}

// Validity checks using imported production validator
assert.equal(
	isFilterLeafValid({ field: "", operator: "=", value: { mode: "static", value: "" } }),
	false
);
assert.equal(
	isFilterLeafValid({ field: "status", operator: "=", value: { mode: "static", value: "" } }),
	false
);
assert.equal(
	isFilterLeafValid({ field: "status", operator: "=", value: { mode: "static", value: "Open" } }),
	true
);
assert.equal(
	isFilterLeafValid({ field: "status", operator: "is", value: { mode: "static", value: "set" } }),
	true
);
assert.equal(
	isFilterLeafValid({
		field: "amount",
		operator: "Between",
		value: [
			{ mode: "static", value: 10 },
			{ mode: "static", value: 50 },
		],
	}),
	true
);
assert.equal(
	isFilterLeafValid({
		field: "amount",
		operator: "Between",
		value: [{ mode: "static", value: 10 }],
	}),
	false
);
assert.equal(
	isFilterLeafValid({
		field: "customer",
		operator: "=",
		value: { mode: "variable", value: "doc.customer" },
	}),
	true
);

// Operator compatibility check
assert.equal(
	isFilterLeafValid(
		{
			field: "creation",
			operator: "invalid_op",
			value: { mode: "static", value: "2026-01-01" },
		},
		{ fieldDef: { fieldtype: "Datetime" } }
	),
	false
);

// Detailed validation result test
assert.equal(validateFilterLeaf({ field: "", operator: "=" }).valid, false);
assert.equal(
	validateFilterLeaf({ field: "status", operator: "=", value: { mode: "static", value: "Open" } })
		.valid,
	true
);

// Nested-set operators in headless validation
const nestedSetContext = {
	doctype: "Item Group",
	metaMap: {
		"Item Group": [
			{ fieldname: "parent_item_group", fieldtype: "Link", options: "Item Group" },
		],
	},
	nestedSetOptions: { nestedSetDoctypes: ["Item Group"], rootDoctype: "Item Group" },
};
assert.equal(
	isFilterLeafValid(
		{
			field: "parent_item_group",
			operator: "descendants of",
			value: { mode: "static", value: "All Item Groups" },
		},
		nestedSetContext
	),
	true
);
assert.equal(
	validateFilterLeaf(
		{
			field: "parent_item_group",
			operator: "descendants of",
			value: { mode: "static", value: "All Item Groups" },
		},
		nestedSetContext
	).valid,
	true
);

// Unresolved field validation test
const unresolvedResult = validateFilterLeaf(
	{ field: "nonexistent_field", operator: "=", value: { mode: "static", value: "test" } },
	{ doctype: "Sales Order", metaMap: { "Sales Order": [] } }
);
assert.equal(unresolvedResult.valid, false);
assert.equal(
	unresolvedResult.errors.includes(
		"The selected filter field is unavailable. Choose a valid field for this DocType."
	),
	true
);

// Unsupported operator test
const unsupportedResult = validateFilterLeaf(
	{ field: "creation", operator: "invalid_op", value: { mode: "static", value: "2026-01-01" } },
	{ fieldDef: { fieldtype: "Datetime", isResolved: true } }
);
assert.equal(unsupportedResult.valid, false);
assert.equal(
	unsupportedResult.errors.includes("Choose a supported operator for the selected field."),
	true
);

// Production value formatting tests using formatSingleValue
assert.equal(formatSingleValue({ mode: "static", value: "Open" }), "Open");
assert.equal(
	formatSingleValue({ mode: "variable", value: "doc.customer" }),
	"Variable (doc.customer)"
);
assert.equal(
	formatSingleValue([
		{ mode: "static", value: "A" },
		{ mode: "static", value: "B" },
	]),
	"A, B"
);

// Production formatFilterSummary component-helper tests
const summaryOpen = formatFilterSummary(
	{ field: "status", operator: "=", value: { mode: "static", value: "Open" } },
	"Sales Order"
);
assert.equal(summaryOpen.isValid, true);
assert.equal(summaryOpen.fieldLabel, "Status");
assert.equal(summaryOpen.operatorLabel, "equals");
assert.equal(summaryOpen.valueLabel, "Open");

const summaryInvalid = formatFilterSummary({ field: "", operator: "=" }, "Sales Order");
assert.equal(summaryInvalid.isValid, false);

// Nested field path definition test
const mockMetaMap = {
	"Sales Order": [
		{ fieldname: "customer", fieldtype: "Link", options: "Customer", label: "Customer" },
	],
	Customer: [
		{
			fieldname: "customer_group",
			fieldtype: "Link",
			options: "Customer Group",
			label: "Customer Group",
		},
	],
};

const nestedDef = resolveFilterFieldDef("customer.customer_group", "Sales Order", mockMetaMap);
assert.equal(nestedDef.fieldtype, "Link");
assert.equal(nestedDef.label, "Customer · Customer Group");

console.log("filter leaf summary unit tests passed");
