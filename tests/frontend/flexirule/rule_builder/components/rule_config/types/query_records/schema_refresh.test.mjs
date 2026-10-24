import assert from "node:assert/strict";
import { getQueryRecordsSchemaRefreshSignature } from "../../../../../../../../flexirule/public/js/flexirule/rule_builder/components/rule_config/types/query_records/schema_refresh.mjs";

const fetchBase = {
	mode: "Fetch Records",
	referenceDoctype: "Sales Invoice",
	referenceDocname: null,
	config: {
		fields: ["name", "customer"],
		result_shape: "selected_fields",
		group_by: null,
		filters: [{ field: "status", operator: "=", value: "Paid" }],
		order_by: "modified desc",
		limit: 20,
	},
};
const fetchSignature = getQueryRecordsSchemaRefreshSignature(fetchBase);

// Row selection options do not alter the exposed output contract.
assert.equal(
	getQueryRecordsSchemaRefreshSignature({
		...fetchBase,
		config: {
			...fetchBase.config,
			filters: [{ field: "status", operator: "=", value: "Draft" }],
			order_by: "name asc",
			limit: 100,
		},
	}),
	fetchSignature
);

// Fetch strategy and a document-name reference do not define Fetch Records schema.
assert.equal(
	getQueryRecordsSchemaRefreshSignature({
		...fetchBase,
		config: { ...fetchBase.config, fetch_strategy: "Get latest Doc" },
	}),
	fetchSignature
);
assert.equal(
	getQueryRecordsSchemaRefreshSignature({
		...fetchBase,
		referenceDocname: "different-document",
	}),
	fetchSignature
);

// Output-defining Fetch Records inputs invalidate the signature.
for (const config of [
	{ ...fetchBase.config, fields: ["name", "customer", "grand_total"] },
	{ ...fetchBase.config, result_shape: "whole_documents" },
	{ ...fetchBase.config, group_by: "customer" },
]) {
	assert.notEqual(
		getQueryRecordsSchemaRefreshSignature({ ...fetchBase, config }),
		fetchSignature
	);
}
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({ ...fetchBase, referenceDoctype: "Customer" }),
	fetchSignature
);
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({ ...fetchBase, mode: "Query List" }),
	fetchSignature
);
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({
		...fetchBase,
		config: { ...fetchBase.config, fields: ["sum(grand_total) as total_amount"] },
	}),
	fetchSignature
);
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({
		...fetchBase,
		config: { ...fetchBase.config, fields: ["sum(grand_total) as invoice_total"] },
	}),
	getQueryRecordsSchemaRefreshSignature({
		...fetchBase,
		config: { ...fetchBase.config, fields: ["sum(grand_total) as total_amount"] },
	})
);

// Query Doc's schema depends on DocType/fetch strategy, not the selected document name.
const queryDocBase = {
	...fetchBase,
	mode: "Query Doc",
	referenceDocname: "INV-001",
	config: { doctype_name: "Sales Invoice", fetch_strategy: "Get doc", fields: ["name"] },
};
const queryDocSignature = getQueryRecordsSchemaRefreshSignature(queryDocBase);
assert.equal(
	getQueryRecordsSchemaRefreshSignature({ ...queryDocBase, referenceDocname: "INV-002" }),
	queryDocSignature
);
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({
		...queryDocBase,
		config: { ...queryDocBase.config, fetch_strategy: "Get latest Doc" },
	}),
	queryDocSignature
);

// Query Report's selected report determines its output columns.
const reportBase = {
	mode: "Query Report",
	referenceDoctype: "Report",
	referenceDocname: "Accounts Receivable",
	config: { report_name: "Accounts Receivable" },
};
const reportSignature = getQueryRecordsSchemaRefreshSignature(reportBase);
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({
		...reportBase,
		referenceDocname: "General Ledger",
		config: { report_name: "General Ledger" },
	}),
	reportSignature
);

// Group By's aggregate function affects the result contract.
const groupByBase = {
	mode: "Group By",
	referenceDoctype: "Sales Invoice",
	config: { group_by_field: "customer", agg_field: "grand_total", agg_function: "sum" },
};
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({
		...groupByBase,
		config: { ...groupByBase.config, agg_function: "avg" },
	}),
	getQueryRecordsSchemaRefreshSignature(groupByBase)
);

console.log("query records schema refresh tests passed");
