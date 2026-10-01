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

export function extractStringValue(val) {
	if (val === null || val === undefined) return "";
	if (typeof val === "string") return val;
	if (typeof val === "object") {
		if (val.value !== undefined && val.value !== null) {
			return String(val.value);
		}
	}
	return "";
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
	const s1 = extractStringValue(val1);
	const s2 = extractStringValue(val2);
	if (s1 === s2) {
		if (
			typeof val1 === "object" &&
			typeof val2 === "object" &&
			val1 !== null &&
			val2 !== null
		) {
			return val1.mode === val2.mode;
		}
		return true;
	}
	return false;
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
		data.reference_doctype = extractStringValue(refDt);
	} else if (!isPopulated(refDt) && isPopulated(cfgDt)) {
		data.reference_doctype = extractStringValue(cfgDt);
	} else if (isPopulated(refDt) && isPopulated(cfgDt)) {
		if (!isEqualValue(refDt, cfgDt)) {
			// Rule Action takes precedence
			config.doctype_name = cloneValue(refDt);
			data.reference_doctype = extractStringValue(refDt);
		} else {
			data.reference_doctype = extractStringValue(refDt);
		}
	} else {
		data.reference_doctype = "";
		config.doctype_name = cloneValue(cfgDt) || "";
	}

	// Reconcile Docname
	const refDn = data.reference_docname;
	const cfgDn = config.docname;

	if (isPopulated(refDn) && !isPopulated(cfgDn)) {
		config.docname = cloneValue(refDn);
		data.reference_docname = extractStringValue(refDn);
	} else if (!isPopulated(refDn) && isPopulated(cfgDn)) {
		data.reference_docname = extractStringValue(cfgDn);
	} else if (isPopulated(refDn) && isPopulated(cfgDn)) {
		if (!isEqualValue(refDn, cfgDn)) {
			// Rule Action takes precedence
			config.docname = cloneValue(refDn);
			data.reference_docname = extractStringValue(refDn);
		} else {
			data.reference_docname = extractStringValue(refDn);
		}
	} else {
		data.reference_docname = "";
		config.docname = cloneValue(cfgDn) || "";
	}

	return data;
}
