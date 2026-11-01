import assert from "node:assert/strict";
import {
	buildResolvedOutputSchema,
	RESULT_SHAPES,
	serializeOutputFields,
} from "../../../../../../../../flexirule/public/js/flexirule/rule_builder/components/rule_config/types/query_records/output_fields_model.mjs";

const fieldInfoByPath = {
	customer: {
		fieldname: "customer",
		label: "Customer",
		fieldtype: "Link",
		options: "Customer",
	},
	grand_total: {
		fieldname: "grand_total",
		label: "Grand Total",
		fieldtype: "Currency",
	},
};

const incompleteFunctionFields = serializeOutputFields([
	{ kind: "function", functionName: "sum", field: "grand_total", alias: "" },
]);
assert.deepEqual(
	buildResolvedOutputSchema({
		shape: RESULT_SHAPES.selectedFields,
		fields: incompleteFunctionFields,
		fieldInfoByPath,
	}),
	[],
	"An incomplete function should not add a result field before it has a valid alias."
);

const configuredFields = serializeOutputFields([
	{ kind: "field", field: "customer", alias: "customer_name" },
	{ kind: "function", functionName: "sum", field: "grand_total", alias: "total_amount" },
]);
const schema = buildResolvedOutputSchema({
	shape: RESULT_SHAPES.selectedFields,
	fields: configuredFields,
	fieldInfoByPath,
});

assert.deepEqual(
	schema.map((field) => field.fieldname),
	["customer_name", "total_amount"]
);
assert.equal(schema[0].fieldtype, "Link");
assert.equal(schema[0].options, "Customer");
assert.equal(schema[1].fieldtype, "Currency");
assert.equal(schema[1].source.kind, "aggregate");
assert.equal(schema[1].source.expression, "sum(grand_total) as total_amount");

// eslint-disable-next-line no-console
console.log("query records output schema function tests passed");
