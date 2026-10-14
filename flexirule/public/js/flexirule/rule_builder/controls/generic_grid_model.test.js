import assert from "node:assert/strict";
import {
	GRID_CLIPBOARD_FORMAT,
	buildRowProps,
	getPathValue,
	getRowKey,
	paginateRows,
	parseClipboardRows,
	rowMatchesSearch,
	selectRangeKeys,
} from "./generic_grid_model.js";

const rows = [
	{ id: "a", field: "title", kind: "field", meta: { label: "Title" } },
	{ id: "b", field: "customer_name", kind: "field", meta: { label: "Customer" } },
	{ id: "c", field: "grand_total", kind: "function", meta: { label: "Grand Total" } },
];

assert.equal(getRowKey(rows[0], 0), "a");
assert.equal(getRowKey({}, 4), "row-4");
assert.equal(getPathValue(rows[0], "meta.label"), "Title");
assert.equal(rowMatchesSearch(rows[1], ["field", "meta.label"], "CUSTOMER"), true);
assert.equal(rowMatchesSearch(rows[2], ["field", "meta.label"], "missing"), false);
assert.equal(rowMatchesSearch(rows[0], ["field"], "  "), true);

assert.deepEqual(selectRangeKeys(rows, 2, 0), ["a", "b", "c"]);
assert.deepEqual(selectRangeKeys(rows, 1, 1), ["b"]);
assert.deepEqual(selectRangeKeys([], 0, 2), []);

assert.deepEqual(paginateRows(rows, 2, 2), {
	rows: [rows[2]],
	page: 2,
	pageSize: 2,
	pageCount: 2,
	start: 2,
	end: 3,
	total: 3,
});
assert.deepEqual(paginateRows(rows, 100, 2).rows, [rows[2]]);
assert.deepEqual(paginateRows([], 1, 10).rows, []);

assert.deepEqual(parseClipboardRows("not json"), []);
assert.deepEqual(parseClipboardRows(JSON.stringify([rows[0], null, "not a row"])), [rows[0]]);
assert.deepEqual(
	parseClipboardRows(
		JSON.stringify({ format: GRID_CLIPBOARD_FORMAT, version: 1, rows: [rows[1]] })
	),
	[rows[1]]
);
assert.deepEqual(
	parseClipboardRows(JSON.stringify({ format: GRID_CLIPBOARD_FORMAT, version: 2, rows })),
	[]
);

const customRowProps = { doctype: "Sales Invoice", variableOptions: ["customer"], showValidation: true };
const resolvedRowProps = buildRowProps(rows[0], 0, customRowProps, true, false, false);
assert.equal(resolvedRowProps.doctype, "Sales Invoice");
assert.deepEqual(resolvedRowProps.variableOptions, ["customer"]);
assert.equal(resolvedRowProps.showValidation, true);
assert.equal(resolvedRowProps.row, rows[0]);
assert.equal(resolvedRowProps.modelValue, rows[0]);
assert.equal(resolvedRowProps.index, 0);
assert.equal(resolvedRowProps.selected, true);
assert.equal(resolvedRowProps.invalid, false);
assert.equal(resolvedRowProps.readOnly, false);
assert.equal(
	buildRowProps(rows[1], 3, (row, index) => ({ label: row.meta.label, rowIndex: index })).rowIndex,
	3
);
