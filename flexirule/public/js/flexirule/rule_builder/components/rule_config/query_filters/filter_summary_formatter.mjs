import { getFieldType } from "./filter_operators.mjs";
import { isFilterLeafValid } from "./query_filter_validation.mjs";

const OPERATOR_LABELS = {
	"=": "equals",
	"!=": "does not equal",
	like: "contains",
	"not like": "does not contain",
	in: "is one of",
	"not in": "is not one of",
	">": "is greater than",
	"<": "is less than",
	">=": "is greater than or equal to",
	"<=": "is less than or equal to",
	is: "is",
	Between: "is between",
	Timespan: "is in timespan",
	"starts with": "starts with",
	"ends with": "ends with",
	"descendants of": "is descendant of",
	"descendants of (inclusive)": "is descendant of (inclusive)",
	"not descendants of": "is not descendant of",
	"ancestors of": "is ancestor of",
	"not ancestors of": "is not ancestor of",
};

export function humanize(raw) {
	if (!raw) return "";
	return String(raw)
		.replace(/_/g, " ")
		.replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatSingleValue(val) {
	if (val === null || val === undefined || val === "") return "";
	if (typeof val === "object" && val.mode) {
		if (val.mode === "static") {
			return formatSingleValue(val.value);
		}
		if (val.mode === "variable") {
			const varName = val.value || val.variable || "";
			return typeof __ === "function"
				? __("Variable ({0})", [varName])
				: `Variable (${varName})`;
		}
		if (val.mode === "resolver" || val.resolver_type) {
			const name = val.resolver_type || val.mode || "Resolver";
			return humanize(name);
		}
		return humanize(val.mode);
	}
	if (Array.isArray(val)) {
		return val.map(formatSingleValue).filter(Boolean).join(", ");
	}
	return String(val);
}

export function resolveFilterFieldDef(fieldname, doctype, metaMap = null) {
	if (!fieldname) return null;
	if (fieldname === "name")
		return { fieldname, fieldtype: "Data", isResolved: true, label: "Name" };
	if (["owner", "modified_by"].includes(fieldname))
		return {
			fieldname,
			fieldtype: "Link",
			options: "User",
			isResolved: true,
			label: humanize(fieldname),
		};
	if (["creation", "modified"].includes(fieldname))
		return { fieldname, fieldtype: "Datetime", isResolved: true, label: humanize(fieldname) };
	if (fieldname === "docstatus")
		return { fieldname, fieldtype: "Int", isResolved: true, label: "Docstatus" };

	const parts = String(fieldname).split(".");
	if (parts.length > 1) {
		let currentDoctype = doctype;
		let targetFieldtype = null;
		let isResolved = false;
		const formattedParts = [];

		for (let i = 0; i < parts.length; i++) {
			const part = parts[i];
			let df = null;

			if (currentDoctype) {
				if (metaMap && metaMap[currentDoctype]) {
					df = metaMap[currentDoctype].find((f) => f.fieldname === part);
				} else if (
					typeof frappe !== "undefined" &&
					frappe.meta?.has_field?.(currentDoctype, part)
				) {
					df = frappe.meta.get_docfield(currentDoctype, part);
				}
			}

			if (df) {
				const labelText = df.original_label || df.label || humanize(part);
				formattedParts.push(typeof __ === "function" ? __(labelText) : labelText);
				targetFieldtype = df.fieldtype;
				isResolved = true;
				if (["Link", "Table", "Table MultiSelect"].includes(df.fieldtype) && df.options) {
					currentDoctype = df.options;
				} else {
					currentDoctype = null;
				}
			} else {
				formattedParts.push(humanize(part));
				currentDoctype = null;
			}
		}

		return {
			fieldname,
			fieldtype: targetFieldtype || "Data",
			isResolved,
			label: formattedParts.join(" · "),
		};
	}

	const raw = String(fieldname).replace(/^doc\./, "");
	let df = null;
	if (doctype) {
		if (metaMap && metaMap[doctype]) {
			df = metaMap[doctype].find((f) => f.fieldname === raw);
		} else if (typeof frappe !== "undefined" && frappe.meta?.has_field?.(doctype, raw)) {
			df = frappe.meta.get_docfield(doctype, raw);
		}
	}

	if (df) {
		const labelText = df.original_label || df.label || humanize(raw);
		return {
			...df,
			fieldname,
			fieldtype: df.fieldtype,
			isResolved: true,
			label: typeof __ === "function" ? __(labelText) : labelText,
		};
	}

	return { fieldname, fieldtype: "Data", isResolved: false, label: humanize(raw) };
}

export function formatFilterSummary(node, doctype, metaMap = null) {
	if (!node || !node.field) {
		return {
			fieldLabel: "",
			operatorLabel: "",
			valueLabel: "",
			hasValue: false,
			isValid: false,
			invalidReason:
				typeof __ === "function"
					? __("Incomplete filter: select a field")
					: "Incomplete filter: select a field",
		};
	}

	const fieldDef = resolveFilterFieldDef(node.field, doctype, metaMap);
	const isValid = isFilterLeafValid(node, { fieldDef, doctype, metaMap });

	const fieldLabel = fieldDef?.label || humanize(node.field);

	const op = node.operator || "";
	let operatorLabel = op;
	const fieldtype = getFieldType(fieldDef);

	if (["Date", "Datetime"].includes(fieldtype)) {
		const dateLabels = {
			"<": "is before",
			">": "is after",
			"<=": "is on or before",
			">=": "is on or after",
		};
		if (dateLabels[op]) {
			operatorLabel = typeof __ === "function" ? __(dateLabels[op]) : dateLabels[op];
		} else if (OPERATOR_LABELS[op]) {
			operatorLabel =
				typeof __ === "function" ? __(OPERATOR_LABELS[op]) : OPERATOR_LABELS[op];
		}
	} else if (OPERATOR_LABELS[op]) {
		operatorLabel = typeof __ === "function" ? __(OPERATOR_LABELS[op]) : OPERATOR_LABELS[op];
	}

	let valueLabel = "";
	const value = node.value;

	if (String(op).toLowerCase() === "is") {
		const raw = typeof value === "object" && value?.mode === "static" ? value.value : value;
		if (typeof raw === "string" && ["set", "not set"].includes(raw.trim().toLowerCase())) {
			valueLabel =
				raw.trim().toLowerCase() === "set"
					? typeof __ === "function"
						? __("Set")
						: "Set"
					: typeof __ === "function"
					? __("Not Set")
					: "Not Set";
		} else {
			valueLabel = formatSingleValue(value) || (typeof __ === "function" ? __("Set") : "Set");
		}
	} else if (op === "Between") {
		const arr = Array.isArray(value) ? value : [];
		const start = formatSingleValue(arr[0]);
		const end = formatSingleValue(arr[1]);
		if (start && end) {
			valueLabel =
				typeof __ === "function" ? __("{0} and {1}", [start, end]) : `${start} and ${end}`;
		} else {
			valueLabel = start || end || "";
		}
	} else {
		valueLabel = formatSingleValue(value);
	}

	let invalidReason = "";
	if (!isValid) {
		if (!node.field) {
			invalidReason =
				typeof __ === "function"
					? __("Incomplete filter: select a field")
					: "Incomplete filter: select a field";
		} else if (!node.operator) {
			invalidReason =
				typeof __ === "function"
					? __("Incomplete filter: select an operator")
					: "Incomplete filter: select an operator";
		} else {
			invalidReason =
				typeof __ === "function"
					? __("Incomplete filter: enter a value")
					: "Incomplete filter: enter a value";
		}
	}

	return {
		fieldLabel,
		operatorLabel,
		valueLabel,
		hasValue: Boolean(op),
		isValid,
		invalidReason,
	};
}
