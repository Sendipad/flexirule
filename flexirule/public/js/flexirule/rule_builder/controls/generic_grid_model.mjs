export const GRID_CLIPBOARD_FORMAT = "flexirule-generic-grid";

export function getRowKey(row, index, keyName = "id") {
	const key = row && typeof row === "object" ? row[keyName] : undefined;
	return key === null || key === undefined || key === "" ? "row-" + index : String(key);
}

export function getPathValue(source, path) {
	if (!path) return undefined;
	return String(path)
		.split(".")
		.reduce((value, key) => (value == null ? undefined : value[key]), source);
}

export function rowMatchesSearch(row, fields, query) {
	const normalizedQuery = String(query ?? "").trim().toLocaleLowerCase();
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

export function selectRangeKeys(rows, startIndex, endIndex, getKey = (row, index) => getRowKey(row, index)) {
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
	const resolved =
		typeof customProps === "function" ? customProps(row, index) : customProps;
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
