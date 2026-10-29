import assert from "node:assert/strict";
import { test } from "node:test";
import {
	isInputTarget,
	matchesShortcut,
	parseShortcutString,
} from "../../../../../flexirule/public/js/flexirule/rule_builder/utils/keyboard_shortcuts.mjs";

test("parses shortcut modifiers and key aliases", () => {
	assert.deepEqual(parseShortcutString("Ctrl+Shift+E"), {
		key: "e",
		alt: false,
		ctrl: true,
		meta: false,
		mod: false,
		shift: true,
	});
	assert.deepEqual(parseShortcutString("Option+Shift+Return"), {
		key: "enter",
		alt: true,
		ctrl: false,
		meta: false,
		mod: false,
		shift: true,
	});
	assert.equal(parseShortcutString("Space").key, " ");
	assert.equal(parseShortcutString("Mod+Shift+E").mod, true);
	assert.equal(parseShortcutString(""), null);
	assert.equal(parseShortcutString("Ctrl+Shift"), null);
	assert.equal(parseShortcutString("Ctrl+Unexpected+E"), null);
});

test("matches shortcuts only when all requested and unrequested modifiers agree", () => {
	const base = { key: "E", ctrlKey: true, shiftKey: true, altKey: false, metaKey: false };
	assert.equal(matchesShortcut(base, "Ctrl+Shift+E"), true);
	assert.equal(matchesShortcut({ ...base, altKey: true }, "Ctrl+Shift+E"), false);
	assert.equal(matchesShortcut({ ...base, metaKey: true }, "Ctrl+Shift+E"), false);
	assert.equal(matchesShortcut({ key: "e", ctrlKey: true }, "Ctrl+Shift+E"), false);
	assert.equal(matchesShortcut({ key: " ", ctrlKey: false }, "Space"), true);
});

test("Mod accepts exactly one platform modifier", () => {
	assert.equal(matchesShortcut({ key: "e", ctrlKey: true }, "Mod+E"), true);
	assert.equal(matchesShortcut({ key: "e", metaKey: true }, "Mod+E"), true);
	assert.equal(matchesShortcut({ key: "e", ctrlKey: true, metaKey: true }, "Mod+E"), false);
	assert.equal(matchesShortcut({ key: "e" }, "Mod+E"), false);
});

test("identifies inputs, contenteditable ancestors, and editor widgets", () => {
	assert.equal(isInputTarget({ tagName: "INPUT" }), true);
	assert.equal(isInputTarget({ tagName: "TEXTAREA" }), true);
	assert.equal(isInputTarget({ tagName: "BUTTON" }), false);
	assert.equal(
		isInputTarget({
			tagName: "SPAN",
			closest: (selector) => (selector.includes("[role='textbox']") ? {} : null),
		}),
		true
	);
	assert.equal(
		isInputTarget({
			tagName: "SPAN",
			parentElement: { tagName: "DIV", isContentEditable: true },
		}),
		true
	);
	assert.equal(
		isInputTarget({ tagName: "DIV", getAttribute: (name) => (name === "role" ? "combobox" : null) }),
		true
	);
	assert.equal(isInputTarget(null), false);
});
