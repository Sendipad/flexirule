import { toRaw, isRef } from "vue";

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
 * Deep clones an object safely.
 * Strips Vue reactive proxies and handles Maps, Sets, Dates, RegExps,
 * Arrays, and circular references for a production-ready fallback.
 */
export function deepClone(obj, hash = new WeakMap()) {
	// Unwrap Vue ref/proxy if possible
	if (isRef && isRef(obj)) {
		obj = obj.value;
	}
	if (toRaw) {
		obj = toRaw(obj);
	}

	// Handle primitives and null
	if (obj === null || typeof obj !== "object") {
		return obj;
	}

	// Handle cyclic references
	if (hash.has(obj)) {
		return hash.get(obj);
	}

	// Handle Date
	if (obj instanceof Date) {
		return new Date(obj.getTime());
	}

	// Handle RegExp
	if (obj instanceof RegExp) {
		return new RegExp(obj.source, obj.flags);
	}

	// Handle Array
	if (Array.isArray(obj)) {
		const arr = [];
		hash.set(obj, arr);
		for (let i = 0; i < obj.length; i++) {
			arr[i] = deepClone(obj[i], hash);
		}
		return arr;
	}

	// Handle Map
	if (obj instanceof Map) {
		const map = new Map();
		hash.set(obj, map);
		obj.forEach((value, key) => {
			map.set(key, deepClone(value, hash));
		});
		return map;
	}

	// Handle Set
	if (obj instanceof Set) {
		const set = new Set();
		hash.set(obj, set);
		obj.forEach((value) => {
			set.add(deepClone(value, hash));
		});
		return set;
	}

	// For standard objects, create a new object with the same prototype
	const proto = Object.getPrototypeOf(obj);
	const clone = Object.create(proto);
	hash.set(obj, clone);

	// Object.keys correctly iterates own enumerable string properties (handles Vue reactives transparently)
	const keys = Object.keys(obj);
	for (let i = 0; i < keys.length; i++) {
		const key = keys[i];
		clone[key] = deepClone(obj[key], hash);
	}

	return clone;
}
