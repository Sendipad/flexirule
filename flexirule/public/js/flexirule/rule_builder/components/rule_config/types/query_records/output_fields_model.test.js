import assert from "node:assert/strict";
import {
	buildResolvedOutputSchema,
	inferResultShape,
	parseOutputFields,
	resolveFieldInfo,
	RESULT_SHAPES,
	serializeOutputFields,
	validateOutputFields,
} from "./output_fields_model.js";
import { normalizeResolvedOutputSchema } from "../../../../../utils/output_schema.js";

assert.equal(inferResultShape(undefined), RESULT_SHAPES.documentNames);
assert.equal(inferResultShape("*"), RESULT_SHAPES.wholeDocuments);
assert.equal(
	inferResultShape(["name", { items: ["item_code", "qty"] }]),
	RESULT_SHAPES.embeddedChildren
);
assert.equal(
	inferResultShape(["name"], RESULT_SHAPES.selectedFields),
	RESULT_SHAPES.selectedFields
);

const source = [
	"name",
	"customer.customer_name as customer_name",
	{ items: ["item_code", "qty"] },
	{ COUNT: "name", as: "total_users" },
];
const rows = parseOutputFields(source);
assert.deepEqual(
	rows.map((row) => row.kind),
	["field", "field", "child", "function"]
);
assert.deepEqual(serializeOutputFields(rows), [
	"name",
	"customer.customer_name as customer_name",
	{ items: ["item_code", "qty"] },
	"count(name) as total_users",
]);

const expressionRows = parseOutputFields(["sum(grand_total) as total_value"]);
assert.equal(expressionRows[0].kind, "function");
assert.deepEqual(serializeOutputFields(expressionRows), ["sum(grand_total) as total_value"]);
assert.deepEqual(validateOutputFields(expressionRows, RESULT_SHAPES.selectedFields), []);

const mixedAggregateRows = parseOutputFields(["customer", "count(name) as total_users"]);
assert.ok(
	validateOutputFields(mixedAggregateRows, RESULT_SHAPES.selectedFields).some((error) =>
		error.includes("require Group By")
	)
);
assert.deepEqual(
	validateOutputFields(mixedAggregateRows, RESULT_SHAPES.selectedFields, "customer"),
	[]
);

const invalidChildShape = parseOutputFields(["name"]);
assert.ok(
	validateOutputFields(invalidChildShape, RESULT_SHAPES.embeddedChildren).some((error) =>
		error.includes("child-table selection")
	)
);

const invalidMultiLevelPath = parseOutputFields(["customer.address.country"]);
assert.ok(
	validateOutputFields(invalidMultiLevelPath, RESULT_SHAPES.selectedFields).some((error) =>
		error.includes("only one-level Link or child-table field paths")
	)
);

const invalidChildAggregate = parseOutputFields(["sum(items.qty) as total_qty"]);
assert.ok(
	validateOutputFields(invalidChildAggregate, RESULT_SHAPES.selectedFields).some((error) =>
		error.includes("child/link aggregates need backend support")
	)
);

const commaDelimitedFields = parseOutputFields("name, status as status_label");
assert.deepEqual(serializeOutputFields(commaDelimitedFields), ["name", "status as status_label"]);

const commaDelimitedAggregates = parseOutputFields(
	"count(name) as total_users, sum(grand_total) as total_value"
);
assert.deepEqual(
	commaDelimitedAggregates.map((row) => row.kind),
	["function", "function"]
);
assert.deepEqual(serializeOutputFields(commaDelimitedAggregates), [
	"count(name) as total_users",
	"sum(grand_total) as total_value",
]);

const nestedCommasStayInsideExpressions = parseOutputFields(
	"first_name, concat(first_name, last_name) as full_name"
);
assert.equal(nestedCommasStayInsideExpressions.length, 2);
assert.equal(nestedCommasStayInsideExpressions[1].kind, "raw");

const aggregateOnlyRows = parseOutputFields(["count(name) as total_users"]);
assert.deepEqual(validateOutputFields(aggregateOnlyRows, RESULT_SHAPES.selectedFields), []);

// Alias editing must preserve exactly what the user types; validation, not
// live normalization, decides whether the alias is snake_case.
const trailingUnderscoreAlias = parseOutputFields(["title as reference_"]);
assert.equal(trailingUnderscoreAlias[0].alias, "reference_");
assert.deepEqual(serializeOutputFields(trailingUnderscoreAlias), ["title as reference_"]);
assert.ok(
	validateOutputFields(trailingUnderscoreAlias, RESULT_SHAPES.selectedFields).some((error) =>
		error.includes("snake_case")
	)
);

