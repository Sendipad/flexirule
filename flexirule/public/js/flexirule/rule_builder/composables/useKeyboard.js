/**
 * useKeyboard — Keyboard shortcut handler for the Rule Builder.
 *
 * Phase 5: Extracts keyboard shortcuts from App.vue into
 * a reusable composable, following Frappe builder patterns.
 *
 * Usage:
 *   const { registerShortcuts, unregisterShortcuts } = useKeyboard()
 *   onMounted(() => registerShortcuts(handlers))
 *   onUnmounted(() => unregisterShortcuts())
 */
import { onMounted, onUnmounted } from "vue";

/**
 * Default keyboard shortcut bindings.
 * Maps key combinations to handler names.
 */
const DEFAULT_BINDINGS = {
	"ctrl+s": "save",
	"meta+s": "save",
	"ctrl+z": "undo",
	"meta+z": "undo",
	"ctrl+shift+z": "redo",
	"meta+shift+z": "redo",
	"ctrl+y": "redo",
	"meta+y": "redo",
	delete: "deleteSelected",
	backspace: "deleteSelected",
	escape: "deselect",
	"ctrl+a": "selectAll",
	"meta+a": "selectAll",
	"ctrl+l": "autoLayout",
	"meta+l": "autoLayout",
	"ctrl+f": "search",
	"meta+f": "search",
};

export function useKeyboard(customBindings = {}) {
	let _handlers = {};
	let _listener = null;

	const bindings = { ...DEFAULT_BINDINGS, ...customBindings };

	/**
	 * Register keyboard shortcut handlers.
	 *
	 * @param {Object} handlers - Map of handler names to functions.
	 *   e.g. { save: () => store.save(), undo: () => store.undo() }
	 */
	function registerShortcuts(handlers) {
		_handlers = handlers;

		_listener = (event) => {
			// Skip if user is typing in an input/textarea
			const tag = event.target?.tagName?.toLowerCase();
			if (tag === "input" || tag === "textarea" || tag === "select") {
				// Only intercept Ctrl+S in inputs
				if (!_isKeyCombo(event, "ctrl+s") && !_isKeyCombo(event, "meta+s")) {
					return;
				}
			}

			// Also skip if contenteditable
			if (event.target?.isContentEditable) return;

			const combo = _getKeyCombo(event);
			const handlerName = bindings[combo];

			if (handlerName && _handlers[handlerName]) {
				event.preventDefault();
				event.stopPropagation();
				_handlers[handlerName](event);
			}
		};

		document.addEventListener("keydown", _listener);
	}

	/**
	 * Unregister all keyboard shortcut handlers.
	 */
	function unregisterShortcuts() {
		if (_listener) {
			document.removeEventListener("keydown", _listener);
			_listener = null;
		}
		_handlers = {};
	}

	/**
	 * Build a key combination string from a KeyboardEvent.
	 */
	function _getKeyCombo(event) {
		const parts = [];
		if (event.ctrlKey) parts.push("ctrl");
		if (event.metaKey) parts.push("meta");
		if (event.shiftKey) parts.push("shift");
		if (event.altKey) parts.push("alt");

		const key = event.key.toLowerCase();
		if (!["control", "meta", "shift", "alt"].includes(key)) {
			parts.push(key);
		}

		return parts.join("+");
	}

	/**
	 * Check if event matches a specific key combo.
	 */
	function _isKeyCombo(event, combo) {
		return _getKeyCombo(event) === combo;
	}

	// Auto-cleanup on component unmount
	onUnmounted(() => {
		unregisterShortcuts();
	});

	return {
		registerShortcuts,
		unregisterShortcuts,
	};
}
