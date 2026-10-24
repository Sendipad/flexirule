import assert from "node:assert/strict";
import {
	GRID_CLIPBOARD_FORMAT,
	buildRowProps,
	getPrimaryActionAfterIndex,
	getSummaryToggleAction,
	matchesShortcut,
	getPathValue,
	getBulkEditAction,
	getRowKey,
	paginateRows,
	parseClipboardRows,
	rowMatchesSearch,
	selectRangeKeys,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/generic_grid_model.mjs";

const rows = [
	{ id: "a", field: "title", kind: "field", meta: { label: "Title" } },
	{ id: "b", field: "customer_name", kind: "field", meta: { label: "Customer" } },
	{ id: "c", field: "grand_total", kind: "function", meta: { label: "Grand Total" } },
];

assert.equal(matchesShortcut({ key: "e", ctrlKey: true, shiftKey: true }, "Ctrl+Shift+E"), true);
assert.equal(matchesShortcut({ key: "E", ctrlKey: true, shiftKey: true }, "Ctrl+Shift+E"), true);
assert.equal(matchesShortcut({ key: "e", altKey: true }, "Ctrl+Shift+E"), false);
assert.equal(matchesShortcut({ key: "e", ctrlKey: true }, "Ctrl+Shift+E"), false);
assert.equal(matchesShortcut({ key: "g", altKey: true, shiftKey: true }, "Alt+Shift+G"), true);
assert.equal(matchesShortcut({ key: "g", altKey: true }, "Alt+Shift+G"), false);
assert.equal(matchesShortcut({ key: "Enter", shiftKey: true }, "Shift+Enter"), true);
assert.equal(matchesShortcut({ key: "Enter", altKey: true }, "Alt+Enter"), true);
assert.equal(matchesShortcut({ key: "Enter", altKey: true, ctrlKey: true }, "Alt+Enter"), false);
assert.equal(matchesShortcut({ key: "e" }, "Ctrl+Shift+E"), false);
assert.equal(matchesShortcut(null, "Ctrl+Shift+E"), false);

assert.equal(getRowKey(rows[0], 0), "a");
assert.equal(getRowKey({}, 4), "row-4");
assert.equal(
	getRowKey(rows[1], 1, (row) => row.field),
	"customer_name"
);
assert.equal(
	getRowKey(rows[1], 1, () => ""),
	"row-1"
);
assert.equal(
	getRowKey(rows[1], 1, () => {
		throw new Error("resolver failure");
	}),
	"row-1"
);
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

const customRowProps = {
	doctype: "Sales Invoice",
	variableOptions: ["customer"],
	showValidation: true,
};
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
	buildRowProps(rows[1], 3, (row, index) => ({ label: row.meta.label, rowIndex: index }))
		.rowIndex,
	3
);

assert.equal(getSummaryToggleAction(rows[0]), "edit");
assert.equal(getSummaryToggleAction({ isEditing: true }), "view");
assert.equal(getSummaryToggleAction({ isEditing: true }, { isNew: true, mode: "hybrid" }), null);
assert.equal(getSummaryToggleAction({ isEditing: true }, { isValid: false, mode: "hybrid" }), null);
assert.equal(getSummaryToggleAction({ isEditing: true }, { mode: "summary" }), "view");
assert.equal(getSummaryToggleAction({ isEditing: true }, { mode: "Summary" }), "view");
assert.equal(getSummaryToggleAction({ isEditing: true }, { mode: "Form" }), null);
assert.equal(getSummaryToggleAction(rows[0], { readOnly: true }), null);
assert.equal(getSummaryToggleAction({ isEditing: true }, { readOnly: true }), null);
assert.equal(getSummaryToggleAction(rows[0], { availableRowActions: ["remove"] }), null);
assert.equal(getSummaryToggleAction({ mode: "editing" }, { editStateKey: "mode" }), "view");
assert.equal(getSummaryToggleAction(rows[0], { availableRowActions: null }), null);

assert.equal(getBulkEditAction([]), null);
assert.equal(getBulkEditAction([{ isEditing: true }, { isEditing: true }]), "view");
assert.equal(getBulkEditAction([{ isEditing: false }, { isEditing: false }]), "edit");
assert.equal(getBulkEditAction([{ isEditing: true }, { isEditing: false }]), "edit");
assert.equal(getBulkEditAction([{ mode: "editing" }, { mode: "editing" }], "mode"), "view");

assert.equal(
	getPrimaryActionAfterIndex(1, []),
	1,
	"active row inserts after it without selecting its index"
);
assert.equal(
	getPrimaryActionAfterIndex(0, [1, 2]),
	0,
	"active row takes precedence over selected rows"
);
assert.equal(
	getPrimaryActionAfterIndex(null, [1, 2]),
	2,
	"selected-row fallback remains supported"
);
assert.equal(
	getPrimaryActionAfterIndex(null, []),
	null,
	"without an active or selected row, append at the end"
);
assert.equal(getPrimaryActionAfterIndex(-1, []), null);
assert.equal(getPrimaryActionAfterIndex(null, [1, -2, 1.5]), 1);
