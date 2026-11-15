import test from "node:test";
import assert from "node:assert/strict";
import {
	buildSourceCatalogue,
	searchSourceCatalogue,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/source_catalogue.mjs";
import { resolveStaticPresentation } from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/static_presentation_policy.mjs";

test("flexvalue_refactor: empty searchable button catalogue retrieval", () => {
	const docFields = [
		{
			fieldname: "status",
			label: "Status",
			fieldtype: "Select",
			options: ["Draft", "Submitted"],
		},
		{
			fieldname: "customer",
			label: "Customer",
			fieldtype: "Link",
			options: "Customer",
		},
	];
	const variableOptions = [{ value: "vars.computed_total", label: "Computed Total" }];
	const resolvers = [
		{
			kind: "date_time",
			label: "Date & Time",
			family: "date_time",
			operation: "calculate",
		},
		{ kind: "lookup", label: "Lookup", family: "lookup", operation: "fetch" },
	];

	const catalogue = buildSourceCatalogue({
		docFields,
		variableOptions,
		resolvers,
	});

	// Check fields
	assert.ok(catalogue.some((i) => i.id === "doc.status" && i.category === "fields"));
	assert.ok(catalogue.some((i) => i.id === "doc.customer" && i.category === "fields"));

	// Check variables
	assert.ok(catalogue.some((i) => i.id === "vars.computed_total" && i.category === "variables"));

	// Check resolvers
	assert.ok(catalogue.some((i) => i.id === "date_time" && i.category === "resolvers"));
	assert.ok(catalogue.some((i) => i.id === "lookup" && i.category === "resolvers"));

	// Search
	const foundCustomer = searchSourceCatalogue(catalogue, "cust");
	assert.equal(foundCustomer[0].canonicalPath, "doc.customer");

	const foundLookup = searchSourceCatalogue(catalogue, "lookup");
	assert.equal(foundLookup[0].kind, "lookup");
});

test("flexvalue_refactor: static presentation configuration handles link and multiselect correctly", () => {
	// Link override
	const linkConfig = resolveStaticPresentation({
		staticPresentation: {
			control: "link",
			doctype: "Item",
			filters: { is_stock_item: 1 },
		},
		fieldType: "Data",
	});
	assert.equal(linkConfig.control, "link");
	assert.equal(linkConfig.doctype, "Item");
	assert.deepEqual(linkConfig.filters, { is_stock_item: 1 });

	// Multi-select override
	const multiConfig = resolveStaticPresentation({
		staticPresentation: {
			control: "multi-select",
			options: ["Option 1", "Option 2"],
		},
		fieldType: "Select",
	});
	assert.equal(multiConfig.control, "multi-select");
	assert.deepEqual(multiConfig.options, ["Option 1", "Option 2"]);
	assert.equal(multiConfig.isMultiSelect, true);
});
