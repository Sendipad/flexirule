/**
 * Core command & action definitions shared across TreeBuilder, GenericGrid, and consumers.
 */

/**
 * Standard keyboard shortcuts for unified actions.
 */
export const UNIFIED_SHORTCUTS = Object.freeze({
	TOGGLE_EDIT: "Ctrl+Shift+E",
	INSERT: "Shift+Enter",
	SELECT: "Space",
	DELETE: "Delete",
	COPY: "Ctrl+C",
	DUPLICATE: "Alt+Shift+ArrowDown",
	OPEN_MENU: "Shift+F10",
});

/**
 * Normalize shortcut key tokens for matching and display.
 */
export function normalizeShortcut(shortcut) {
	if (!shortcut || typeof shortcut !== "string") return "";
	return shortcut
		.split("+")
		.map((part) => part.trim())
		.filter(Boolean)
		.join("+");
}

/**
 * Check if target is an interactive input or editor control where single-key
 * shortcuts or navigation keys must NEVER be intercepted.
 */
export function isInputOrEditorTarget(target) {
	if (!target || typeof target !== "object") return false;

	// 1. Native HTML form controls
	const tagName = target.tagName ? String(target.tagName).toUpperCase() : "";
	if (["INPUT", "TEXTAREA", "SELECT"].includes(tagName)) return true;

	// 2. Rich text & code editors
	if (Boolean(target.isContentEditable)) return true;
	if (typeof target.closest === "function") {
		if (
			target.closest(
				".monaco-editor, .CodeMirror, .ace_editor, .ProseMirror, [contenteditable='true']"
			)
		) {
			return true;
		}

		// 3. Frappe custom inputs, comboboxes, and text widgets
		if (
			target.closest(
				".combobox-input-group, .flex-value-control-input, [role='combobox'], [role='textbox']"
			)
		) {
			return true;
		}
	}

	return false;
}

/**
 * Factory to create a standardized command definition.
 */
export function defineCommand(definition) {
	return {
		id: definition.id,
		label: definition.label,
		icon: definition.icon || "",
		shortcut: definition.shortcut || "",
		group: definition.group || "default",
		isDestructive: Boolean(definition.isDestructive),
		allowInInputs: Boolean(definition.allowInInputs),
		isVisible: typeof definition.isVisible === "function" ? definition.isVisible : () => true,
		isEnabled: typeof definition.isEnabled === "function" ? definition.isEnabled : () => true,
		execute: definition.execute,
		guard: typeof definition.guard === "function" ? definition.guard : null,
		requiresConfirmation:
			typeof definition.requiresConfirmation === "function"
				? definition.requiresConfirmation
				: () => false,
		confirmationMessage:
			typeof definition.confirmationMessage === "function"
				? definition.confirmationMessage
				: () => "",
	};
}
