import { computed, ref } from "vue";
import { isInputOrEditorTarget } from "./command_action_types.mjs";

const registry = ref([]);
// Hierarchical context stack: top of the stack is the innermost active context
const contextStack = ref(["global"]);
const activeContexts = computed(() => new Set(contextStack.value));

export function useKeyboardRegistry() {
	const registerShortcut = (options) => {
		const {
			key,
			ctrl = false,
			meta = false,
			mod = false, // Ctrl on Windows/Linux, Meta on Mac
			shift = false,
			alt = false,
			callback,
			context = "global",
			priority = 0,
			description = "",
			prevent = true,
			allowInInputs = false,
		} = options;

		// Reserved browser shortcuts that we should NOT override
		const reserved = [
			{ key: "t", ctrl: true }, // New tab
			{ key: "w", ctrl: true }, // Close tab
			{ key: "n", ctrl: true }, // New window
			{ key: "r", ctrl: true }, // Reload
			{ key: "l", ctrl: true }, // Focus address bar
			{ key: "f", ctrl: true }, // Find
			{ key: "d", ctrl: true }, // Bookmark page (CRITICAL: preserve native bookmark)
			{ key: "t", meta: true },
			{ key: "w", meta: true },
			{ key: "n", meta: true },
			{ key: "r", meta: true },
			{ key: "l", meta: true },
			{ key: "f", meta: true },
			{ key: "d", meta: true },
		];

		const isReserved = reserved.some(
			(r) =>
				r.key.toLowerCase() === key.toLowerCase() &&
				!!r.ctrl === (ctrl || mod) &&
				!!r.meta === (meta || mod)
		);

		if (isReserved) {
			console.warn(`[KeyboardRegistry] Attempted to register reserved shortcut: ${key}`);
			return () => {};
		}

		const shortcut = {
			key: String(key).toLowerCase(),
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
			id: Math.random().toString(36).slice(2, 11),
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
		if (!context) return;
		// If already in stack, remove prior occurrence to move it to the top
		const existingIndex = contextStack.value.indexOf(context);
		if (existingIndex !== -1) {
			contextStack.value.splice(existingIndex, 1);
		}
		contextStack.value.push(context);
	};

	const popContext = (context) => {
		if (!context || context === "global") return;
		const index = contextStack.value.lastIndexOf(context);
		if (index !== -1) {
			contextStack.value.splice(index, 1);
		}
	};

	const getTopContext = () => {
		return contextStack.value[contextStack.value.length - 1] || "global";
	};

	const handleKeydown = (e) => {
		const isInput = isInputOrEditorTarget(e.target);

		const pressedKey = e.key.toLowerCase();
		const ctrl = e.ctrlKey;
		const meta = e.metaKey;
		const shift = e.shiftKey;
		const alt = e.altKey;

		// Filter shortcuts matching the key combination and currently active contexts
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
			// Sort matches by context stack depth descending (innermost context first),
			// then by priority descending.
			matches.sort((a, b) => {
				const depthA = contextStack.value.lastIndexOf(a.context);
				const depthB = contextStack.value.lastIndexOf(b.context);
				if (depthA !== depthB) return depthB - depthA;
				return b.priority - a.priority;
			});

			const bestMatch = matches[0];

			// Input protection:
			// If focus is in an input/editor, only trigger if allowInInputs is true,
			// or if it's an explicit modifier shortcut (like Ctrl+S) with length > 1 or modified.
			if (isInput && !bestMatch.allowInInputs) {
				const isModified = bestMatch.ctrl || bestMatch.meta || bestMatch.mod;
				if (
					!isModified ||
					(bestMatch.key.length === 1 && !bestMatch.shift && !bestMatch.alt)
				) {
					// Allow native character typing, backspace, delete, navigation
					return;
				}
			}

			// If text is selected on the page, never intercept Ctrl+C / Cmd+C
			if (
				bestMatch.key === "c" &&
				(bestMatch.ctrl || bestMatch.meta || bestMatch.mod) &&
				typeof window !== "undefined" &&
				window.getSelection()?.toString()?.length > 0
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
		getTopContext,
		handleKeydown,
		registry,
		contextStack,
		activeContexts,
	};
}

// Singleton listener
if (typeof window !== "undefined") {
	const { handleKeydown } = useKeyboardRegistry();
	// Use bubble phase (false) so that components can stop propagation if necessary
	window.addEventListener("keydown", (e) => handleKeydown(e), false);
}
