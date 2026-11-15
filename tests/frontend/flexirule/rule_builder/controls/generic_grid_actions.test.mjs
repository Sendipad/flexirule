import assert from "node:assert/strict";
import { useGenericGridActions } from "../../../../../flexirule/public/js/flexirule/rule_builder/controls/useGenericGridActions.js";

const fakeGridApi = {
	requestRowActionCalls: [],
	requestRowAction(action, entry) {
		this.requestRowActionCalls.push({ action, entry });
	},
	duplicateRowCalls: [],
	duplicateRow(entry) {
		this.duplicateRowCalls.push(entry);
	},
	selectionEnabled: { value: true },
	hasPrimaryAction: { value: true },
};

const actions = useGenericGridActions({
	gridApi: fakeGridApi,
	canCopyPaste: { value: true },
	readOnly: { value: false },
	availableRowActions: { value: ["edit", "move", "remove"] },
	editShortcut: { value: "Ctrl+Shift+E" },
});

// 1. Action list generation
const context = {
	entry: { index: 0, row: { id: "row-1" }, key: "row-1" },
	pageIndex: 0,
	isEditing: false,
	canToggle: true,
	canFinishEditing: false,
	isSelected: false,
	selectedCount: 0,
};

const actionList = actions.getRowActionList(context);
assert.ok(
	actionList.length >= 4,
	"Should have toggle edit, select, insert, duplicate, copy, remove"
);

// 2. Command execution
actions.toggleEditCommand.execute(context);
assert.equal(fakeGridApi.requestRowActionCalls.length, 1);
assert.equal(fakeGridApi.requestRowActionCalls[0].action, "edit");

actions.duplicateCommand.execute(context);
assert.equal(fakeGridApi.duplicateRowCalls.length, 1);
assert.equal(fakeGridApi.duplicateRowCalls[0].key, "row-1");

console.log("useGenericGridActions unit tests passed");
