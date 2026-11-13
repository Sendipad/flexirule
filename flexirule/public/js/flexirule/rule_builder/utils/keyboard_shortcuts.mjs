/**
 * Centralized Keyboard Shortcut Utilities
 *
 * Provides shortcut parsing, event matching, and input control target detection
 * shared by GenericGrid, TreeBuilder, and composables.
 */

export function parseShortcutString(shortcut) {
	if (shortcut === " " || String(shortcut).toLowerCase() === "space") {
		return { key: " ", alt: false, ctrl: false, meta: false, mod: false, shift: false };
	}
	const keys = String(shortcut || "")
		.toLowerCase()
		.split("+")
		.map((key) => key.trim())
		.filter(Boolean);
	if (!keys.length) return null;

	let key = keys[keys.length - 1];
	if (key === "space") key = " ";
	const alt = keys.includes("alt");
	const ctrl = keys.includes("ctrl") || keys.includes("control");
	const meta = keys.includes("cmd") || keys.includes("meta") || keys.includes("command");
	const mod = keys.includes("mod");
	const shift = keys.includes("shift");

	return { key, alt, ctrl, meta, mod, shift };
}

/**
 * Match a keyboard event against a shortcut definition or string.
 */
export function matchesShortcut(event, shortcut) {
	if (!event || typeof event.key !== "string") return false;
	const parsed = typeof shortcut === "string" ? parseShortcutString(shortcut) : shortcut;
	if (!parsed || !parsed.key) return false;

	const pressedKey = event.key.toLowerCase();
	if (pressedKey !== parsed.key) return false;

	const wantsAlt = Boolean(parsed.alt);
	const wantsCtrl = Boolean(parsed.ctrl);
	const wantsMeta = Boolean(parsed.meta);
	const wantsMod = Boolean(parsed.mod);
	const wantsShift = Boolean(parsed.shift);

	if (wantsMod) {
		if (!(event.ctrlKey || event.metaKey)) return false;
	} else {
		if (Boolean(event.ctrlKey) !== wantsCtrl) return false;
		if (Boolean(event.metaKey) !== wantsMeta) return false;
	}

	if (Boolean(event.altKey) !== wantsAlt) return false;
	if (Boolean(event.shiftKey) !== wantsShift) return false;

	return true;
}

/**
 * Determine if an event target is an active text input or editable control.
 */
export function isInputTarget(target) {
	if (!target || typeof target !== "object") return false;
	if (typeof Element !== "undefined" && target instanceof Element) {
		const tagName = target.tagName;
		if (["INPUT", "TEXTAREA", "SELECT"].includes(tagName)) return true;
		if (target.isContentEditable) return true;
		if (
			target.closest?.(
				"input, textarea, select, [contenteditable='true'], [role='textbox'], [role='combobox'], .monaco-editor, .CodeMirror, .ace_editor"
			)
		) {
			return true;
		}
	} else if (target.tagName) {
		const tagName = String(target.tagName).toUpperCase();
		if (["INPUT", "TEXTAREA", "SELECT"].includes(tagName)) return true;
		if (target.isContentEditable) return true;
	}
	return false;
}
