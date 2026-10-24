import { getFilterOperators } from "./filter_operators.mjs";
import { resolveFilterFieldDef } from "./filter_summary_formatter.mjs";

export function isValueConfigured(val) {
	if (val === null || val === undefined || val === "") return false;
	if (
		typeof val === "object" &&
		!Array.isArray(val) &&
		Object.prototype.hasOwnProperty.call(val, "mode")
	) {
		if (val.mode === "static") {
			return isValueConfigured(val.value);
		}
		if (val.mode === "variable") {
			return Boolean(val.value || val.variable);
		}
		return (
			Boolean(
				val.value !== undefined && val.value !== null && String(val.value).trim() !== ""
			) || Boolean(val.expression || val.resolver_type)
		);
	}
	if (Array.isArray(val)) {
		return val.length > 0 && val.every(isValueConfigured);
	}
	return String(val).trim() !== "";
}

export function isValidIsValue(val) {
	if (val && typeof val === "object" && val.mode && val.mode !== "static") {
		return isValueConfigured(val);
	}
	const raw = val && typeof val === "object" && val.mode === "static" ? val.value : val;
	if (typeof raw === "string") {
		const trimmed = raw.trim();
		if (trimmed.startsWith("{") || trimmed.startsWith("@")) {
			return true;
		}
	}
	return ["set", "not set"].includes(
		String(raw ?? "")
			.trim()
			.toLowerCase()
	);
}

function resolveFieldDef(leaf, context = {}) {
	if (context.fieldDef) return context.fieldDef;
	if (!leaf?.field) return null;
	const resolved = resolveFilterFieldDef(leaf.field, context.doctype, context.metaMap);
	if (resolved && resolved.isResolved) return resolved;
	return null;
}

export function isFilterLeafValid(leaf, context = {}) {
	if (!leaf || typeof leaf !== "object" || !leaf.field) return false;
	if (!leaf.operator) return false;

	const fieldDef = resolveFieldDef(leaf, context);
	const allowed =
		context.allowedOperators ||
		(fieldDef ? getFilterOperators(fieldDef, context.nestedSetOptions) : null);
	if (allowed && allowed.length > 0 && !allowed.includes(leaf.operator)) {
		return false;
	}

	const op = leaf.operator;
	if (op === "Between") {
		const arr = Array.isArray(leaf.value) ? leaf.value : [];
		return arr.length >= 2 && isValueConfigured(arr[0]) && isValueConfigured(arr[1]);
	}
	if (String(op).toLowerCase() === "is") {
		return isValidIsValue(leaf.value);
	}
	return isValueConfigured(leaf.value);
}

export function validateFilterLeaf(leaf, context = {}) {
	const errors = [];
	if (!leaf || typeof leaf !== "object" || !leaf.field) {
		errors.push("Filter field is required.");
		return { valid: false, errors };
	}
	if (!leaf.operator) {
		errors.push("Filter operator is required.");
		return { valid: false, errors };
	}

	const fieldDef = resolveFieldDef(leaf, context);
	const allowed =
		context.allowedOperators ||
		(fieldDef ? getFilterOperators(fieldDef, context.nestedSetOptions) : null);

	if (allowed && allowed.length > 0 && !allowed.includes(leaf.operator)) {
		errors.push("Choose a supported operator for the selected field.");
		return { valid: false, errors };
	}

	const op = leaf.operator;
	if (op === "Between") {
		const arr = Array.isArray(leaf.value) ? leaf.value : [];
		if (arr.length < 2 || !isValueConfigured(arr[0]) || !isValueConfigured(arr[1])) {
			errors.push("Both values are required for Between.");
		}
	} else if (String(op).toLowerCase() === "is") {
		if (!isValidIsValue(leaf.value)) {
			errors.push("Choose Set or Not Set.");
		}
	} else if (!isValueConfigured(leaf.value)) {
		errors.push("Filter value is required.");
	}

	return { valid: errors.length === 0, errors };
}
