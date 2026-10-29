import { onMounted, onUnmounted, ref } from "vue";
import { parseShortcutString } from "../controls/generic_grid_model.mjs";

const registry = ref([]);
const activeContexts = ref(new Set(["global"]));

export function useKeyboardRegistry() {
	const registerShortcut = (options) => {
		let key = options.key;
		let ctrl = options.ctrl || false;
		let meta = options.meta || false;
		let mod = options.mod || false;
		let shift = options.shift || false;
		let alt = options.alt || false;

		if (options.shortcut) {
			const parsed = parseShortcutString(options.shortcut);
			if (parsed) {
				key = parsed.key;
				ctrl = parsed.ctrl;
				meta = parsed.meta;
				alt = parsed.alt;
				shift = parsed.shift;
			}
		}

		const {
			callback,
			context = "global",
			priority = 0,
			description = "",
			prevent = true,
			allowInInputs = false,
		} = options;

		if (!key) return () => {};

		// Reserved browser shortcuts that we should NOT override
		const reserved = [
			{ key: "t", ctrl: true }, // New tab
			{ key: "w", ctrl: true }, // Close tab
			{ key: "n", ctrl: true }, // New window
			{ key: "r", ctrl: true }, // Reload
			{ key: "l", ctrl: true }, // Focus address bar
			{ key: "f", ctrl: true }, // Find
			{ key: "t", meta: true },
			{ key: "w", meta: true },
			{ key: "n", meta: true },
			{ key: "r", meta: true },
			{ key: "l", meta: true },
			{ key: "f", meta: true },
		];

		const isReserved = reserved.some(
			(r) =>
				r.key.toLowerCase() === key.toLowerCase() &&
				!!r.ctrl === !!ctrl &&
				!!r.meta === !!meta
		);

		if (isReserved) {
			console.warn(`[KeyboardRegistry] Attempted to register reserved shortcut: ${key}`);
			return;
		}

		const shortcut = {
			key: key.toLowerCase(),
			ctrl,
			meta,
			mod,
			shift,
			alt,
			callback,
			context,
			priority,
			description,
			prevent,
			allowInInputs,
			id: Math.random().toString(36).substr(2, 9),
		};

		// Add to beginning of registry
		registry.value.unshift(shortcut);
		// Sort by priority descending
		registry.value.sort((a, b) => b.priority - a.priority);

		return () => {
			registry.value = registry.value.filter((s) => s.id !== shortcut.id);
		};
	};

	const pushContext = (context) => {
		activeContexts.value.add(context);
	};

	const popContext = (context) => {
		activeContexts.value.delete(context);
	};

	const handleKeydown = (e) => {
		// Don't trigger if typing in an input, unless the shortcut is specifically allowed
		const isInput =
			["INPUT", "TEXTAREA", "SELECT"].includes(e.target.tagName) ||
			e.target.isContentEditable ||
			e.target.closest(".monaco-editor") ||
			e.target.closest(".CodeMirror") ||
			e.target.closest(".ace_editor");

		const pressedKey = e.key.toLowerCase();
		const ctrl = e.ctrlKey;
		const meta = e.metaKey;
		const shift = e.shiftKey;
		const alt = e.altKey;

		const matches = registry.value.filter((s) => {
			if (!activeContexts.value.has(s.context)) return false;
			if (s.key !== pressedKey) return false;

			if (s.mod) {
				if (!(ctrl || meta)) return false;
			} else {
				if (s.ctrl !== ctrl) return false;
				if (s.meta !== meta) return false;
			}

			if (s.shift !== shift) return false;
			if (s.alt !== alt) return false;
			return true;
		});

		if (matches.length > 0) {
			const bestMatch = matches[0]; // Already sorted by priority

			// If focus is inside an input, only allow if explicitly permitted or modifier combination
			if (
				isInput &&
				!bestMatch.allowInInputs &&
				!bestMatch.ctrl &&
				!bestMatch.meta &&
				bestMatch.key.length === 1
			) {
				return;
			}

			if (bestMatch.prevent) {
				e.preventDefault();
				e.stopPropagation();
			}

			bestMatch.callback(e);
		}
	};

	return {
		registerShortcut,
		pushContext,
		popContext,
		handleKeydown,
		registry,
		activeContexts,
	};
}

// Singleton listener
if (typeof window !== "undefined") {
	const { handleKeydown } = useKeyboardRegistry();
	// Use bubble phase (false) so that components can stop propagation
	window.addEventListener("keydown", (e) => handleKeydown(e), false);
}
