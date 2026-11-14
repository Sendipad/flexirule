/**
 * Identify controls that must query remote DocType records.
 * MultiSelect is local by default; a supplied referenceDoctype is the explicit
 * signal for builder consumers that use it as a remote-record picker.
 */
export function isRemoteRecordFieldType(fieldType, referenceDoctype = "") {
	const type = String(fieldType || "");
	if (["Link", "Dynamic Link", "MultiSelectList"].includes(type)) return true;
	return type === "MultiSelect" && typeof referenceDoctype === "string" && !!referenceDoctype.trim();
}

/**
 * Resolve the target DocType of a Dynamic Link only from its controlling field's
 * actual value. Dynamic Link.options is a fieldname, never a DocType name.
 */
export function resolveDynamicLinkDoctype({ options, context = {}, engine = {} } = {}) {
	const targetField = typeof options === "string" ? options.trim() : "";
	if (!targetField) return "";

	for (const source of [context?.doc, engine?.doc]) {
		const value = source && typeof source === "object" ? source[targetField] : null;
		if (typeof value === "string" && value.trim()) return value.trim();
	}

	const controlContext = context?.controlContext;
	const contextValue =
		typeof controlContext?.getFieldValue === "function"
			? controlContext.getFieldValue(targetField)
			: null;
	if (contextValue && typeof contextValue === "object" && contextValue.mode === "static") {
		return String(contextValue.value || "").trim();
	}
	if (typeof contextValue === "string" && contextValue.trim()) return contextValue.trim();

	return typeof context?.dynamicDoctype === "string" ? context.dynamicDoctype.trim() : "";
}

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