const invalidSpacedAlias = parseOutputFields(["title as Reference Doctype"]);
assert.equal(invalidSpacedAlias[0].alias, "Reference Doctype");
assert.deepEqual(serializeOutputFields(invalidSpacedAlias), ["title as Reference Doctype"]);
assert.ok(
	validateOutputFields(invalidSpacedAlias, RESULT_SHAPES.selectedFields).some((error) =>
		error.includes("snake_case")
	)
);

const aliasedSchema = buildResolvedOutputSchema({
	shape: RESULT_SHAPES.selectedFields,
	fields: ["voucher_type as reference_doctype", "title", "count(name) as totals"],
	fieldInfoByPath: {
		voucher_type: { label: "Voucher Type", fieldtype: "Select", reqd: 1 },
		title: { label: "Title", fieldtype: "Data", reqd: 0 },
		name: { label: "ID (name)", fieldtype: "Data", reqd: 0 },
	},
});
assert.deepEqual(
	aliasedSchema.map(({ fieldname, label, fieldtype, reqd }) => ({
		fieldname,
		label,
		fieldtype,
		reqd,
	})),
	[
		{
			fieldname: "reference_doctype",
			label: "Reference Doctype",
			fieldtype: "Select",
			reqd: 1,
		},
		{ fieldname: "title", label: "Title", fieldtype: "Data", reqd: 0 },
		{ fieldname: "totals", label: "Totals", fieldtype: "Int", reqd: 0 },
	]
);
assert.deepEqual(aliasedSchema[0].source, {
	kind: "field",
	fieldname: "voucher_type",
	expression: "voucher_type as reference_doctype",
});
assert.deepEqual(aliasedSchema[2].source, {
	kind: "aggregate",
	function: "count",
	fieldname: "name",
	expression: "count(name) as totals",
});

const wholeDocumentSchema = buildResolvedOutputSchema({
	shape: RESULT_SHAPES.wholeDocuments,
	wholeDocumentFields: [
		{
			fieldname: "title",
			label: "Title",
			fieldtype: "Data",
			reqd: 1,
			source: { kind: "field", fieldname: "title", expression: "title" },
		},
		{ fieldname: "status", label: "Status", fieldtype: "Select", reqd: 0 },
	],
	systemFields: [
		{
			fieldname: "name",
			label: "ID (name)",
			fieldtype: "Data",
			reqd: 0,
			source: { kind: "system", fieldname: "name", expression: "name" },
		},
		{ fieldname: "owner", label: "Created By (owner)", fieldtype: "Link", options: "User" },
	],
});
assert.deepEqual(
	wholeDocumentSchema.map((field) => field.fieldname),
	["title", "status", "name", "owner"]
);
assert.equal(wholeDocumentSchema[0].reqd, 1);
assert.deepEqual(wholeDocumentSchema[0].source, {
	kind: "field",
	fieldname: "title",
	expression: "title",
});
assert.equal(wholeDocumentSchema[2].reqd, 0);
assert.deepEqual(wholeDocumentSchema[2].source, {
	kind: "system",
	fieldname: "name",
	expression: "name",
});
assert.deepEqual(wholeDocumentSchema[1].source, {
	kind: "field",
	fieldname: "status",
	expression: "status",
});
assert.deepEqual(wholeDocumentSchema[3].source, {
	kind: "system",
	fieldname: "owner",
	expression: "owner",
});
for (const field of [...aliasedSchema, ...wholeDocumentSchema]) {
	assert.equal(Number.isInteger(field.reqd), true);
	assert.equal(typeof field.source, "object");
	assert.equal(typeof field.source.kind, "string");
}
assert.deepEqual(
	normalizeResolvedOutputSchema([
		{ fieldname: "legacy_key", fieldtype: "Data", mandatory: 1, source: { kind: "field" } },
		{ fieldname: "optional_key", fieldtype: "Int", mandatory: 0 },
		{ fieldname: "canonical_key", fieldtype: "Data", reqd: 1 },
	]),
	[
		{ fieldname: "legacy_key", fieldtype: "Data", source: { kind: "field" }, reqd: 1 },
		{
			fieldname: "optional_key",
			fieldtype: "Int",
			reqd: 0,
			source: { kind: "unknown" },
		},
		{
			fieldname: "canonical_key",
			fieldtype: "Data",
			reqd: 1,
			source: { kind: "unknown" },
		},
	]
);
assert.deepEqual(
	normalizeResolvedOutputSchema(
		[
			{ fieldname: "edited_key", fieldtype: "Data" },
			{
				fieldname: "known_key",
				fieldtype: "Data",
				source: { kind: "field", fieldname: "title" },
			},
		],
		{ fallbackSourceKind: "manual" }
	),
	[
		{
			fieldname: "edited_key",
			fieldtype: "Data",
			reqd: 0,
			source: { kind: "manual" },
		},
		{
			fieldname: "known_key",
			fieldtype: "Data",
			source: { kind: "field", fieldname: "title" },
			reqd: 0,
		},
	]
);
assert.deepEqual(normalizeResolvedOutputSchema([{ fieldname: "empty_source", source: {} }]), [
	{ fieldname: "empty_source", reqd: 0, source: { kind: "unknown" } },
]);

