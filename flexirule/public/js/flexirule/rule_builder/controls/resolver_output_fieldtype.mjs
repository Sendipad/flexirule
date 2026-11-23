/**
 * Infer resolver output using Frappe DocField fieldtypes.
 *
 * Dynamic resolver outputs are config-dependent. Returning null means the
 * operation must not persist a guessed fieldtype; the backend remains the
 * authoritative source for validation.
 */

function findResolverSpec(resolverSpecs, family, operation) {
	if (!Array.isArray(resolverSpecs)) return null;
	return (
		resolverSpecs.find((item) => item.family === family && item.operation === operation) || null
	);
}

function knownNumericValue(value) {
	if (value && typeof value === "object") {
		if (value.mode !== "static") return null;
		value = value.value;
	}
	if (typeof value === "number" && Number.isFinite(value)) return value;
	if (typeof value === "string" && value.trim() !== "") {
		const parsed = Number(value);
		return Number.isFinite(parsed) ? parsed : null;
	}
	return value == null ? 0 : null;
}

function nestedOutputFieldtype(value, resolverSpecs) {
	if (!value || typeof value !== "object") return null;
	if (value.mode === "static") return value.value_type || null;
	if (value.mode === "template") return "Data";
	if (value.mode === "resolver") {
		return resolveResolverOutputFieldtype(
			value.family,
			value.operation,
			value.config || {},
			findResolverSpec(resolverSpecs, value.family, value.operation),
			resolverSpecs
		);
	}
	return null;
}

/**
 * @param {string} family Canonical resolver family.
 * @param {string} operation Canonical resolver operation.
 * @param {object} config Resolver operation configuration.
 * @param {object|null} resolverSpec Backend resolver contract entry.
 * @param {Array|null} resolverSpecs Full backend resolver contract entries.
 * @returns {string|null} Exact Frappe DocField fieldtype, or null when unknown.
 */
export function resolveResolverOutputFieldtype(
	family,
	operation,
	config = {},
	resolverSpec = null,
	resolverSpecs = null
) {
	const cfg = config && typeof config === "object" ? config : {};

	if (family === "date_time" && operation === "current") {
		const token = String(cfg.token || "date").toLowerCase();
		if (token === "datetime" || token === "now") return "Datetime";
		if (token === "time") return "Time";
		return "Date";
	}

	if (family === "date_time" && operation === "diff") {
		const unit = String(cfg.diff_unit || "days").toLowerCase();
		return unit === "hours" || unit === "minutes" ? "Float" : "Int";
	}

	if (family === "date_time" && operation === "calculate") {
		const timeUnits = new Set(["hours", "minutes", "seconds"]);
		const sourceType = nestedOutputFieldtype(cfg.source, resolverSpecs);
		if (cfg.source != null) {
			if (sourceType === "Date" || sourceType === "date") {
				if (!timeUnits.has(cfg.offset_unit)) return "Date";
				const offset = knownNumericValue(cfg.offset_value);
				return offset == null ? null : offset === 0 ? "Date" : "Datetime";
			}
			if (sourceType === "Datetime" || sourceType === "datetime") return "Datetime";
			if (sourceType === "Time" || sourceType === "time") return "Time";
			return null;
		}

		const baseType = cfg.base_type;
		if (baseType === "current_datetime" || baseType === "now") return "Datetime";
		if (baseType === "current_time") return "Time";
		if (baseType === "doc_field" || cfg.base_field) return null;
		if (baseType == null) return null;
		if (baseType === "today" || baseType === "current_date") {
			if (timeUnits.has(cfg.offset_unit)) {
				const offset = knownNumericValue(cfg.offset_value);
				return offset == null ? null : offset === 0 ? "Date" : "Datetime";
			}
		}
		return "Date";
	}

	if (family === "date_time" && operation === "boundary") {
		const source = cfg.source ?? cfg.base_field;
		const sourceType = nestedOutputFieldtype(source, resolverSpecs);
		if (sourceType === "Date" || sourceType === "date") return "Date";
		if (sourceType === "Datetime" || sourceType === "datetime") return "Datetime";
		return null;
	}

	if (family === "system_context" && operation === "get") {
		if (cfg.sys_token === "role_check") return "Check";
		if (cfg.sys_token === null) return null;
		return "Data";
	}

	if (resolverSpec?.output_type_is_dynamic) return null;
	return resolverSpec?.output_type || null;
}
