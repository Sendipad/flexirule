import { resolvePresentationMode } from "./inline_presentation_policy.mjs";

export const GRID_CLIPBOARD_FORMAT = "flexirule-generic-grid";

/** Match a configurable keyboard shortcut while respecting all modifier keys. */
export function matchesShortcut(event, shortcut) {
	if (!event || typeof event.key !== "string") return false;
	const keys = String(shortcut || "")
		.toLowerCase()
		.split("+")
		.map((key) => key.trim())
		.filter(Boolean);
	if (!keys.length) return false;

	const key = keys[keys.length - 1];
	const wantsAlt = keys.includes("alt");
	const wantsCtrl = keys.includes("ctrl") || keys.includes("control");
	const wantsMeta = keys.includes("cmd") || keys.includes("meta") || keys.includes("command");
	const wantsShift = keys.includes("shift");
	return (
		event.key.toLowerCase() === key &&
		Boolean(event.altKey) === wantsAlt &&
		Boolean(event.ctrlKey) === wantsCtrl &&
		Boolean(event.metaKey) === wantsMeta &&
		Boolean(event.shiftKey) === wantsShift
	);
}

export function getRowKey(row, index, keyName = "id") {
	let key;
	try {
		key =
			typeof keyName === "function"
				? keyName(row, index)
				: row && typeof row === "object"
				? row[keyName]
				: undefined;
	} catch {
		// A failing user key resolver must not break rendering; use the positional fallback.
		key = undefined;
	}
	return key === null || key === undefined || key === "" ? "row-" + index : String(key);
}

export function getPathValue(source, path) {
	if (!path) return undefined;
	return String(path)
		.split(".")
		.reduce((value, key) => (value == null ? undefined : value[key]), source);
}

export function rowMatchesSearch(row, fields, query) {
	const normalizedQuery = String(query ?? "")
		.trim()
		.toLocaleLowerCase();
	if (!normalizedQuery) return true;

	let values;
	if (typeof fields === "function") {
		values = fields(row);
	} else if (Array.isArray(fields)) {
		values = fields.map((path) => getPathValue(row, path));
	} else {
		return true;
	}
	if (!Array.isArray(values)) values = [values];

	return values
		.flat(Infinity)
		.filter((value) => value !== null && value !== undefined)
		.map((value) => String(value))
		.join(" ")
		.toLocaleLowerCase()
		.includes(normalizedQuery);
}

export function paginateRows(rows, page = 1, pageSize = 10) {
	const list = Array.isArray(rows) ? rows : [];
	const size = Math.max(1, Math.floor(Number(pageSize) || 10));
	const pageCount = Math.max(1, Math.ceil(list.length / size));
	const currentPage = Math.min(pageCount, Math.max(1, Math.floor(Number(page) || 1)));
	const start = (currentPage - 1) * size;

	return {
		rows: list.slice(start, start + size),
		page: currentPage,
		pageSize: size,
		pageCount,
		start,
		end: Math.min(start + size, list.length),
		total: list.length,
	};
}

export function selectRangeKeys(
	rows,
	startIndex,
	endIndex,
	getKey = (row, index) => getRowKey(row, index)
) {
	const list = Array.isArray(rows) ? rows : [];
	if (!list.length) return [];
	const start = Math.max(0, Math.min(list.length - 1, Math.min(startIndex, endIndex)));
	const end = Math.max(0, Math.min(list.length - 1, Math.max(startIndex, endIndex)));
	return list.slice(start, end + 1).map((row, index) => getKey(row, start + index));
}

export function parseClipboardRows(text) {
	if (typeof text !== "string" || !text.trim()) return [];
	try {
		const parsed = JSON.parse(text);
		const rows = Array.isArray(parsed)
			? parsed
			: parsed?.format === GRID_CLIPBOARD_FORMAT && parsed.version === 1
			? parsed.rows
			: null;
		return Array.isArray(rows)
			? rows.filter((row) => row !== null && typeof row === "object" && !Array.isArray(row))
			: [];
	} catch {
		return [];
	}
}

/**
 * Resolve the props passed to a row renderer. Consumer-supplied props are preserved,
 * while the stable row contract is added consistently for slot and component renderers.
 */
export function buildRowProps(row, index, customProps, selected, invalid, readOnly) {
	const resolved = typeof customProps === "function" ? customProps(row, index) : customProps;
	return {
		...(resolved && typeof resolved === "object" ? resolved : {}),
		row,
		modelValue: row,
		index,
		selected: Boolean(selected),
		invalid: Boolean(invalid),
		readOnly: Boolean(readOnly),
	};
}

/**
 * Resolve the summary's double-click action for either readable or editing rows.
 * Read-only rows and rows without an edit action remain non-interactive.
 */
export function getSummaryToggleAction(
	row,
	{
		readOnly = false,
		availableRowActions = ["edit"],
		editStateKey = "isEditing",
		isNew = false,
		isValid = true,
		mode = "hybrid",
	} = {}
) {
	if (readOnly || !Array.isArray(availableRowActions) || !availableRowActions.includes("edit")) {
		return null;
	}
	const isEditing = Boolean(row?.[editStateKey]);
	if (isEditing) {
		const resolvedMode = resolvePresentationMode(mode);
		if (resolvedMode === "summary") return "view";
		if (resolvedMode === "hybrid") return !isNew && isValid ? "view" : null;
		return null;
	}
	return "edit";
}

/**
 * A selection is toggled as one group: all-editing becomes readable; any other
 * combination becomes editable. This avoids leaving a mixed selection in mixed modes.
 */
export function getBulkEditAction(rows, editStateKey = "isEditing") {
	const list = Array.isArray(rows) ? rows : [];
	if (!list.length) return null;
	return list.every((row) => Boolean(row?.[editStateKey])) ? "view" : "edit";
}

/**
 * Resolve where the primary action should insert relative to the user's active row.
 * Row activation is independent of the index-based multi-selection UI.
 */
export function getPrimaryActionAfterIndex(activeIndex, selectedIndexes = []) {
	if (Number.isInteger(activeIndex) && activeIndex >= 0) return activeIndex;
	const validIndexes = (Array.isArray(selectedIndexes) ? selectedIndexes : []).filter(
		(index) => Number.isInteger(index) && index >= 0
	);
	return validIndexes.length ? Math.max(...validIndexes) : null;
}
