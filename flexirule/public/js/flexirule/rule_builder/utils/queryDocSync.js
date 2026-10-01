/**
 * Query Doc two-way field synchronization and initialization helper.
 */

export function cloneValue(val) {
	if (val === null || val === undefined) return val;
	if (typeof val === "object") {
		try {
			return JSON.parse(JSON.stringify(val));
		} catch (e) {
			return val;
		}
	}
	return val;
}

export function isPopulated(val) {
	if (val === null || val === undefined || val === "") return false;
	if (typeof val === "object") {
		if (Object.keys(val).length === 0) return false;
		if (
			val.mode === "static" &&
			(val.value === null || val.value === undefined || val.value === "")
		) {
			return false;
		}
		if (
			val.mode === "expression" &&
			(val.value === null || val.value === undefined || val.value === "")
		) {
			return false;
		}
	}
	return true;
}

export function isEqualValue(val1, val2) {
	if (val1 === val2) return true;
	if (!isPopulated(val1) && !isPopulated(val2)) return true;
	if (typeof val1 === "object" || typeof val2 === "object") {
		try {
			return JSON.stringify(val1) === JSON.stringify(val2);
		} catch (e) {
			return false;
		}
	}
	return String(val1 || "").trim() === String(val2 || "").trim();
}

/**
 * Reconciles reference_doctype/reference_docname with config.doctype_name/config.docname
 * for Query Records -> Query Doc node data based on deterministic precedence rules.
 */
export function reconcileQueryDocFields(data) {
	if (!data) return data;
	const actionType = data.action_type;
	const op = data.operation;
	if (actionType !== "Query Records" || op !== "Query Doc") return data;

	if (!data.config || typeof data.config !== "object") {
		data.config = {};
	}
	const config = data.config;

	// Reconcile Doctype
	const refDt = data.reference_doctype;
	const cfgDt = config.doctype_name;

	if (isPopulated(refDt) && !isPopulated(cfgDt)) {
		config.doctype_name = cloneValue(refDt);
	} else if (!isPopulated(refDt) && isPopulated(cfgDt)) {
		data.reference_doctype = cloneValue(cfgDt);
	} else if (isPopulated(refDt) && isPopulated(cfgDt)) {
		if (!isEqualValue(refDt, cfgDt)) {
			// Rule Action takes precedence
			config.doctype_name = cloneValue(refDt);
		}
	}

	// Reconcile Docname
	const refDn = data.reference_docname;
	const cfgDn = config.docname;

	if (isPopulated(refDn) && !isPopulated(cfgDn)) {
		config.docname = cloneValue(refDn);
	} else if (!isPopulated(refDn) && isPopulated(cfgDn)) {
		data.reference_docname = cloneValue(cfgDn);
	} else if (isPopulated(refDn) && isPopulated(cfgDn)) {
		if (!isEqualValue(refDn, cfgDn)) {
			// Rule Action takes precedence
			config.docname = cloneValue(refDn);
		}
	}

	return data;
}
