import assert from "node:assert/strict";
import {
	BASE_FILTER_OPERATORS,
	NESTED_SET_OPERATORS,
	getFilterOperators,
	supportsNestedSetOperators,
} from "../../../../../../../flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/filter_operators.mjs";

const checkOperators = getFilterOperators({ fieldtype: "Check" });
assert.deepEqual(checkOperators, ["=", "!="], "Check fields must expose Equals and Not Equals");

const adaptedCheckOperators = getFilterOperators({
	fieldtype: "Data",
	original_type: "Check",
});
assert.deepEqual(
	adaptedCheckOperators,
	["=", "!="],
	"Check fields must retain equality and inequality when their input control is adapted"
);

const treeLink = { fieldname: "parent_warehouse", fieldtype: "Link", options: "Warehouse" };
assert.equal(
	supportsNestedSetOperators(treeLink, { nestedSetDoctypes: ["Warehouse"] }),
	true,
	"Link fields pointing to a nested-set DocType must support hierarchy operators"
);
const treeOperators = getFilterOperators(treeLink, {
	nestedSetDoctypes: ["Warehouse"],
});
for (const operator of NESTED_SET_OPERATORS) {
	assert.ok(treeOperators.includes(operator), `Tree Link should include ${operator}`);
}

assert.equal(
	supportsNestedSetOperators(
		{ fieldname: "parent", fieldtype: "Link", options: "Customer" },
		{ nestedSetDoctypes: ["Warehouse"] }
	),
	false,
	"Ordinary Link fields must not expose hierarchy operators"
);

assert.equal(
	supportsNestedSetOperators(
		{ fieldname: "name", fieldtype: "Data" },
		{ nestedSetDoctypes: ["Warehouse"], rootDoctype: "Warehouse" }
	),
	true,
	"The name field of a Tree DocType should support hierarchy operators"
);

const intOperators = getFilterOperators({ fieldtype: "Int" });
for (const unsupported of ["like", "not like", "in", "not in", "Between", "Timespan"]) {
	assert.ok(!intOperators.includes(unsupported), `Int should not include ${unsupported}`);
}
for (const required of ["=", "!=", ">", "<", ">=", "<="]) {
	assert.ok(intOperators.includes(required), `Int should include ${required}`);
}

assert.ok(BASE_FILTER_OPERATORS.includes("="));
console.log("query filter operator tests passed");
