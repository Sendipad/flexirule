import test from "node:test";
import assert from "node:assert/strict";
import {
	buildSourceCatalogue,
	searchSourceCatalogue,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/source_catalogue.mjs";

test("source_catalogue: builds unified catalogue and deduplicates overlapping doc fields", () => {
	const docFields = [
		{ fieldname: "customer_name", label: "Customer Name", fieldtype: "Data" },
		{ fieldname: "grand_total", label: "Grand Total", fieldtype: "Currency" },
	];
	const variableOptions = [
		{ value: "doc.customer_name", label: "doc.customer_name (Customer Name)" }, // Duplicate of docFields!
		{ value: "vars.discount_rate", label: "Discount Rate" },
		{ value: "old_doc.status", label: "Previous Status" },
		{ value: "row.qty", label: "Child Row Qty" },
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

	// Overlapping doc.customer_name is deduplicated:
	// 2 fields (customer_name, grand_total)
	// + 3 unique variables (vars.discount_rate, old_doc.status, row.qty)
	// + 2 resolvers = 7 items
	assert.equal(catalogue.length, 7);

	const customerItems = catalogue.filter((item) => item.canonicalPath === "doc.customer_name");
	assert.equal(customerItems.length, 1);

	// Qualified scopes are strictly preserved
	const oldDocItem = catalogue.find((i) => i.canonicalPath === "old_doc.status");
	assert.ok(oldDocItem);
	assert.equal(oldDocItem.scope, "old_doc");
	assert.deepEqual(oldDocItem.payload.path, { scope: "old_doc", segments: ["status"] });

	const rowItem = catalogue.find((i) => i.canonicalPath === "row.qty");
	assert.ok(rowItem);
	assert.equal(rowItem.scope, "row");
	assert.deepEqual(rowItem.payload.path, { scope: "row", segments: ["qty"] });
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

test("source_catalogue: prioritizes fields and contextual row/item/loop variables when isLeftOperand is true", () => {
	const catalogue = [
		{
			id: "math.formula",
			primaryLabel: "Formula",
			sourceType: "resolver",
			category: "resolvers",
			searchTerms: ["formula"],
		},
		{
			id: "doc.status",
			primaryLabel: "Status",
			sourceType: "field",
			category: "fields",
			searchTerms: ["status"],
		},
		{
			id: "row.amount",
			primaryLabel: "Row Amount",
			sourceType: "variable",
			scope: "row",
			category: "variables",
			searchTerms: ["row amount"],
		},
		{
			id: "vars.counter",
			primaryLabel: "Counter",
			sourceType: "variable",
			scope: "vars",
			category: "variables",
			searchTerms: ["counter"],
		},
	];

	const sortedLeft = searchSourceCatalogue(catalogue, "", { isLeftOperand: true });
	assert.strictEqual(sortedLeft[0].id, "row.amount");
	assert.strictEqual(sortedLeft[1].id, "doc.status");
	assert.strictEqual(sortedLeft[2].id, "vars.counter");
	assert.strictEqual(sortedLeft[3].id, "math.formula");
});
