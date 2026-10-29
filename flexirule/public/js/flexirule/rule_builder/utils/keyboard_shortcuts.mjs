const MODIFIERS = new Set([
	"alt",
	"option",
	"ctrl",
	"control",
	"meta",
	"cmd",
	"command",
	"mod",
	"shift",
]);

function normalizeKey(value) {
	const raw = String(value ?? "");
	if (raw === " ") return " ";
	const key = raw.trim().toLowerCase();
	const aliases = {
		esc: "escape",
		return: "enter",
		space: " ",
		spacebar: " ",
	};
	return aliases[key] ?? key;
}

export function parseShortcutString(shortcut) {
	if (typeof shortcut !== "string") return null;
	if (shortcut === " ") {
		return { key: " ", alt: false, ctrl: false, meta: false, mod: false, shift: false };
	}

	const tokens = shortcut
		.split("+")
		.map((token) => token.trim().toLowerCase())
		.filter(Boolean);
	if (!tokens.length) return null;

	const rawKey = tokens[tokens.length - 1];
	if (MODIFIERS.has(rawKey)) return null;
	if (tokens.slice(0, -1).some((token) => !MODIFIERS.has(token))) return null;

	const key = normalizeKey(rawKey);
	if (!key) return null;

	const mod = tokens.includes("mod");
	const ctrl = tokens.includes("ctrl") || tokens.includes("control");
	const meta = tokens.includes("meta") || tokens.includes("cmd") || tokens.includes("command");
	if (mod && (ctrl || meta)) return null;

	return {
		key,
		alt: tokens.includes("alt") || tokens.includes("option"),
		ctrl,
		meta,
		mod,
		shift: tokens.includes("shift"),
	};
}

export function matchesShortcut(event, shortcut) {
	if (!event || typeof event.key !== "string") return false;
	const parsed = typeof shortcut === "string" ? parseShortcutString(shortcut) : shortcut;
	if (!parsed || typeof parsed.key !== "string" || !parsed.key) return false;
	if (normalizeKey(event.key) !== normalizeKey(parsed.key)) return false;

	const alt = Boolean(event.altKey);
	const ctrl = Boolean(event.ctrlKey);
	const meta = Boolean(event.metaKey);
	const shift = Boolean(event.shiftKey);

	if (Boolean(parsed.mod)) {
		if (ctrl === meta) return false;
	} else if (ctrl !== Boolean(parsed.ctrl) || meta !== Boolean(parsed.meta)) {
		return false;
	}

	return alt === Boolean(parsed.alt) && shift === Boolean(parsed.shift);
}

const INPUT_TARGET_SELECTOR =
	"input, textarea, select, [contenteditable]:not([contenteditable='false']), [role='textbox'], [role='combobox'], [role='searchbox'], .monaco-editor, .CodeMirror, .ace_editor";

export function isInputTarget(target) {
	if (!target || typeof target !== "object") return false;

	try {
		if (typeof target.closest === "function" && target.closest(INPUT_TARGET_SELECTOR)) {
			return true;
		}
	} catch {
		// Fall back to inspecting the target and its ancestors for non-DOM test doubles.
	}

	let current = target;
	while (current && typeof current === "object") {
		const tagName = String(current.tagName || "").toUpperCase();
		if (["INPUT", "TEXTAREA", "SELECT"].includes(tagName)) return true;
		if (current.isContentEditable) return true;

		const contentEditable = current.getAttribute?.("contenteditable");
		if (
			contentEditable !== null &&
			contentEditable !== undefined &&
			contentEditable !== "false"
		) {
			return true;
		}

		const role = current.getAttribute?.("role") || current.role;
		if (["textbox", "combobox", "searchbox"].includes(String(role || "").toLowerCase())) {
			return true;
		}

		current = current.parentElement || current.parentNode || null;
	}
	return false;
}
