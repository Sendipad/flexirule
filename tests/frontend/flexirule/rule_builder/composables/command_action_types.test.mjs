import assert from "node:assert/strict";
import {
	UNIFIED_SHORTCUTS,
	isInputOrEditorTarget,
	normalizeShortcut,
	defineCommand,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/composables/command_action_types.mjs";

assert.equal(UNIFIED_SHORTCUTS.TOGGLE_EDIT, "Ctrl+Shift+E");
assert.equal(UNIFIED_SHORTCUTS.INSERT, "Shift+Enter");
assert.equal(UNIFIED_SHORTCUTS.DELETE, "Delete");
assert.equal(UNIFIED_SHORTCUTS.DUPLICATE, "Alt+Shift+ArrowDown");
assert.equal(normalizeShortcut(" Ctrl + Shift + E "), "Ctrl+Shift+E");

// Target detection
assert.equal(isInputOrEditorTarget(null), false);
assert.equal(isInputOrEditorTarget({}), false);

const fakeInput = { tagName: "INPUT", isContentEditable: false, closest: () => null };
assert.equal(isInputOrEditorTarget(fakeInput), true);

const fakeDiv = { tagName: "DIV", isContentEditable: false, closest: () => null };
assert.equal(isInputOrEditorTarget(fakeDiv), false);

const fakeMonaco = {
	tagName: "DIV",
	isContentEditable: false,
	closest: (sel) => sel.includes("monaco-editor"),
};
assert.equal(isInputOrEditorTarget(fakeMonaco), true);

// Command schema
const cmd = defineCommand({
	id: "test.cmd",
	label: "Test Command",
	shortcut: "Delete",
	execute: () => true,
});
assert.equal(cmd.id, "test.cmd");
assert.equal(cmd.label, "Test Command");
assert.equal(cmd.shortcut, "Delete");
assert.equal(cmd.isVisible({}), true);
assert.equal(cmd.isEnabled({}), true);
assert.equal(cmd.execute({}), true);

console.log("command_action_types unit tests passed");
