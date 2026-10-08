import assert from "node:assert/strict";
import { deserializeQueryFilters, serializeQueryFilters } from "./query_filter_serializer.js";

const tree = deserializeQueryFilters([
	["Sales Order", "status", "=", { mode: "static", value: "Open" }],
	"or",
	["Sales Order", "docstatus", "=", { mode: "static", value: 1 }],
]);
assert.equal(tree.type, "group");
assert.equal(tree.children.length, 2);
assert.equal(tree.children[0].type, "leaf");
assert.equal(tree.children[1].type, "leaf");
assert.equal(tree.operator, "or");

const nested = {
	id: "root",
	type: "group",
	operator: "and",
	children: [
		{
			id: "a",
			type: "leaf",
			doctype: "Sales Order",
			field: "status",
			operator: "=",
			value: { mode: "static", value: "Open" },
		},
		{
			id: "g",
			type: "group",
			operator: "or",
			children: [
				{
					id: "b",
					type: "leaf",
					doctype: "Sales Order",
					field: "docstatus",
					operator: "=",
					value: { mode: "static", value: 1 },
				},
			],
		},
	],
};
const payload = serializeQueryFilters(nested);
assert.deepEqual(payload, [
	["Sales Order", "status", "=", { mode: "static", value: "Open" }],
	"and",
	["Sales Order", "docstatus", "=", { mode: "static", value: 1 }],
]);
console.log("query filter serializer tests passed");