assert.deepEqual(
	normalizeResolvedOutputSchema([
		{
			fieldname: "summary",
			fieldtype: "Table",
			children: [{ fieldname: "count", fieldtype: "Int" }],
		},
	]),
	[
		{
			fieldname: "summary",
			fieldtype: "Table",
			reqd: 0,
			source: { kind: "unknown" },
			children: [
				{
					fieldname: "count",
					fieldtype: "Int",
					reqd: 0,
					source: { kind: "unknown" },
				},
			],
		},
	]
);

const literalColumns = [
	{
		kind: "literal",
		fieldname: "document_type",
		label: "Document Type",
		fieldtype: "Data",
		reqd: 0,
		value_spec: { mode: "static", value: "Sales Invoice" },
	},
	"count(name) as issued_count",
];
assert.deepEqual(
	parseOutputFields(literalColumns).map((row) => row.kind),
	["literal", "function"]
);
assert.deepEqual(serializeOutputFields(parseOutputFields(literalColumns)), literalColumns);
assert.deepEqual(
	buildResolvedOutputSchema({
		shape: RESULT_SHAPES.selectedFields,
		fields: literalColumns,
	}),
	[
		{
			label: "Document Type",
			fieldname: "document_type",
			fieldtype: "Data",
			reqd: 0,
			source: {
				kind: "literal",
				fieldname: "document_type",
				value_spec: { mode: "static", value: "Sales Invoice" },
			},
		},
		{
			label: "Issued Count",
			fieldname: "issued_count",
			fieldtype: "Int",
			reqd: 0,
			source: {
				kind: "aggregate",
				function: "count",
				fieldname: "name",
				expression: "count(name) as issued_count",
			},
		},
	]
);
assert.equal(
	validateOutputFields(parseOutputFields(literalColumns), RESULT_SHAPES.selectedFields).length,
	0
);
assert.ok(
	validateOutputFields(
		parseOutputFields([
			{
				kind: "literal",
				fieldname: "document_type",
				label: "Document Type",
				value_spec: { mode: "static", value: "Sales Invoice" },
			},
		]),
		RESULT_SHAPES.selectedFields
	).some((error) => error.includes("source field or aggregate"))
);


const fieldMetadata = {
	Invoice: [
		{ fieldname: "customer", label: "Customer", fieldtype: "Link", options: "Customer" },
		{ fieldname: "items", label: "Items", fieldtype: "Table", options: "Invoice Item" },
	],
	Customer: [{ fieldname: "customer_name", label: "Customer Name", fieldtype: "Data" }],
	"Invoice Item": [{ fieldname: "item_code", label: "Item Code", fieldtype: "Link", options: "Item" }],
	Item: [{ fieldname: "item_name", label: "Item Name", fieldtype: "Data" }],
};
assert.equal(resolveFieldInfo(fieldMetadata, "Invoice", "customer").label, "Customer");
assert.equal(resolveFieldInfo(fieldMetadata, "Invoice", "customer.customer_name").label, "Customer Name");
assert.equal(resolveFieldInfo(fieldMetadata, "Invoice", "items.item_code").label, "Item Code");
assert.deepEqual(resolveFieldInfo({}, "Invoice", "customer"), {});
assert.deepEqual(resolveFieldInfo(fieldMetadata, "Invoice", ""), {});
assert.deepEqual(resolveFieldInfo(fieldMetadata, "Invoice", "missing_field"), {});

console.log("output fields model tests passed");
