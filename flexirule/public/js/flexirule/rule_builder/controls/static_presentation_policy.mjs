/**
 * Pure ES module defining the static input presentation resolution policy.
 * Precedence:
 * 1. Explicit staticPresentation prop
 * 2. context.staticPresentation
 * 3. Operator-specific presentation (e.g. membership -> multi-select)
 * 4. Resolved field metadata
 * 5. Safe generic fallback (input)
 */

export function resolveStaticPresentation({
	staticPresentation = null,
	context = {},
	fieldType = "Data",
	fieldOptions = [],
	referenceDoctype = "",
} = {}) {
	const explicit = staticPresentation || context?.staticPresentation || null;

	const op = String(context?.operator || "").toLowerCase();
	const isMembershipOp = ["in", "not in", "not_in", "in list", "not in list"].includes(op);

	// Determine control type
	let control = "input";
	let options = fieldOptions;
	let doctype = referenceDoctype;
	let filters = context?.filters || {};
	let placeholder = context?.placeholder || "";

	if (explicit?.control && explicit.control !== "auto") {
		control = explicit.control;
		if (explicit.options !== undefined) options = explicit.options;
		if (explicit.doctype !== undefined) doctype = explicit.doctype;
		if (explicit.filters !== undefined) filters = explicit.filters;
		if (explicit.placeholder !== undefined) placeholder = explicit.placeholder;
	} else if (isMembershipOp) {
		// Only use multi-select (option-picker) when a real option source exists (Link, Select, or explicitly provided options)
		const hasOptions =
			(Array.isArray(options) && options.length > 0) ||
			(typeof options === "string" && options.trim().length > 0) ||
			Boolean(doctype) ||
			["Select", "Link", "Dynamic Link", "MultiSelect", "MultiSelectList"].includes(
				fieldType
			);

		control = hasOptions ? "multi-select" : "input";
	} else if (
		fieldType === "Select" ||
		fieldType === "MultiSelect" ||
		fieldType === "MultiSelectList"
	) {
		control = fieldType === "Select" ? "select" : "multi-select";
	} else if (fieldType === "Link" || fieldType === "Dynamic Link") {
		control = "link";
	} else {
		control = "input";
	}

	return {
		control,
		options,
		doctype,
		filters,
		placeholder,
		isMultiSelect: control === "multi-select",
		isLink: control === "link",
		isSelect: control === "select",
	};
}
