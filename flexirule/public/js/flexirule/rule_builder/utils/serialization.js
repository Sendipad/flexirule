/**
 * Serialization Utilities for Action Builder
 * Ensures consistent transformation between reactive Objects (internal state)
 * and serialized Strings (UI Code editors/Frappe backend).
 */

/**
 * Converts any value to a pretty JSON string for display in Code editors.
 * Safely handles already-serialized strings and null values.
 */
export function toCodeString(value) {
	if (value === null || value === undefined) return "";
	if (typeof value === "string") return value;

	try {
		// Handles reactive proxies by stringifying and parsing if needed,
		// but JSON.stringify usually handles Vue 3 proxies fine.
		return JSON.stringify(value, null, 2);
	} catch (e) {
		console.error("FlexiRule Serialization Error (toCodeString):", e);
		return "";
	}
}

/**
 * Parses a JSON string from a Code editor back into a plain JavaScript Object.
 * Returns a fallback if parsing fails.
 */
export function fromCodeString(value, fallback = {}) {
	if (!value || typeof value !== "string") return value || fallback;

	try {
		const parsed = JSON.parse(value);
		return parsed && typeof parsed === "object" ? parsed : fallback;
	} catch (e) {
		// Silent failure for partial typing in editors
		return fallback;
	}
}

/**
 * Utility to check if a DocField is intended to hold JSON data.
 */
export function isJsonField(df) {
	if (!df) return false;
	return df.fieldtype === "JSON" || (df.fieldtype === "Code" && df.options === "JSON");
}

/**
 * Deep clones an object or array.
 * Uses structuredClone if available, with a fallback that handles most POJOs.
 * Preserves undefined values which JSON.stringify would drop.
 */
export function deepClone(obj) {
	if (obj === null || typeof obj !== "object") {
		return obj;
	}

	if (typeof structuredClone === "function") {
		try {
			return structuredClone(obj);
		} catch (e) {
			// Fallback if structuredClone fails (e.g. on certain proxies)
		}
	}

	if (Array.isArray(obj)) {
		const copy = [];
		for (let i = 0; i < obj.length; i++) {
			copy[i] = deepClone(obj[i]);
		}
		return copy;
	}

	const copy = {};
	for (const key in obj) {
		if (Object.prototype.hasOwnProperty.call(obj, key)) {
			copy[key] = deepClone(obj[key]);
		}
	}
	return copy;
}
