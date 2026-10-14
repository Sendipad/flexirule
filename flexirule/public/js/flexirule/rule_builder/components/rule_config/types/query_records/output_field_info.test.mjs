import assert from "node:assert/strict";
import { resolveFieldInfo } from "./output_field_info.mjs";

const fieldMetadata = {
	Invoice: [
		{ fieldname: "customer", label: "Customer", fieldtype: "Link", options: "Customer" },
		{ fieldname: "items", label: "Items", fieldtype: "Table", options: "Invoice Item" },
	],
	Customer: [{ fieldname: "customer_name", label: "Customer Name", fieldtype: "Data" }],
	"Invoice Item": [
		{ fieldname: "item_code", label: "Item Code", fieldtype: "Link", options: "Item" },
	],
	Item: [{ fieldname: "item_name", label: "Item Name", fieldtype: "Data" }],
};

assert.equal(resolveFieldInfo(fieldMetadata, "Invoice", "customer").label, "Customer");
assert.equal(
	resolveFieldInfo(fieldMetadata, "Invoice", "customer.customer_name").label,
	"Customer Name"
);
assert.equal(resolveFieldInfo(fieldMetadata, "Invoice", "items.item_code").label, "Item Code");
assert.deepEqual(resolveFieldInfo({}, "Invoice", "customer"), {});
assert.deepEqual(resolveFieldInfo(fieldMetadata, "Invoice", ""), {});
assert.deepEqual(resolveFieldInfo(fieldMetadata, "Invoice", "missing_field"), {});
assert.deepEqual(resolveFieldInfo(fieldMetadata, "Invoice", "customer.bad_field"), {});

console.log("output field metadata tests passed");
