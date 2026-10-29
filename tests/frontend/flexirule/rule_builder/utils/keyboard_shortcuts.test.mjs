import assert from "node:assert";
import { test } from "node:test";
import {
	parseShortcutString,
	matchesShortcut,
	isInputTarget,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/keyboard_shortcuts.mjs";

test("parseShortcutString correctly parses modifier combinations", () => {
	assert.deepStrictEqual(parseShortcutString("Ctrl+Shift+E"), {
		key: "e",
		alt: false,
		ctrl: true,
		meta: false,
		mod: false,
		shift: true,
	});

	assert.deepStrictEqual(parseShortcutString("Shift+Enter"), {
		key: "enter",
		alt: false,
		ctrl: false,
		meta: false,
		mod: false,
		shift: true,
	});
});

test("matchesShortcut correctly matches events", () => {
	const event = { key: "E", ctrlKey: true, shiftKey: true, altKey: false, metaKey: false };
	assert.strictEqual(matchesShortcut(event, "Ctrl+Shift+E"), true);
	assert.strictEqual(matchesShortcut(event, "Ctrl+E"), false);
});

test("isInputTarget identifies input elements", () => {
	assert.strictEqual(isInputTarget({ tagName: "INPUT" }), true);
	assert.strictEqual(isInputTarget({ tagName: "TEXTAREA" }), true);
	assert.strictEqual(isInputTarget({ tagName: "SELECT" }), true);
	assert.strictEqual(isInputTarget({ tagName: "DIV", isContentEditable: false }), false);
});

test("matchesShortcut matches navigation and selection key strings", () => {
	const arrowDown = { key: "ArrowDown", ctrlKey: false, shiftKey: false, altKey: false, metaKey: false };
	assert.strictEqual(matchesShortcut(arrowDown, "ArrowDown"), true);

	const homeKey = { key: "Home", ctrlKey: false, shiftKey: false, altKey: false, metaKey: false };
	assert.strictEqual(matchesShortcut(homeKey, "Home"), true);

	const spaceKey = { key: " ", ctrlKey: false, shiftKey: false, altKey: false, metaKey: false };
	assert.strictEqual(matchesShortcut(spaceKey, " "), true);
});
