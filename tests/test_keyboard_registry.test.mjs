import test from "node:test";
import assert from "node:assert/strict";
import { useKeyboardRegistry } from "../flexirule/public/js/flexirule/rule_builder/composables/useKeyboardRegistry.js";
import {
	UNIFIED_SHORTCUTS,
	isInputOrEditorTarget,
	normalizeShortcut,
} from "../flexirule/public/js/flexirule/rule_builder/composables/command_action_types.mjs";

test("UNIFIED_SHORTCUTS defines authoritative keys", () => {
	assert.equal(UNIFIED_SHORTCUTS.TOGGLE_EDIT, "Ctrl+Shift+E");
	assert.equal(UNIFIED_SHORTCUTS.INSERT, "Shift+Enter");
	assert.equal(UNIFIED_SHORTCUTS.DELETE, "Delete");
	assert.equal(UNIFIED_SHORTCUTS.DUPLICATE, "Alt+Shift+ArrowDown");
	assert.equal(normalizeShortcut(" Ctrl + Shift + E "), "Ctrl+Shift+E");
});

test("isInputOrEditorTarget detects input elements", () => {
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
});

test("useKeyboardRegistry hierarchical context stacking and precedence", () => {
	const registry = useKeyboardRegistry();
	let parentCalled = false;
	let childCalled = false;

	registry.pushContext("modal");
	registry.pushContext("grid:1");

	const unregParent = registry.registerShortcut({
		key: "Delete",
		context: "modal",
		callback: () => {
			parentCalled = true;
		},
	});

	const unregChild = registry.registerShortcut({
		key: "Delete",
		context: "grid:1",
		callback: () => {
			childCalled = true;
		},
	});

	const fakeEvent = {
		key: "Delete",
		ctrlKey: false,
		metaKey: false,
		shiftKey: false,
		altKey: false,
		target: { tagName: "DIV", isContentEditable: false, closest: () => null },
		preventDefault() {},
		stopPropagation() {},
	};

	registry.handleKeydown(fakeEvent);

	assert.equal(childCalled, true, "Innermost context should execute");
	assert.equal(parentCalled, false, "Parent context should not execute when shadowed");

	// Pop child context
	registry.popContext("grid:1");
	childCalled = false;
	parentCalled = false;

	registry.handleKeydown(fakeEvent);
	assert.equal(parentCalled, true, "Parent context executes after child context popped");

	unregParent();
	unregChild();
	registry.popContext("modal");
});

test("useKeyboardRegistry blocks Delete inside inputs", () => {
	const registry = useKeyboardRegistry();
	let deleteCalled = false;

	registry.pushContext("grid:test");
	const unreg = registry.registerShortcut({
		key: "Delete",
		context: "grid:test",
		callback: () => {
			deleteCalled = true;
		},
	});

	const fakeInputEvent = {
		key: "Delete",
		ctrlKey: false,
		metaKey: false,
		shiftKey: false,
		altKey: false,
		target: { tagName: "INPUT", isContentEditable: false, closest: () => null },
		preventDefault() {},
		stopPropagation() {},
	};

	registry.handleKeydown(fakeInputEvent);
	assert.equal(deleteCalled, false, "Delete must be blocked when typing inside an input");

	unreg();
	registry.popContext("grid:test");
});
