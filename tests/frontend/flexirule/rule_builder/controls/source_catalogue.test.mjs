import test from "node:test";
import assert from "node:assert/strict";
import {
	buildSourceCatalogue,
	searchSourceCatalogue,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/source_catalogue.mjs";

test("source_catalogue: builds unified catalogue from fields, variables, and resolvers", () => {
	const docFields = [
		{ fieldname: "customer_name", label: "Customer Name", fieldtype: "Data" },
		{ fieldname: "grand_total", label: "Grand Total", fieldtype: "Currency" },
	];
	const variableOptions = [
		{ value: "vars.discount_rate", label: "Discount Rate" },
		{ value: "doc.posting_date", label: "doc.posting_date (Posting Date)" },
	];
	const resolvers = [
		{
			kind: "date_time",
			label: "Date & Time",
			family: "date_time",
			operation: "calculate",
			description: "Calculate dates",
		},
		{
			kind: "math_formula",
			label: "Math Formula",
			family: "math",
			operation: "formula",
			description: "Perform math calculation",
		},
	];

	const catalogue = buildSourceCatalogue({
		docFields,
		variableOptions,
		resolvers,
		allowedResolverKinds: ["date_time", "math_formula"],
	});

	// 2 fields + 2 variables + 2 resolvers = 6 items
	assert.equal(catalogue.length, 6);
	const customerItem = catalogue.find((item) => item.fieldname === "customer_name");
	assert.ok(customerItem);
	assert.equal(customerItem.primaryLabel, "Customer Name");
	assert.equal(customerItem.canonicalPath, "doc.customer_name");
});

test("source_catalogue: searches by translated label, fieldname, and canonical path", () => {
	const translations = {
		"Customer Name": "Nom du Client",
		"Date & Time": "Date et Heure",
	};
	const translate = (s) => translations[s] || s;

	const docFields = [{ fieldname: "customer_name", label: "Customer Name", fieldtype: "Data" }];
	const resolvers = [
		{
			kind: "date_time",
			label: "Date & Time",
			family: "date_time",
			operation: "calculate",
		},
	];

	const catalogue = buildSourceCatalogue({ docFields, resolvers, translate });

	// Search by translated label
	const resultsFrench = searchSourceCatalogue(catalogue, "Nom du");
	assert.equal(resultsFrench.length, 1);
	assert.equal(resultsFrench[0].primaryLabel, "Nom du Client");

	// Search by canonical path
	const resultsPath = searchSourceCatalogue(catalogue, "doc.customer");
	assert.equal(resultsPath.length, 1);
	assert.equal(resultsPath[0].primaryLabel, "Nom du Client");

	// Search by resolver translated name
	const resultsResolver = searchSourceCatalogue(catalogue, "Heure");
	assert.equal(resultsResolver.length, 1);
	assert.equal(resultsResolver[0].primaryLabel, "Date et Heure");
});

test("source_catalogue: prioritizes compatible resolvers and exact/prefix matches", () => {
	const resolvers = [
		{
			kind: "date_time",
			label: "Date & Time",
			family: "date_time",
			operation: "calculate",
		},
		{
			kind: "math_formula",
			label: "Math Formula",
			family: "math",
			operation: "formula",
		},
	];

	const catalogue = buildSourceCatalogue({
		resolvers,
		allowedResolverKinds: ["math_formula"], // date_time is not allowed in this context
	});

	const mathItem = catalogue.find((i) => i.kind === "math_formula");
	const dateItem = catalogue.find((i) => i.kind === "date_time");

	assert.equal(mathItem.isCompatible, true);
	assert.equal(dateItem.isCompatible, false);

	const searchAll = searchSourceCatalogue(catalogue, "");
	assert.equal(searchAll[0].kind, "math_formula");
	assert.equal(searchAll[1].kind, "date_time");
});
