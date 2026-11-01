import assert from "node:assert/strict";
import {
	deserializeQueryFilters,
	serializeQueryFilters,
	toPersistedQueryFilterTree,
} from "../../../../../../../flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/query_filter_serializer.mjs";

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
				{
					id: "c",
					type: "leaf",
					doctype: "Sales Order",
					field: "status",
					operator: "=",
					value: { mode: "static", value: "Closed" },
				},
			],
		},
	],
};
const payload = serializeQueryFilters(nested);
assert.deepEqual(payload, [
	["Sales Order", "status", "=", { mode: "static", value: "Open" }],
	"and",
	[
		["Sales Order", "docstatus", "=", { mode: "static", value: 1 }],
		"or",
		["Sales Order", "status", "=", { mode: "static", value: "Closed" }],
	],
]);
const reopened = deserializeQueryFilters(payload);
assert.equal(reopened.operator, "and");
assert.equal(reopened.children[1].type, "group");
assert.equal(reopened.children[1].operator, "or");
assert.equal(reopened.children[1].children.length, 2);
assert.deepEqual(serializeQueryFilters(reopened), payload);
// eslint-disable-next-line no-console
console.log("query filter serializer tests passed");

const canonical = deserializeQueryFilters({
	type: "group",
	operator: "and",
	children: [
		{
			type: "leaf",
			doctype: "Journal Entry",
			field: "is_system_generated",
			operator: "=",
			value: { mode: "static", value: "" },
		},
	],
});
assert.deepEqual(toPersistedQueryFilterTree(canonical), {
	type: "group",
	operator: "and",
	children: [
		{
			type: "leaf",
			doctype: "Journal Entry",
			field: "is_system_generated",
			operator: "=",
			value: { mode: "static", value: "" },
		},
	],
});
assert.deepEqual(serializeQueryFilters(canonical), [
	"Journal Entry",
	"is_system_generated",
	"=",
	{ mode: "static", value: "" },
]);
// eslint-disable-next-line no-console
console.log("canonical query filter persistence tests passed");

const staticListTree = {
	type: "group",
	operator: "and",
	children: [
		{
			type: "leaf",
			doctype: "Sales Order",
			field: "status",
			operator: "in",
			value: { mode: "static", value: ["Open", "Closed"] },
		},
	],
};
const staticListPayload = toPersistedQueryFilterTree(staticListTree);
assert.deepEqual(staticListPayload.children[0].value, {
	mode: "static",
	value: ["Open", "Closed"],
});
assert.deepEqual(
	toPersistedQueryFilterTree(deserializeQueryFilters(staticListPayload)),
	staticListPayload
);
// eslint-disable-next-line no-console
console.log("static list query filter persistence tests passed");
