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

function getNestedSetOptions(context = {}) {
	if (context.nestedSetOptions) return context.nestedSetOptions;
	const bootDoctypes =
		typeof frappe !== "undefined" && frappe.boot?.nested_set_doctypes
			? frappe.boot.nested_set_doctypes
			: [];
	return {
		nestedSetDoctypes: bootDoctypes,
		rootDoctype: context.doctype,
	};
}

function resolveFieldDef(leaf, context = {}) {
	if (context.fieldDef) return context.fieldDef;
	if (!leaf?.field) return null;
	return resolveFilterFieldDef(leaf.field, context.doctype, context.metaMap);
}

function isFieldUnavailable(fieldDef, context = {}) {
	if (!fieldDef || fieldDef.isResolved !== false) return false;
	if (fieldDef.metadataChecked) return true;
	if (
		context.metaMap ||
		(typeof frappe !== "undefined" && frappe.meta) ||
		context.requireResolvedField
	) {
		return true;
	}
	return false;
}

export function isFilterLeafValid(leaf, context = {}) {
	if (!leaf || typeof leaf !== "object" || !leaf.field) return false;
	if (!leaf.operator) return false;

	const fieldDef = resolveFieldDef(leaf, context);
	if (isFieldUnavailable(fieldDef, context)) {
		return false;
	}

	const nestedSetOpts = getNestedSetOptions(context);
	const allowed =
		context.allowedOperators ||
		(fieldDef && fieldDef.isResolved !== false
			? getFilterOperators(fieldDef, nestedSetOpts)
			: null);
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
	if (isFieldUnavailable(fieldDef, context)) {
		errors.push(
			"The selected filter field is unavailable. Choose a valid field for this DocType."
		);
		return { valid: false, errors };
	}

	const nestedSetOpts = getNestedSetOptions(context);
	const allowed =
		context.allowedOperators ||
		(fieldDef && fieldDef.isResolved !== false
			? getFilterOperators(fieldDef, nestedSetOpts)
			: null);

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
