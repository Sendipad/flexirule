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
	const isSelectField = ["Select", "MultiSelect", "MultiSelectList"].includes(fieldType);

	// Resolve explicit metadata independently of the selected control so "auto" does not lose supplied metadata
	let options = explicit?.options !== undefined ? explicit.options : fieldOptions;
	let doctype = explicit?.doctype !== undefined ? explicit.doctype : referenceDoctype;
	let filters = explicit?.filters !== undefined ? explicit.filters : context?.filters || {};
	let placeholder =
		explicit?.placeholder !== undefined ? explicit.placeholder : context?.placeholder || "";

	// Determine control type
	let control = "input";

	if (explicit?.control && explicit.control !== "auto") {
		control = explicit.control;
	} else if (isMembershipOp) {
		// Membership operators require list-capable entry
		control = "multi-select";
	} else if (
		fieldType === "Link" ||
		fieldType === "Dynamic Link" ||
		(Boolean(explicit?.doctype) && !isSelectField)
	) {
		// Only Link field metadata (or an explicit non-Select DocType override) selects LinkControl.
		control = "link";
	} else if (
		isSelectField ||
		(Array.isArray(options) && options.length > 0) ||
		(typeof options === "string" && options.trim().length > 0)
	) {
		control =
			fieldType === "MultiSelect" || fieldType === "MultiSelectList"
				? "multi-select"
				: "select";
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
